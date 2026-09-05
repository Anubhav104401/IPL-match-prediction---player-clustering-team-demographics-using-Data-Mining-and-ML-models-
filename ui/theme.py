"""
Global theme layer.

`inject()` is called exactly once per rerun from ``app.py``. It loads the type
system, publishes the design tokens as CSS custom properties, paints the
animated aurora backdrop, and restyles every Streamlit primitive the app
touches so native widgets sit inside the design language rather than beside it.
"""

from __future__ import annotations

import streamlit as st

from ui.tokens import css_variables

# Fine luminance noise, kept as its own constant because the percent-encoding
# is unreadable inline. It stops the large gradients from banding on OLED.
_GRAIN = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence "
    "type='fractalNoise' baseFrequency='0.85' numOctaves='3'/%3E%3C/filter%3E"
    "%3Crect width='160' height='160' filter='url(%23n)'/%3E%3C/svg%3E\")"
)

# ──────────────────────────────────────────────────────────────────────────────
#  Stylesheet
#  Authored as one document so the cascade is predictable. `/*__VARS__*/` and
#  `/*__GRAIN__*/` are substituted at inject time.
# ──────────────────────────────────────────────────────────────────────────────

_STYLESHEET = """
:root {
    /*__VARS__*/
    --sn-shadow-sm: 0 1px 2px rgba(0,0,0,0.4);
    --sn-shadow-md: 0 8px 24px -8px rgba(0,0,0,0.65);
    --sn-shadow-lg: 0 24px 64px -24px rgba(0,0,0,0.85);
    --sn-blur: saturate(150%) blur(18px);
}

/* ═══ Reset & type ══════════════════════════════════════════════════════════ */

html, body, .stApp {
    font-family: var(--sn-font-body);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

h1, h2, h3, h4, h5, h6,
[data-testid="stHeading"] h1, [data-testid="stHeading"] h2,
[data-testid="stHeading"] h3, [data-testid="stHeading"] h4 {
    font-family: var(--sn-font-display);
    letter-spacing: -0.022em;
    color: var(--sn-ink-primary);
}

code, kbd, pre, [data-testid="stCode"] {
    font-family: var(--sn-font-mono) !important;
    font-variant-ligatures: none;
}

::selection { background: var(--sn-cyan-a40); color: #FFFFFF; }

/* ═══ Backdrop: aurora + grain ══════════════════════════════════════════════ */

/* The backdrop lives on <body>, not on .stApp. Streamlit's app container is a
   zero-height positioned wrapper, so giving it a stacking context of its own
   detaches the fixed layers from the paint order. Painting on <body> and
   clearing Streamlit's opaque ground keeps the layering honest. */

html, body {
    background: var(--sn-surface-base);
}

.stApp,
[data-testid="stAppViewContainer"] {
    background: transparent;
}

/* Three slow-drifting colour fields. Blurred to the point of being light,
   not shapes — they add depth without competing with the data. */
body::before {
    content: "";
    position: fixed;
    inset: -30vmax;
    z-index: -2;
    pointer-events: none;
    background:
        radial-gradient(38vmax 30vmax at 12% 8%,  rgba(34,211,238,0.16), transparent 62%),
        radial-gradient(44vmax 34vmax at 88% 4%,  rgba(167,139,250,0.15), transparent 64%),
        radial-gradient(40vmax 40vmax at 72% 88%, rgba(56,189,248,0.10), transparent 66%),
        radial-gradient(34vmax 28vmax at 18% 92%, rgba(163,230,53,0.07), transparent 60%);
    filter: blur(28px);
    animation: sn-drift 34s var(--sn-ease-inout) infinite alternate;
}

body::after {
    content: "";
    position: fixed;
    inset: 0;
    z-index: -1;
    pointer-events: none;
    opacity: 0.035;
    background-image: /*__GRAIN__*/;
}

@keyframes sn-drift {
    0%   { transform: translate3d(0,0,0) rotate(0deg)   scale(1); }
    50%  { transform: translate3d(2.5%, -2%, 0) rotate(4deg) scale(1.08); }
    100% { transform: translate3d(-2%, 2.5%, 0) rotate(-4deg) scale(1.04); }
}

/* ═══ Layout ════════════════════════════════════════════════════════════════ */

.stMainBlockContainer, [data-testid="stMainBlockContainer"] {
    padding: 1.25rem 3rem 5rem 3rem;
    max-width: 1520px;
}

@media (max-width: 900px) {
    .stMainBlockContainer, [data-testid="stMainBlockContainer"] { padding: 1rem 1.1rem 4rem; }
}

[data-testid="stHeader"] {
    background: rgba(7,8,15,0.55);
    backdrop-filter: var(--sn-blur);
    -webkit-backdrop-filter: var(--sn-blur);
    border-bottom: 1px solid var(--sn-line-hairline);
}

[data-testid="stToolbar"] { right: 1rem; }

/* Streamlit's default 1px separators are too loud on a dark ground. */
hr, [data-testid="stDivider"] hr {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--sn-line-subtle) 12%,
                                var(--sn-line-subtle) 88%, transparent);
    margin: 1.75rem 0;
}

/* ═══ Sidebar ═══════════════════════════════════════════════════════════════ */

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(12,16,32,0.94) 0%, rgba(7,8,15,0.97) 100%);
    backdrop-filter: var(--sn-blur);
    -webkit-backdrop-filter: var(--sn-blur);
    border-right: 1px solid var(--sn-line-hairline);
    box-shadow: 1px 0 0 rgba(34,211,238,0.05), var(--sn-shadow-lg);
}

[data-testid="stSidebar"] > div:first-child { padding-top: 0.5rem; }

[data-testid="stSidebarContent"] { padding: 0 0.9rem 1.5rem; }

[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarCollapsedControl"] button {
    color: var(--sn-ink-secondary);
    transition: color 160ms var(--sn-ease-out);
}
[data-testid="stSidebarCollapseButton"] button:hover { color: var(--sn-cyan); }

/* ═══ Navigation ════════════════════════════════════════════════════════════ */

[data-testid="stLogo"] {
    height: auto;
    max-height: 2.6rem;
    width: auto;
    margin: 0.45rem 0 0.2rem 0.35rem;
}

[data-testid="stSidebarNav"] { padding: 0.2rem 0 0.4rem; }

[data-testid="stSidebarNav"] ul {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}

[data-testid="stNavSectionHeader"] {
    padding: 0.95rem 0.6rem 0.3rem !important;
    background: transparent !important;
}

[data-testid="stNavSectionHeader"] p {
    font-family: var(--sn-font-mono);
    font-size: 0.6rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--sn-ink-faint) !important;
}

[data-testid="stSidebarNavLink"] {
    position: relative;
    padding: 0.52rem 0.85rem !important;
    border-radius: 0.7rem !important;
    border: 1px solid transparent;
    background: transparent !important;
    overflow: hidden;
    transition: background 180ms var(--sn-ease-out),
                border-color 180ms var(--sn-ease-out),
                transform 180ms var(--sn-ease-out);
}

[data-testid="stSidebarNavLink"]:hover {
    background: rgba(255,255,255,0.05) !important;
    border-color: var(--sn-line-hairline);
    transform: translateX(2px);
}

/* The live rail on the current page. */
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background: linear-gradient(90deg, var(--sn-cyan-a12),
                                rgba(167,139,250,0.06) 70%, transparent) !important;
    border-color: var(--sn-cyan-a24);
}

[data-testid="stSidebarNavLink"][aria-current="page"]::before {
    content: "";
    position: absolute;
    left: 0; top: 18%; bottom: 18%;
    width: 3px;
    border-radius: 0 3px 3px 0;
    background: var(--sn-gradient-brand);
    box-shadow: 0 0 12px var(--sn-cyan-a40);
}

[data-testid="stSidebarNavLink"] span {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--sn-ink-secondary) !important;
    transition: color 180ms var(--sn-ease-out);
}

[data-testid="stSidebarNavLink"][aria-current="page"] span {
    color: var(--sn-ink-primary) !important;
    font-weight: 600;
}

[data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] {
    font-size: 1.05rem;
    opacity: 0.7;
    transition: opacity 180ms var(--sn-ease-out), color 180ms var(--sn-ease-out);
}

[data-testid="stSidebarNavLink"]:hover [data-testid="stIconMaterial"] { opacity: 1; }

[data-testid="stSidebarNavLink"][aria-current="page"] [data-testid="stIconMaterial"] {
    color: var(--sn-cyan) !important;
    opacity: 1;
}

/* Separator Streamlit draws under the nav block. */
[data-testid="stSidebarNavSeparator"] {
    border-color: var(--sn-line-hairline) !important;
    margin: 0.4rem 0.3rem;
}

/* ═══ Metrics ═══════════════════════════════════════════════════════════════ */

[data-testid="stMetric"] {
    background: linear-gradient(160deg, rgba(255,255,255,0.045), rgba(255,255,255,0.012));
    border: 1px solid var(--sn-line-hairline);
    border-radius: 1rem;
    padding: 1.05rem 1.2rem;
    position: relative;
    overflow: hidden;
    transition: transform 240ms var(--sn-ease-out),
                border-color 240ms var(--sn-ease-out),
                box-shadow 240ms var(--sn-ease-out);
}

[data-testid="stMetric"]::before {
    content: "";
    position: absolute;
    inset: 0 0 auto 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--sn-cyan-a40) 30%,
                                rgba(167,139,250,0.35) 70%, transparent);
    opacity: 0.7;
}

[data-testid="stMetric"]:hover {
    transform: translateY(-3px);
    border-color: var(--sn-cyan-a24);
    box-shadow: var(--sn-shadow-md), 0 0 0 1px var(--sn-cyan-a12);
}

[data-testid="stMetricLabel"] p {
    font-size: 0.7rem !important;
    font-weight: 600;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--sn-ink-muted);
}

[data-testid="stMetricValue"] {
    font-family: var(--sn-font-display);
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.03em;
    line-height: 1.1;
}

[data-testid="stMetricDelta"] { font-size: 0.8rem; font-weight: 600; }

/* ═══ Buttons ═══════════════════════════════════════════════════════════════ */

.stButton button, .stFormSubmitButton button, .stDownloadButton button {
    font-weight: 600;
    letter-spacing: 0.005em;
    border-radius: 0.75rem;
    transition: transform 180ms var(--sn-ease-spring),
                box-shadow 220ms var(--sn-ease-out),
                filter 220ms var(--sn-ease-out);
    position: relative;
    overflow: hidden;
}

.stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {
    background: var(--sn-gradient-brand);
    border: none;
    color: #04121A;
    box-shadow: 0 6px 22px -8px var(--sn-cyan-a40), inset 0 1px 0 rgba(255,255,255,0.28);
}

/* Sheen sweep on hover — a single pass, not a loop. */
.stButton button[kind="primary"]::after,
.stFormSubmitButton button[kind="primary"]::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(110deg, transparent 20%, rgba(255,255,255,0.45) 50%, transparent 80%);
    transform: translateX(-130%);
    transition: transform 720ms var(--sn-ease-out);
}

.stButton button[kind="primary"]:hover::after,
.stFormSubmitButton button[kind="primary"]:hover::after { transform: translateX(130%); }

.stButton button:hover, .stFormSubmitButton button:hover, .stDownloadButton button:hover {
    transform: translateY(-2px);
    filter: brightness(1.06);
    box-shadow: 0 12px 30px -10px var(--sn-cyan-a40);
}

.stButton button:active, .stFormSubmitButton button:active { transform: translateY(0); }

.stButton button[kind="secondary"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--sn-line-subtle);
    color: var(--sn-ink-secondary);
}
.stButton button[kind="secondary"]:hover {
    border-color: var(--sn-cyan-a40);
    color: var(--sn-ink-primary);
}

/* ═══ Inputs ════════════════════════════════════════════════════════════════ */

[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
    background: rgba(255,255,255,0.035) !important;
    border: 1px solid var(--sn-line-hairline) !important;
    border-radius: 0.7rem !important;
    transition: border-color 180ms var(--sn-ease-out), box-shadow 180ms var(--sn-ease-out);
}

[data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover,
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div:hover {
    border-color: var(--sn-line-strong) !important;
}

[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within > div,
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: var(--sn-cyan-a40) !important;
    box-shadow: 0 0 0 3px var(--sn-cyan-a12) !important;
}

[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label {
    font-size: 0.74rem !important;
    font-weight: 600;
    letter-spacing: 0.085em;
    text-transform: uppercase;
    color: var(--sn-ink-muted);
}

/* Popover surface for dropdowns */
div[data-baseweb="popover"] ul, div[data-baseweb="popover"] > div {
    background: var(--sn-surface-overlay) !important;
    border: 1px solid var(--sn-line-subtle) !important;
    border-radius: 0.8rem !important;
    box-shadow: var(--sn-shadow-lg) !important;
}
div[data-baseweb="popover"] li:hover { background: var(--sn-cyan-a12) !important; }

/* Sliders */
[data-testid="stSlider"] [role="slider"] {
    box-shadow: 0 0 0 4px var(--sn-cyan-a12), 0 2px 8px rgba(0,0,0,0.5);
}

/* ═══ Tabs ══════════════════════════════════════════════════════════════════ */

.stTabs [data-baseweb="tab-list"] {
    gap: 0.35rem;
    background: rgba(255,255,255,0.025);
    border: 1px solid var(--sn-line-hairline);
    border-radius: 0.9rem;
    padding: 0.3rem;
}

.stTabs [data-baseweb="tab-list"] button[data-baseweb="tab"] {
    border-radius: 0.65rem;
    padding: 0.45rem 1rem;
    font-weight: 550;
    font-size: 0.86rem;
    color: var(--sn-ink-muted);
    transition: color 180ms var(--sn-ease-out), background 180ms var(--sn-ease-out);
}

.stTabs [data-baseweb="tab-list"] button[data-baseweb="tab"]:hover {
    color: var(--sn-ink-secondary);
    background: rgba(255,255,255,0.04);
}

.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    background: linear-gradient(135deg, var(--sn-cyan-a24), rgba(167,139,250,0.14));
    color: var(--sn-ink-primary);
    box-shadow: inset 0 0 0 1px var(--sn-cyan-a24);
}

.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

/* ═══ Data display ══════════════════════════════════════════════════════════ */

[data-testid="stDataFrame"], [data-testid="stTable"] {
    border-radius: 0.9rem;
    overflow: hidden;
    border: 1px solid var(--sn-line-hairline);
    box-shadow: var(--sn-shadow-sm);
}

[data-testid="stDataFrame"] [role="columnheader"] {
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    color: var(--sn-ink-muted) !important;
}

[data-testid="stDataFrame"] [role="gridcell"] { font-variant-numeric: tabular-nums; }

/* Charts sit on glass so they read as one object with their caption. */
[data-testid="stPlotlyChart"] {
    border-radius: 1rem;
    overflow: hidden;
    background: linear-gradient(160deg, rgba(255,255,255,0.03), rgba(255,255,255,0.008));
    border: 1px solid var(--sn-line-hairline);
    padding: 0.4rem;
    transition: border-color 260ms var(--sn-ease-out), box-shadow 260ms var(--sn-ease-out);
}
[data-testid="stPlotlyChart"]:hover {
    border-color: var(--sn-line-subtle);
    box-shadow: var(--sn-shadow-md);
}
[data-testid="stPlotlyChart"] .modebar { background: transparent !important; }

/* ═══ Containers, expanders, alerts ═════════════════════════════════════════ */

[data-testid="stExpander"] {
    border: 1px solid var(--sn-line-hairline);
    border-radius: 0.9rem;
    background: rgba(255,255,255,0.02);
    overflow: hidden;
}
[data-testid="stExpander"] summary:hover { background: rgba(255,255,255,0.03); }

[data-testid="stAlert"] {
    border-radius: 0.85rem;
    border-left-width: 3px;
}

[data-testid="stCaptionContainer"] p, .stCaption {
    color: var(--sn-ink-muted);
    font-size: 0.78rem;
    letter-spacing: 0.01em;
}

/* Spinner in brand colour */
[data-testid="stSpinner"] i { border-top-color: var(--sn-cyan) !important; }

/* ═══ Scrollbar ═════════════════════════════════════════════════════════════ */

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.10);
    border-radius: 99px;
    border: 2px solid transparent;
    background-clip: content-box;
}
::-webkit-scrollbar-thumb:hover { background: var(--sn-cyan-a40); background-clip: content-box; }

/* ═══ Entrance choreography ═════════════════════════════════════════════════ */

@keyframes sn-rise {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: none; }
}

/* Stagger the first few blocks of the main column so a page assembles itself
   rather than snapping in. Capped at 6 so long pages stay responsive. */
[data-testid="stMain"] [data-testid="stVerticalBlock"] > div:nth-child(-n+6) {
    animation: sn-rise 620ms var(--sn-ease-out) backwards;
}
[data-testid="stMain"] [data-testid="stVerticalBlock"] > div:nth-child(1) { animation-delay: 0ms; }
[data-testid="stMain"] [data-testid="stVerticalBlock"] > div:nth-child(2) { animation-delay: 55ms; }
[data-testid="stMain"] [data-testid="stVerticalBlock"] > div:nth-child(3) { animation-delay: 110ms; }
[data-testid="stMain"] [data-testid="stVerticalBlock"] > div:nth-child(4) { animation-delay: 165ms; }
[data-testid="stMain"] [data-testid="stVerticalBlock"] > div:nth-child(5) { animation-delay: 220ms; }
[data-testid="stMain"] [data-testid="stVerticalBlock"] > div:nth-child(6) { animation-delay: 275ms; }

/* Respect the OS setting — every animation above is decorative. */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.001ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.001ms !important;
    }
}

/* ═══ Print ═════════════════════════════════════════════════════════════════ */

@media print {
    [data-testid="stSidebar"], [data-testid="stHeader"] { display: none !important; }
    .stApp::before, .stApp::after { display: none !important; }
    .stMainBlockContainer { padding: 0 !important; max-width: none !important; }
}
"""


# The resolved sheet, built once at import.
_RESOLVED = (
    _STYLESHEET
    .replace("/*__VARS__*/", css_variables())
    .replace("/*__GRAIN__*/", _GRAIN)
)

# Registered as an st.components.v2 component rather than injected through
# ``st.html``. Streamlit's HTML sanitizer rejects a <style> of this shape
# outright — silently, taking the entire sheet with it — whereas a component's
# ``css`` channel is delivered verbatim. With ``isolate_styles=False`` there is
# no shadow root, so the rules apply to the whole document as intended.
_theme = st.components.v2.component("sn_theme", css=_RESOLVED, isolate_styles=False)


def inject() -> None:
    """Apply the global stylesheet. Call once per rerun, before any content.

    Web fonts are deliberately not loaded here: they are declared as
    ``[[theme.fontFaces]]`` in ``.streamlit/config.toml`` so that Streamlit's
    own widgets pick them up too.
    """
    _theme()
