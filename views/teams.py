"""
Teams — franchise performance and rivalries.

Every encoding on this page uses the franchise's own kit colour, so a reader who
knows the league can read the charts without consulting a legend.
"""

from __future__ import annotations

import numpy as np
import streamlit as st

from ui import brand, charts, components as ui, data
from ui.tokens import ACCENT


def render() -> None:
    matches = data.load_matches()

    if matches is None:
        ui.hero("Franchise performance", "The match ledger is missing.", eyebrow="Teams")
        ui.empty_state("No match data", "datasets/matches.csv could not be read.", "python main.py")
        return

    record = data.team_record()
    decided = matches.dropna(subset=["winner"])

    # ── Hero ──────────────────────────────────────────────────────────────────
    leader = record.iloc[0]
    ui.hero(
        "Franchise performance and the rivalries that shaped it",
        "Career records, head-to-head win rates between the ten winningest sides, "
        "and who owned each season. Colour is always the franchise's own kit — "
        "no legend required.",
        eyebrow="Teams · Performance",
        pills=[
            ui.pill(f"{len(record)} franchises", ACCENT["cyan"]),
            ui.pill(f"{len(decided):,} decided matches"),
            ui.pill(f"Leader: {brand.code(leader['Team'])}", brand.color(leader["Team"]), live=True),
        ],
        accent=ACCENT["violet"],
        accent_2=ACCENT["rose"],
    )

    # ── Headline counts ───────────────────────────────────────────────────────
    rate_leader = record[record["Played"] >= 50].nlargest(1, "Win %")
    rate_leader = rate_leader.iloc[0] if not rate_leader.empty else leader

    # The most-played fixture in league history.
    pairs = decided.apply(
        lambda r: " vs ".join(sorted([str(r["team1"]), str(r["team2"])])), axis=1
    )
    rivalry = pairs.value_counts()
    top_rivalry = rivalry.index[0] if not rivalry.empty else "—"
    rivalry_n = int(rivalry.iloc[0]) if not rivalry.empty else 0
    rivalry_label = " v ".join(brand.code(t) for t in top_rivalry.split(" vs "))

    ui.stat_grid([
        ui.stat("Franchises", str(len(record)), icon="◈", note="all-time, including defunct sides",
                accent=ACCENT["cyan"], count_to=len(record)),
        ui.stat("Most wins", str(int(leader["Wins"])), icon="★",
                note=str(leader["Team"]), accent=brand.color(leader["Team"]),
                count_to=int(leader["Wins"])),
        ui.stat("Best win rate", f"{rate_leader['Win %']:.1f}", unit="%", icon="▲",
                note=f"{rate_leader['Team']} · min. 50 matches",
                accent=brand.color(rate_leader["Team"]),
                count_to=float(rate_leader["Win %"]), decimals=1),
        ui.stat("Biggest rivalry", str(rivalry_n), icon="⚔",
                note=f"{rivalry_label} meetings", accent=ACCENT["amber"],
                count_to=rivalry_n),
    ])

    # ── Ladder ────────────────────────────────────────────────────────────────
    ui.section("All-time ladder", "Wins, matches played and conversion rate", "01")

    chart_col, table_col = st.columns([1, 1], gap="medium")

    with chart_col:
        top = record.head(12).copy()
        top["Code"] = [brand.code(t) for t in top["Team"]]
        fig = charts.ranked_bar(
            top, "Code", "Wins",
            color_map={brand.code(t): brand.color(t) for t in top["Team"]},
            height=430,
        )
        fig.update_layout(title="Career wins by franchise")
        fig.update_yaxes(range=[0, float(top["Wins"].max()) * 1.16])
        st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

    with table_col:
        st.dataframe(
            record,
            width="stretch",
            hide_index=True,
            height=430,
            column_config={
                "Team": st.column_config.TextColumn("Franchise", width="medium"),
                "Played": st.column_config.NumberColumn("P", format="%d"),
                "Wins": st.column_config.NumberColumn("W", format="%d"),
                "Win %": st.column_config.ProgressColumn(
                    "Win rate", format="%.1f%%", min_value=0, max_value=100
                ),
            },
        )

    ui.insight(
        f"<strong>{leader['Team']}</strong> and <strong>{record.iloc[1]['Team']}</strong> have "
        f"between them won <strong>{int(leader['Wins'] + record.iloc[1]['Wins'])}</strong> matches — "
        f"{(leader['Wins'] + record.iloc[1]['Wins']) / len(decided) * 100:.0f}% of every decided "
        "fixture in league history. Sides that folded after two or three seasons sit at the "
        "bottom on volume while holding respectable rates.",
        tone="info",
    )

    # ── Head to head ──────────────────────────────────────────────────────────
    ui.section("Head to head", "Win percentage among the ten winningest sides", "02")

    matrix, teams = data.head_to_head(10)
    if len(teams) >= 2:
        fig = charts.matrix(
            matrix,
            [brand.code(t) for t in teams],
            x_title="Opponent",
            y_title="Team",
            color_title="Win %",
            height=580,
            text_fmt="%{z:.0f}",
        )
        fig.update_layout(
            title="Row team's win rate against column team",
            margin=dict(l=70, r=30, t=54, b=70),
        )
        st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

        # Surface the most lopsided rivalry with a meaningful sample.
        flat = []
        for i, home in enumerate(teams):
            for j, away in enumerate(teams):
                if i != j and not np.isnan(matrix[i, j]):
                    flat.append((home, away, matrix[i, j]))
        if flat:
            home, away, pct = max(flat, key=lambda r: r[2])
            ui.insight(
                f"The most one-sided fixture on this grid is <strong>{home}</strong> against "
                f"<strong>{away}</strong>, which they win <strong>{pct:.0f}%</strong> of the time. "
                "Green reads as dominance for the row team; the diagonal is left blank because "
                "a side cannot play itself.",
                tone="success",
            )
    else:
        ui.empty_state("Not enough teams", "At least two franchises are needed for a matrix.")

    # ── Season ownership ──────────────────────────────────────────────────────
    ui.section("Who owned each season", "Most wins per season, coloured by franchise", "03")

    if "season" in decided.columns:
        per_season = (
            decided.groupby(["season", "winner"]).size().reset_index(name="Wins")
        )
        best = per_season.sort_values("Wins", ascending=False).groupby("season").head(1)
        best = best.sort_values("season")
        best["Season"] = best["season"].astype(str)
        best["Code"] = [brand.code(t) for t in best["winner"]]

        # One bar per season, each in its winner's kit colour and labelled with
        # the franchise code — a legend here would be a wall of twelve swatches.
        # Stacked, not grouped: exactly one franchise tops each season, so
        # grouping would reserve an empty slot for every other side and leave
        # twelve hairline bars.
        fig = charts.grouped_bar(
            best, "Season", "Wins", "winner",
            color_map=brand.color_map(best["winner"]),
            height=420, text="Code", legend=False, barmode="stack",
        )
        fig.update_layout(title="Season leader by wins")
        st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

        repeat = best["winner"].value_counts()
        if not repeat.empty:
            ui.insight(
                f"<strong>{repeat.index[0]}</strong> topped the win count in "
                f"<strong>{repeat.iloc[0]}</strong> separate seasons — more than any other side. "
                "Leading the regular season is not the same as lifting the trophy, which is "
                "decided in playoffs this dataset treats as ordinary fixtures.",
                tone="neutral",
            )

    # ── Toss behaviour ────────────────────────────────────────────────────────
    ui.section("Toss behaviour", "What captains choose, and whether it works", "04")

    left, right = st.columns(2, gap="medium")

    if "toss_decision" in matches.columns:
        with left:
            by_season = (
                matches.dropna(subset=["toss_decision"])
                .groupby(["season", "toss_decision"]).size().reset_index(name="Matches")
            )
            by_season["Season"] = by_season["season"].astype(str)
            fig = charts.grouped_bar(
                by_season, "Season", "Matches", "toss_decision",
                color_map={"bat": ACCENT["amber"], "field": ACCENT["cyan"]},
                height=360, barmode="stack",
            )
            fig.update_layout(title="Bat or field, by season")
            st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

        with right:
            toss = matches.dropna(subset=["toss_decision", "winner", "toss_winner"])
            toss = toss.assign(won=lambda d: d["toss_winner"] == d["winner"])
            rate = toss.groupby("toss_decision")["won"].mean().mul(100).round(1)
            fig = charts.rate_comparison(
                [f"Chose to {i}" for i in rate.index],
                rate.tolist(),
                [ACCENT["amber"] if i == "bat" else ACCENT["cyan"] for i in rate.index],
                baseline=50.0,
                baseline_label="coin flip",
                height=360,
                axis_title="Share of those matches won",
            )
            fig.update_layout(title="Does the choice pay off?")
            st.plotly_chart(fig, width="stretch", config=charts.CONFIG)

        if len(rate) == 2:
            gap = abs(rate.iloc[0] - rate.iloc[1])
            better = rate.idxmax()
            ui.insight(
                f"Captains who win the toss and choose to <strong>{better}</strong> go on to win "
                f"<strong>{rate.max():.1f}%</strong> of those matches, against "
                f"<strong>{rate.min():.1f}%</strong> for the alternative — a gap of "
                f"<strong>{gap:.1f} points</strong>. Read it as a correlation: the choice is "
                "made *because* of conditions the model also sees.",
                tone="warning" if gap > 5 else "info",
            )
