#!/usr/bin/env python3
"""Approve the current look of the videos, so the night job may publish full videos again.

    python scripts/approve_demo.py --style B3 --demo <release url> [--note "what you checked"]
    python scripts/approve_demo.py --style B3 --revoke

Owner decision 2026-11-15: each visual style is approved once from its demo (styles in stickman/lock.json). The entry
records the current look fingerprint; changing the runtime pin, the adapters or the story skill changes it, and every
style goes back to demo mode until approved again.

It records the current skill_hash in data/approval.json. Commit and push that file to main.
Any later change to the generator skill or the render tool changes the hash, and the job goes
back to demo mode by itself until you approve again.
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from skill_hash import skill_hash  # noqa: E402

PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "approval.json"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")   # notes may be Vietnamese; a cp1252 console must not crash after the file is written
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", required=True, help="the visual style the demo showed (B1, B2, B3 ...)")
    ap.add_argument("--demo", help="the demo release you watched")
    ap.add_argument("--note", default="")
    ap.add_argument("--revoke", action="store_true")
    a = ap.parse_args()
    cur = json.loads(PATH.read_text(encoding="utf-8")) if PATH.is_file() else {}
    style = a.style.upper()
    lock = json.loads((PATH.parent.parent / "stickman" / "lock.json").read_text(encoding="utf-8"))
    if style not in lock["enabled_styles"]:
        print(f"style {style} is not enabled: {lock['disabled_styles'].get(style, 'unknown')}"); return 1
    styles = cur.setdefault("styles", {})
    if a.revoke:
        styles[style] = dict(styles.get(style, {}), approved=False, approved_at=None)
    else:
        styles[style] = dict(approved=True, skill_hash=skill_hash(), approved_at=dt.datetime.now().isoformat(timespec="minutes"),
                             demo=a.demo or styles.get(style, {}).get("demo"), note=a.note or "")
    PATH.write_text(json.dumps(cur, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(cur, ensure_ascii=False, indent=2))
    print("Now commit and push data/approval.json to main.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
