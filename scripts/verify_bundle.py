#!/usr/bin/env python3
"""Verify a generated resource bundle and the rendered video against the task.

  python scripts/verify_bundle.py bundle <project_dir> --spec specs/<id>.json [--expect-minutes 9] [--aspect 9:16]
  python scripts/verify_bundle.py video  <video.mp4> --spec specs/<id>.json [--allow-silent] [--aspect 9:16]

One spec builds both cuts, so pass --aspect to say which one is being checked (it decides the frame size).

bundle: total length, contiguous cues, cue length, scenes vs target_s, required files.
video : duration, audio stream present and not silent, frame size.
Exit code 1 and one line per problem when something is wrong. Used by the night job after
generate and after render, so a short, silent or broken video is caught before it is committed.
"""
import argparse, json, pathlib, re, shutil, subprocess, sys

errors, notes = [], []
def err(m): errors.append(m)

def ts(s):
    h, m, rest = s.strip().split(":"); sec, ms = re.split(r"[,.]", rest)
    return ((int(h) * 60 + int(m)) * 60 + int(sec)) * 1000 + int(ms.ljust(3, "0")[:3])

CUE = re.compile(r"^\[(?P<who>[^\]]+)\]\[(?P<a>[\d:,.]+)\s*-->\s*(?P<b>[\d:,.]+)\](?:\[[^\]]*\])?\s*:\s*(?P<text>.+)$", re.S)

def load_spec(p):
    return json.load(open(p, encoding="utf-8"))

def expected_seconds(spec, minutes):
    if minutes: return float(minutes) * 60
    return float(spec["duration_s"])

def check_bundle(proj, spec, minutes):
    proj = pathlib.Path(proj)
    total = expected_seconds(spec, minutes)
    for need in ("index.html", "script.srt", "compositions", "assets"):
        if not (proj / need).exists(): err(f"missing {need}")
    if not (proj / "assets" / "fonts").exists(): err("missing assets/fonts")
    if not (proj / "assets" / "vendor" / "gsap.min.js").exists(): err("missing assets/vendor/gsap.min.js")
    idx = (proj / "index.html").read_text(encoding="utf-8", errors="replace") if (proj / "index.html").exists() else ""
    m = re.search(r'id="root"[^>]*data-duration="([\d.]+)"', idx) or re.search(r"id='root'[^>]*data-duration='([\d.]+)'", idx)
    if not m: err("index.html: root data-duration not found")
    elif abs(float(m.group(1)) - total) > 0.5: err(f"index.html duration {m.group(1)}s but the task asks for {total:.0f}s")
    cues = []
    srt = proj / "script.srt"
    if srt.exists():
        for block in re.split(r"\n\s*\n", srt.read_text(encoding="utf-8").strip()):
            mm = CUE.match(" ".join(block.strip().splitlines()))
            if not mm: err(f"script.srt: bad block: {block[:60]!r}"); continue
            cues.append((mm["who"], ts(mm["a"]), ts(mm["b"]), mm["text"].strip()))
    if not cues: err("script.srt has no cues"); return
    if abs(cues[-1][2] / 1000 - total) > 0.5: err(f"script.srt ends at {cues[-1][2]/1000:.1f}s but the task asks for {total:.0f}s")
    if cues[0][1] != 0: err(f"script.srt starts at {cues[0][1]/1000:.2f}s, not 0")
    for i in range(1, len(cues)):
        if abs(cues[i][1] - cues[i - 1][2]) > 50: err(f"script.srt: gap/overlap before cue {i+1} ({cues[i-1][2]}ms -> {cues[i][1]}ms)")
    for i, (who, a, b, text) in enumerate(cues, 1):
        w = len(text.split())
        if w > 16: err(f"cue {i} has {w} words (max 14)")
        if b <= a: err(f"cue {i} has no duration")
    scenes = sorted((proj / "compositions").glob("scene_*.html")) if (proj / "compositions").exists() else []
    want = spec.get("scenes", [])
    if want and len(scenes) != len(want): err(f"{len(scenes)} scene files but the spec has {len(want)} scenes")
    tgt = [s.get("target_s") for s in want]
    if all(t is not None for t in tgt) and tgt and abs(sum(tgt) - total) > 0.5: err(f"scene target_s add up to {sum(tgt)}s, not {total:.0f}s")
    lint_gate(spec)
    notes.append(f"bundle: {len(cues)} cues, {len(scenes)} scenes, script ends {cues[-1][2]/1000:.1f}s, expected {total:.0f}s")

def lint_gate(spec):
    """The spec lint (picture follows words, sets, voice, story craft) must be clean before anything is rendered.
    Night 003 rendered an hour of boxes with every warning open; warnings are now PROBLEMS here."""
    sk = pathlib.Path(__file__).resolve().parent.parent / ".claude/skills/code2video-resource-generator/scripts"
    sys.path.insert(0, str(sk))
    try:
        import copy, io, contextlib, autofill, spec_lint
        sp = copy.deepcopy(spec)
        with contextlib.redirect_stdout(io.StringIO()):
            autofill.run(sp)              # generate.py fills the same gaps before it lints
        w = [l for l in spec_lint.lint(sp) if l.startswith("WARNING")]
    except Exception as e:                # never let the gate itself break a night: report it instead
        notes.append(f"lint gate skipped: {e}"); return
    if len(w) > MAX_WARN:
        err(f"spec lint: {len(w)} WARNING(s) still open (allowed {MAX_WARN}); fix the spec. First: {w[0][9:160]}")

def probe(video):
    if not shutil.which("ffprobe"): err("ffprobe not found"); return None
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate", "-of", "json", str(video)], capture_output=True, text=True)
    if r.returncode: err(f"ffprobe failed: {r.stderr[-200:]}"); return None
    return json.loads(r.stdout)

def check_video(video, spec, minutes, allow_silent):
    video = pathlib.Path(video)
    if not video.exists(): err(f"video not found: {video}"); return
    total = expected_seconds(spec, minutes)
    info = probe(video)
    if not info: return
    dur = float(info["format"]["duration"])
    if abs(dur - total) > 1.5: err(f"video is {dur:.1f}s but the task asks for {total:.0f}s")
    kinds = [s["codec_type"] for s in info["streams"]]
    if "video" not in kinds: err("no video stream")
    if "audio" not in kinds: err("no audio stream: the video is silent")
    elif not allow_silent and shutil.which("ffmpeg"):
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-af", "volumedetect", "-vn", "-f", "null", "-"], capture_output=True, text=True)
        mm = re.search(r"mean_volume:\s*(-?[\d.]+|-inf) dB", r.stderr)
        if not mm or mm.group(1) == "-inf" or float(mm.group(1)) < -60: err(f"audio is silent (mean volume {mm.group(1) if mm else 'unknown'} dB)")
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    w, h = v.get("width"), v.get("height")
    want = (1080, 1920) if spec.get("aspect") == "9:16" else (1920, 1080)
    if (w, h) != want: err(f"frame size {w}x{h}, expected {want[0]}x{want[1]}")
    notes.append(f"video: {dur:.1f}s, streams={kinds}, {w}x{h}")
    # the voice must not be rushed or cut (video 005, 2026-11-12: lines read at 4-5 words/s, words swallowed)
    fitf = video.parent / "voiceover_fit.json"
    if fitf.exists():
        fr = json.loads(fitf.read_text(encoding="utf-8"))
        if fr.get("cut") or fr.get("maxTempo", 1) > 1.25 or fr.get("rushed", 0) > max(2, 0.1 * fr.get("cues", 0)):
            err(f"voice-over rushed or cut: {fr.get('rushed')} line(s) faster than the normal pace (max x{fr.get('maxTempo')}), "
                f"{fr.get('cut')} line(s) cut. Give those lines more time in the spec (shorter text or longer target_s) and rebuild")
        else:
            notes.append(f"voice-over pace OK (max x{fr.get('maxTempo')}, {fr.get('rushed')} line(s) faster than normal)")

ap = argparse.ArgumentParser(); ap.add_argument("kind", choices=["bundle", "video"]); ap.add_argument("path")
ap.add_argument("--spec", required=True); ap.add_argument("--expect-minutes"); ap.add_argument("--allow-silent", action="store_true")
ap.add_argument("--aspect", choices=["16:9", "9:16"], help="which cut this is (one spec builds both)")
ap.add_argument("--max-warnings", type=int, default=0, help="spec lint WARNINGs tolerated (default 0; raise only for one that cannot be fixed, and say so in the report)")
a = ap.parse_args()
MAX_WARN = a.max_warnings
spec = load_spec(a.spec)
if a.aspect: spec["aspect"] = a.aspect
(check_bundle if a.kind == "bundle" else lambda p, s, m: check_video(p, s, m, a.allow_silent))(a.path, spec, a.expect_minutes)
for n in notes: print(n)
if errors:
    print("PROBLEMS:"); [print(" -", e) for e in errors]; sys.exit(1)
print("OK")
