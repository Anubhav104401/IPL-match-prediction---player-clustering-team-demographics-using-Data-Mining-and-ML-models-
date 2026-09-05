"""
Data access layer.

Every read the UI performs goes through this module: paths are anchored to the
project root (so the app runs from any working directory), results are cached
by Streamlit, and each loader degrades to ``None`` rather than raising when a
pipeline artefact has not been generated yet. Views render an empty state in
that case instead of a traceback.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DATASETS = ROOT / "datasets"
WAREHOUSE = ROOT / "ipl_warehouse.db"
PLOTS = ROOT / "plots"

# Ordered by preference — the enriched file is a superset of the raw stats.
_PLAYER_SOURCES = (
    DATASETS / "advanced_player_clusters.csv",
    DATASETS / "enriched_player_stats.csv",
    DATASETS / "player_stats.csv",
)


# ──────────────────────────────────────────────────────────────────────────────
#  Loaders
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_players() -> pd.DataFrame | None:
    """Player-level stats with cluster assignments, if clustering has been run."""
    for path in _PLAYER_SOURCES:
        if path.exists():
            return pd.read_csv(path)
    return None


@st.cache_data(show_spinner=False)
def load_matches() -> pd.DataFrame | None:
    """The raw match ledger — one row per IPL fixture."""
    path = DATASETS / "matches.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def load_enriched_matches() -> pd.DataFrame | None:
    """Engineered match features (form, head-to-head, venue win rates)."""
    path = DATASETS / "enriched_match_features.csv"
    return pd.read_csv(path) if path.exists() else None


@st.cache_data(show_spinner=False)
def load_predictions() -> pd.DataFrame | None:
    """Held-out predictions written by the classification stage."""
    for name in ("match_predictions_advanced.csv", "match_predictions.csv"):
        path = DATASETS / name
        if path.exists():
            return pd.read_csv(path)
    root_level = ROOT / "match_predictions.csv"
    return pd.read_csv(root_level) if root_level.exists() else None


def warehouse() -> sqlite3.Connection | None:
    """Open a read-only-ish connection to the star schema, or ``None``."""
    if not WAREHOUSE.exists():
        return None
    return sqlite3.connect(str(WAREHOUSE), check_same_thread=False)


@st.cache_data(show_spinner=False)
def warehouse_query(sql: str) -> pd.DataFrame | None:
    """Run an OLAP query against the warehouse, caching the result frame."""
    conn = warehouse()
    if conn is None:
        return None
    try:
        return pd.read_sql(sql, conn)
    except Exception:
        return None
    finally:
        conn.close()


@st.cache_data(show_spinner=False)
def warehouse_counts() -> dict[str, int]:
    """Row counts for each dimension and fact table."""
    conn = warehouse()
    if conn is None:
        return {}
    counts: dict[str, int] = {}
    try:
        for table in ("dim_date", "dim_team", "dim_venue", "dim_player", "fact_matches"):
            try:
                counts[table] = int(
                    pd.read_sql(f"SELECT COUNT(*) AS n FROM {table}", conn).iloc[0, 0]
                )
            except Exception:
                counts[table] = 0
    finally:
        conn.close()
    return counts


# ──────────────────────────────────────────────────────────────────────────────
#  Derived views
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def team_wins() -> pd.DataFrame:
    """Career win totals per franchise, most successful first."""
    matches = load_matches()
    if matches is None:
        return pd.DataFrame(columns=["Team", "Wins"])
    wins = matches.dropna(subset=["winner"])["winner"].value_counts().reset_index()
    wins.columns = ["Team", "Wins"]
    return wins


@st.cache_data(show_spinner=False)
def team_record() -> pd.DataFrame:
    """Played / won / win-rate per franchise."""
    matches = load_matches()
    if matches is None:
        return pd.DataFrame(columns=["Team", "Played", "Wins", "Win %"])

    played = pd.concat([matches["team1"], matches["team2"]]).value_counts()
    won = matches.dropna(subset=["winner"])["winner"].value_counts()

    record = pd.DataFrame({"Played": played, "Wins": won}).fillna(0).astype(int)
    record["Win %"] = (record["Wins"] / record["Played"].replace(0, np.nan) * 100).round(1)
    return record.reset_index(names="Team").sort_values("Wins", ascending=False)


@st.cache_data(show_spinner=False)
def season_timeline() -> pd.DataFrame:
    """Matches, average winning margin and total runs chased, per season."""
    matches = load_matches()
    if matches is None or "season" not in matches.columns:
        return pd.DataFrame(columns=["Season", "Matches"])

    grouped = matches.groupby("season", dropna=True)
    out = pd.DataFrame({
        "Matches": grouped.size(),
        "Avg margin": grouped["result_margin"].mean().round(1),
        "Avg target": grouped["target_runs"].mean().round(0),
    }).reset_index(names="Season")
    out["Season"] = out["Season"].astype(str)
    return out.sort_values("Season")


@st.cache_data(show_spinner=False)
def head_to_head(top_n: int = 10) -> tuple[np.ndarray, list[str]]:
    """Win-percentage matrix among the ``top_n`` winningest franchises.

    Cell ``[i, j]`` is the share of completed meetings that team *i* won against
    team *j*. The diagonal is NaN so it renders as a gap, not a 50% cell.
    """
    matches = load_matches()
    if matches is None:
        return np.zeros((0, 0)), []

    decided = matches.dropna(subset=["winner"])
    teams = team_wins().head(top_n)["Team"].tolist()
    index = {team: i for i, team in enumerate(teams)}

    wins = np.zeros((len(teams), len(teams)))
    played = np.zeros((len(teams), len(teams)))

    subset = decided[decided["team1"].isin(index) & decided["team2"].isin(index)]
    for t1, t2, winner in zip(subset["team1"], subset["team2"], subset["winner"]):
        i, j = index[t1], index[t2]
        played[i, j] += 1
        played[j, i] += 1
        if winner == t1:
            wins[i, j] += 1
        elif winner == t2:
            wins[j, i] += 1

    with np.errstate(divide="ignore", invalid="ignore"):
        pct = np.where(played > 0, wins / played * 100, np.nan)
    np.fill_diagonal(pct, np.nan)
    return pct, teams


@st.cache_data(show_spinner=False)
def pca_projection(feature_cols: tuple[str, ...]) -> pd.DataFrame | None:
    """Project players into two dimensions for the cluster scatter.

    Returns the player frame with ``PC1``/``PC2`` columns appended, plus the
    explained-variance ratio stored in ``df.attrs['explained']``.
    """
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    df = load_players()
    if df is None:
        return None

    available = [c for c in feature_cols if c in df.columns]
    if len(available) < 2:
        return None

    matrix = StandardScaler().fit_transform(df[available].fillna(0))
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(matrix)

    out = df.copy()
    out["PC1"], out["PC2"] = coords[:, 0], coords[:, 1]
    out.attrs["explained"] = float(pca.explained_variance_ratio_.sum() * 100)
    out.attrs["features"] = available
    return out


@st.cache_data(show_spinner=False)
def venue_leaders(limit: int = 8) -> pd.DataFrame:
    """Busiest venues by matches hosted."""
    matches = load_matches()
    if matches is None or "venue" not in matches.columns:
        return pd.DataFrame(columns=["Venue", "Matches"])
    counts = matches["venue"].value_counts().head(limit).reset_index()
    counts.columns = ["Venue", "Matches"]
    return counts


@st.cache_data(show_spinner=False)
def toss_advantage() -> tuple[float, int]:
    """Share of matches the toss winner also won, and the sample size."""
    matches = load_matches()
    if matches is None:
        return 0.0, 0
    decided = matches.dropna(subset=["winner", "toss_winner"])
    if decided.empty:
        return 0.0, 0
    agreed = (decided["toss_winner"] == decided["winner"]).mean() * 100
    return round(float(agreed), 1), int(len(decided))


# ──────────────────────────────────────────────────────────────────────────────
#  Pipeline introspection
# ──────────────────────────────────────────────────────────────────────────────

def pipeline_status() -> list[tuple[str, bool]]:
    """Which stage outputs exist on disk — drives the sidebar status readout."""
    return [
        ("Raw data", (DATASETS / "matches.csv").exists()),
        ("Features", (DATASETS / "enriched_match_features.csv").exists()),
        ("Clusters", (DATASETS / "advanced_player_clusters.csv").exists()),
        ("Predictions", load_predictions() is not None),
        ("Warehouse", WAREHOUSE.exists()),
    ]


def corpus_summary() -> dict[str, float | int | str]:
    """Headline counts used by the overview hero and stat strip."""
    matches = load_matches()
    players = load_players()

    if matches is None:
        return {}

    seasons = matches["season"].nunique() if "season" in matches.columns else 0
    span = ""
    if "season" in matches.columns and not matches["season"].isna().all():
        ordered = sorted(str(s) for s in matches["season"].dropna().unique())
        span = f"{ordered[0]} – {ordered[-1]}"

    return {
        "matches": int(len(matches)),
        "seasons": int(seasons),
        "span": span,
        "teams": int(pd.concat([matches["team1"], matches["team2"]]).nunique()),
        "venues": int(matches["venue"].nunique()) if "venue" in matches.columns else 0,
        "cities": int(matches["city"].nunique()) if "city" in matches.columns else 0,
        "players": int(len(players)) if players is not None else 0,
        "clusters": (
            int(players["cluster_label"].nunique())
            if players is not None and "cluster_label" in players.columns
            else 0
        ),
    }
