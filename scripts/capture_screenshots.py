"""
Regenerate the screenshots embedded in README.md.

Boots the Streamlit app on a scratch port, drives it with Playwright, and writes
one PNG per page to ``docs/screenshots/``. Reduced-motion is emulated so the
entrance animations and count-up numerals settle on their final values instead
of being caught mid-flight.

Usage:
    python scripts/capture_screenshots.py            # all pages
    python scripts/capture_screenshots.py players    # one page

Requires the dev extras:
    pip install playwright && playwright install chromium
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"

WIDTH = 1500
SCALE = 2          # supersample, then downscale — sharper than capturing at 1x
OUTPUT_WIDTH = 1500  # final PNG width
MAX_HEIGHT = 5200  # guard against a runaway page

# (slug, url path, extra interaction). The default page lives at "/".
PAGES: tuple[tuple[str, str, str | None], ...] = (
    ("overview", "", None),
    ("players", "players", None),
    ("teams", "teams", None),
    ("prediction", "prediction", "predict"),
    ("warehouse", "warehouse", None),
)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_for(url: str, timeout: float = 90.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"Streamlit did not come up at {url}")


def _settle(page, seconds: float = 2.5) -> None:
    """Wait for Plotly to finish laying out and web fonts to be ready."""
    page.wait_for_load_state("networkidle")
    try:
        page.wait_for_function("document.fonts.status === 'loaded'", timeout=8000)
    except Exception:
        pass
    page.wait_for_timeout(int(seconds * 1000))


def _content_height(page) -> int:
    """True rendered height of the page's main column, in CSS pixels.

    Streamlit's main area is its own scroll container, so neither
    ``body.scrollHeight`` nor Playwright's ``full_page`` sees past the fold.
    The block container's own box is the honest measure.
    """
    return int(page.evaluate(
        """() => {
            const block = document.querySelector('[data-testid="stMainBlockContainer"]');
            const main = document.querySelector('[data-testid="stMain"]');
            const candidates = [
                block ? block.getBoundingClientRect().height + 140 : 0,
                main ? main.scrollHeight : 0,
                document.body.scrollHeight,
            ];
            return Math.ceil(Math.max(...candidates));
        }"""
    ))


def _downscale(path: Path) -> None:
    """Resample the 2x capture down to OUTPUT_WIDTH so the repo stays light."""
    try:
        from PIL import Image
    except ImportError:
        return

    with Image.open(path) as img:
        if img.width <= OUTPUT_WIDTH:
            return
        ratio = OUTPUT_WIDTH / img.width
        resized = img.convert("RGB").resize(
            (OUTPUT_WIDTH, round(img.height * ratio)), Image.LANCZOS
        )
        resized.save(path, "PNG", optimize=True)


def capture(only: str | None = None) -> list[Path]:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    port = _free_port()
    base = f"http://localhost:{port}"

    server = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
         "--server.port", str(port),
         "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    written: list[Path] = []
    try:
        _wait_for(base)

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(
                viewport={"width": WIDTH, "height": 1000},
                device_scale_factor=SCALE,
                reduced_motion="reduce",
                color_scheme="dark",
            )
            page = context.new_page()

            for slug, path, action in PAGES:
                if only and slug != only:
                    continue

                print(f"  · {slug}", flush=True)
                page.set_viewport_size({"width": WIDTH, "height": 1000})
                page.goto(f"{base}/{path}", wait_until="domcontentloaded")
                page.wait_for_selector(".sn-hero__title", timeout=60_000)
                _settle(page)

                if action == "predict":
                    # The verdict is the whole point of this page — capture it.
                    page.get_by_role("button", name="Run prediction").click()
                    page.wait_for_selector(".sn-verdict", timeout=180_000)
                    _settle(page, 3.0)

                # Streamlit scrolls inside its own container, so Playwright's
                # full_page capture only ever sees one viewport. Grow the
                # viewport to fit the content instead. Two passes: the first
                # reveals anything that was lazily rendered below the fold, the
                # second measures the page at its true height.
                for _ in range(2):
                    height = _content_height(page)
                    page.set_viewport_size(
                        {"width": WIDTH, "height": min(height, MAX_HEIGHT)}
                    )
                    # Plotly sizes itself from the container and does not
                    # observe a viewport change on its own.
                    page.evaluate("() => window.dispatchEvent(new Event('resize'))")
                    _settle(page, 1.8)

                # The backdrop's film grain is barely visible in the browser but
                # it is high-frequency noise across every pixel, which roughly
                # quadruples the PNG. Drop it for the capture only.
                page.add_style_tag(content="body::after { display: none !important; }")
                page.wait_for_timeout(250)

                target = OUT / f"{slug}.png"
                page.screenshot(path=str(target))
                _downscale(target)
                written.append(target)

            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()

    return written


def main() -> int:
    if shutil.which("streamlit") is None and not (ROOT / "app.py").exists():
        print("app.py not found", file=sys.stderr)
        return 1

    only = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"Capturing screenshots to {OUT.relative_to(ROOT)} …")
    files = capture(only)

    for path in files:
        size_kb = path.stat().st_size / 1024
        print(f"  {path.relative_to(ROOT)}  ({size_kb:,.0f} KB)")
    print(f"Done — {len(files)} screenshot(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
