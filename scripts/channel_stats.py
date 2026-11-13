#!/usr/bin/env python3
"""How our own videos are doing, from the channel's public video list (no API key, no login).

    python scripts/channel_stats.py [--channel URL] [--out data/performance.md]

Reads channel.json `own_channel` (e.g. https://www.youtube.com/@HezbStories) unless --channel is given,
lists the uploads with yt-dlp, and writes data/performance.md: views, days since upload, views per day and
how each video compares with the channel median. Rows the owner added by hand (CTR, average view
duration from YouTube Studio) are kept: the table is merged on the video id.

Exit 0 with a note when no channel is set or YouTube refuses, so the night job never stops on it.
See data/growth-playbook.md (P1, R5).
"""
import argparse
import datetime as dt
import json
import pathlib
import statistics
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
COLS = ["video_id", "title", "uploaded", "days", "views", "views_per_day", "vs_median", "ctr_percent", "avg_view_pct", "notes"]


def listing(url, limit=60):
    target = url.rstrip("/")
    if not target.endswith(("/videos", "/shorts", "/streams")):
        target += "/videos"
    cmd = [sys.executable, "-m", "yt_dlp", "--flat-playlist", "--dump-json", "--playlist-end", str(limit),
           "--no-warnings", "--ignore-errors", "--extractor-args", "youtubetab:approximate_date", target]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    except subprocess.TimeoutExpired:
        return []
    out = []
    for line in (r.stdout or "").splitlines():
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def read_table(path):
    rows = {}
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == len(COLS) and cells[0] not in ("video_id", "---") and not set(cells[0]) <= {"-"}:
            rows[cells[0]] = dict(zip(COLS, cells))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel")
    ap.add_argument("--out", default=str(ROOT / "data" / "performance.md"))
    a = ap.parse_args()
    cfg = json.loads((ROOT / "channel.json").read_text(encoding="utf-8"))
    url = a.channel or cfg.get("own_channel") or ""
    out = pathlib.Path(a.out)
    if not url:
        print("note: channel.json has no own_channel URL; performance.md not updated (ask the owner for it in the report)")
        return 0
    vids = listing(url)
    if not vids:
        print(f"note: no videos listed for {url} (YouTube refused or the channel is empty); performance.md not updated")
        return 0
    today = dt.date.today()
    old = read_table(out)
    rows = []
    for v in vids:
        vid = v.get("id") or ""
        ts = v.get("timestamp") or v.get("release_timestamp")
        up = dt.date.fromtimestamp(ts) if ts else None
        if not up and v.get("upload_date"):
            up = dt.datetime.strptime(v["upload_date"], "%Y%m%d").date()
        days = max(1, (today - up).days) if up else None
        views = int(v.get("view_count") or 0)
        r = dict(old.get(vid, {}))
        r.update(video_id=vid, title=(v.get("title") or "")[:70].replace("|", "/"),
                 uploaded=up.isoformat() if up else "?", days=str(days or "?"), views=str(views),
                 views_per_day=f"{views / days:.1f}" if days else "?")
        rows.append(r)
    med = statistics.median([int(r["views"]) for r in rows]) or 1
    for r in rows:
        r["vs_median"] = f"{int(r['views']) / med:.2f}x"
        for c in COLS:
            r.setdefault(c, "")
    L = ["# Channel performance", "",
         f"Written by scripts/channel_stats.py on {today} from {url} (public counts). The owner may fill",
         "ctr_percent and avg_view_pct from YouTube Studio; those cells are kept on the next run.",
         "Read this before changing ideas, titles or scripts (data/growth-playbook.md R5, P1).", "",
         f"channel median views: {int(med)}; videos listed: {len(rows)}", "",
         "| " + " | ".join(COLS) + " |", "|" + "---|" * len(COLS)]
    for r in sorted(rows, key=lambda r: r["uploaded"], reverse=True):
        L.append("| " + " | ".join(str(r.get(c, "")) for c in COLS) + " |")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {out}: {len(rows)} videos, median {int(med)} views")
    return 0


if __name__ == "__main__":
    sys.exit(main())
