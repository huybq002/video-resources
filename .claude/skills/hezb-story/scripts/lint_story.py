#!/usr/bin/env python3
"""Lint a story script (stories/<id>.json, references/story-schema.md). Every WARNING must be fixed before voicing.

    python .claude/skills/hezb-story/scripts/lint_story.py stories/<id>.json [--previous-style B2]
"""
import argparse, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
EMOTES = {"joy", "happy", "excited", "surprise", "shock", "angry", "frustrated", "worry", "fear", "doubt", "think", "confused",
          "sad", "tired", "relief", "calm", "proud", "laugh", "neutral"}
GREETING = re.compile(r"^(hi|hello|hey|welcome|today we|in this video|let's talk|have you ever wondered)\b", re.I)
META = re.compile(r"\b(invented|fictional|fiction|true story|real story|based on real)\b", re.I)
BARE_PLACE = {"kitchen", "office", "street", "home", "room", "bedroom", "cafe", "shop", "park", "hospital", "school", "bank"}


def lint(story, previous_style=None):
    w = []
    lock = json.loads((ROOT / "stickman" / "lock.json").read_text(encoding="utf-8"))
    style = str(story.get("style", "")).upper()
    if style not in lock["enabled_styles"]:
        w.append(f"WARNING: style {style or '(none)'} is not enabled ({lock['disabled_styles'].get(style, 'unknown')}); use one of {lock['enabled_styles']}")
    if previous_style and style == previous_style.upper():
        w.append(f"WARNING: style {style} was the previous video's style: change it (the channel must not look templated)")
    cast = {c.get("id"): c for c in story.get("cast", [])}
    for cid, c in cast.items():
        if not c.get("gender"): w.append(f"WARNING: cast '{cid}' has no gender (it decides the voice)")
        if len(str(c.get("look", "")).split()) < 4: w.append(f"WARNING: cast '{cid}' needs a 'look' (clothes, hair, one signature object)")
    scenes = story.get("scenes", [])
    if not scenes: return w + ["WARNING: the story has no scenes"]
    words, char_lines, acted, lines_all = 0, 0, 0, []
    for sc in scenes:
        sid = sc.get("id")
        place = str(sc.get("place", "")).strip()
        if len(place.split()) < 4 or place.lower() in BARE_PLACE:
            w.append(f"WARNING: scene {sid}: 'place' must say where THIS beat happens in this story (4+ words, not a bare category): {place!r}")
        if not sc.get("lines"): w.append(f"WARNING: scene {sid} has no lines")
        for ln in sc.get("lines", []):
            t = str(ln.get("t", "")).strip(); who = ln.get("who", "narrator")
            lines_all.append(t); words += len(t.split())
            if who != "narrator" and who not in cast: w.append(f"WARNING: scene {sid}: speaker '{who}' is not in the cast")
            if len(t.split()) > 22: w.append(f"WARNING: scene {sid}: a line of {len(t.split())} words (max 22): {t[:50]!r}")
            if META.search(t): w.append(f"WARNING: scene {sid}: no fiction/truth talk in the lines ({META.search(t).group(0)!r}): the label goes in the description")
            em = str(ln.get("emote", "")).lower()
            if em and em.split(":")[0] not in EMOTES: w.append(f"WARNING: scene {sid}: unknown emote {em!r} (use {', '.join(sorted(EMOTES))})")
            if who != "narrator":
                char_lines += 1; acted += bool(em)
    if lines_all:
        first = lines_all[0]
        if len(first.split()) > 14: w.append(f"WARNING: the first line has {len(first.split())} words (max 14): it is the hook")
        if GREETING.search(first): w.append(f"WARNING: the film opens with a greeting/filler: {first[:40]!r}")
        if not scenes[-1].get("lines") or not str(scenes[-1]["lines"][-1].get("t", "")).strip().endswith("?"):
            w.append("WARNING: the last line should be a question the viewer can answer in the comments")
    if char_lines and acted / char_lines < 0.6:
        w.append(f"WARNING: only {acted} of {char_lines} character lines carry an 'emote': act the lines (the voice follows it)")
    if story.get("duration_min"):
        target = float(story["duration_min"]) * 60 * 2.6
        if not (0.8 * target <= words <= 1.2 * target):
            w.append(f"WARNING: {words} words for {story['duration_min']} min (want about {int(target)} at 2.6 words/s): the film's length is the voice's length")
    if len({str(sc.get('place', '')).strip().lower() for sc in scenes}) < min(3, len(scenes)):
        w.append("WARNING: fewer than 3 different places: a story that never moves looks like a slideshow")
    return w


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("story"); ap.add_argument("--previous-style")
    a = ap.parse_args()
    out = lint(json.load(open(a.story, encoding="utf-8")), a.previous_style)
    for l in out: print(l)
    print(f"story lint: {len(out)} warning(s)")
    sys.exit(1 if out else 0)


if __name__ == "__main__":
    main()
