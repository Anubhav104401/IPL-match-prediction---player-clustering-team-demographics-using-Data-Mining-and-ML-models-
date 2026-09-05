"""
IPL Analytics Console — application shell.

Run with:
    streamlit run app.py

Responsibilities, in order: page configuration, theme injection, Plotly template
registration, sidebar chrome, routing, and mounting the client-side runtime.
Page content itself lives in ``views/``; everything visual lives in ``ui/``.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="IPL Analytics Console",
    page_icon=str(ROOT / "assets" / "icon.svg"),
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            "**IPL Analytics Console**\n\n"
            "Clustering, classification and OLAP over seventeen seasons of the "
            "Indian Premier League. Built with Streamlit and Plotly."
        ),
        "Report a bug": None,
        "Get help": None,
    },
)

# Imported after set_page_config — Streamlit requires it to be the first command.
from ui import charts, components as ui, data, theme  # noqa: E402
from views import overview, players, prediction, teams, warehouse  # noqa: E402


def _sidebar() -> None:
    """Everything below the navigation: pipeline status and provenance."""
    with st.sidebar:
        ui.nav_label("Pipeline status")

        status = data.pipeline_status()
        ui.markup(
            '<div style="display:flex;flex-wrap:wrap;gap:0.35rem;padding:0 0.35rem">'
            + "".join(
                ui.pill(name, "#34D399" if ok else "#FB7185", live=ok)
                for name, ok in status
            )
            + "</div>"
        )

        counts = data.warehouse_counts()
        summary = data.corpus_summary()
        ui.sidebar_footer([
            ("Matches", f"{summary.get('matches', 0):,}"),
            ("Players", f"{summary.get('players', 0):,}"),
            ("Warehouse rows", f"{sum(counts.values()):,}" if counts else "—"),
            ("Seasons", str(summary.get("seasons", 0))),
        ])

        ui.markup(
            '<div style="padding:0.9rem 0.5rem 0;font-size:0.68rem;line-height:1.6;'
            'color:var(--sn-ink-faint)">'
            "Clustering · Classification · OLAP<br>"
            "Streamlit + Plotly + scikit-learn"
            "</div>"
        )


def main() -> None:
    theme.inject()
    ui.inject_css()
    charts.register_template()

    st.logo(
        str(ROOT / "assets" / "logo.svg"),
        icon_image=str(ROOT / "assets" / "icon.svg"),
        size="large",
    )

    pages = {
        "Explore": [
            # The default page is always served at "/", so it takes no url_path.
            st.Page(overview.render, title="Overview", icon=":material/dashboard:",
                    default=True),
            st.Page(players.render, title="Players", icon=":material/groups:",
                    url_path="players"),
            st.Page(teams.render, title="Teams", icon=":material/shield:",
                    url_path="teams"),
        ],
        "Model": [
            st.Page(prediction.render, title="Match prediction",
                    icon=":material/insights:", url_path="prediction"),
        ],
        "Data": [
            st.Page(warehouse.render, title="Data warehouse",
                    icon=":material/database:", url_path="warehouse"),
        ],
    }

    navigation = st.navigation(pages, position="sidebar", expanded=True)
    _sidebar()
    navigation.run()

    # Mounted last so it can see every element the page rendered.
    ui.mount_runtime()


if __name__ == "__main__":
    main()
