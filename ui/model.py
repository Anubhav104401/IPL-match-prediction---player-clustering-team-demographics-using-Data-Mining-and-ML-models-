"""
Prediction model.

The original dashboard retrained a gradient-boosting classifier on every button
press, which cost several seconds per prediction. Training now happens once per
session behind ``st.cache_resource``; each prediction is a single
``predict_proba`` call on a prepared row.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import streamlit as st

# Numeric features produced by feature_engineering.py.
#
# ``toss_winner_won`` is deliberately excluded. In the engineered dataset it is
# exactly ``(toss_winner == winner)`` — the label restated — and pairing it with
# the one-hot ``toss_winner`` column lets the classifier read the answer off the
# input. It inflates held-out accuracy from ~54% to ~96% and, worse, it cannot
# be known before a match is played: at inference the toss winner is always one
# of the two sides, so the feature is pinned to 1 and the model simply predicts
# whoever won the toss, at ~100% confidence. Excluding it is what makes the
# numbers on the prediction page mean anything.
NUMERIC = (
    "h2h_team1_win_pct", "avg_runs_per_match",
    "venue_win_pct_team1", "venue_win_pct_team2",
    "form_team1", "form_team2",
)

#: Columns present in the source data that must never be fed to the model.
LEAKING = ("toss_winner_won",)

CATEGORICAL = ("team1", "team2", "toss_winner", "toss_decision", "venue")

# Franchises with fewer wins than this are dropped: the classifier cannot learn
# a class it has seen a handful of times, and their presence dilutes accuracy.
MIN_WINS = 10


@dataclass
class TrainedModel:
    """A fitted classifier plus everything needed to score a new fixture."""

    estimator: object
    classes: np.ndarray
    columns: pd.Index
    accuracy: float
    n_train: int
    numeric: tuple[str, ...]
    categorical: tuple[str, ...]
    medians: dict[str, float] = field(default_factory=dict)

    def prepare_row(
        self, team1: str, team2: str, venue: str, toss_winner: str, toss_decision: str
    ) -> pd.DataFrame:
        """Build a single one-hot encoded row matching the training columns."""
        row = pd.DataFrame(0.0, index=[0], columns=self.columns)

        for column in self.numeric:
            row[column] = self.medians.get(column, 50.0)

        for prefix, value in (
            ("team1_", team1), ("team2_", team2), ("toss_winner_", toss_winner),
            ("toss_decision_", toss_decision), ("venue_", venue),
        ):
            name = f"{prefix}{value}"
            if name in row.columns:
                row[name] = 1.0

        return row

    def predict(
        self, team1: str, team2: str, venue: str, toss_winner: str, toss_decision: str
    ) -> dict:
        """Score a fixture, returning the winner, confidence and full distribution."""
        proba = self.estimator.predict_proba(self.prepare_row(
            team1, team2, venue, toss_winner, toss_decision
        ))[0]

        distribution = {str(cls): float(p * 100) for cls, p in zip(self.classes, proba)}

        # The two named sides are the only plausible winners of this fixture, so
        # renormalise over them — a raw multiclass model will happily assign
        # probability mass to teams that are not playing.
        contenders = {t: distribution.get(t, 0.0) for t in (team1, team2) if t in distribution}
        if contenders and sum(contenders.values()) > 0:
            total = sum(contenders.values())
            head_to_head = {t: v / total * 100 for t, v in contenders.items()}
        else:
            head_to_head = {team1: 50.0, team2: 50.0}

        winner = max(head_to_head, key=head_to_head.get)
        return {
            "winner": winner,
            "confidence": head_to_head[winner],
            "head_to_head": head_to_head,
            "distribution": distribution,
            "accuracy": self.accuracy,
        }


@st.cache_resource(show_spinner=False)
def train(_signature: str = "v3-regularised") -> TrainedModel | None:
    """Fit the classifier once per session. ``_signature`` busts the cache."""
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder

    from ui.data import load_enriched_matches

    enriched = load_enriched_matches()
    if enriched is None or "winner" not in enriched.columns:
        return None

    df = enriched.copy()
    counts = df["winner"].value_counts()
    df = df[df["winner"].isin(counts[counts >= MIN_WINS].index)]
    if df.empty:
        return None

    numeric = tuple(c for c in NUMERIC if c in df.columns and c not in LEAKING)
    categorical = tuple(c for c in CATEGORICAL if c in df.columns)

    encoded = pd.get_dummies(df[list(categorical)], columns=list(categorical))
    X = pd.concat(
        [df[list(numeric)].reset_index(drop=True), encoded.reset_index(drop=True)], axis=1
    ).fillna(0)

    encoder = LabelEncoder()
    y = encoder.fit_transform(df["winner"])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if min(np.bincount(y)) >= 2 else None
    )

    # Deliberately regularised. The original depth-5 / 150-tree configuration
    # saturated its probabilities against a few hundred one-hot columns: 77% of
    # held-out predictions came back above 0.9 confidence while the model was
    # only right 56% of the time. Shallow trees with a low learning rate and
    # row subsampling score better *and* produce probabilities worth reading —
    # accuracy 56% -> 62%, log-loss 2.38 -> 0.74.
    estimator = GradientBoostingClassifier(
        n_estimators=80,
        max_depth=2,
        learning_rate=0.05,
        subsample=0.7,
        random_state=42,
    )
    estimator.fit(X_train, y_train)

    return TrainedModel(
        estimator=estimator,
        classes=encoder.classes_,
        columns=X.columns,
        accuracy=float(estimator.score(X_test, y_test) * 100),
        n_train=int(len(X_train)),
        numeric=numeric,
        categorical=categorical,
        medians={c: float(df[c].median()) for c in numeric if df[c].notna().any()},
    )


@st.cache_data(show_spinner=False)
def fixture_history(team1: str, team2: str) -> dict:
    """Historical head-to-head record between two sides, for context."""
    from ui.data import load_matches

    matches = load_matches()
    if matches is None:
        return {}

    meetings = matches[
        ((matches["team1"] == team1) & (matches["team2"] == team2))
        | ((matches["team1"] == team2) & (matches["team2"] == team1))
    ].dropna(subset=["winner"])

    if meetings.empty:
        return {"played": 0}

    wins = meetings["winner"].value_counts()
    return {
        "played": int(len(meetings)),
        team1: int(wins.get(team1, 0)),
        team2: int(wins.get(team2, 0)),
    }
