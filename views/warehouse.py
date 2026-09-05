"""
Warehouse — the star schema and the OLAP questions it answers.

Five analytical queries run against the SQLite warehouse built by
``datawarehouse.py``. Each is shown with the SQL that produced it, because the
query *is* the analysis on this page.
"""

from __future__ import annotations

import streamlit as st

from ui import brand, charts, components as ui, data
from ui.tokens import ACCENT, rgba

# ──────────────────────────────────────────────────────────────────────────────
#  Star schema diagram
# ──────────────────────────────────────────────────────────────────────────────

_DIMENSIONS = (
    # (table, x, y, accent, columns)
    ("dim_date",   40,  30, ACCENT["cyan"],   "date_key · season · year"),
    ("dim_team",   40, 200, ACCENT["violet"], "team_key · team_name"),
    ("dim_venue", 560,  30, ACCENT["lime"],   "venue_key · venue_name · city"),
    ("dim_player",560, 200, ACCENT["amber"],  "player_key · stats · cluster"),
)


def _schema_diagram(counts: dict[str, int]) -> str:
    """An inline SVG of the star schema, sized by actual row counts."""
    box_w, box_h = 210, 74
    fact_x, fact_y, fact_w, fact_h = 300, 108, 200, 88
    cx, cy = fact_x + fact_w / 2, fact_y + fact_h / 2

    parts = [
        '<svg viewBox="0 0 810 310" width="100%" role="img" '
        'aria-label="Star schema: four dimension tables joined to fact_matches" '
        'style="max-width:900px;margin:0 auto;display:block">',
        "<defs>",
        '<linearGradient id="factg" x1="0" y1="0" x2="1" y2="1">',
        f'<stop offset="0%" stop-color="{ACCENT["cyan"]}"/>',
        f'<stop offset="100%" stop-color="{ACCENT["violet"]}"/>',
        "</linearGradient>",
        '<filter id="fglow" x="-60%" y="-60%" width="220%" height="220%">',
        '<feGaussianBlur stdDeviation="10" result="b"/>',
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>',
        "</filter>",
        "</defs>",
    ]

    # Join lines first so the boxes paint over their endpoints.
    for table, x, y, accent, _ in _DIMENSIONS:
        anchor_x = x + box_w if x < fact_x else x
        anchor_y = y + box_h / 2
        parts.append(
            f'<path d="M {anchor_x} {anchor_y} C {(anchor_x + cx) / 2} {anchor_y}, '
            f'{(anchor_x + cx) / 2} {cy}, {cx} {cy}" '
            f'stroke="{rgba(accent, 0.45)}" stroke-width="1.6" fill="none" '
            f'stroke-dasharray="5 6">'
            f'<animate attributeName="stroke-dashoffset" from="22" to="0" '
            f'dur="1.4s" repeatCount="indefinite"/></path>'
        )

    # Dimension tables.
    for table, x, y, accent, columns in _DIMENSIONS:
        rows = counts.get(table, 0)
        parts.append(
            f'<g><rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="14" '
            f'fill="{rgba(accent, 0.09)}" stroke="{rgba(accent, 0.38)}" stroke-width="1.2"/>'
            f'<text x="{x + 16}" y="{y + 27}" fill="{accent}" '
            f'font-family="JetBrains Mono, monospace" font-size="13" font-weight="600">'
            f"{table}</text>"
            f'<text x="{x + 16}" y="{y + 46}" fill="#8B95AF" '
            f'font-family="Inter, sans-serif" font-size="10.5">{columns}</text>'
            f'<text x="{x + 16}" y="{y + 63}" fill="#6C7796" '
            f'font-family="JetBrains Mono, monospace" font-size="10.5">'
            f"{rows:,} rows</text></g>"
        )

    # Fact table.
    fact_rows = counts.get("fact_matches", 0)
    parts.append(
        f'<g filter="url(#fglow)"><rect x="{fact_x}" y="{fact_y}" width="{fact_w}" '
        f'height="{fact_h}" rx="16" fill="rgba(34,211,238,0.14)" '
        f'stroke="url(#factg)" stroke-width="1.8"/>'
        f'<text x="{cx}" y="{fact_y + 32}" text-anchor="middle" fill="#E6EAF7" '
        f'font-family="Space Grotesk, sans-serif" font-size="15" font-weight="700">'
        f"fact_matches</text>"
        f'<text x="{cx}" y="{fact_y + 52}" text-anchor="middle" fill="#A3AECB" '
        f'font-family="Inter, sans-serif" font-size="10.5">4 foreign keys · 6 measures</text>'
        f'<text x="{cx}" y="{fact_y + 72}" text-anchor="middle" fill="{ACCENT["cyan"]}" '
        f'font-family="JetBrains Mono, monospace" font-size="11.5" font-weight="600">'
        f"{fact_rows:,} rows</text></g>"
    )

    parts.append("</svg>")
    return "".join(parts)


# ──────────────────────────────────────────────────────────────────────────────
#  Queries
# ──────────────────────────────────────────────────────────────────────────────

Q_VENUES = """
SELECT v.venue_name AS Venue,
       ROUND(AVG(f.result_margin), 2) AS Avg_Margin,
       COUNT(*) AS Matches
FROM fact_matches f
JOIN dim_venue v ON f.venue_key = v.venue_key
WHERE f.result_margin > 0
GROUP BY v.venue_name
HAVING Matches >= 5
ORDER BY Avg_Margin DESC
LIMIT 8
"""

Q_TOSS = """
SELECT d.season AS Season, f.toss_decision AS Decision, COUNT(*) AS Matches
FROM fact_matches f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.toss_decision IS NOT NULL
GROUP BY d.season, f.toss_decision
ORDER BY d.season
"""

Q_DOMINANT = """
WITH team_season AS (
    SELECT d.season, t.team_name, COUNT(*) AS wins
    FROM fact_matches f
    JOIN dim_date d ON f.date_key = d.date_key
    JOIN dim_team t ON f.winner_key = t.team_key
    GROUP BY d.season, t.team_name
),
ranked AS (
    SELECT season, team_name, wins,
           ROW_NUMBER() OVER (PARTITION BY season ORDER BY wins DESC) AS rn
    FROM team_season
)
SELECT season AS Season, team_name AS Team, wins AS Wins
FROM ranked WHERE rn = 1 ORDER BY season
"""

Q_ALLROUNDERS = """
SELECT player_name AS Player, total_runs AS Runs,
       ROUND(strike_rate, 2) AS SR, wickets AS Wickets,
       ROUND(all_rounder_score, 2) AS AR_Score, cluster_label AS Cluster
FROM dim_player
WHERE all_rounder_score > 0
ORDER BY all_rounder_score DESC
LIMIT 12
"""

Q_CLUSTERS = """
SELECT cluster_label AS Cluster, COUNT(*) AS Players,
       ROUND(AVG(total_runs), 1) AS Avg_Runs,
       ROUND(AVG(strike_rate), 2) AS Avg_SR,
       ROUND(AVG(wickets), 1) AS Avg_Wickets,
       ROUND(AVG(all_rounder_score), 2) AS Avg_AR
FROM dim_player
WHERE cluster_label != 'Unknown'
GROUP BY cluster_label
ORDER BY Avg_AR DESC
"""


def render() -> None:
    counts = data.warehouse_counts()

    if not counts:
        ui.hero("Data warehouse", "The warehouse has not been built.", eyebrow="Warehouse")
        ui.empty_state(
            "No warehouse found",
            "ipl_warehouse.db does not exist yet. The build script creates four dimension "
            "tables and one fact table from the cleaned datasets.",
            "python datawarehouse.py",
        )
        return

    ui.hero(
        "A star schema, and the questions it was built to answer",
        "Four conformed dimensions around a single grain — one row per match. "
        "Every query below is answered by joins the schema was designed for, "
        "not by scanning flat files.",
        eyebrow="Warehouse · OLAP",
        pills=[
            ui.pill(f"{counts.get('fact_matches', 0):,} facts", ACCENT["cyan"], live=True),
            ui.pill("4 dimensions", ACCENT["violet"]),
            ui.pill("SQLite · star schema"),
        ],
        accent=ACCENT["mint"],
        accent_2=ACCENT["cyan"],
    )

    ui.stat_grid([
        ui.stat("fact_matches", f"{counts.get('fact_matches', 0):,}", icon="◈",
                note="grain: one row per match", accent=ACCENT["cyan"],
                count_to=counts.get("fact_matches", 0)),
        ui.stat("dim_date", f"{counts.get('dim_date', 0):,}", icon="◷",
                note="date · season · year", accent=ACCENT["sky"],
                count_to=counts.get("dim_date", 0)),
        ui.stat("dim_team", f"{counts.get('dim_team', 0):,}", icon="⬢",
                note="every franchise on record", accent=ACCENT["violet"],
                count_to=counts.get("dim_team", 0)),
        ui.stat("dim_venue", f"{counts.get('dim_venue', 0):,}", icon="⌖",
                note="grounds and their cities", accent=ACCENT["lime"],
                count_to=counts.get("dim_venue", 0)),
        ui.stat("dim_player", f"{counts.get('dim_player', 0):,}", icon="◆",
                note="stats and cluster label", accent=ACCENT["amber"],
                count_to=counts.get("dim_player", 0)),
    ])

    # ── Schema ────────────────────────────────────────────────────────────────
    ui.section("Schema", "Dimensions joined to a single fact table", "01")
    ui.markup(
        '<div class="sn-card" style="padding:1.6rem 1.2rem">'
        + _schema_diagram(counts)
        + "</div>"
    )
    ui.insight(
        "A star schema keeps the fact table narrow — four foreign keys and the measures — "
        "so aggregations scan far less data than the equivalent query over the raw CSVs. "
        "Descriptive attributes live in the dimensions, denormalised on purpose.",
        tone="neutral",
    )

    # ── Queries ───────────────────────────────────────────────────────────────
    ui.section("Analytical queries", "Five OLAP questions, each with its SQL", "02")

    tabs = st.tabs([
        "Venues", "Toss by season", "Season leaders", "All-rounders", "Cluster profile",
    ])

    with tabs[0]:
        _venues()
    with tabs[1]:
        _toss()
    with tabs[2]:
        _dominant()
    with tabs[3]:
        _all_rounders()
    with tabs[4]:
        _clusters()


def _sql(query: str) -> None:
    with st.expander("SQL"):
        st.code(query.strip(), language="sql")


def _venues() -> None:
    df = data.warehouse_query(Q_VENUES)
    if df is None or df.empty:
        ui.empty_state("No rows", "The venue query returned nothing.")
        return

    st.markdown("**Which grounds produce the most lopsided results?**")
    chart, table = st.columns([1, 1], gap="medium")

    short = df.copy()
    short["Ground"] = short["Venue"].str.split(",").str[0]

    with chart:
        fig = charts.ranked_bar(short, "Ground", "Avg_Margin", horizontal=True, height=400)
        fig.update_layout(title="Average winning margin (runs)")
        st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

    with table:
        st.dataframe(
            short[["Ground", "Avg_Margin", "Matches"]],
            width="stretch",
            hide_index=True,
            height=400,
            column_config={
                "Ground": st.column_config.TextColumn("Ground", width="medium"),
                "Avg_Margin": st.column_config.NumberColumn("Margin", format="%.1f"),
                "Matches": st.column_config.NumberColumn("Played", format="%d"),
            },
        )

    ui.insight(
        f"<strong>{df.iloc[0]['Venue']}</strong> tops the list at "
        f"<strong>{df.iloc[0]['Avg_Margin']}</strong> runs across {int(df.iloc[0]['Matches'])} "
        "matches. Grounds with short square boundaries and high first-innings totals tend to "
        "produce blowouts rather than close finishes.",
        tone="info",
    )
    _sql(Q_VENUES)


def _toss() -> None:
    df = data.warehouse_query(Q_TOSS)
    if df is None or df.empty:
        ui.empty_state("No rows", "The toss query returned nothing.")
        return

    st.markdown("**Has the bat-or-field preference shifted across seasons?**")
    df["Season"] = df["Season"].astype(str)
    fig = charts.grouped_bar(
        df, "Season", "Matches", "Decision",
        color_map={"bat": ACCENT["amber"], "field": ACCENT["cyan"]},
        height=400, barmode="stack",
    )
    fig.update_layout(title="Toss decisions per season")
    st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

    share = df.groupby("Decision")["Matches"].sum()
    if "field" in share.index:
        pct = share["field"] / share.sum() * 100
        ui.insight(
            f"Captains elect to field <strong>{pct:.0f}%</strong> of the time overall. "
            "Chasing has become the default as dew and improved batting depth made "
            "run-chases more predictable than setting a target.",
            tone="info",
        )
    _sql(Q_TOSS)


def _dominant() -> None:
    df = data.warehouse_query(Q_DOMINANT)
    if df is None or df.empty:
        ui.empty_state("No rows", "The season-leader query returned nothing.")
        return

    st.markdown("**Which side won most matches in each season?**")
    df["Season"] = df["Season"].astype(str)

    chart, table = st.columns([3, 2], gap="medium")
    with chart:
        fig = charts.grouped_bar(
            df, "Season", "Wins", "Team",
            color_map=brand.color_map(df["Team"]),
            height=400,
        )
        fig.update_layout(title="Season leaders", legend=dict(font=dict(size=10)))
        st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

    with table:
        st.dataframe(df, width="stretch", hide_index=True, height=400)

    _sql(Q_DOMINANT)


def _all_rounders() -> None:
    df = data.warehouse_query(Q_ALLROUNDERS)
    if df is None or df.empty:
        ui.empty_state("No rows", "The all-rounder query returned nothing.")
        return

    st.markdown("**Who scores highest on the composite all-rounder index?**")
    bars, table = st.columns([2, 3], gap="medium")

    with bars:
        ui.rank_list(
            list(zip(df["Player"], df["AR_Score"])),
            colors=[brand.cluster_color(c) for c in df["Cluster"]],
            decimals=1,
            suffix=" pts",
        )

    with table:
        st.dataframe(
            df, width="stretch", hide_index=True, height=430,
            column_config={
                "AR_Score": st.column_config.ProgressColumn(
                    "AR score", format="%.1f",
                    min_value=0, max_value=float(df["AR_Score"].max()),
                ),
            },
        )

    ui.insight(
        f"<strong>{df.iloc[0]['Player']}</strong> leads at "
        f"<strong>{df.iloc[0]['AR_Score']}</strong>, combining "
        f"{int(df.iloc[0]['Runs']):,} runs with {int(df.iloc[0]['Wickets'])} wickets. "
        "Bar colour is the player's cluster, so you can see which archetypes the index rewards.",
        tone="success",
    )
    _sql(Q_ALLROUNDERS)


def _clusters() -> None:
    df = data.warehouse_query(Q_CLUSTERS)
    if df is None or df.empty:
        ui.empty_state("No rows", "The cluster query returned nothing.")
        return

    st.markdown("**How do the archetypes differ on average?**")
    st.dataframe(df, width="stretch", hide_index=True)

    melted = df.melt(
        id_vars="Cluster",
        value_vars=[c for c in ("Avg_Runs", "Avg_Wickets", "Avg_AR") if c in df.columns],
        var_name="Metric", value_name="Value",
    )
    fig = charts.grouped_bar(
        melted, "Cluster", "Value", "Metric",
        color_map={"Avg_Runs": ACCENT["rose"], "Avg_Wickets": ACCENT["violet"],
                   "Avg_AR": ACCENT["lime"]},
        height=380,
    )
    fig.update_layout(title="Cluster means side by side")
    st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

    ui.insight(
        "Averages are computed inside the warehouse rather than in pandas — this is exactly "
        "the aggregation a star schema exists to make cheap.",
        tone="neutral",
    )
    _sql(Q_CLUSTERS)
