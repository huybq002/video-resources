#!/usr/bin/env python3
"""Turn outputs/<id>/publish/publish.json into ready-to-paste posts, and check the platform limits.

    python scripts/make_publish_pack.py <id> [--spec specs/<id>.json]

Claude writes publish.json (the judgement: titles, descriptions, keywords per platform, from the
claude-youtube seo/metadata sub-skills). This script renders youtube.md, youtube_shorts.md and
tiktok.md next to it and refuses anything a platform would cut off, so nothing is discovered
after upload. Exit code 1 and one line per problem when a limit is broken.

publish.json shape (every field optional except title/description):
{
  "keyword": "...", "keywords": ["..."],
  "youtube":        {"title": "...", "description": "...", "tags": ["..."], "hashtags": ["#..."]},
  "youtube_shorts": {"title": "...", "description": "...", "hashtags": ["#..."]},
  "tiktok":         {"caption": "...", "hashtags": ["#..."]},
  "thumbnail_text": "3-4 words", "pinned_comment": "...", "posting_notes": "..."
}
"""
import argparse
import json
import pathlib
import sys

LIMITS = {"yt_title": 100, "yt_desc": 5000, "yt_tags_total": 500, "yt_tag": 30,
          "short_title": 100, "short_title_soft": 40, "tt_caption": 2200}
problems = []


def need(cond, msg):
    if not cond:
        problems.append(msg)


def block(title, pairs):
    out = [f"# {title}", ""]
    for k, v in pairs:
        if not v:
            continue
        if isinstance(v, list):
            v = " ".join(v) if k.lower().startswith("hashtag") else ", ".join(v)
        out += [f"## {k}", "", str(v).rstrip(), ""]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--spec")
    a = ap.parse_args()
    pub_dir = pathlib.Path("outputs") / a.id / "publish"
    src = pub_dir / "publish.json"
    if not src.is_file():
        print(f"missing {src}: Claude writes it before this step", file=sys.stderr)
        return 1
    p = json.load(open(src, encoding="utf-8"))
    dur = None
    if a.spec and pathlib.Path(a.spec).is_file():
        dur = json.load(open(a.spec, encoding="utf-8")).get("duration_s")

    yt = p.get("youtube", {})
    sh = p.get("youtube_shorts", {})
    tt = p.get("tiktok", {})
    tags = yt.get("tags", [])
    tags_len = sum(len(t) + 1 for t in tags)

    need(yt.get("title"), "youtube.title is missing")
    need(len(yt.get("title", "")) <= LIMITS["yt_title"], f"youtube.title is {len(yt.get('title',''))} chars (max {LIMITS['yt_title']})")
    need(yt.get("description"), "youtube.description is missing")
    need(len(yt.get("description", "")) <= LIMITS["yt_desc"], f"youtube.description is {len(yt.get('description',''))} chars (max {LIMITS['yt_desc']})")
    need(tags_len <= LIMITS["yt_tags_total"], f"youtube.tags total {tags_len} chars (max {LIMITS['yt_tags_total']})")
    for t in tags:
        need(len(t) <= LIMITS["yt_tag"], f"youtube tag too long ({len(t)} chars): {t!r}")
    need(sh.get("title"), "youtube_shorts.title is missing")
    need(len(sh.get("title", "")) <= LIMITS["short_title_soft"],
         f"youtube_shorts.title is {len(sh.get('title',''))} chars; keep it <= {LIMITS['short_title_soft']} so the feed does not cut it")
    need(tt.get("caption"), "tiktok.caption is missing")
    need(len(tt.get("caption", "")) <= LIMITS["tt_caption"], f"tiktok.caption is {len(tt.get('caption',''))} chars (max {LIMITS['tt_caption']})")
    for name, d in (("youtube", yt), ("youtube_shorts", sh), ("tiktok", tt)):
        hs = d.get("hashtags", [])
        need(all(h.startswith("#") for h in hs), f"{name}.hashtags must all start with '#'")
        need(len(hs) <= 8, f"{name} has {len(hs)} hashtags; 3-5 works better than a wall")
    if dur and dur > 180:
        print(f"note: the video is {dur:.0f}s, so the vertical cut is NOT eligible as a Short "
              f"(limit 180s) - post it as a normal vertical video, or cut a 45-60s teaser.")

    (pub_dir / "youtube.md").write_text(block("YouTube (16:9) — landscape.mp4", [
        ("Title", yt.get("title")), ("Description", yt.get("description")),
        ("Tags (comma separated)", tags), ("Hashtags", yt.get("hashtags", [])),
        ("Thumbnail text", p.get("thumbnail_text")), ("Pinned comment", p.get("pinned_comment")),
    ]), encoding="utf-8")
    (pub_dir / "youtube_shorts.md").write_text(block("YouTube Shorts (9:16) — portrait.mp4", [
        ("Title", sh.get("title")), ("Description", sh.get("description")),
        ("Hashtags", sh.get("hashtags", [])), ("Pinned comment", p.get("pinned_comment")),
    ]), encoding="utf-8")
    (pub_dir / "tiktok.md").write_text(block("TikTok (9:16) — portrait.mp4", [
        ("Caption", tt.get("caption")), ("Hashtags", tt.get("hashtags", [])),
        ("Posting notes", p.get("posting_notes")),
    ]), encoding="utf-8")

    print("publish pack:", ", ".join(f.name for f in sorted(pub_dir.glob("*.md"))))
    if problems:
        print("PROBLEMS:")
        for x in problems:
            print(" -", x)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
