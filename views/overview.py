"""
Overview — the landing page.

Answers "what is this and what's in it?" before the reader touches a control:
the size of the corpus, the shape of the league across seasons, who has won
most, and which pipeline stages have produced artefacts.
"""

from __future__ import annotations

import streamlit as st

from ui import brand, charts, components as ui, data
from ui.tokens import ACCENT


def render() -> None:
    summary = data.corpus_summary()

    if not summary:
        ui.hero(
            "IPL Analytics Console",
            "The match ledger has not been loaded yet.",
            eyebrow="Overview",
        )
        ui.empty_state(
            "No data found",
            "datasets/matches.csv is missing. Run the pipeline once to populate "
            "every dataset this console reads.",
            "python main.py",
        )
        return

    # ── Hero ──────────────────────────────────────────────────────────────────
    ui.hero(
        "Seventeen seasons of the IPL, mined end to end",
        "Unsupervised clustering profiles every player into an archetype, gradient "
        "boosting predicts match winners, and a star-schema warehouse answers the "
        "OLAP questions underneath. This console is the front end to all of it.",
        eyebrow="Overview",
        pills=[
            ui.pill(f"{summary['span']}", ACCENT["cyan"], live=True),
            ui.pill(f"{summary['matches']:,} matches"),
            ui.pill(f"{summary['teams']} franchises"),
            ui.pill(f"{summary['venues']} venues"),
        ],
    )

    # ── Headline counts ───────────────────────────────────────────────────────
    timeline = data.season_timeline()
    match_curve = timeline["Matches"].tolist() if not timeline.empty else None
    margin_curve = timeline["Avg margin"].dropna().tolist() if not timeline.empty else None
    toss_pct, toss_n = data.toss_advantage()

    ui.stat_grid([
        ui.stat("Matches", f"{summary['matches']:,}", icon="◈",
                note="Complete ball-by-ball ledger", spark=match_curve,
                accent=ACCENT["cyan"], count_to=summary["matches"]),
        ui.stat("Seasons", str(summary["seasons"]), icon="◷",
                note=summary["span"], accent=ACCENT["violet"],
                count_to=summary["seasons"]),
        ui.stat("Players profiled", f"{summary['players']:,}", icon="◆",
                note=f"{summary['clusters']} archetypes discovered",
                accent=ACCENT["lime"], count_to=summary["players"]),
        ui.stat("Venues", str(summary["venues"]), icon="⌖",
                note=f"across {summary['cities']} cities", spark=margin_curve,
                accent=ACCENT["amber"], count_to=summary["venues"]),
        ui.stat("Toss → win", f"{toss_pct}", unit="%", icon="◑",
                note=f"over {toss_n:,} decided matches", accent=ACCENT["rose"],
                count_to=toss_pct, decimals=1),
    ])

    # ── League rhythm ─────────────────────────────────────────────────────────
    ui.section("League rhythm", "Fixtures and winning margins, season by season", "01")

    left, right = st.columns([3, 2], gap="medium")

    with left:
        if not timeline.empty:
            fig = charts.area_line(timeline, "Season", "Matches",
                                   color=ACCENT["cyan"], height=330)
            fig.update_layout(title="Matches played per season")
            st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

    with right:
        if not timeline.empty and timeline["Avg margin"].notna().any():
            fig = charts.area_line(timeline.dropna(subset=["Avg margin"]),
                                   "Season", "Avg margin",
                                   color=ACCENT["amber"], height=330)
            fig.update_layout(title="Average winning margin")
            st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

    if toss_pct:
        edge = toss_pct - 50
        direction = "an edge" if edge > 0 else "no edge"
        ui.insight(
            f"Winning the toss converts to a win <strong>{toss_pct}%</strong> of the time "
            f"across {toss_n:,} decided matches — {direction} of "
            f"<strong>{abs(edge):.1f} points</strong> over a coin flip. "
            "The classifier still keeps toss as a feature, but it earns its place "
            "through interactions with venue and form rather than on its own.",
            tone="info" if abs(edge) < 3 else "warning",
        )

    # ── Franchise ladder ──────────────────────────────────────────────────────
    ui.section("Franchise ladder", "Career wins across every season on record", "02")

    ladder, splits = st.columns([3, 2], gap="medium")

    record = data.team_record()

    with ladder:
        top = record.head(10)
        ui.rank_list(
            list(zip(top["Team"], top["Wins"])),
            colors=[brand.color(t) for t in top["Team"]],
            prefixes=[ui.crest(t, "sm") for t in top["Team"]],
            suffix=" W",
        )

    with splits:
        if not record.empty:
            best = record.nlargest(6, "Win %")
            fig = charts.ranked_bar(
                best, "Team", "Win %",
                color_map=brand.color_map(best["Team"]),
                horizontal=True,
                height=330,
            )
            fig.update_layout(title="Best win rate (all-time)")
            fig.update_yaxes(
                ticktext=[brand.code(t) for t in best["Team"]],
                tickvals=list(best["Team"]),
            )
            st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

    if not record.empty:
        leader = record.iloc[0]
        rate_leader = record.nlargest(1, "Win %").iloc[0]
        ui.insight(
            f"<strong>{leader['Team']}</strong> leads on volume with "
            f"<strong>{int(leader['Wins'])}</strong> wins from {int(leader['Played'])} matches, "
            f"while <strong>{rate_leader['Team']}</strong> holds the best rate at "
            f"<strong>{rate_leader['Win %']}%</strong>. Volume and rate diverge because "
            "franchises entered the league in different seasons — always read the two together.",
            tone="success",
        )

    # ── Venues ────────────────────────────────────────────────────────────────
    ui.section("Home grounds", "Where the league actually gets played", "03")

    venue_col, share_col = st.columns([3, 2], gap="medium")
    venues = data.venue_leaders(8)

    with venue_col:
        if not venues.empty:
            ui.rank_list(
                list(zip(venues["Venue"], venues["Matches"])),
                colors=charts.CATEGORICAL_FOR_VENUES,
                suffix=" M",
            )

    with share_col:
        if not venues.empty:
            fig = charts.donut(
                venues["Venue"].str.split(",").str[0].tolist(),
                venues["Matches"].tolist(),
                charts.CATEGORICAL_FOR_VENUES,
                center=f"{int(venues['Matches'].sum()):,}<br><span style='font-size:11px'>matches</span>",
                height=330,
            )
            fig.update_layout(title="Share of the top eight grounds", showlegend=False)
            st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

    # ── Pipeline ──────────────────────────────────────────────────────────────
    ui.section("Pipeline artefacts", "Every stage that has written output to disk", "04")

    status = data.pipeline_status()
    ui.markup(
        '<div style="display:flex;flex-wrap:wrap;gap:0.5rem">'
        + "".join(
            ui.pill(
                f"{name} {'ready' if ok else 'missing'}",
                ACCENT["mint"] if ok else ACCENT["rose"],
                live=ok,
            )
            for name, ok in status
        )
        + "</div>"
    )

    if not all(ok for _, ok in status):
        ui.insight(
            "Some stages have not produced output yet. Run <strong>python main.py</strong> "
            "to execute preprocessing, feature engineering, clustering, classification "
            "and the warehouse build in order.",
            tone="warning",
        )
