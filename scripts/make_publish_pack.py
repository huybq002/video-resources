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
  "thumbnail_text": "3-4 words", "pinned_comment": "...", "posting_notes": "...",
  "title_options": ["...", "...", "..."]       # 3 candidate titles for YouTube Studio's Test & compare
}

2026-11-13: the packaging rules of data/growth-playbook.md are checked here too (title 40-60 chars, no genre
label in brackets, 3 title options, no "invented / fiction / AI" in the first 125 characters of the description,
the search phrase in those 125 characters, description 600+ characters with the labels at the end).
"""
import argparse
import json
import pathlib
import re
import sys

# a genre label in brackets at the end of a title: "(Mystery Story)", "[Procrastination]", "| Animated Story"
GENRE_LABEL = re.compile(r"[\(\[][^)\]]{2,30}[\)\]]\s*$|\|\s*[\w ]{2,30}$")
META_WORDS = re.compile(r"\b(invented|fiction|fictional|ai[- ]generated|ai voice|disclaimer|not advice)\b", re.I)
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
    t_ = yt.get("title", "")
    need(len(t_) <= 60, f"youtube.title is {len(t_)} chars; keep it <= 60 so search and the feed show all of it (playbook T1)")
    need(len(t_) >= 25, f"youtube.title is only {len(t_)} chars; say the strange fact or the outcome (playbook T3)")
    lab_ = GENRE_LABEL.search(t_)
    need(not lab_, f"youtube.title ends in a genre label ({lab_.group(0).strip() if lab_ else ''}): "
         "it promises nothing; put the search phrase in the description and tags instead (playbook T2)")
    opts = p.get("title_options") or []
    need(len(opts) >= 3, "title_options needs 3 candidate titles for YouTube Studio's Test & compare (playbook T4)")
    for o in opts:
        need(len(o) <= 60 and not GENRE_LABEL.search(o), f"title option breaks T1/T2: {o!r}")
    d_ = yt.get("description", "")
    head = d_[:125]
    meta_ = META_WORDS.search(head)
    need(not meta_, f"the first 125 chars of the description contain {(meta_.group(0) if meta_ else '')!r}: "
         "search and the feed show only those; open with the hook, put the AI/fiction label in the last block (playbook D1, D2)")
    kw_ = (p.get("keyword") or "").lower().strip()
    if not kw_:       # the task's keyword: tasks/pending|done/<id>.md frontmatter
        for tf in (pathlib.Path("tasks") / d / f"{a.id}.md" for d in ("pending", "done")):
            if tf.is_file():
                m = re.search(r"^keyword:\s*(.+)$", tf.read_text(encoding="utf-8"), re.M)
                kw_ = (m.group(1).strip().strip('"').split("/")[0].strip().lower() if m else "")
                break
    need(kw_, "no search phrase: set publish.json keyword (the phrase from the digest's 'What people type')")
    if kw_:
        main_words = [w for w in re.findall(r"[a-z']+", kw_) if len(w) > 3 and w not in ("story", "explained", "animated")]
        need(not main_words or any(w in head.lower() for w in main_words),
             f"the search phrase {kw_!r} (or its main word) is not in the first 125 chars of the description (playbook D1)")
    need(len(d_) >= 600, f"youtube.description is {len(d_)} chars; write 600-1500 so search knows what the video is about (playbook D3)")
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
        need("teaser" in (p.get("posting_notes") or "").lower(),
             "posting_notes must say the vertical cut is longer than 3 min and propose the 45-58 s teaser Short (playbook S1)")

    (pub_dir / "youtube.md").write_text(block("YouTube (16:9) — landscape.mp4", [
        ("Title", yt.get("title")), ("Description", yt.get("description")),
        ("Tags (comma separated)", tags), ("Hashtags", yt.get("hashtags", [])),
        ("Thumbnail text", p.get("thumbnail_text")), ("Pinned comment", p.get("pinned_comment")),
        ("Other titles to A/B test (YouTube Studio: Test & compare)", "\n".join(f"- {o}" for o in (p.get("title_options") or []) if o != yt.get("title"))),
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
