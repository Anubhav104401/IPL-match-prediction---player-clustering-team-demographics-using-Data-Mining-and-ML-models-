"""
Franchise identity system.

Every franchise that has ever played in the IPL gets a short code, a primary and
secondary colour drawn from its real kit, and a derived gradient. Encoding teams
by their own colours — instead of an arbitrary categorical ramp — is the single
highest-value visual decision in a cricket dashboard: the reader recognises the
team before they read the label.
"""

from __future__ import annotations

import hashlib
from typing import Final, NamedTuple

from ui.tokens import rgba


class Franchise(NamedTuple):
    """A franchise's visual identity."""

    name: str
    code: str
    primary: str
    secondary: str

    @property
    def gradient(self) -> str:
        return f"linear-gradient(135deg, {self.primary} 0%, {self.secondary} 100%)"

    @property
    def glow(self) -> str:
        return rgba(self.primary, 0.45)


# Kit colours, sampled from official franchise branding.
_FRANCHISES: Final[tuple[Franchise, ...]] = (
    Franchise("Chennai Super Kings",        "CSK",  "#F9CD05", "#005DB7"),
    Franchise("Mumbai Indians",             "MI",   "#1B6FB5", "#D1AB3E"),
    Franchise("Royal Challengers Bangalore","RCB",  "#D5152C", "#2B2B2B"),
    Franchise("Royal Challengers Bengaluru","RCB",  "#D5152C", "#2B2B2B"),
    Franchise("Kolkata Knight Riders",      "KKR",  "#6A3FA0", "#D4AF37"),
    Franchise("Rajasthan Royals",           "RR",   "#EA1A85", "#254AA5"),
    Franchise("Sunrisers Hyderabad",        "SRH",  "#F26522", "#DC1F2E"),
    Franchise("Delhi Capitals",             "DC",   "#2561AE", "#EF1B23"),
    Franchise("Delhi Daredevils",           "DD",   "#2561AE", "#B4975A"),
    Franchise("Punjab Kings",               "PBKS", "#DD1F2D", "#A7A9AC"),
    Franchise("Kings XI Punjab",            "KXIP", "#DD1F2D", "#8E8E93"),
    Franchise("Gujarat Titans",             "GT",   "#4B6A9B", "#B9A16B"),
    Franchise("Lucknow Super Giants",       "LSG",  "#3496D6", "#E9B33E"),
    Franchise("Deccan Chargers",            "DCH",  "#28598A", "#B6BAC4"),
    Franchise("Kochi Tuskers Kerala",       "KTK",  "#E4632D", "#F2A65A"),
    Franchise("Pune Warriors",              "PW",   "#2E86AB", "#6EC5E9"),
    Franchise("Rising Pune Supergiants",    "RPS",  "#4A5FC1", "#E23D64"),
    Franchise("Rising Pune Supergiant",     "RPS",  "#4A5FC1", "#E23D64"),
    Franchise("Gujarat Lions",              "GL",   "#E04F16", "#F5A623"),
)

_BY_NAME: Final[dict[str, Franchise]] = {f.name.lower(): f for f in _FRANCHISES}

# Fallback palette for any name we do not recognise — deterministic per name so
# an unknown team keeps the same colour across reruns and across pages.
_FALLBACK: Final[tuple[tuple[str, str], ...]] = (
    ("#22D3EE", "#0E7490"), ("#A78BFA", "#5B21B6"), ("#A3E635", "#4D7C0F"),
    ("#FBBF24", "#B45309"), ("#FB7185", "#9F1239"), ("#38BDF8", "#075985"),
)


def _initials(name: str) -> str:
    words = [w for w in name.replace("-", " ").split() if w[:1].isalpha()]
    if not words:
        return name[:3].upper()
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:4]).upper()


def franchise(name: str | None) -> Franchise:
    """Resolve a team name to its identity, inventing a stable one if unknown."""
    if not name:
        return Franchise("Unknown", "TBD", "#6C7796", "#3D4763")

    key = str(name).strip().lower()
    if key in _BY_NAME:
        return _BY_NAME[key]

    # Tolerate spelling drift across seasons (e.g. Bangalore → Bengaluru).
    for known_key, value in _BY_NAME.items():
        if known_key in key or key in known_key:
            return value

    digest = hashlib.md5(key.encode()).hexdigest()
    primary, secondary = _FALLBACK[int(digest[:8], 16) % len(_FALLBACK)]
    return Franchise(str(name), _initials(str(name)), primary, secondary)


def code(name: str | None) -> str:
    """Short code for a team, e.g. ``Chennai Super Kings`` → ``CSK``."""
    return franchise(name).code


def color(name: str | None) -> str:
    """Primary kit colour for a team."""
    return franchise(name).primary


def color_map(names) -> dict[str, str]:
    """Build a Plotly ``color_discrete_map`` for a set of team names."""
    return {str(n): color(n) for n in names}


# ── Player cluster identity ───────────────────────────────────────────────────
# Cluster labels come out of KMeans as human-readable archetypes; giving each a
# fixed colour and glyph makes the scatter legible without reading the legend.
CLUSTER_STYLE: Final[dict[str, tuple[str, str]]] = {
    # Vocabulary emitted by clustering.assign_cluster_labels().
    "Elite All-Rounder":   ("#A3E635", "✦"),
    "Impact Player":       ("#FBBF24", "◆"),
    "Top Batsman":         ("#FB7185", "▲"),
    "Specialist Batsman":  ("#F472B6", "▲"),
    "Key Bowler":          ("#A78BFA", "◈"),
    "Specialist Bowler":   ("#818CF8", "◈"),
    "Role Player":         ("#38BDF8", "●"),
    "Tail-Ender":          ("#34D399", "◐"),
    "Noise/Outlier":       ("#6C7796", "○"),
    "Unknown":             ("#6C7796", "○"),
}


def cluster_color(label: str | None) -> str:
    """Colour for a cluster archetype, falling back to the shared palette."""
    if label in CLUSTER_STYLE:
        return CLUSTER_STYLE[label][0]
    from ui.tokens import CATEGORICAL

    digest = hashlib.md5(str(label).encode()).hexdigest()
    return CATEGORICAL[int(digest[:8], 16) % len(CATEGORICAL)]


def cluster_glyph(label: str | None) -> str:
    """Glyph for a cluster archetype."""
    return CLUSTER_STYLE.get(str(label), ("", "◆"))[1]


def cluster_color_map(labels) -> dict[str, str]:
    return {str(label): cluster_color(str(label)) for label in labels}
