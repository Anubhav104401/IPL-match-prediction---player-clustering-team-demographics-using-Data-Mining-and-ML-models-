"""
Prediction — the interactive showpiece.

Pick a fixture and the page answers with a verdict: who wins, how confident the
model is, what the historical record says, and how much of that confidence you
should actually trust given the model's held-out accuracy.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui import brand, charts, components as ui, data, model as ml
from ui.tokens import ACCENT


def render() -> None:
    matches = data.load_matches()
    enriched = data.load_enriched_matches()

    if matches is None or enriched is None:
        ui.hero("Match prediction", "Engineered features are missing.", eyebrow="Predict")
        ui.empty_state(
            "No engineered features",
            "datasets/enriched_match_features.csv has not been generated. The classifier "
            "trains on form, head-to-head and venue win rates produced by that stage.",
            "python feature_engineering.py",
        )
        return

    teams = sorted(set(matches["team1"].dropna()) | set(matches["team2"].dropna()))
    venues = sorted(matches["venue"].dropna().unique())

    ui.hero(
        "Set a fixture, get a verdict",
        "A gradient-boosting classifier trained on head-to-head history, recent form "
        "and venue record — using only what is knowable before the first ball. "
        "Probabilities are renormalised over the two sides actually playing, so the "
        "number you read is a real head-to-head confidence.",
        eyebrow="Predict · Classification",
        pills=[
            ui.pill(f"{len(teams)} selectable sides", ACCENT["cyan"]),
            ui.pill(f"{len(venues)} venues"),
            ui.pill("Gradient boosting · 80 trees, depth 2", ACCENT["violet"]),
        ],
        accent=ACCENT["amber"],
        accent_2=ACCENT["rose"],
    )

    # ── Fixture setup ─────────────────────────────────────────────────────────
    ui.section("Fixture", "Choose the two sides, the ground and the toss", "01")

    col_a, col_b, col_c = st.columns(3, gap="medium")

    with col_a:
        team1 = st.selectbox("Home side", teams, index=0, key="pred_team1")
    with col_b:
        opponents = [t for t in teams if t != team1] or teams
        team2 = st.selectbox("Away side", opponents, index=0, key="pred_team2")
    with col_c:
        venue = st.selectbox("Venue", venues, index=0, key="pred_venue")

    col_d, col_e = st.columns(2, gap="medium")
    with col_d:
        toss_winner = st.selectbox("Toss won by", [team1, team2], index=0, key="pred_toss")
    with col_e:
        toss_decision = st.selectbox("Elected to", ["field", "bat"], index=0, key="pred_decision")

    ui.versus(team1, team2, venue)

    # ── Historical context, available before any prediction ───────────────────
    history = ml.fixture_history(team1, team2)
    if history.get("played"):
        w1, w2 = history.get(team1, 0), history.get(team2, 0)
        ui.stat_grid([
            ui.stat("Previous meetings", str(history["played"]), icon="◈",
                    note="completed matches on record", accent=ACCENT["cyan"],
                    count_to=history["played"]),
            ui.stat(f"{brand.code(team1)} wins", str(w1), icon="★",
                    note=f"{w1 / history['played'] * 100:.0f}% of meetings",
                    accent=brand.color(team1), count_to=w1),
            ui.stat(f"{brand.code(team2)} wins", str(w2), icon="★",
                    note=f"{w2 / history['played'] * 100:.0f}% of meetings",
                    accent=brand.color(team2), count_to=w2),
        ])
    else:
        ui.insight(
            f"<strong>{team1}</strong> and <strong>{team2}</strong> have never met in this "
            "dataset. The model will fall back on each side's form and venue record, so treat "
            "the confidence below with more caution than usual.",
            tone="warning",
        )

    # ── Run it ────────────────────────────────────────────────────────────────
    st.write("")
    go = st.button("Run prediction", type="primary", width="stretch")

    if not go:
        ui.insight(
            "The classifier trains once per session and is cached — the first run takes a "
            "few seconds, every run after that is instant.",
            tone="neutral",
        )
        return

    with st.spinner("Training the classifier and scoring the fixture…"):
        trained = ml.train()

    if trained is None:
        ui.empty_state("Model could not be trained",
                       "The engineered feature set has too few labelled matches.",
                       "python feature_engineering.py")
        return

    result = trained.predict(team1, team2, venue, toss_winner, toss_decision)

    # ── Verdict ───────────────────────────────────────────────────────────────
    ui.section("Verdict", "Model output for this fixture", "02")

    winner = result["winner"]
    loser = team2 if winner == team1 else team1

    ui.verdict(
        winner,
        result["confidence"],
        meta_pills=[
            ui.pill(f"over {brand.code(loser)}", brand.color(loser)),
            ui.pill(f"held-out accuracy {result['accuracy']:.1f}%", ACCENT["violet"]),
            ui.pill(f"trained on {trained.n_train:,} matches"),
            ui.pill(f"toss: {brand.code(toss_winner)} → {toss_decision}", ACCENT["amber"]),
        ],
    )

    split_col, field_col = st.columns([2, 3], gap="medium")

    with split_col:
        pair = result["head_to_head"]
        ui.rank_list(
            sorted(pair.items(), key=lambda kv: kv[1], reverse=True),
            colors=[brand.color(t) for t in sorted(pair, key=pair.get, reverse=True)],
            prefixes=[ui.crest(t, "sm") for t in sorted(pair, key=pair.get, reverse=True)],
            decimals=1,
            suffix="%",
        )
        st.caption("Head-to-head probability, renormalised over the two sides playing.")

    with field_col:
        distribution = result["distribution"]
        top = sorted(distribution.items(), key=lambda kv: kv[1], reverse=True)[:8]
        frame = pd.DataFrame(top, columns=["Team", "Probability"])
        frame["Code"] = [brand.code(t) for t in frame["Team"]]
        fig = charts.ranked_bar(
            frame, "Code", "Probability",
            color_map={brand.code(t): brand.color(t) for t in frame["Team"]},
            height=330,
            label_fmt="%{y:.1f}%",
        )
        fig.update_layout(title="Raw multiclass output, before renormalising")
        st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

    # ── Honest framing ────────────────────────────────────────────────────────
    confidence = result["confidence"]
    if confidence >= 65:
        tone, verdict_word = "success", "a clear lean"
    elif confidence >= 55:
        tone, verdict_word = "info", "a slight lean"
    else:
        tone, verdict_word = "warning", "essentially a coin flip"

    ui.insight(
        f"The model gives <strong>{winner}</strong> a <strong>{confidence:.1f}%</strong> "
        f"head-to-head probability — {verdict_word}. Its held-out accuracy is "
        f"<strong>{result['accuracy']:.1f}%</strong> across all classes, so a confident-looking "
        "number is not the same as a reliable one. T20 cricket is high-variance by "
        "construction: a single over can invert the result.",
        tone=tone,
    )

    ui.insight(
        "An earlier version of this model scored around <strong>96%</strong> — because "
        "its feature set included <code>toss_winner_won</code>, which is simply "
        "<em>did the toss winner win the match</em>: the label, restated. It is excluded "
        "here, and the honest number is what you see above. A leaking feature is not a "
        "good model; it is a broken evaluation.",
        tone="warning",
    )
