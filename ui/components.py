"""
Bespoke UI primitives.

Streamlit gives us widgets; this module gives us a *design system*. Markup is
rendered as real DOM rather than an iframe, so components inherit the page's
fonts, tokens and stacking context. The stylesheet travels through the
components.v2 ``css`` channel (Streamlit's HTML sanitizer rejects a sheet of
this shape), and one small JavaScript component (``mount_runtime``) wires up
the behaviours CSS cannot do alone: count-up numerals and cursor-tracked
card lighting.
"""

from __future__ import annotations

import html
from typing import Iterable, Sequence

import streamlit as st

from ui.brand import Franchise, franchise
from ui.tokens import ACCENT, rgba

# ──────────────────────────────────────────────────────────────────────────────
#  Component stylesheet
# ──────────────────────────────────────────────────────────────────────────────

_CSS = """
/* ═══ Shared card surface ═══════════════════════════════════════════════════ */

.sn-card {
    position: relative;
    border-radius: 1.15rem;
    border: 1px solid var(--sn-line-hairline);
    background:
        radial-gradient(520px circle at var(--mx, 50%) var(--my, -20%),
                        rgba(255,255,255,0.055), transparent 42%),
        linear-gradient(160deg, rgba(255,255,255,0.04), rgba(255,255,255,0.008));
    overflow: hidden;
    transition: border-color 280ms var(--sn-ease-out),
                box-shadow 280ms var(--sn-ease-out),
                transform 280ms var(--sn-ease-out);
}

.sn-card:hover {
    border-color: var(--sn-line-subtle);
    box-shadow: 0 18px 46px -22px rgba(0,0,0,0.9);
}

/* ═══ Hero ══════════════════════════════════════════════════════════════════ */

.sn-hero {
    position: relative;
    padding: 2.1rem 2.3rem 1.9rem;
    margin-bottom: 1.4rem;
    border-radius: 1.4rem;
    border: 1px solid var(--sn-line-hairline);
    background:
        radial-gradient(900px circle at 8% -30%, var(--hero-a, rgba(34,211,238,0.18)), transparent 55%),
        radial-gradient(700px circle at 92% 130%, var(--hero-b, rgba(167,139,250,0.16)), transparent 55%),
        linear-gradient(150deg, rgba(255,255,255,0.045), rgba(255,255,255,0.005));
    overflow: hidden;
}

/* Faint pitch-line geometry, echoing a cricket field's concentric rings. */
.sn-hero::after {
    content: "";
    position: absolute;
    right: -8%;
    top: -60%;
    width: 34rem;
    height: 34rem;
    border-radius: 50%;
    border: 1px solid rgba(255,255,255,0.05);
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.03),
                inset 0 0 0 5rem rgba(255,255,255,0.012),
                inset 0 0 0 10rem rgba(255,255,255,0.012);
    pointer-events: none;
}

.sn-hero__eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-family: var(--sn-font-mono);
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--sn-cyan);
    padding: 0.3rem 0.7rem;
    border-radius: 99px;
    background: var(--sn-cyan-a12);
    border: 1px solid var(--sn-cyan-a24);
}

.sn-hero__title {
    margin: 0.85rem 0 0;
    font-family: var(--sn-font-display);
    font-size: clamp(1.9rem, 3.4vw, 3rem);
    font-weight: 700;
    line-height: 1.04;
    letter-spacing: -0.035em;
    background: linear-gradient(120deg, #FFFFFF 8%, #C9D4F0 46%, var(--sn-cyan) 96%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    max-width: 22ch;
}

.sn-hero__sub {
    margin: 0.85rem 0 0;
    max-width: 68ch;
    font-size: 0.98rem;
    line-height: 1.6;
    color: var(--sn-ink-secondary);
}

.sn-hero__meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 1.25rem;
}

/* ═══ Pills & badges ════════════════════════════════════════════════════════ */

.sn-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.42rem;
    padding: 0.34rem 0.78rem;
    border-radius: 99px;
    font-size: 0.755rem;
    font-weight: 550;
    letter-spacing: 0.015em;
    color: var(--sn-ink-secondary);
    background: rgba(255,255,255,0.045);
    border: 1px solid var(--sn-line-hairline);
    white-space: nowrap;
}

.sn-pill__dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--dot, var(--sn-cyan));
    box-shadow: 0 0 8px var(--dot, var(--sn-cyan));
}

.sn-pill--live .sn-pill__dot { animation: sn-pulse 2.2s ease-in-out infinite; }

@keyframes sn-pulse {
    0%, 100% { opacity: 1;   transform: scale(1); }
    50%      { opacity: 0.35; transform: scale(0.82); }
}

/* ═══ Section header ════════════════════════════════════════════════════════ */

.sn-section {
    display: flex;
    align-items: baseline;
    gap: 0.85rem;
    margin: 2.2rem 0 1.05rem;
}

.sn-section__idx {
    font-family: var(--sn-font-mono);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--sn-ink-faint);
    padding-top: 0.2rem;
}

.sn-section__title {
    font-family: var(--sn-font-display);
    font-size: 1.32rem;
    font-weight: 650;
    letter-spacing: -0.02em;
    color: var(--sn-ink-primary);
    white-space: nowrap;
}

.sn-section__desc {
    font-size: 0.83rem;
    color: var(--sn-ink-muted);
    line-height: 1.5;
}

.sn-section__rule {
    flex: 1;
    height: 1px;
    min-width: 1.5rem;
    background: linear-gradient(90deg, var(--sn-line-subtle), transparent);
}

/* ═══ Stat tiles ════════════════════════════════════════════════════════════ */

.sn-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.85rem;
}

.sn-stat {
    position: relative;
    padding: 1.05rem 1.15rem 0.95rem;
    border-radius: 1.05rem;
    border: 1px solid var(--sn-line-hairline);
    background:
        radial-gradient(420px circle at var(--mx, 50%) var(--my, -30%),
                        var(--accent-soft, rgba(255,255,255,0.05)), transparent 45%),
        linear-gradient(165deg, rgba(255,255,255,0.045), rgba(255,255,255,0.01));
    overflow: hidden;
    transition: transform 300ms var(--sn-ease-out),
                border-color 300ms var(--sn-ease-out),
                box-shadow 300ms var(--sn-ease-out);
}

.sn-stat::before {
    content: "";
    position: absolute;
    inset: 0 0 auto 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), transparent 78%);
    opacity: 0.85;
}

.sn-stat:hover {
    transform: translateY(-4px);
    border-color: var(--accent-line, var(--sn-line-subtle));
    box-shadow: 0 20px 40px -24px var(--accent-glow, rgba(0,0,0,0.9));
}

.sn-stat__head {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.7rem;
}

.sn-stat__icon {
    display: grid;
    place-items: center;
    width: 1.65rem; height: 1.65rem;
    border-radius: 0.55rem;
    font-size: 0.86rem;
    background: var(--accent-soft, rgba(255,255,255,0.06));
    border: 1px solid var(--accent-line, var(--sn-line-hairline));
}

.sn-stat__label {
    font-size: 0.665rem;
    font-weight: 700;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    color: var(--sn-ink-muted);
}

.sn-stat__value {
    font-family: var(--sn-font-display);
    font-size: 1.95rem;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.035em;
    color: var(--sn-ink-primary);
    font-variant-numeric: tabular-nums;
    display: flex;
    align-items: baseline;
    gap: 0.22rem;
}

.sn-stat__unit {
    font-size: 0.92rem;
    font-weight: 600;
    color: var(--sn-ink-muted);
    letter-spacing: 0;
}

.sn-stat__foot {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 0.6rem;
    margin-top: 0.6rem;
    min-height: 1.4rem;
}

.sn-stat__note {
    font-size: 0.72rem;
    color: var(--sn-ink-muted);
    line-height: 1.35;
}

.sn-stat__spark { opacity: 0.9; flex-shrink: 0; }

/* ═══ Ranked bar list ═══════════════════════════════════════════════════════ */

.sn-ranks { display: flex; flex-direction: column; gap: 0.55rem; }

.sn-rank {
    display: grid;
    grid-template-columns: 1.6rem 1fr auto;
    align-items: center;
    gap: 0.7rem;
    padding: 0.42rem 0.6rem;
    border-radius: 0.7rem;
    transition: background 200ms var(--sn-ease-out);
}

.sn-rank:hover { background: rgba(255,255,255,0.035); }

.sn-rank__pos {
    font-family: var(--sn-font-mono);
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--sn-ink-faint);
    text-align: right;
}

.sn-rank__body { min-width: 0; }

.sn-rank__label {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--sn-ink-secondary);
    margin-bottom: 0.3rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.sn-rank__track {
    height: 6px;
    border-radius: 99px;
    background: rgba(255,255,255,0.055);
    overflow: hidden;
}

.sn-rank__fill {
    height: 100%;
    border-radius: 99px;
    background: var(--fill, var(--sn-gradient-brand));
    box-shadow: 0 0 12px -2px var(--fill-glow, transparent);
    transform-origin: left;
    animation: sn-grow 900ms var(--sn-ease-out) backwards;
}

@keyframes sn-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }

.sn-rank__value {
    font-family: var(--sn-font-mono);
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--sn-ink-primary);
    font-variant-numeric: tabular-nums;
}

/* ═══ Franchise crest ═══════════════════════════════════════════════════════ */

.sn-crest {
    display: grid;
    place-items: center;
    border-radius: 50%;
    font-family: var(--sn-font-display);
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #FFFFFF;
    background: var(--crest, #333);
    box-shadow: 0 0 0 1px rgba(255,255,255,0.14),
                0 0 0 5px rgba(255,255,255,0.03),
                0 12px 30px -12px var(--crest-glow, rgba(0,0,0,0.8));
    text-shadow: 0 1px 3px rgba(0,0,0,0.45);
    flex-shrink: 0;
}

.sn-crest--sm { width: 1.5rem; height: 1.5rem; font-size: 0.55rem; }
.sn-crest--md { width: 2.6rem; height: 2.6rem; font-size: 0.82rem; }
.sn-crest--lg { width: 5.6rem; height: 5.6rem; font-size: 1.55rem; }

/* ═══ Versus panel ══════════════════════════════════════════════════════════ */

.sn-vs {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 1.4rem;
    padding: 2rem 1.6rem;
    border-radius: 1.3rem;
    border: 1px solid var(--sn-line-hairline);
    background:
        radial-gradient(680px circle at 0% 50%, var(--home-glow), transparent 52%),
        radial-gradient(680px circle at 100% 50%, var(--away-glow), transparent 52%),
        linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.008));
    overflow: hidden;
}

.sn-vs__side {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    text-align: center;
}

.sn-vs__name {
    font-family: var(--sn-font-display);
    font-size: 1.02rem;
    font-weight: 650;
    letter-spacing: -0.015em;
    color: var(--sn-ink-primary);
    line-height: 1.25;
    max-width: 14ch;
}

.sn-vs__role {
    font-family: var(--sn-font-mono);
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--sn-ink-faint);
}

.sn-vs__mid { display: grid; place-items: center; gap: 0.6rem; }

.sn-vs__glyph {
    display: grid;
    place-items: center;
    width: 3rem; height: 3rem;
    border-radius: 0.9rem;
    transform: rotate(45deg);
    border: 1px solid var(--sn-line-subtle);
    background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
}

.sn-vs__glyph span {
    transform: rotate(-45deg);
    font-family: var(--sn-font-display);
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: var(--sn-ink-secondary);
}

.sn-vs__venue {
    font-size: 0.72rem;
    color: var(--sn-ink-muted);
    text-align: center;
    max-width: 18ch;
    line-height: 1.4;
}

/* ═══ Verdict (prediction result) ═══════════════════════════════════════════ */

.sn-verdict {
    display: grid;
    grid-template-columns: auto 1fr;
    align-items: center;
    gap: 1.6rem;
    padding: 1.7rem 1.9rem;
    border-radius: 1.3rem;
    border: 1px solid var(--win-line);
    background:
        radial-gradient(600px circle at 12% 50%, var(--win-glow), transparent 58%),
        linear-gradient(150deg, rgba(255,255,255,0.045), rgba(255,255,255,0.008));
    overflow: hidden;
    animation: sn-verdict-in 700ms var(--sn-ease-spring) backwards;
}

@keyframes sn-verdict-in {
    from { opacity: 0; transform: translateY(18px) scale(0.985); }
    to   { opacity: 1; transform: none; }
}

.sn-verdict__label {
    font-family: var(--sn-font-mono);
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--sn-ink-muted);
}

.sn-verdict__name {
    font-family: var(--sn-font-display);
    font-size: clamp(1.4rem, 2.6vw, 2.05rem);
    font-weight: 700;
    letter-spacing: -0.03em;
    line-height: 1.1;
    margin: 0.4rem 0 0.7rem;
    color: var(--sn-ink-primary);
}

.sn-verdict__meta { display: flex; flex-wrap: wrap; gap: 0.45rem; }

/* ═══ Confidence ring ═══════════════════════════════════════════════════════ */

.sn-ring { position: relative; display: grid; place-items: center; }

.sn-ring svg { transform: rotate(-90deg); overflow: visible; }

.sn-ring__arc {
    stroke-linecap: round;
    fill: none;
    filter: drop-shadow(0 0 6px var(--ring-glow, transparent));
    animation: sn-sweep 1.25s var(--sn-ease-out) backwards;
}

@keyframes sn-sweep { from { stroke-dashoffset: var(--circ); } }

.sn-ring__center {
    position: absolute;
    display: grid;
    place-items: center;
    line-height: 1;
}

.sn-ring__num {
    font-family: var(--sn-font-display);
    font-size: 1.42rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--sn-ink-primary);
    font-variant-numeric: tabular-nums;
}

.sn-ring__cap {
    font-family: var(--sn-font-mono);
    font-size: 0.52rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--sn-ink-faint);
    margin-top: 0.25rem;
}

/* ═══ Insight callout ═══════════════════════════════════════════════════════ */

.sn-insight {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.85rem;
    align-items: start;
    padding: 0.95rem 1.15rem;
    border-radius: 0.95rem;
    border: 1px solid var(--tone-line);
    border-left: 3px solid var(--tone);
    background: var(--tone-bg);
}

.sn-insight__icon { font-size: 0.95rem; line-height: 1.5; }

.sn-insight__body {
    font-size: 0.845rem;
    line-height: 1.6;
    color: var(--sn-ink-secondary);
}

.sn-insight__body strong { color: var(--sn-ink-primary); font-weight: 600; }

/* ═══ Sidebar identity ══════════════════════════════════════════════════════ */

.sn-brand {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 1.1rem 0.4rem 0.9rem;
}

.sn-brand__text { min-width: 0; }

.sn-brand__name {
    font-family: var(--sn-font-display);
    font-size: 0.98rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--sn-ink-primary);
    line-height: 1.15;
}

.sn-brand__tag {
    font-family: var(--sn-font-mono);
    font-size: 0.6rem;
    font-weight: 500;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--sn-ink-faint);
    margin-top: 0.22rem;
}

.sn-brand__mark { animation: sn-spin 18s linear infinite; flex-shrink: 0; }

@keyframes sn-spin { to { transform: rotate(360deg); } }

.sn-navlabel {
    font-family: var(--sn-font-mono);
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--sn-ink-faint);
    padding: 0.9rem 0.5rem 0.35rem;
}

.sn-sidefoot {
    margin-top: 0.9rem;
    padding: 0.85rem 0.9rem;
    border-radius: 0.85rem;
    border: 1px solid var(--sn-line-hairline);
    background: rgba(255,255,255,0.025);
    font-size: 0.72rem;
    line-height: 1.55;
    color: var(--sn-ink-muted);
}

.sn-sidefoot__row {
    display: flex;
    justify-content: space-between;
    gap: 0.6rem;
    padding: 0.15rem 0;
}

.sn-sidefoot__val {
    font-family: var(--sn-font-mono);
    color: var(--sn-ink-secondary);
    font-variant-numeric: tabular-nums;
}

/* ═══ Empty state ═══════════════════════════════════════════════════════════ */

.sn-empty {
    display: grid;
    place-items: center;
    gap: 0.7rem;
    text-align: center;
    padding: 3.2rem 2rem;
    border-radius: 1.2rem;
    border: 1px dashed var(--sn-line-subtle);
    background: rgba(255,255,255,0.015);
}

.sn-empty__icon { font-size: 1.9rem; opacity: 0.75; }

.sn-empty__title {
    font-family: var(--sn-font-display);
    font-size: 1.05rem;
    font-weight: 650;
    color: var(--sn-ink-secondary);
}

.sn-empty__body { font-size: 0.83rem; color: var(--sn-ink-muted); max-width: 46ch; line-height: 1.6; }

.sn-empty__code {
    font-family: var(--sn-font-mono);
    font-size: 0.78rem;
    padding: 0.35rem 0.7rem;
    border-radius: 0.5rem;
    background: rgba(34,211,238,0.10);
    border: 1px solid var(--sn-cyan-a24);
    color: var(--sn-cyan);
}

/* ═══ Responsive ════════════════════════════════════════════════════════════ */

@media (max-width: 760px) {
    .sn-hero { padding: 1.5rem 1.3rem; }
    .sn-vs { grid-template-columns: 1fr; gap: 1rem; }
    .sn-verdict { grid-template-columns: 1fr; text-align: center; justify-items: center; }
}
"""


# ──────────────────────────────────────────────────────────────────────────────
#  JavaScript runtime
#  One component, mounted once per page, that upgrades the static HTML above:
#  numerals count up on first paint, and cards light up under the cursor.
# ──────────────────────────────────────────────────────────────────────────────

_RUNTIME_JS = """
export default function () {
    const root = window.parent?.document || document;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // ── Count-up numerals ────────────────────────────────────────────────────
    const easeOut = (t) => 1 - Math.pow(1 - t, 3);

    const countUp = (el) => {
        if (el.dataset.snDone === '1') return;
        el.dataset.snDone = '1';

        const target = parseFloat(el.dataset.count);
        if (!isFinite(target)) return;
        const decimals = parseInt(el.dataset.decimals || '0', 10);
        const final = el.textContent;

        // Skip entirely when motion is unwelcome, or when the tab is hidden —
        // rAF is throttled to a crawl in background tabs and the counter would
        // otherwise sit frozen on a meaningless intermediate value.
        if (reduced || document.hidden) return;

        const duration = 1100;
        const start = performance.now();

        // Safety net: whatever happens to the frame loop, the true value is
        // restored shortly after the animation should have finished.
        const settle = setTimeout(() => { el.textContent = final; }, duration + 500);

        const frame = (now) => {
            const p = Math.min((now - start) / duration, 1);
            const value = target * easeOut(p);
            el.textContent = value.toLocaleString('en-US', {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals,
            });
            if (p < 1) {
                requestAnimationFrame(frame);
            } else {
                clearTimeout(settle);
                el.textContent = final;
            }
        };
        requestAnimationFrame(frame);
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                countUp(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.25 });

    root.querySelectorAll('[data-count]').forEach((el) => observer.observe(el));

    // ── Cursor-tracked card lighting ─────────────────────────────────────────
    if (!root.__snPointerBound) {
        root.__snPointerBound = true;
        root.addEventListener('pointermove', (e) => {
            const card = e.target.closest?.('.sn-stat, .sn-card');
            if (!card) return;
            const r = card.getBoundingClientRect();
            card.style.setProperty('--mx', `${((e.clientX - r.left) / r.width) * 100}%`);
            card.style.setProperty('--my', `${((e.clientY - r.top) / r.height) * 100}%`);
        }, { passive: true });
    }
}
"""

_runtime = st.components.v2.component("sn_runtime", js=_RUNTIME_JS, isolate_styles=False)


# Markup is delivered through a component rather than ``st.html``: Streamlit's
# HTML sanitizer strips <svg> outright, and inline SVG is most of this design
# (crests, sparklines, the confidence ring, the schema diagram). A component's
# ``data`` payload is handed to JavaScript untouched.
_MARKUP_JS = """
export default function (component) {
    const { data, parentElement } = component;
    let host = parentElement.querySelector(':scope > .sn-markup');
    if (!host) {
        host = document.createElement('div');
        host.className = 'sn-markup';
        parentElement.appendChild(host);
    }
    if (host.innerHTML !== data) {
        host.innerHTML = data;
    }
}
"""

_markup = st.components.v2.component("sn_markup", js=_MARKUP_JS, isolate_styles=False)


def markup(html_markup: str) -> None:
    """Render trusted in-repo markup, SVG included, without sanitisation."""
    _markup(data=html_markup)


_styles = st.components.v2.component("sn_styles", css=_CSS, isolate_styles=False)


def inject_css() -> None:
    """Register the component stylesheet. Call once per rerun, after the theme."""
    _styles()


def mount_runtime() -> None:
    """Mount the JS runtime. Call once, at the very end of a page render."""
    _runtime()


# ──────────────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _esc(value) -> str:
    return html.escape(str(value), quote=True)


def _fmt(value: float, decimals: int = 0) -> str:
    return f"{value:,.{decimals}f}"


def sparkline(
    values: Sequence[float],
    color: str = ACCENT["cyan"],
    width: int = 74,
    height: int = 24,
) -> str:
    """Render a compact SVG sparkline with a soft area fill under the line."""
    points = [float(v) for v in values if v is not None]
    if len(points) < 2:
        return ""

    lo, hi = min(points), max(points)
    span = (hi - lo) or 1.0
    step = width / (len(points) - 1)

    coords = [
        (i * step, height - ((v - lo) / span) * (height - 4) - 2)
        for i, v in enumerate(points)
    ]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area = f"{line} {width:.1f},{height} 0,{height}"
    uid = abs(hash((tuple(points), color))) % 100000
    last_x, last_y = coords[-1]

    return (
        f'<svg class="sn-stat__spark" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" fill="none" aria-hidden="true">'
        f'<defs><linearGradient id="sp{uid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.34"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/>'
        f"</linearGradient></defs>"
        f'<polygon points="{area}" fill="url(#sp{uid})"/>'
        f'<polyline points="{line}" stroke="{color}" stroke-width="1.6" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2.1" fill="{color}"/>'
        f"</svg>"
    )


def brand_mark(size: int = 34) -> str:
    """The app's logo: a cricket ball with its seam, drawn as inline SVG."""
    return (
        f'<svg class="sn-brand__mark" width="{size}" height="{size}" viewBox="0 0 48 48" '
        f'fill="none" aria-hidden="true">'
        f'<defs><linearGradient id="snball" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{ACCENT["cyan"]}"/>'
        f'<stop offset="55%" stop-color="{ACCENT["indigo"]}"/>'
        f'<stop offset="100%" stop-color="{ACCENT["violet"]}"/>'
        f"</linearGradient></defs>"
        f'<circle cx="24" cy="24" r="19" stroke="url(#snball)" stroke-width="2.4"/>'
        f'<circle cx="24" cy="24" r="19" fill="url(#snball)" fill-opacity="0.10"/>'
        f'<path d="M13 12c7 6 15 18 22 24" stroke="url(#snball)" stroke-width="1.7" '
        f'stroke-linecap="round" opacity="0.9"/>'
        f'<path d="M9.5 18c6 4.5 14.5 14 19.5 20.5" stroke="url(#snball)" '
        f'stroke-width="1.1" stroke-linecap="round" opacity="0.5"/>'
        f'<path d="M18 8.5c6.5 5 15 15.5 20 22.5" stroke="url(#snball)" '
        f'stroke-width="1.1" stroke-linecap="round" opacity="0.5"/>'
        f"</svg>"
    )


def crest(team: str, size: str = "md") -> str:
    """A franchise crest — initials on the team's own kit gradient."""
    f: Franchise = franchise(team)
    return (
        f'<div class="sn-crest sn-crest--{size}" '
        f'style="--crest:{f.gradient};--crest-glow:{f.glow}" '
        f'title="{_esc(f.name)}">{_esc(f.code)}</div>'
    )


def pill(label: str, color: str | None = None, live: bool = False) -> str:
    """A small labelled pill, optionally with a pulsing status dot."""
    dot = ""
    classes = "sn-pill"
    if color:
        dot = f'<span class="sn-pill__dot" style="--dot:{color}"></span>'
        if live:
            classes += " sn-pill--live"
    return f'<span class="{classes}">{dot}{_esc(label)}</span>'


# ──────────────────────────────────────────────────────────────────────────────
#  Blocks
# ──────────────────────────────────────────────────────────────────────────────

def hero(
    title: str,
    subtitle: str = "",
    eyebrow: str = "",
    pills: Iterable[str] = (),
    accent: str = ACCENT["cyan"],
    accent_2: str = ACCENT["violet"],
) -> None:
    """The page's opening statement: eyebrow, headline, standfirst, meta pills."""
    parts = [
        f'<div class="sn-hero" style="--hero-a:{rgba(accent, 0.18)};'
        f'--hero-b:{rgba(accent_2, 0.16)}">'
    ]
    if eyebrow:
        parts.append(f'<span class="sn-hero__eyebrow">{_esc(eyebrow)}</span>')
    parts.append(f'<h1 class="sn-hero__title">{_esc(title)}</h1>')
    if subtitle:
        parts.append(f'<p class="sn-hero__sub">{_esc(subtitle)}</p>')
    pill_html = "".join(pills)
    if pill_html:
        parts.append(f'<div class="sn-hero__meta">{pill_html}</div>')
    parts.append("</div>")
    markup("".join(parts))


def section(title: str, description: str = "", index: str | None = None) -> None:
    """A titled divider that gives a page its rhythm."""
    idx = f'<span class="sn-section__idx">{_esc(index)}</span>' if index else ""
    desc = f'<span class="sn-section__desc">{_esc(description)}</span>' if description else ""
    markup(
        f'<div class="sn-section">{idx}'
        f'<span class="sn-section__title">{_esc(title)}</span>'
        f"{desc}"
        f'<span class="sn-section__rule"></span></div>'
    )


def stat(
    label: str,
    value: str,
    *,
    icon: str = "",
    unit: str = "",
    note: str = "",
    spark: Sequence[float] | None = None,
    accent: str = ACCENT["cyan"],
    count_to: float | None = None,
    decimals: int = 0,
) -> str:
    """Build one KPI tile. Returns HTML — pass a list of these to `stat_grid`."""
    icon_html = f'<span class="sn-stat__icon">{_esc(icon)}</span>' if icon else ""
    unit_html = f'<span class="sn-stat__unit">{_esc(unit)}</span>' if unit else ""
    note_html = f'<span class="sn-stat__note">{_esc(note)}</span>' if note else "<span></span>"
    spark_html = sparkline(spark, accent) if spark else ""

    count_attr = ""
    if count_to is not None:
        count_attr = f' data-count="{count_to}" data-decimals="{decimals}"'

    return (
        f'<div class="sn-stat" style="--accent:{accent};'
        f"--accent-soft:{rgba(accent, 0.14)};"
        f"--accent-line:{rgba(accent, 0.32)};"
        f'--accent-glow:{rgba(accent, 0.45)}">'
        f'<div class="sn-stat__head">{icon_html}'
        f'<span class="sn-stat__label">{_esc(label)}</span></div>'
        f'<div class="sn-stat__value"><span{count_attr}>{_esc(value)}</span>{unit_html}</div>'
        f'<div class="sn-stat__foot">{note_html}{spark_html}</div>'
        f"</div>"
    )


def stat_grid(tiles: Sequence[str]) -> None:
    """Lay out KPI tiles in an auto-fitting responsive grid."""
    markup(f'<div class="sn-stats">{"".join(tiles)}</div>')


def rank_list(
    rows: Sequence[tuple[str, float]],
    *,
    colors: Sequence[str] | None = None,
    prefixes: Sequence[str] | None = None,
    decimals: int = 0,
    suffix: str = "",
) -> None:
    """A ranked leaderboard of proportional bars — denser than a bar chart."""
    if not rows:
        return
    peak = max(abs(v) for _, v in rows) or 1.0

    items: list[str] = []
    for i, (label, value) in enumerate(rows):
        color = colors[i] if colors and i < len(colors) else ACCENT["cyan"]
        prefix = prefixes[i] if prefixes and i < len(prefixes) else ""
        width = max(abs(value) / peak * 100, 1.5)
        items.append(
            f'<div class="sn-rank">'
            f'<span class="sn-rank__pos">{i + 1:02d}</span>'
            f'<div class="sn-rank__body">'
            f'<div class="sn-rank__label">{prefix}{_esc(label)}</div>'
            f'<div class="sn-rank__track">'
            f'<div class="sn-rank__fill" style="width:{width:.1f}%;'
            f"--fill:linear-gradient(90deg,{rgba(color, 0.55)},{color});"
            f'--fill-glow:{rgba(color, 0.5)};animation-delay:{i * 55}ms"></div>'
            f"</div></div>"
            f'<span class="sn-rank__value">{_fmt(value, decimals)}{_esc(suffix)}</span>'
            f"</div>"
        )
    markup(f'<div class="sn-ranks">{"".join(items)}</div>')


def versus(team_a: str, team_b: str, venue: str = "") -> None:
    """The match-up panel: two crests, each washing its own colour inward."""
    fa, fb = franchise(team_a), franchise(team_b)
    venue_html = f'<span class="sn-vs__venue">{_esc(venue)}</span>' if venue else ""
    markup(
        f'<div class="sn-vs" style="--home-glow:{rgba(fa.primary, 0.16)};'
        f'--away-glow:{rgba(fb.primary, 0.16)}">'
        f'<div class="sn-vs__side">{crest(team_a, "lg")}'
        f'<span class="sn-vs__name">{_esc(fa.name)}</span>'
        f'<span class="sn-vs__role">Home side</span></div>'
        f'<div class="sn-vs__mid">'
        f'<div class="sn-vs__glyph"><span>VS</span></div>{venue_html}</div>'
        f'<div class="sn-vs__side">{crest(team_b, "lg")}'
        f'<span class="sn-vs__name">{_esc(fb.name)}</span>'
        f'<span class="sn-vs__role">Away side</span></div>'
        f"</div>"
    )


def confidence_ring(pct: float, color: str, size: int = 122, caption: str = "confidence") -> str:
    """An animated SVG arc gauge. Returns HTML for embedding in a block."""
    radius = size / 2 - 8
    circumference = 2 * 3.14159265 * radius
    offset = circumference * (1 - max(0.0, min(pct, 100.0)) / 100)

    return (
        f'<div class="sn-ring" style="--ring-glow:{rgba(color, 0.55)}">'
        f'<svg width="{size}" height="{size}">'
        f'<circle cx="{size/2}" cy="{size/2}" r="{radius}" '
        f'stroke="rgba(255,255,255,0.07)" stroke-width="7" fill="none"/>'
        f'<circle class="sn-ring__arc" cx="{size/2}" cy="{size/2}" r="{radius}" '
        f'stroke="{color}" stroke-width="7" '
        f'stroke-dasharray="{circumference:.2f}" stroke-dashoffset="{offset:.2f}" '
        f'style="--circ:{circumference:.2f}"/>'
        f"</svg>"
        f'<div class="sn-ring__center">'
        f'<span class="sn-ring__num">{pct:.1f}%</span>'
        f'<span class="sn-ring__cap">{_esc(caption)}</span>'
        f"</div></div>"
    )


def verdict(team: str, confidence: float, meta_pills: Iterable[str] = ()) -> None:
    """The prediction showpiece: winner, crest, confidence ring, context pills."""
    f = franchise(team)
    markup(
        f'<div class="sn-verdict" style="--win-glow:{rgba(f.primary, 0.20)};'
        f'--win-line:{rgba(f.primary, 0.30)}">'
        f'<div style="display:flex;align-items:center;gap:1.3rem">'
        f'{crest(team, "lg")}'
        f"{confidence_ring(confidence, f.primary)}"
        f"</div>"
        f"<div>"
        f'<span class="sn-verdict__label">Projected winner</span>'
        f'<div class="sn-verdict__name">{_esc(f.name)}</div>'
        f'<div class="sn-verdict__meta">{"".join(meta_pills)}</div>'
        f"</div></div>"
    )


_TONES = {
    "info":    (ACCENT["cyan"], "◆"),
    "success": (ACCENT["mint"], "✓"),
    "warning": (ACCENT["amber"], "▲"),
    "danger":  (ACCENT["rose"], "■"),
    "neutral": ("#8B95AF", "◇"),
}


def insight(body_html: str, tone: str = "info", icon: str | None = None) -> None:
    """A callout for the one sentence a reader should take away from a chart.

    ``body_html`` is trusted markup authored in this repo (it carries <strong>
    emphasis), so it is intentionally not escaped.
    """
    color, default_icon = _TONES.get(tone, _TONES["info"])
    markup(
        f'<div class="sn-insight" style="--tone:{color};'
        f"--tone-bg:{rgba(color, 0.07)};"
        f'--tone-line:{rgba(color, 0.22)}">'
        f'<span class="sn-insight__icon">{_esc(icon or default_icon)}</span>'
        f'<div class="sn-insight__body">{body_html}</div>'
        f"</div>"
    )


def empty_state(title: str, body: str, command: str = "") -> None:
    """Shown when a pipeline artefact is missing — always says how to fix it."""
    cmd = f'<code class="sn-empty__code">{_esc(command)}</code>' if command else ""
    markup(
        f'<div class="sn-empty">'
        f'<span class="sn-empty__icon">◍</span>'
        f'<span class="sn-empty__title">{_esc(title)}</span>'
        f'<span class="sn-empty__body">{_esc(body)}</span>'
        f"{cmd}</div>"
    )


def sidebar_identity() -> None:
    """The sidebar's masthead."""
    markup(
        f'<div class="sn-brand">{brand_mark()}'
        f'<div class="sn-brand__text">'
        f'<div class="sn-brand__name">IPL Analytics</div>'
        f'<div class="sn-brand__tag">Data mining console</div>'
        f"</div></div>"
    )


def sidebar_footer(rows: Sequence[tuple[str, str]]) -> None:
    """A compact status readout pinned under the sidebar navigation."""
    body = "".join(
        f'<div class="sn-sidefoot__row"><span>{_esc(k)}</span>'
        f'<span class="sn-sidefoot__val">{_esc(v)}</span></div>'
        for k, v in rows
    )
    markup(f'<div class="sn-sidefoot">{body}</div>')


def nav_label(text: str) -> None:
    """A small uppercase label above a group of sidebar controls."""
    markup(f'<div class="sn-navlabel">{_esc(text)}</div>')
