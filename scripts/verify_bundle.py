#!/usr/bin/env python3
"""Verify a stickman film before it is published (2026-11-15: stories + stickman-video-director runtime).

  python scripts/verify_bundle.py bundle outputs/<id>/<cut> --story stories/<id>.json
  python scripts/verify_bundle.py video  outputs/<id>/<cut>/output.mp4 --story stories/<id>.json --aspect 16:9|9:16 [--allow-silent]

bundle: the story lint is clean, the cut has its project (project.json, narration, room tone, score) and the runtime's
        validate passed for it (outputs/<id>/<cut>/validate.log).
video : length matches the voice (timing.json), audio present and not silent, frame size, and the director's pass on the
        finished film (scripts/media/director_pass.py: dead air, flat mix, frozen picture, black frames).
Exit code 1 and one line per problem.
"""
import argparse, json, pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
errors, notes = [], []
def err(m): errors.append(m)


def voice_seconds(story_path):
    sid = json.load(open(story_path, encoding="utf-8")).get("id", pathlib.Path(story_path).stem)
    t = ROOT / "outputs" / sid / "voice" / "timing.json"
    return float(json.loads(t.read_text(encoding="utf-8"))["duration"]) if t.exists() else None


def check_bundle(cut, story_path, max_warn):
    cut = pathlib.Path(cut); proj = cut / "project"
    sys.path.insert(0, str(ROOT / ".claude" / "skills" / "hezb-story" / "scripts"))
    import lint_story
    w = lint_story.lint(json.load(open(story_path, encoding="utf-8")))
    if len(w) > max_warn: err(f"story lint: {len(w)} WARNING(s) open (allowed {max_warn}). First: {w[0][9:170]}")
    for need in ("project.json", "narration.wav", "room.wav", "score.wav"):
        if not (proj / need).exists(): err(f"missing {proj / need}")
    log = (cut / "validate.log").read_text(encoding="utf-8", errors="replace") if (cut / "validate.log").exists() else ""
    if '"valid":true' not in log.replace(" ", ""): err(f"the runtime's validate has not passed for {cut.name} (run scripts/stickman/assemble.py --check)")
    if proj.joinpath("project.json").exists():
        p = json.loads(proj.joinpath("project.json").read_text(encoding="utf-8"))
        notes.append(f"bundle: style {p.get('style')}, {len(p.get('shots', []))} shots, {len(p.get('captions', []))} captions, {len(p.get('sfx', []))} sfx")


def check_video(video, story_path, aspect, allow_silent):
    video = pathlib.Path(video)
    if not video.exists(): err(f"video not found: {video}"); return
    if not shutil.which("ffprobe"): err("ffprobe not found"); return
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", str(video)],
                       capture_output=True, text=True)
    if r.returncode: err(f"ffprobe failed: {r.stderr[-200:]}"); return
    info = json.loads(r.stdout); dur = float(info["format"]["duration"])
    want_s = voice_seconds(story_path)
    if want_s and abs(dur - want_s) > 1.0: err(f"video is {dur:.1f}s but the voice is {want_s:.1f}s (render the whole film)")
    kinds = [s["codec_type"] for s in info["streams"]]
    if "video" not in kinds: err("no video stream")
    if "audio" not in kinds: err("no audio stream: the video is silent")
    elif not allow_silent:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-af", "volumedetect", "-vn", "-f", "null", "-"], capture_output=True, text=True)
        mm = re.search(r"mean_volume:\s*(-?[\d.]+|-inf) dB", r.stderr)
        if not mm or mm.group(1) == "-inf" or float(mm.group(1)) < -60: err(f"audio is silent (mean volume {mm.group(1) if mm else 'unknown'} dB)")
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    w, h = v.get("width"), v.get("height"); want = (1080, 1920) if aspect == "9:16" else (1920, 1080)
    if (w, h) != want: err(f"frame size {w}x{h}, expected {want[0]}x{want[1]}")
    notes.append(f"video: {dur:.1f}s, streams={kinds}, {w}x{h}")
    if not allow_silent:
        dp = ROOT / "scripts" / "media" / "director_pass.py"
        r = subprocess.run([sys.executable, str(dp), str(video), "--out", str(video.parent / "director_pass")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        for line in r.stdout.splitlines():
            if line.startswith("PROBLEM:"): err(line[len("PROBLEM: "):])
            elif line.startswith("director_pass:"): notes.append(line)


ap = argparse.ArgumentParser(); ap.add_argument("kind", choices=["bundle", "video"]); ap.add_argument("path")
ap.add_argument("--story", required=True); ap.add_argument("--aspect", choices=["16:9", "9:16"], default="16:9")
ap.add_argument("--allow-silent", action="store_true"); ap.add_argument("--max-warnings", type=int, default=0)
a = ap.parse_args()
if a.kind == "bundle": check_bundle(a.path, a.story, a.max_warnings)
else: check_video(a.path, a.story, a.aspect, a.allow_silent)
for n in notes: print(n)
if errors:
    print("PROBLEMS:"); [print(" -", e) for e in errors]; sys.exit(1)
print("OK")
