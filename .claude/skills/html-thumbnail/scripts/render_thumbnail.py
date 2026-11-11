#!/usr/bin/env python3
"""Render HTML thumbnail file(s) to PNG with headless Chromium.

Usage:
  python render_thumbnail.py <file.html | dir> [--out DIR] [--size 1280x720]

A directory renders every *.html in it. Output PNG has the same base name.
Use --size 720x1280 for Shorts covers.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def render_with_chrome_cli(files, out_dir, w, h) -> bool:
    """Fallback when playwright cannot start (its bundled node needs libatomic.so.1, absent
    from the runner image on 2026-11-12): screenshot each file with the system chrome."""
    chrome = os.environ.get("CHROME_PATH") or shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        return False
    for f in files:
        target = (out_dir / (f.stem + ".png")).resolve()
        cmd = [chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
               "--allow-file-access-from-files", f"--window-size={w},{h}",
               f"--screenshot={target}", f.resolve().as_uri()]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        if not target.exists():
            return False
        print(f"OK {target} (chrome cli)")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--out", default=None)
    ap.add_argument("--size", default="1280x720")
    args = ap.parse_args()

    try:
        w, h = (int(v) for v in args.size.lower().split("x"))
    except ValueError:
        print(f"Bad --size '{args.size}', expected WIDTHxHEIGHT", file=sys.stderr)
        return 2

    src = Path(args.source)
    files = sorted(src.glob("*.html")) if src.is_dir() else [src]
    if not files or not all(f.exists() for f in files):
        print(f"No HTML found at {src}", file=sys.stderr)
        return 2
    out_dir = Path(args.out) if args.out else (src if src.is_dir() else src.parent)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            chrome = os.environ.get("CHROME_PATH")  # set in CI by setup-chrome
            browser = p.chromium.launch(executable_path=chrome) if chrome else p.chromium.launch()
            page = browser.new_page(viewport={"width": w, "height": h})
            for f in files:
                page.goto(f.resolve().as_uri(), wait_until="networkidle")
                page.evaluate("document.fonts.ready")
                target = out_dir / (f.stem + ".png")
                page.screenshot(path=str(target), clip={"x": 0, "y": 0, "width": w, "height": h})
                print(f"OK {target}")
            browser.close()
        return 0
    except Exception as e:  # noqa: BLE001 - playwright driver failures are many kinds
        print(f"playwright failed ({type(e).__name__}); trying the system chrome", file=sys.stderr)
        return 0 if render_with_chrome_cli(files, out_dir, w, h) else 1


if __name__ == "__main__":
    sys.exit(main())
