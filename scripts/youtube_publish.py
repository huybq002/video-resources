#!/usr/bin/env python3
"""Upload the finished videos of a night to YouTube, as private (or scheduled) drafts the owner reviews.

    python scripts/youtube_publish.py --run-id <GITHUB_RUN_ID> [--dry-run]   # every task published by that run
    python scripts/youtube_publish.py --id <task id> [--id ...] [--dry-run]   # by hand

The night job runs this after the Claude step. It uploads nothing unless ALL of these hold:
  1. channel.json youtube_upload.enabled is true (the owner's switch; off by default),
  2. the look is approved: data/approval.json matches scripts/skill_hash.py (demo nights never upload),
  3. the secrets YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN are set (see README "YouTube upload"),
  4. the task finished: outputs/<id>/manifest.json has a release_url, publish/publish.json passes
     policy_check.py publish, and the task file does not say `upload: false`.
Anything missing is a skip with one line saying why (exit 0), not a failure.

What it uploads, per cut (outputs/<id>/landscape.mp4 and portrait.mp4, as publish_release.py names them):
  title / description / tags from publish/publish.json (youtube for 16:9, youtube_shorts for 9:16), the hashtags,
  the music credit from <cut>/*.music.json and channel.json publish.ai_disclosure appended when missing,
  categoryId from publish.youtube_category_id, the 1280x720 (or 720x1280) thumbnail from outputs/<id>/thumbnails/,
  containsSyntheticMedia = true. Privacy: private unless the task/channel says otherwise; public needs allow_public.
  With youtube_upload.schedule_utc "HH:MM" the video is private with a publishAt at the next such time (>= 2 h ahead).
  A vertical cut longer than 180 s is not a Short, so it is skipped unless youtube_upload.vertical_over_3min is true.
Results go to outputs/<id>/youtube.json; a cut already listed there is never uploaded twice.
--dry-run (or youtube_upload.dry_run) prints the exact metadata and touches nothing, needs no secrets, makes no request.
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import pathlib
import re
import struct
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CI = ROOT / ".claude/skills/code2video-resource-generator/ci/upload_youtube.py"
SHORT_MAX_S = 180
DEFAULTS = {"enabled": False, "dry_run": False, "cuts": ["landscape", "portrait"], "privacy": "private",
            "allow_public": False, "schedule_utc": "", "vertical_over_3min": False, "thumbnail": ""}


def load_uploader():
    spec = importlib.util.spec_from_file_location("upload_youtube", CI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_json(p, default=None):
    p = pathlib.Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else default


def config(channel):
    return {**DEFAULTS, **{k: v for k, v in channel.get("youtube_upload", {}).items() if not k.startswith("_")}}


def approved(root=ROOT):
    """Same rule as the night job's approval gate."""
    sys.path.insert(0, str(root / "scripts"))
    try:
        from skill_hash import skill_hash
    finally:
        sys.path.pop(0)
    a = read_json(root / "data/approval.json", {}) or {}
    return bool(a.get("approved")) and a.get("skill_hash") == skill_hash()


def task_fields(root, tid):
    """Frontmatter of tasks/{done,pending}/<id>.md as a flat dict of strings (no yaml dependency)."""
    for d in ("done", "pending"):
        f = root / "tasks" / d / f"{tid}.md"
        if f.is_file():
            m = re.match(r"---\n(.*?)\n---", f.read_text(encoding="utf-8").replace("\r\n", "\n"), re.S)
            out = {}
            for line in (m.group(1).splitlines() if m else []):
                k, sep, v = line.partition(":")
                if sep and not line.startswith((" ", "#")):
                    out[k.strip()] = v.split(" #")[0].strip().strip('"')
            return out
    return {}


def png_size(p):
    with open(p, "rb") as fh:
        head = fh.read(24)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", head[16:24])
    return None


def pick_thumbnail(folder, cut, prefer=""):
    """First thumbnail (preferred variant first, then a, b, c...) whose shape matches the cut."""
    folder = pathlib.Path(folder)
    if not folder.is_dir():
        return None
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    files.sort(key=lambda p: (p.stem != prefer, p.name))
    for p in files:
        wh = png_size(p)
        if wh is None:                      # jpg: trust the name (…-portrait / …-916 = vertical)
            vertical = bool(re.search(r"portrait|vertical|9x16|916", p.stem))
        else:
            vertical = wh[1] > wh[0]
        if vertical == (cut == "portrait"):
            return p
    return None


def find_video(out, cut):
    for p in (out / f"{cut}.mp4", out / cut / "output.mp4", out / cut / "final.mp4"):
        if p.is_file():
            return p
    return None


def music_credit(out, cut):
    for p in sorted((out / cut).glob("*.music.json")) if (out / cut).is_dir() else []:
        c = str((read_json(p, {}) or {}).get("credit", "")).strip()
        if c:
            return c
    return ""


def next_slot(hhmm, now=None, min_ahead_h=2):
    now = now or dt.datetime.now(dt.timezone.utc)
    h, m = map(int, hhmm.split(":"))
    t = now.replace(hour=h, minute=m, second=0, microsecond=0)
    while t < now + dt.timedelta(hours=min_ahead_h):
        t += dt.timedelta(days=1)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_meta(pub, cut, channel, credit="", privacy="private", publish_at="", tags_fallback=None):
    yt = pub.get("youtube", {})
    d = pub.get("youtube_shorts", {}) if cut == "portrait" else yt
    title = (d.get("title") or yt.get("title") or "").strip()
    desc = (d.get("description") or yt.get("description") or "").strip()
    hashtags = list(d.get("hashtags") or yt.get("hashtags") or [])
    if cut == "portrait" and not any(h.lower() == "#shorts" for h in hashtags):
        hashtags.append("#Shorts")
    extra = []
    missing = [h for h in hashtags if h.lower() not in desc.lower()]
    if missing:
        extra.append(" ".join(missing))
    if credit and credit not in desc:
        extra.append(credit)
    disc = str(channel.get("publish", {}).get("ai_disclosure", "")).strip()
    if disc and disc not in desc:
        extra.append(disc)
    desc = "\n\n".join([desc] + extra) if desc else "\n\n".join(extra)
    m = {"title": title, "description": desc, "tags": list(yt.get("tags") or tags_fallback or []),
         "categoryId": str(channel.get("publish", {}).get("youtube_category_id", "27")),
         "privacy": privacy, "language": channel.get("lang", "en"), "madeForKids": False}
    if publish_at:
        m["privacy"], m["publishAt"] = "private", publish_at
    return m


def select_ids(root, ids, run_id):
    if ids:
        return list(ids)
    if not run_id:
        return []
    found = []
    for man in sorted((root / "outputs").glob("*/manifest.json")):
        tag = str((read_json(man, {}) or {}).get("tag", ""))
        if tag.endswith(f"-{run_id}") and not tag.startswith("demo-"):
            found.append(man.parent.name)
    return found


def plan_task(root, tid, channel, cfg):
    """Returns (jobs, skip_reason). Each job: {cut, video, thumb, meta}."""
    out = root / "outputs" / tid
    if tid.endswith("-demo"):
        return [], "demo build, never uploaded"
    man = read_json(out / "manifest.json")
    if not man or not man.get("release_url"):
        return [], "no manifest.json with a release_url (task not published)"
    task = task_fields(root, tid)
    if task.get("upload", "").lower() == "false":
        return [], "task says upload: false"
    pub_path = out / "publish" / "publish.json"
    pub = read_json(pub_path)
    if not pub:
        return [], f"missing {pub_path.relative_to(root).as_posix()}"
    pol = subprocess.run([sys.executable, str(root / "scripts/policy_check.py"), "publish", str(pub_path),
                          "--channel", str(root / "channel.json")], capture_output=True, text=True, cwd=root)
    if pol.returncode:
        return [], "policy_check publish fails:\n    " + (pol.stdout + pol.stderr).strip().replace("\n", "\n    ")
    privacy = task.get("privacy") or cfg["privacy"] or "private"
    publish_at = next_slot(cfg["schedule_utc"]) if cfg.get("schedule_utc") else ""
    dur = man.get("duration_s") or 0
    done = read_json(out / "youtube.json", {}) or {}
    jobs, notes = [], []
    for cut in cfg["cuts"]:
        if cut in done:
            notes.append(f"{cut}: already uploaded ({done[cut].get('url')})")
            continue
        if cut == "portrait" and dur > SHORT_MAX_S and not cfg["vertical_over_3min"]:
            notes.append(f"{cut}: {dur:.0f}s > {SHORT_MAX_S}s is not a Short (set vertical_over_3min to upload it anyway)")
            continue
        video = find_video(out, cut)
        if not video:
            notes.append(f"{cut}: no video on this runner")
            continue
        meta = build_meta(pub, cut, channel, music_credit(out, cut), privacy, publish_at, pub.get("keywords"))
        jobs.append({"cut": cut, "video": video, "thumb": pick_thumbnail(out / "thumbnails", cut, cfg.get("thumbnail", "")), "meta": meta})
    return jobs, "; ".join(notes)


def main(argv=None, root=ROOT, env=os.environ) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", action="append", default=[])
    ap.add_argument("--run-id", default=env.get("GITHUB_RUN_ID", ""))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    channel = read_json(root / "channel.json", {})
    cfg = config(channel)
    dry = a.dry_run or bool(cfg["dry_run"])
    if not cfg["enabled"] and not a.dry_run:
        print("youtube upload: off (channel.json youtube_upload.enabled is false)")
        return 0
    if not approved(root):
        if not dry:
            print("youtube upload: skipped, the look is not approved (data/approval.json does not match skill_hash.py)")
            return 0
        print("youtube upload: the look is NOT approved; a real run would upload nothing (dry run continues)")
    up = load_uploader()
    if not dry and up.missing_secrets():
        print("youtube upload: skipped, missing secret(s): " + ", ".join(up.missing_secrets()))
        return 0
    ids = select_ids(root, a.id, a.run_id)
    if not ids:
        print(f"youtube upload: nothing published by run {a.run_id or '?'}")
        return 0
    failed, access = 0, None
    for tid in ids:
        jobs, why = plan_task(root, tid, channel, cfg)
        if why:
            print(f"{tid}: {why}")
        for j in jobs:
            m = j["meta"]
            errs = up.check_meta(m, bool(cfg["allow_public"]))
            if errs:
                print(f"{tid} {j['cut']}: metadata errors: " + "; ".join(errs))
                failed += 1
                continue
            print(f"{'DRY RUN' if dry else 'UPLOAD'} {tid} {j['cut']}: {j['video'].name} ({j['video'].stat().st_size / 1e6:.1f} MB) "
                  f"privacy={m['privacy']}{' publishAt=' + m['publishAt'] if m.get('publishAt') else ''} "
                  f"thumb={j['thumb'].name if j['thumb'] else 'none'}")
            if dry:
                print(json.dumps(m, ensure_ascii=False, indent=1))
                continue
            try:
                access = access or up.token()
                res = up.upload(str(j["video"]), m, access)
                vid = res["id"]
                ts = up.thumbnail(vid, str(j["thumb"]), access) if j["thumb"] else 0
            except Exception as e:                       # one failed cut does not stop the others
                print(f"{tid} {j['cut']}: FAILED: {e}")
                failed += 1
                continue
            rec_path = root / "outputs" / tid / "youtube.json"
            rec = read_json(rec_path, {}) or {}
            rec[j["cut"]] = {"id": vid, "url": f"https://youtu.be/{vid}", "privacy": m["privacy"], "publishAt": m.get("publishAt"),
                             "title": m["title"], "thumbnail": j["thumb"].name if j["thumb"] else None, "thumbnail_status": ts,
                             "uploaded_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
            rec_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{tid} {j['cut']}: https://youtu.be/{vid} ({m['privacy']}) - review it in YouTube Studio")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
