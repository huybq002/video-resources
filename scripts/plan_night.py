#!/usr/bin/env python3
"""Night planning gates (outside the hashed skill folder, so changing it never forces a new demo approval).

    python scripts/plan_night.py check-ideas [--date YYYY-MM-DD]
        exit 1 unless data/ideas.md got at least channel.json night.min_ideas_per_run (default 3) ideas dated tonight
        (any status: new / queued / done / dropped-for-policy still counts as researched).

    python scripts/plan_night.py budget --durations 3,4.5 [--deadline EPOCH]
        estimates the minutes each video needs (two cuts, voice-over, checks, publish) and says whether all of them
        finish before the deadline ($DEADLINE_EPOCH by default). Exit 1 if not, with the longest durations that fit.

    python scripts/plan_night.py status
        how many tasks are runnable, how many videos tonight must make (night.videos_per_night, default 2).

The length of a video is NOT fixed: each idea gets the length its story needs, inside night.duration_range_min
(default 1-8 minutes); the budget only checks that tonight's videos all fit before the deadline.
"""
import argparse, datetime as dt, json, os, pathlib, re, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent


def channel():
    return json.loads((ROOT / "channel.json").read_text(encoding="utf-8"))


def night_cfg():
    c = channel(); n = dict(c.get("night") or {})
    n.setdefault("min_ideas_per_run", max(3, int((c.get("research") or {}).get("min_ideas_per_run", 3))))
    n.setdefault("videos_per_night", 2)
    n.setdefault("duration_range_min", [1, 8])
    n.setdefault("render_s_per_video_s", 7.0)      # per cut, 30 fps, measured on the runner
    n.setdefault("overhead_min_per_video", 30)     # spec + lint + backgrounds + voice-over + checks + thumbnails + release
    n.setdefault("margin", 1.3)
    return n


def ideas_tonight(date):
    p = ROOT / "data" / "ideas.md"
    if not p.exists(): return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0] == date and cells[1] != "topic":
            rows.append(cells)
    return rows


def need_minutes(dur_min, n):
    return n["overhead_min_per_video"] + dur_min * 60 * n["render_s_per_video_s"] * 2 * n["margin"] / 60


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("check-ideas"); a1.add_argument("--date")
    a2 = sub.add_parser("budget"); a2.add_argument("--durations", required=True); a2.add_argument("--deadline", type=int)
    sub.add_parser("status")
    a = ap.parse_args(); n = night_cfg()
    if a.cmd == "check-ideas":
        # the night starts at 00:00 ICT = 17:00 UTC: ideas written tonight carry the ICT date
        date = a.date or (dt.datetime.utcnow() + dt.timedelta(hours=7)).strftime("%Y-%m-%d")
        rows = ideas_tonight(date); k = n["min_ideas_per_run"]
        print(f"ideas dated {date}: {len(rows)} (need >= {k})")
        for r in rows: print("  -", r[1], r[2], r[3][:90])
        if len(rows) < k:
            print(f"FAIL: research gave {len(rows)} idea(s); write at least {k} into data/ideas.md (WebSearch fallback if "
                  f"research_youtube.py was refused) before choosing tonight's videos."); sys.exit(1)
        print("ideas OK"); return
    if a.cmd == "status":
        pend = sorted((ROOT / "tasks" / "pending").glob("*.md"))
        print(f"runnable tasks: {len(pend)}; videos tonight: >= {n['videos_per_night']}; "
              f"length per idea within {n['duration_range_min'][0]}-{n['duration_range_min'][1]} min")
        return
    durs = [float(x) for x in a.durations.split(",") if x.strip()]
    lo, hi = n["duration_range_min"]
    bad = [d for d in durs if not (lo <= d <= hi)]
    if bad: print(f"WARNING: duration(s) {bad} outside night.duration_range_min {lo}-{hi}")
    deadline = a.deadline or int(os.environ.get("DEADLINE_EPOCH", "0") or 0)
    left = (deadline - time.time()) / 60 if deadline else None
    total = 0.0
    for i, d in enumerate(durs, 1):
        m = need_minutes(d, n); total += m
        print(f"video {i}: {d:g} min -> about {m:.0f} min of work")
    print(f"total about {total:.0f} min" + (f", {left:.0f} min left before the deadline" if left is not None else ""))
    if left is not None and total > left - 15:
        # longest equal length that still fits all of them (keeps 15 min to commit, push and report)
        per = (left - 15) / max(1, len(durs)); fit = (per - n["overhead_min_per_video"]) * 60 / (60 * n["render_s_per_video_s"] * 2 * n["margin"])
        print(f"FAIL: does not fit. Each of the {len(durs)} videos must be <= {max(0, fit):.1f} min tonight "
              f"(shorten the later ones first; never drop below {n['videos_per_night']} videos)."); sys.exit(1)
    print("budget OK")


if __name__ == "__main__":
    main()
