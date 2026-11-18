"""One command from a directed story to the finished film (hezb-motion).

    python motion/make_film.py --voice outputs/<id>/voice --direct outputs/<id>/direct.py --out outputs/<id>/landscape
        [--size 1280x720] [--fps 24] [--workers 3] [--seconds 30] [--stills-only]

Steps (each skipped when its output is newer than its inputs):
  1. motion/install.sh       node modules + engine bundle
  2. align.py                voice/words.json (faster-whisper word timings)
  3. direct.py <out>         film.json (your direction: places, cast, verbs, shots, sound)
  4. tools/props3d.mjs       the .glb models film.json names (insert3d shots)
  5. stills                  <out>/stills/contact-sheet.png: one frame per shot, for you to LOOK at before the long render
  6. tools/score.mjs         out/score.wav (Tone.js)
  7. tools/render.mjs        out/video.mp4 (headless Chromium; software GL on the runner: 1280x720 at 24 fps)
  8. mix.py                  <out>/output.mp4 (voice + score + room tone + foley, -14 LUFS)
publish_release.py picks up <out>/output.mp4 and bundles the folder (film.json, models, stills).
"""
import argparse, json, os, pathlib, subprocess, sys, shutil, time

HERE = pathlib.Path(__file__).resolve().parent


def run(cmd, **kw):
    print("$", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", required=True); ap.add_argument("--direct", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--size", default=os.environ.get("MOTION_SIZE", "1280x720")); ap.add_argument("--fps", type=int, default=int(os.environ.get("MOTION_FPS", "24")))
    ap.add_argument("--workers", type=int, default=int(os.environ.get("MOTION_WORKERS", "3")))
    ap.add_argument("--seconds", type=float, default=0, help="render only the first N seconds (a demo or a test)")
    ap.add_argument("--stills-only", action="store_true", help="stop after the contact sheet (look before you render)")
    ap.add_argument("--whisper-model", default=os.environ.get("MOTION_WHISPER", "small"))
    a = ap.parse_args()
    voice, out = pathlib.Path(a.voice), pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    run(["bash", HERE / "install.sh"])
    if not (voice / "words.json").exists() or (voice / "words.json").stat().st_mtime < (voice / "narration.wav").stat().st_mtime:
        run([sys.executable, HERE / "align.py", voice, "--model", a.whisper_model])
    run([sys.executable, a.direct, out])
    film = json.load(open(out / "film.json", encoding="utf-8"))
    models = [pathlib.Path(u).stem for u in (film.get("models") or {}).values()]
    if models: run(["node", HERE / "tools/props3d.mjs", out / "models", *models])
    # stills: the middle of every shot, tiled
    mids = [round((s["t0"] + s["t1"]) / 2, 2) for s in film["shots"]]
    if a.seconds: mids = [m for m in mids if m < a.seconds]
    step = max(1, len(mids) // 36); mids = mids[::step]
    st = out / "stills"; shutil.rmtree(st, ignore_errors=True); st.mkdir()
    run(["node", HERE / "tools/render.mjs", out, "--size", a.size, "--still", ",".join(map(str, mids))])
    for p in (out / "out").glob("still-*.png"): p.replace(st / p.name)
    tile = f"tile=6x{(len(mids) + 5) // 6}"
    run(["ffmpeg", "-y", "-loglevel", "error", "-pattern_type", "glob", "-i", str(st / "still-*.png"), "-vf", f"scale=480:-1,{tile}", "-frames:v", "1", str(st / "contact-sheet.png")]) if os.name != "nt" else None
    print("contact sheet:", st / "contact-sheet.png", flush=True)
    if a.stills_only: return
    run(["node", HERE / "tools/score.mjs", out])
    rargs = ["node", HERE / "tools/render.mjs", out, "--size", a.size, "--fps", a.fps, "--workers", a.workers]
    if a.seconds: rargs += ["--to", a.seconds]
    run(rargs)
    run([sys.executable, HERE / "mix.py", out, voice, out / "output.mp4"])
    for p in ("score.wav", "mix.wav", "video.mp4"): (out / "out" / p).unlink(missing_ok=True)   # keep the bundle small
    print(f"film ready: {out / 'output.mp4'} ({(time.time() - t0) / 60:.1f} min)")


if __name__ == "__main__":
    main()
