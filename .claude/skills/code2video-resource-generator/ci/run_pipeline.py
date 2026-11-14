"""ONE command for Claude (in the GitHub job or locally) after the spec is written:
python ci/run_pipeline.py <spec.json> <out_dir> [--series bible.json] [--jobs 2] [--chunk 120] [--upload [--privacy private|unlisted|public] [--allow-public]] [--stop-after generate|tts|render]

generate (script.srt, backgrounds, characters, scenes)  ->  tts (voiceover.wav fitted to script.srt)  ->  render in parallel slices (npx hyperframes render)
-> assemble final.mp4 (+voice-over, sound effects on the picture's beats, music, thumbnail)  ->  metadata.json  ->  upload to YouTube (only with --upload; default privacy private)
Prints one short status line per step (cheap for Claude to read) and the full log goes to <out_dir>/pipeline.log. Exit code != 0 on failure, last log lines printed.
Run it as ONE foreground command with a long timeout (set BASH_MAX_TIMEOUT_MS in the job); nothing needs polling.
"""
import argparse, concurrent.futures as cf, json, os, pathlib, subprocess, sys, time

HERE = pathlib.Path(__file__).resolve().parent; SK = HERE.parent; PY = sys.executable
ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("out"); ap.add_argument("--series"); ap.add_argument("--jobs", type=int, default=max(1, min(4, (os.cpu_count() or 2) // 2)))
ap.add_argument("--max-warnings", type=int, default=0, help="stop after generate when the spec lint prints more WARNINGs than this (default 0)")
ap.add_argument("--chunk", type=float, default=120); ap.add_argument("--upload", action="store_true"); ap.add_argument("--privacy", default="private"); ap.add_argument("--allow-public", action="store_true")
ap.add_argument("--stop-after", choices=["generate", "tts", "render"])
ap.add_argument("--aspect", choices=["16:9", "9:16"], help="override spec.aspect for this build (one aspect per run; build both by calling twice)")
ap.add_argument("--no-series-update", action="store_true", help="read the series bible but do not write the episode back (second aspect)")
a = ap.parse_args()
spec = pathlib.Path(a.spec).resolve(); out = pathlib.Path(a.out).resolve(); proj = out; out.mkdir(parents=True, exist_ok=True); log = out.parent / (out.name + "_pipeline.log")
T0 = time.time(); LOG = open(log, "w", encoding="utf-8")

def say(msg): print(f"[{time.time()-T0:6.0f}s] {msg}", flush=True)
def run(name, cmd, cwd=None, env=None):
    LOG.write(f"\n$ {' '.join(map(str, cmd))}\n"); LOG.flush()
    r = subprocess.run(cmd, cwd=cwd, stdout=LOG, stderr=subprocess.STDOUT, env={**os.environ, **(env or {})}, shell=(sys.platform == "win32" and cmd[0] == "npx"))
    if r.returncode:
        LOG.flush(); tail = pathlib.Path(log).read_text(encoding="utf-8", errors="replace").splitlines()[-25:]
        sys.exit(f"FAILED at {name} (exit {r.returncode}). Last log lines:\n" + "\n".join(tail))

# 1 generate
gen = ([PY, str(SK / "scripts" / "generate.py"), str(spec), str(proj)]
       + (["--series", a.series] if a.series else [])
       + (["--aspect", a.aspect] if a.aspect else [])
       + (["--no-series-update"] if a.no_series_update else []))
run("generate", gen); say("generate ok: " + next((l for l in pathlib.Path(log).read_text(encoding="utf-8", errors="replace").splitlines() if l.startswith("script.srt:")), "script.srt written"))
_warn = [l for l in pathlib.Path(log).read_text(encoding="utf-8", errors="replace").splitlines() if l.startswith(("WARNING", "SERIES WARNING"))]
for l in _warn: say(l)
# Night 003 rendered for an hour with every picture/script warning still open and came out as a slideshow of boxes.
# The voice-over and the render cost far more than fixing the spec, so stop here until the spec is clean.
if len(_warn) > a.max_warnings:
    sys.exit(f"STOPPED after generate: {len(_warn)} WARNING(s) (allowed {a.max_warnings}). Fix the spec and re-run; "
             f"pass --max-warnings N only for a warning that cannot be fixed, and say which one in the report.")
if a.stop_after == "generate": sys.exit(0)
# 2 voice-over
run("tts", [PY, str(HERE / "tts.py"), str(proj), "--spec", str(spec)]); say("tts ok: " + [l for l in pathlib.Path(log).read_text(encoding="utf-8", errors="replace").splitlines() if l.startswith("voiceover.wav")][-1])
# 2b mouths from the real voice-over (Rhubarb); without the binary the text-based lip-sync stays
_lang = json.loads(spec.read_text(encoding="utf-8")).get("lang", "en")
run("lipsync", [PY, str(HERE / "lipsync_audio.py"), str(proj), "--lang", _lang]); say(([l for l in pathlib.Path(log).read_text(encoding="utf-8", errors="replace").splitlines() if l.startswith("lipsync:")] or ["lipsync: done"])[-1])
if a.stop_after == "tts": sys.exit(0)
# 3 render in parallel slices
rc = [PY, str(HERE / "render_chunks.py")]
run("plan", rc + ["plan", str(proj), "--chunk", str(a.chunk)]); chunks = json.loads((proj / "chunks.json").read_text()); say(f"render: {len(chunks)} slice(s), {a.jobs} parallel")
def render(c):
    for attempt in (1, 2):
        r = subprocess.run(rc + ["render", str(proj), "--i", str(c["i"]), "--workers", "1"], stdout=LOG, stderr=subprocess.STDOUT)
        if r.returncode == 0: return c["i"]
        LOG.write(f"\nslice {c['i']} failed (attempt {attempt})\n"); LOG.flush()
    raise RuntimeError(f"slice {c['i']} failed twice")
with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
    futs = [ex.submit(render, c) for c in chunks]
    for f in cf.as_completed(futs):
        try: say(f"slice {f.result()} done")
        except Exception as e: sys.exit(f"FAILED at render: {e}; see {log}")
if a.stop_after == "render": sys.exit(0)
# 4 assemble + thumbnail, 5 metadata
run("assemble", rc + ["assemble", str(proj), "--out", "final.mp4"])
run("sfx", [PY, str(HERE / "add_sfx.py"), str(proj / "final.mp4"), "--project", str(proj)]); say(([l for l in pathlib.Path(log).read_text(encoding="utf-8", errors="replace").splitlines() if l.startswith("sfx:")] or ["sfx: done"])[-1])
run("music", [PY, str(HERE / "add_music.py"), str(proj / "final.mp4"), "--spec", str(spec)]); say(([l for l in pathlib.Path(log).read_text(encoding="utf-8", errors="replace").splitlines() if l.startswith("music:")] or ["music: done"])[-1])
run("thumbnail", ["ffmpeg", "-y", "-ss", "3", "-i", str(proj / "final.mp4"), "-frames:v", "1", "-vf", "scale=1280:-2", str(proj / "thumb.jpg")])
meta = out.parent / (out.name + "_metadata.json")
r = subprocess.run([PY, str(HERE / "make_metadata.py"), str(spec), str(proj), "--privacy", a.privacy], capture_output=True, text=True, encoding="utf-8")
if r.returncode: sys.exit("FAILED at metadata:\n" + r.stderr[-800:])
meta.write_text(r.stdout, encoding="utf-8"); say(f"final.mp4 ready: {proj/'final.mp4'}")
# 6 upload (explicit opt-in)
if a.upload:
    up = [PY, str(HERE / "upload_youtube.py"), "--video", str(proj / "final.mp4"), "--meta", str(meta), "--thumb", str(proj / "thumb.jpg"), "--confirm"] + (["--allow-public"] if a.allow_public else [])
    run("upload", up, cwd=str(out.parent)); say("upload ok: " + (out.parent / "upload_result.json").read_text() if (out.parent / "upload_result.json").exists() else "upload ok")
else:
    say("upload skipped (no --upload)")
say("DONE")
