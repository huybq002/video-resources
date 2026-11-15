#!/usr/bin/env python3
"""YouTube metadata.json (title, description with chapters, tags) from the story and its voice timing.

    python scripts/media/make_metadata.py stories/<id>.json outputs/<id>/voice [--privacy private] > outputs/<id>/metadata.json

Chapters come from the scenes' real start times in timing.json (YouTube needs >= 3 chapters, the first at 00:00).
story["youtube"] may override: title, description, tags, categoryId, privacy, madeForKids. The publishing pack
(publish.json, data/growth-playbook.md) writes the final title and description; this file is the upload default.
"""
import argparse, json, pathlib, sys


def mmss(s):
    s = int(s); return f"{s // 3600:d}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("story"); ap.add_argument("voice"); ap.add_argument("--privacy")
    a = ap.parse_args()
    story = json.load(open(a.story, encoding="utf-8")); yt = story.get("youtube", {})
    timing = json.load(open(pathlib.Path(a.voice) / "timing.json", encoding="utf-8"))
    chapters = [(0.0 if i == 0 else s["start"], s.get("title") or f"Part {i + 1}") for i, s in enumerate(timing["scenes"])]
    chap = "\n".join(f"{mmss(t)} {n}" for t, n in chapters) if len(chapters) >= 3 else ""
    cfg = json.loads((pathlib.Path(__file__).resolve().parents[2] / "channel.json").read_text(encoding="utf-8"))
    disc = cfg.get("publish", {}).get("ai_disclosure", "Voice and visuals in this video are AI-generated. Characters and events are fictional.")
    desc = yt.get("description") or "\n\n".join(x for x in [story.get("idea", ""), chap, disc, " ".join(cfg.get("publish", {}).get("base_hashtags", []))] if x)
    meta = {"title": (yt.get("title") or story.get("title") or story.get("idea", ""))[:100], "description": desc[:5000],
            "tags": yt.get("tags", [story.get("keyword")] if story.get("keyword") else []),
            "categoryId": yt.get("categoryId", cfg.get("publish", {}).get("youtube_category_id", "27")),
            "privacy": a.privacy or yt.get("privacy", "private"), "language": story.get("lang", "en"),
            "madeForKids": yt.get("madeForKids", False)}
    sys.stdout.reconfigure(encoding="utf-8"); print(json.dumps(meta, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
