#!/usr/bin/env python3
"""Install-time patch of the pinned stickman-video-director runtime: lift the 60 s cap on `preview` / `validate --seconds` (three places: autopilot.mjs twice, autopilot-core.mjs once).

Owner decision 2026-11-16 ("bỏ chặn phim dài hơn 60 giây"): the night job renders whole films (2-8 minutes) with the runtime's
`preview` command, because its `render` command needs the owner's own `approve` artifacts for every film. The cap is only
lifted when AUTOPILOT_MAX_PREVIEW_SECONDS is set (scripts/stickman/assemble.py sets it); without it the runtime keeps 60 s.
Nothing else is changed: every validation (motion, captions, coverage, fonts, sound) still runs on the whole film.

    python long-preview.py <runtime skill dir>      (idempotent; exits 1 if the runtime no longer matches)
"""
import pathlib, sys

root = pathlib.Path(sys.argv[1]) / "scripts"
CAP = "(Number(process.env.AUTOPILOT_MAX_PREVIEW_SECONDS) || 60)"
EDITS = {
    "autopilot.mjs": [("seconds <= 0 || seconds > 60)", f"seconds <= 0 || seconds > {CAP})"),
                      ("report.preview_seconds > 60)", f"report.preview_seconds > {CAP})")],
    "autopilot-core.mjs": [("number(seconds, 'preview length', 0.001, 60)", f"number(seconds, 'preview length', 0.001, {CAP})")],
}
for name, edits in EDITS.items():
    f = root / name
    s = f.read_text(encoding="utf-8")
    for old, new in edits:
        if new in s: continue
        if s.count(old) != 1:
            sys.exit(f"long-preview: expected exactly one `{old}` in {f}, found {s.count(old)}: the pinned runtime changed; re-check the patch")
        s = s.replace(old, new)
    f.write_text(s, encoding="utf-8")
print("long-preview: cap patched in autopilot.mjs and autopilot-core.mjs (AUTOPILOT_MAX_PREVIEW_SECONDS)")
