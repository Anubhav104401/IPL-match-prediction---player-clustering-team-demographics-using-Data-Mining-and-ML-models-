"""
Design tokens — the single source of truth for the "Stadium Nights" theme.

Everything that renders colour in this app (CSS, Plotly, inline SVG, custom
components) reads from here, so the widget chrome, the charts and the bespoke
components can never drift apart. `.streamlit/config.toml` mirrors these values
for the parts of Streamlit that are configured before Python runs.
"""

from __future__ import annotations

from typing import Final

# ── Surfaces ──────────────────────────────────────────────────────────────────
# A five-step elevation ramp. Higher index = closer to the viewer.
SURFACE: Final[dict[str, str]] = {
    "void":      "#05060C",   # page backdrop, behind the aurora
    "base":      "#07080F",   # app background
    "raised":    "#0C1020",   # cards
    "overlay":   "#111528",   # popovers, table headers
    "elevated":  "#161C33",   # hover states
}

# ── Ink ───────────────────────────────────────────────────────────────────────
INK: Final[dict[str, str]] = {
    "primary":   "#E6EAF7",
    "secondary": "#A3AECB",
    "muted":     "#6C7796",
    "faint":     "#3D4763",
    "inverse":   "#05060C",
}

# ── Lines ─────────────────────────────────────────────────────────────────────
LINE: Final[dict[str, str]] = {
    "hairline": "rgba(255,255,255,0.06)",
    "subtle":   "rgba(255,255,255,0.10)",
    "strong":   "rgba(255,255,255,0.16)",
    "glow":     "rgba(34,211,238,0.35)",
}

# ── Accents ───────────────────────────────────────────────────────────────────
ACCENT: Final[dict[str, str]] = {
    "cyan":   "#22D3EE",
    "violet": "#A78BFA",
    "lime":   "#A3E635",
    "amber":  "#FBBF24",
    "rose":   "#FB7185",
    "sky":    "#38BDF8",
    "mint":   "#34D399",
    "pink":   "#F472B6",
    "orange": "#FB923C",
    "indigo": "#818CF8",
}

# Ordered palette used for every categorical encoding in the app.
CATEGORICAL: Final[list[str]] = [
    ACCENT["cyan"], ACCENT["violet"], ACCENT["lime"], ACCENT["amber"],
    ACCENT["rose"], ACCENT["sky"], ACCENT["mint"], ACCENT["pink"],
    ACCENT["orange"], ACCENT["indigo"],
]

# Perceptually-ordered ramps, authored dark→light so they read on a dark ground.
SEQUENTIAL: Final[list[str]] = [
    "#0B1B2B", "#0E2E44", "#0F455C", "#0D5D74", "#0A768B",
    "#0790A1", "#0FABB6", "#33C6CA", "#6BDFDD", "#A9F2EE",
]

DIVERGING: Final[list[str]] = [
    "#7F1D3A", "#A8264A", "#CE3A5B", "#E4657B", "#F0A8AF",
    "#A8DCCB", "#4FC3A1", "#22A67F", "#0D8562", "#08644A",
]

# ── Gradients ─────────────────────────────────────────────────────────────────
GRADIENT: Final[dict[str, str]] = {
    "brand":   "linear-gradient(135deg, #22D3EE 0%, #818CF8 55%, #A78BFA 100%)",
    "success": "linear-gradient(135deg, #34D399 0%, #A3E635 100%)",
    "warn":    "linear-gradient(135deg, #FBBF24 0%, #FB923C 100%)",
    "danger":  "linear-gradient(135deg, #FB7185 0%, #F472B6 100%)",
    "cool":    "linear-gradient(135deg, #38BDF8 0%, #22D3EE 100%)",
    "royal":   "linear-gradient(135deg, #818CF8 0%, #A78BFA 60%, #F472B6 100%)",
}

# ── Typography ────────────────────────────────────────────────────────────────
FONT: Final[dict[str, str]] = {
    "display": "'Space Grotesk', 'Inter', system-ui, sans-serif",
    "body":    "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif",
    "mono":    "'JetBrains Mono', 'SF Mono', ui-monospace, monospace",
}

#: The families above are loaded by Streamlit itself — see the
#: ``[[theme.fontFaces]]`` tables in ``.streamlit/config.toml``. Injected CSS
#: cannot load them: a remote ``@import`` makes the sanitizer drop the sheet.

# ── Motion ────────────────────────────────────────────────────────────────────
EASE: Final[dict[str, str]] = {
    "out":    "cubic-bezier(0.16, 1, 0.3, 1)",       # decelerating, for entrances
    "inout":  "cubic-bezier(0.65, 0, 0.35, 1)",
    "spring": "cubic-bezier(0.34, 1.56, 0.64, 1)",   # slight overshoot
}


def rgba(hex_color: str, alpha: float) -> str:
    """Convert ``#RRGGBB`` to an ``rgba()`` string at the given alpha."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def css_variables() -> str:
    """Emit every token as a CSS custom property on ``:root``."""
    lines: list[str] = []
    for name, value in SURFACE.items():
        lines.append(f"--sn-surface-{name}: {value};")
    for name, value in INK.items():
        lines.append(f"--sn-ink-{name}: {value};")
    for name, value in LINE.items():
        lines.append(f"--sn-line-{name}: {value};")
    for name, value in ACCENT.items():
        lines.append(f"--sn-{name}: {value};")
        lines.append(f"--sn-{name}-a12: {rgba(value, 0.12)};")
        lines.append(f"--sn-{name}-a24: {rgba(value, 0.24)};")
        lines.append(f"--sn-{name}-a40: {rgba(value, 0.40)};")
    for name, value in GRADIENT.items():
        lines.append(f"--sn-gradient-{name}: {value};")
    for name, value in FONT.items():
        lines.append(f"--sn-font-{name}: {value};")
    for name, value in EASE.items():
        lines.append(f"--sn-ease-{name}: {value};")
    return "\n    ".join(lines)
