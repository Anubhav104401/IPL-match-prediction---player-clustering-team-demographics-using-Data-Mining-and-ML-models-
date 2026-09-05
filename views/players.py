"""
Players — archetype discovery.

The KMeans clustering is the analytical centrepiece of this project, so the page
is built around making the clusters *legible*: a PCA map you can filter, a radar
that says what each archetype actually is, and leaderboards that let a reader
find the player they came for.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui import brand, charts, components as ui, data
from ui.tokens import ACCENT

# Features fed to PCA — the same numeric space the clustering stage works in.
FEATURES = (
    "total_runs", "strike_rate", "batting_average", "fours", "sixes",
    "dot_ball_pct", "wickets_taken", "economy_rate", "all_rounder_score",
)

# Radar axes: (column, display name, higher-is-better)
RADAR_AXES = (
    ("total_runs", "Runs", True),
    ("strike_rate", "Strike rate", True),
    ("batting_average", "Average", True),
    ("sixes", "Six hitting", True),
    ("wickets_taken", "Wickets", True),
    ("economy_rate", "Economy", False),
)

LEADERBOARDS = (
    ("Run scorers", "total_runs", "runs", ACCENT["rose"], 0),
    ("Strike rate", "strike_rate", "SR", ACCENT["amber"], 1),
    ("Wicket takers", "wickets_taken", "wkts", ACCENT["violet"], 0),
    ("All-rounders", "all_rounder_score", "pts", ACCENT["lime"], 1),
)


def render() -> None:
    df = data.load_players()

    if df is None:
        ui.hero("Player archetypes", "Clustering output not found.", eyebrow="Players")
        ui.empty_state(
            "No cluster data",
            "The clustering stage has not written datasets/advanced_player_clusters.csv yet.",
            "python clustering.py",
        )
        return

    has_clusters = "cluster_label" in df.columns
    projected = data.pca_projection(FEATURES)
    explained = projected.attrs.get("explained", 0.0) if projected is not None else 0.0

    # ── Hero ──────────────────────────────────────────────────────────────────
    archetypes = sorted(df["cluster_label"].dropna().unique()) if has_clusters else []
    ui.hero(
        "Every player, placed by how they actually play",
        "KMeans over nine batting and bowling features, projected into two "
        "principal components. Position on this map is behaviour, not reputation — "
        "two players sit close together because their numbers rhyme.",
        eyebrow="Players · Clustering",
        pills=[ui.pill(f"{len(df):,} players", ACCENT["cyan"])]
        + [ui.pill(f"{brand.cluster_glyph(a)}  {a}", brand.cluster_color(a)) for a in archetypes],
        accent=ACCENT["lime"],
        accent_2=ACCENT["cyan"],
    )

    # ── Headline counts ───────────────────────────────────────────────────────
    tiles = [
        ui.stat("Players", f"{len(df):,}", icon="◆", note="with at least one innings",
                accent=ACCENT["cyan"], count_to=len(df)),
        ui.stat("Archetypes", str(len(archetypes) or "—"), icon="✦",
                note="discovered by KMeans", accent=ACCENT["lime"],
                count_to=len(archetypes) or None),
    ]
    if "strike_rate" in df.columns:
        tiles.append(ui.stat("Median strike rate", f"{df['strike_rate'].median():.1f}",
                             icon="▲", note="runs per 100 balls", accent=ACCENT["amber"],
                             count_to=float(df["strike_rate"].median()), decimals=1))
    if "all_rounder_score" in df.columns:
        best = df.nlargest(1, "all_rounder_score").iloc[0]
        tiles.append(ui.stat("Top all-rounder", f"{best['all_rounder_score']:.1f}",
                             icon="★", note=str(best["player"]), accent=ACCENT["violet"],
                             count_to=float(best["all_rounder_score"]), decimals=1))
    tiles.append(ui.stat("Variance captured", f"{explained:.1f}", unit="%", icon="◎",
                         note="by the two components below", accent=ACCENT["rose"],
                         count_to=explained, decimals=1))
    ui.stat_grid(tiles)

    # ── PCA map ───────────────────────────────────────────────────────────────
    ui.section("Archetype map", "Principal component projection of the feature space", "01")

    if projected is None:
        ui.empty_state("Not enough numeric features",
                       "At least two of the clustering features are missing from this dataset.")
    else:
        controls, _ = st.columns([2, 3])
        with controls:
            if has_clusters:
                chosen = st.multiselect(
                    "Show archetypes",
                    archetypes,
                    default=archetypes,
                    key="player_clusters",
                )
            else:
                chosen = []

        plot_df = projected
        if has_clusters and chosen:
            plot_df = projected[projected["cluster_label"].isin(chosen)]

        hover = [c for c in ("player", "total_runs", "strike_rate", "wickets_taken")
                 if c in plot_df.columns]

        fig = charts.cluster_scatter(
            plot_df, "PC1", "PC2",
            "cluster_label" if has_clusters else None,
            hover,
            color_map=brand.cluster_color_map(archetypes) if has_clusters else None,
        )
        fig.update_layout(title="Player clusters — PCA projection")
        st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

        ui.insight(
            f"These two components retain <strong>{explained:.1f}%</strong> of the variance "
            f"across {len(projected.attrs.get('features', []))} standardised features. "
            "Clusters that overlap on this plot are not necessarily overlapping in the "
            "full feature space — the projection is a summary, not the model.",
            tone="neutral",
        )

    # ── Archetype profiles ────────────────────────────────────────────────────
    if has_clusters:
        ui.section("What each archetype is", "Cluster means, scaled across the squad", "02")

        radar_col, split_col = st.columns([3, 2], gap="medium")

        with radar_col:
            axes = [(col, name, better) for col, name, better in RADAR_AXES if col in df.columns]
            if len(axes) >= 3:
                means = df.groupby("cluster_label")[[c for c, _, _ in axes]].mean()
                scaled = pd.DataFrame(index=means.index)
                for col, name, higher_better in axes:
                    lo, hi = df[col].min(), df[col].max()
                    span = (hi - lo) or 1
                    norm = (means[col] - lo) / span * 100
                    scaled[name] = norm if higher_better else 100 - norm

                series = [
                    (str(label), scaled.loc[label].tolist(), brand.cluster_color(str(label)))
                    for label in scaled.index
                ]
                fig = charts.radar([name for _, name, _ in axes], series, height=420)
                fig.update_layout(title="Archetype fingerprints")
                st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

        with split_col:
            counts = df["cluster_label"].value_counts()
            fig = charts.donut(
                counts.index.tolist(),
                counts.tolist(),
                [brand.cluster_color(str(i)) for i in counts.index],
                center=f"{len(df):,}<br><span style='font-size:11px'>players</span>",
                height=420,
            )
            fig.update_layout(title="Squad composition", showlegend=True)
            st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

        largest = df["cluster_label"].value_counts()
        ui.insight(
            f"<strong>{largest.index[0]}</strong> is the largest group at "
            f"<strong>{largest.iloc[0]}</strong> players "
            f"({largest.iloc[0] / len(df) * 100:.0f}% of the squad). On the radar, "
            "economy rate is inverted so that further from the centre is always better — "
            "a bigger polygon is a more complete cricketer.",
            tone="success",
        )

    # ── Leaderboards ──────────────────────────────────────────────────────────
    ui.section("Leaderboards", "Top twenty on each dimension", "03")

    available = [(t, col, unit, colour, dp) for t, col, unit, colour, dp in LEADERBOARDS
                 if col in df.columns]

    if available:
        tabs = st.tabs([title for title, *_ in available])
        for tab, (title, column, unit, colour, decimals) in zip(tabs, available):
            with tab:
                # Guard against tiny-sample noise on rate statistics.
                pool = df
                if column in ("strike_rate", "all_rounder_score") and "balls_faced" in df.columns:
                    pool = df[df["balls_faced"] >= 200]
                    if pool.empty:
                        pool = df

                top = pool.nlargest(12, column)
                bars, table = st.columns([2, 3], gap="medium")

                with bars:
                    ui.rank_list(
                        list(zip(top["player"], top[column])),
                        colors=[colour] * len(top),
                        decimals=decimals,
                        suffix=f" {unit}",
                    )

                with table:
                    # Only the columns that fit legibly in this width: the
                    # identity, the metric being ranked, and enough context to
                    # judge it. The full frame is a click away in the raw CSV.
                    wanted = ["player", column, "cluster_label"]
                    for extra in ("total_runs", "strike_rate", "wickets_taken",
                                  "all_rounder_score"):
                        if extra not in wanted:
                            wanted.append(extra)
                    cols = [c for c in wanted if c in top.columns][:6]
                    st.dataframe(
                        top[cols],
                        width="stretch",
                        hide_index=True,
                        column_config={
                            "player": st.column_config.TextColumn("Player", width="medium"),
                            "total_runs": st.column_config.NumberColumn("Runs", format="%d"),
                            "strike_rate": st.column_config.ProgressColumn(
                                "Strike rate", format="%.1f",
                                min_value=0, max_value=float(df["strike_rate"].max())
                                if "strike_rate" in df.columns else 200,
                            ),
                            "batting_average": st.column_config.NumberColumn("Avg", format="%.1f"),
                            "wickets_taken": st.column_config.NumberColumn("Wkts", format="%d"),
                            "economy_rate": st.column_config.NumberColumn("Econ", format="%.2f"),
                            "all_rounder_score": st.column_config.NumberColumn("AR score", format="%.1f"),
                            "cluster_label": st.column_config.TextColumn("Archetype"),
                        },
                    )

                if column in ("strike_rate", "all_rounder_score") and "balls_faced" in df.columns:
                    st.caption(
                        "Filtered to players with at least 200 balls faced — rate statistics "
                        "are meaningless on a handful of deliveries."
                    )
