"""
Charting layer.

A single Plotly template ("stadium_nights") is registered as the process-wide
default, so *every* figure in the app — including ones built ad hoc — inherits
the type system, palette, grid weight and hover treatment. The factories below
add the composition decisions on top: what gets a legend, where the axis titles
go, how bars are ordered.
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from ui.tokens import ACCENT, CATEGORICAL, DIVERGING, INK, SEQUENTIAL, rgba

TEMPLATE = "stadium_nights"

_GRID = "rgba(255,255,255,0.055)"
_ZERO = "rgba(255,255,255,0.14)"

#: Palette for venue encodings — venues have no brand colour of their own, so
#: they borrow the shared categorical ramp in a fixed order.
CATEGORICAL_FOR_VENUES = list(CATEGORICAL)

#: Sequential ramps, in the form Plotly wants (position, colour) pairs.
SCALE_COOL = [[i / (len(SEQUENTIAL) - 1), c] for i, c in enumerate(SEQUENTIAL)]
SCALE_DIVERGING = [[i / (len(DIVERGING) - 1), c] for i, c in enumerate(DIVERGING)]


def register_template() -> None:
    """Register and activate the house Plotly template. Safe to call repeatedly."""
    if TEMPLATE in pio.templates:
        pio.templates.default = TEMPLATE
        return

    axis = dict(
        gridcolor=_GRID,
        griddash="dot",
        zerolinecolor=_ZERO,
        linecolor="rgba(255,255,255,0.10)",
        tickfont=dict(size=11, color=INK["muted"]),
        title=dict(font=dict(size=11.5, color=INK["faint"])),
        showline=False,
        ticks="outside",
        ticklen=4,
        tickcolor="rgba(255,255,255,0.10)",
        automargin=True,
    )

    pio.templates[TEMPLATE] = go.layout.Template(
        layout=go.Layout(
            font=dict(family="Inter, system-ui, sans-serif", size=12.5, color=INK["secondary"]),
            title=dict(
                font=dict(family="Space Grotesk, Inter, sans-serif", size=15.5,
                          color=INK["primary"]),
                x=0.012,
                xanchor="left",
                y=0.965,
                pad=dict(t=6, l=6),
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            colorway=CATEGORICAL,
            colorscale=dict(sequential=SCALE_COOL, diverging=SCALE_DIVERGING),
            margin=dict(l=52, r=24, t=54, b=48),
            hoverlabel=dict(
                bgcolor="rgba(14,17,32,0.96)",
                bordercolor="rgba(255,255,255,0.14)",
                font=dict(family="Inter, sans-serif", size=12, color=INK["primary"]),
                align="left",
            ),
            hovermode="closest",
            # Legends sit *below* the plot, centred. Placing them beside the
            # title is where they collide: a categorical series with a dozen
            # entries will overrun the title or clip at the right edge.
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.16,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(0,0,0,0)",
                font=dict(size=11.5, color=INK["muted"]),
                itemsizing="constant",
                itemwidth=30,
                title=dict(text=""),
            ),
            xaxis=axis,
            yaxis=axis,
            coloraxis=dict(
                colorbar=dict(
                    outlinewidth=0,
                    thickness=10,
                    len=0.7,
                    tickfont=dict(size=10.5, color=INK["muted"]),
                    title=dict(font=dict(size=11, color=INK["faint"])),
                )
            ),
            polar=dict(
                bgcolor="rgba(255,255,255,0.02)",
                radialaxis=dict(gridcolor=_GRID, linecolor="rgba(0,0,0,0)",
                                tickfont=dict(size=10, color=INK["faint"])),
                angularaxis=dict(gridcolor=_GRID, linecolor=_GRID,
                                 tickfont=dict(size=11, color=INK["muted"])),
            ),
            transition=dict(duration=420, easing="cubic-out"),
        )
    )
    pio.templates.default = TEMPLATE


def finish(fig: go.Figure, *, height: int | None = None, legend: bool = True) -> go.Figure:
    """Final pass applied to every figure before it reaches the page."""
    fig.update_layout(
        showlegend=legend,
        dragmode=False,
        modebar=dict(
            bgcolor="rgba(0,0,0,0)",
            color=INK["faint"],
            activecolor=ACCENT["cyan"],
        ),
    )
    # Reserve room underneath for the legend the template places there.
    if legend and fig.layout.legend.orientation != "v":
        current_b = fig.layout.margin.b or 48
        fig.update_layout(margin=dict(b=max(current_b, 92)))
    if height:
        fig.update_layout(height=height)
    return fig


CONFIG = {
    "displayModeBar": "hover",
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "select2d", "lasso2d", "autoScale2d", "zoomIn2d", "zoomOut2d",
    ],
    "toImageButtonOptions": {"format": "png", "scale": 3, "filename": "ipl-analytics"},
    "responsive": True,
}


# ──────────────────────────────────────────────────────────────────────────────
#  Factories
# ──────────────────────────────────────────────────────────────────────────────

def cluster_scatter(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: str | None,
    hover: Sequence[str],
    color_map: dict[str, str] | None = None,
    height: int = 560,
) -> go.Figure:
    """A PCA projection where each point is a player and colour is an archetype."""
    fig = px.scatter(
        df, x=x, y=y,
        color=color,
        color_discrete_map=color_map,
        hover_data=list(hover),
        height=height,
    )
    fig.update_traces(
        marker=dict(size=9, opacity=0.86, line=dict(width=0.8, color="rgba(7,8,15,0.85)")),
        selector=dict(mode="markers"),
    )
    fig.update_layout(
        xaxis_title="Principal component 1",
        yaxis_title="Principal component 2",
        legend_title_text="",
    )
    return finish(fig, height=height)


def ranked_bar(
    df: pd.DataFrame,
    x: str,
    y: str,
    *,
    color_map: dict[str, str] | None = None,
    color_col: str | None = None,
    height: int = 420,
    horizontal: bool = False,
    label_fmt: str = "%{y:,.0f}",
) -> go.Figure:
    """A bar chart with value labels and per-category colour."""
    orientation_kw = dict(orientation="h") if horizontal else {}
    fig = px.bar(
        df,
        x=y if horizontal else x,
        y=x if horizontal else y,
        color=color_col or x,
        color_discrete_map=color_map,
        height=height,
        **orientation_kw,
    )
    fig.update_traces(
        marker=dict(line=dict(width=0)),
        texttemplate=label_fmt if not horizontal else "%{x:,.0f}",
        textposition="outside",
        textfont=dict(size=11, color=INK["muted"], family="JetBrains Mono, monospace"),
        cliponaxis=False,
        hovertemplate="<b>%{" + ("y" if horizontal else "x") + "}</b><br>"
                      + f"{y}: " + "%{" + ("x" if horizontal else "y") + ":,.0f}<extra></extra>",
    )
    fig.update_layout(
        bargap=0.34,
        xaxis_title=None,
        yaxis_title=None,
        showlegend=False,
        # Value labels sit outside the bar; without headroom they get clipped.
        margin=dict(r=64 if horizontal else 28, t=54, b=52),
    )
    if horizontal:
        fig.update_yaxes(categoryorder="total ascending")
    else:
        fig.update_yaxes(rangemode="tozero")
        fig.update_traces(cliponaxis=False)
    return finish(fig, height=height, legend=False)


def grouped_bar(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: str,
    *,
    color_map: dict[str, str] | None = None,
    height: int = 420,
    barmode: str = "group",
    text: str | None = None,
    legend: bool = True,
) -> go.Figure:
    """A grouped or stacked bar chart for a two-way breakdown.

    Pass ``text`` and ``legend=False`` when the category count is high enough
    that a legend would be a wall of swatches — labelling the bars directly
    reads faster and costs no vertical space.
    """
    fig = px.bar(
        df, x=x, y=y, color=color,
        color_discrete_map=color_map,
        barmode=barmode,
        height=height,
        text=text,
    )
    fig.update_traces(marker=dict(line=dict(width=0)))
    if text:
        fig.update_traces(
            textposition="outside",
            textfont=dict(size=9.5, color=INK["muted"],
                          family="JetBrains Mono, monospace"),
            cliponaxis=False,
        )
    fig.update_layout(
        bargap=0.28, bargroupgap=0.08,
        xaxis_title=None, yaxis_title=None,
        legend_title_text="",
    )
    return finish(fig, height=height, legend=legend)


def matrix(
    values,
    labels: Sequence[str],
    *,
    x_title: str = "",
    y_title: str = "",
    color_title: str = "",
    height: int = 620,
    text_fmt: str = "%{z:.0f}",
) -> go.Figure:
    """A square heat matrix — used for head-to-head win percentages."""
    fig = px.imshow(
        values,
        x=list(labels),
        y=list(labels),
        color_continuous_scale=SCALE_DIVERGING,
        origin="upper",
        aspect="auto",
        height=height,
        zmin=0,
        zmax=100,
    )
    fig.update_traces(
        texttemplate=text_fmt,
        textfont=dict(size=10.5, family="JetBrains Mono, monospace"),
        xgap=3,
        ygap=3,
        hovertemplate=f"<b>%{{y}}</b> vs <b>%{{x}}</b><br>{color_title}: "
                      "%{z:.1f}%<extra></extra>",
    )
    fig.update_layout(
        xaxis_title=x_title,
        yaxis_title=y_title,
        coloraxis_colorbar=dict(title=dict(text=color_title)),
        xaxis=dict(side="bottom", tickangle=-38, showgrid=False),
        yaxis=dict(showgrid=False),
        margin=dict(l=150, r=30, t=54, b=140),
    )
    return finish(fig, height=height, legend=False)


def radar(
    categories: Sequence[str],
    series: Sequence[tuple[str, Sequence[float], str]],
    height: int = 440,
) -> go.Figure:
    """Overlaid radar traces — one closed polygon per entity."""
    fig = go.Figure()
    for name, values, color in series:
        vals = list(values) + [values[0]]
        cats = list(categories) + [categories[0]]
        fig.add_trace(
            go.Scatterpolar(
                r=vals,
                theta=cats,
                name=name,
                fill="toself",
                fillcolor=rgba(color, 0.16),
                line=dict(color=color, width=2),
                marker=dict(size=5, color=color),
                hovertemplate="<b>%{theta}</b><br>" + f"{name}: " + "%{r:.1f}<extra></extra>",
            )
        )
    fig.update_layout(
        polar=dict(
            domain=dict(x=[0.14, 0.86], y=[0.04, 0.86]),
            radialaxis=dict(
                visible=True, range=[0, 100],
                showticklabels=True, tickvals=[25, 50, 75, 100],
                tickfont=dict(size=8.5, color=INK["faint"]),
                angle=90, tickangle=90,
            ),
            angularaxis=dict(tickfont=dict(size=10.5, color=INK["muted"])),
        ),
        height=height,
        margin=dict(l=30, r=30, t=54, b=30),
        legend=dict(y=-0.02, yanchor="top", x=0.5, xanchor="center",
                    orientation="h", font=dict(size=10.5)),
    )
    return finish(fig, height=height)


def donut(
    labels: Sequence[str],
    values: Sequence[float],
    colors: Sequence[str],
    *,
    center: str = "",
    height: int = 320,
) -> go.Figure:
    """A donut with a centred readout — a share-of-total, not a ranking."""
    fig = go.Figure(
        go.Pie(
            labels=list(labels),
            values=list(values),
            hole=0.68,
            marker=dict(colors=list(colors), line=dict(color="rgba(7,8,15,0.9)", width=2)),
            textinfo="none",
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} (%{percent})<extra></extra>",
            sort=False,
        )
    )
    if center:
        fig.add_annotation(
            text=center,
            showarrow=False,
            font=dict(family="Space Grotesk, sans-serif", size=17, color=INK["primary"]),
        )
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=46, b=10),
        # A donut's legend belongs under the ring, not stacked against the title.
        legend=dict(orientation="h", y=-0.04, yanchor="top",
                    x=0.5, xanchor="center", font=dict(size=10.5)),
    )
    return finish(fig, height=height)


def area_line(
    df: pd.DataFrame,
    x: str,
    y: str,
    *,
    color: str = ACCENT["cyan"],
    height: int = 340,
    name: str = "",
) -> go.Figure:
    """A single-series trend with a gradient wash beneath it."""
    fig = go.Figure(
        go.Scatter(
            x=df[x],
            y=df[y],
            mode="lines+markers",
            name=name or y,
            line=dict(color=color, width=2.6, shape="spline", smoothing=0.6),
            marker=dict(size=6, color=color, line=dict(width=1.4, color="rgba(7,8,15,0.9)")),
            fill="tozeroy",
            fillcolor=rgba(color, 0.13),
            hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(height=height, xaxis_title=None, yaxis_title=None, showlegend=False)
    return finish(fig, height=height, legend=False)


def rate_comparison(
    labels: Sequence[str],
    values: Sequence[float],
    colors: Sequence[str],
    *,
    baseline: float | None = 50.0,
    baseline_label: str = "coin flip",
    height: int = 300,
    axis_title: str = "",
) -> go.Figure:
    """Compare independent rates against a reference line.

    Deliberately not a pie or donut: these values are separate percentages, not
    shares of one total, and a ring would imply they sum to 100.
    """
    fig = go.Figure(
        go.Bar(
            x=list(values),
            y=list(labels),
            orientation="h",
            marker=dict(color=list(colors), line=dict(width=0)),
            text=[f"{v:.1f}%" for v in values],
            textposition="outside",
            textfont=dict(size=12, family="JetBrains Mono, monospace",
                          color=INK["secondary"]),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>%{x:.1f}%<extra></extra>",
        )
    )

    if baseline is not None:
        fig.add_vline(
            x=baseline,
            line=dict(color="rgba(255,255,255,0.28)", width=1.5, dash="dot"),
            annotation_text=baseline_label,
            annotation_position="top",
            annotation_font=dict(size=10, color=INK["faint"]),
        )

    upper = max(list(values) + [baseline or 0]) * 1.22
    fig.update_layout(
        height=height,
        bargap=0.45,
        xaxis=dict(range=[0, upper], title=dict(text=axis_title), ticksuffix="%"),
        yaxis=dict(title=None, automargin=True),
        margin=dict(l=20, r=60, t=54, b=44),
        showlegend=False,
    )
    return finish(fig, height=height, legend=False)
