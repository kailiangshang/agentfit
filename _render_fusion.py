"""Render fusion-v3 slides to PNG for visual review."""
from pathlib import Path
from playwright.sync_api import sync_playwright

SLIDES_DIR = Path("competition/2026-08-15/alternatives/fusion-v3/slides")
OUT_DIR = Path("competition/2026-08-15/alternatives/fusion-v3/_screenshots")
OUT_DIR.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
    page = context.new_page()
    for html in sorted(SLIDES_DIR.glob("*.html")):
        page.goto(html.resolve().as_uri())
        page.wait_for_timeout(400)
        out = OUT_DIR / f"{html.stem}.png"
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": 1280, "height": 720})
        print(f"  {out.name}")
    browser.close()
print(f"Done -> {OUT_DIR}")
