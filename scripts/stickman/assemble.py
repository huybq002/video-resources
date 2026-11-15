#!/usr/bin/env python3
"""Assemble and render one cut of a stickman film with the pinned stickman-video-director runtime.

    python scripts/stickman/assemble.py --story stories/<id>.json --voice outputs/<id>/voice \
        --shots outputs/<id>/shots-16x9.json --ratio 16:9 --out outputs/<id>/landscape [--seconds 20] [--check]

Inputs:
  story   the film's script (stories/<id>.json): style, cast, scenes with place + lines (hezb-story skill)
  voice   folder from narrate.py: narration.wav + timing.json (line/scene times, one-line captions)
  shots   the AUTHORED picture for this ratio (written by the night job following the selected style's references in
          the stickman runtime): {"shots": [{start, end, layers: [...]}, ...], "sfx": [{time, name|kind, gain}],
          "assets": {"name.png": "<svg ...>"}, "picture_motion" / b3 semantics when the style needs them}
          Times are absolute seconds on the narration timeline (timing.json). "assets" are SVG drawings the author wrote
          for this story; they are rasterised to PNG (sharp, in the runtime) so image layers can use them.
What it adds (our part, kept from the old pipeline):
  - narration + captions from timing.json (the runtime checks one-line fit and timing);
  - room tone that follows each scene's place (scripts/media/score.py), an original score from the story's mood;
  - sound effects named from our bank (scripts/media/sfx_bank.py: step, key, pop, sting, whoosh ...) as file effects;
  - B4 (when it is enabled): a voice override note, since we use free edge-tts / VieNeu voices, not the B4 Brian voice.
Then it runs the runtime: validate, and preview over the whole film (or --seconds N for a demo), and copies the encode
to <out>/output.mp4 with <out>/output.srt. --check stops after validate.
"""
import argparse, json, os, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "media"))
LOCK = json.loads((ROOT / "stickman" / "lock.json").read_text(encoding="utf-8"))
DIMS = {"16:9": (1920, 1080), "9:16": (1080, 1920)}


def runtime_dir():
    home = pathlib.Path(os.environ.get("STICKMAN_HOME") or ROOT / ".cache" / "stickman-director")
    d = home / LOCK["skill_dir"]
    if not (d / "node_modules").exists():
        subprocess.run(["bash", str(ROOT / "scripts" / "stickman" / "install.sh")], check=True, env={**os.environ, "STICKMAN_HOME": str(home)})
    return d


def node(rt, *args):
    r = subprocess.run(["node", str(rt / "scripts" / "autopilot.mjs"), *map(str, args)], cwd=str(rt), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def rasterise(rt, svg_text, png_path, width=None):
    """SVG drawing -> PNG with the runtime's own sharp (no extra dependency)"""
    svg = png_path.with_suffix(".svg"); svg.write_text(svg_text, encoding="utf-8")
    js = ("const sharp=require('sharp');sharp(process.argv[1],{density:144})" + (f".resize({int(width)})" if width else "")
          + ".png().toFile(process.argv[2]).then(()=>process.exit(0)).catch(e=>{console.error(e.message);process.exit(1)})")
    r = subprocess.run(["node", "-e", js, str(svg), str(png_path)], cwd=str(rt), capture_output=True, text=True)
    if r.returncode: raise SystemExit(f"asset {png_path.name}: SVG could not be rasterised: {r.stderr.strip()[:300]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", required=True); ap.add_argument("--voice", required=True); ap.add_argument("--shots", required=True)
    ap.add_argument("--ratio", choices=list(DIMS), default="16:9"); ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, help="render only the first N seconds (a demo); default: the whole film")
    ap.add_argument("--check", action="store_true", help="validate only")
    a = ap.parse_args()
    story = json.load(open(a.story, encoding="utf-8")); voice = pathlib.Path(a.voice)
    timing = json.load(open(voice / "timing.json", encoding="utf-8")); authored = json.load(open(a.shots, encoding="utf-8"))
    style = story.get("style", "B3").upper()
    if style not in LOCK["enabled_styles"]:
        raise SystemExit(f"style {style} is not enabled: {LOCK['disabled_styles'].get(style, 'unknown style')}. Enabled: {LOCK['enabled_styles']}")
    rt = runtime_dir()
    out = pathlib.Path(a.out).resolve(); proj = out / "project"; proj.mkdir(parents=True, exist_ok=True)
    D = float(timing["duration"]); W, H = DIMS[a.ratio]
    shutil.copy(voice / "narration.wav", proj / "narration.wav")
    # the author's drawings
    for name, svg in (authored.get("assets") or {}).items():
        target = proj / "assets" / name; target.parent.mkdir(parents=True, exist_ok=True)
        rasterise(rt, svg, target.with_suffix(".png"))
    # sound: room tone per place + the film's score
    import score as S, sfx_bank as B
    S.write_wav(proj / "room.wav", S.ambience_for_scenes(timing["scenes"], D))
    S.write_wav(proj / "score.wav", S.score(story, D, [(s["start"], s["end"], str(s.get("value", ""))[:1]) for s in timing["scenes"]]))
    sfx = []
    (proj / "sfx").mkdir(exist_ok=True)
    for i, e in enumerate(authored.get("sfx") or []):
        if e.get("kind") and e["kind"] != "file":
            sfx.append({"time": float(e["time"]), "kind": e["kind"], "gain": float(e.get("gain", 0.3))}); continue
        nm = e.get("name", "pop")
        if nm not in B.NAMES: continue
        f = proj / "sfx" / f"{nm}-{i % 4}.wav"
        if not f.exists(): B.write_wav(f, B.load(nm, None, i % 4))
        sfx.append({"kind": "file", "path": f"sfx/{f.name}", "time": float(e["time"]), "gain": float(e.get("gain", 0.4))})
    p = {"version": 1, "style": style, "width": W, "height": H, "fps": int(authored.get("fps", 30)),
         "voice": {"path": "narration.wav", "lead": 0, "tail": 0},
         "captions": timing["captions"], "shots": authored["shots"], "sfx": sfx,
         "ambience": [{"path": "room.wav", "start": 0, "end": round(D, 3), "gain": 0.12}],
         "music": {"path": "score.wav", "gain": 0.12},
         "reference_review": {"author_id": "hezb-night-job", "capability": {
             "mode": "limited", "environment": "GitHub runner, no image or video generation API (owner decision 2026-11-15)",
             "limitations": ["characters, props and places are drawn as code (vector layers / authored SVG), not painted by an image model",
                             "not sample-equivalent: best effort against the style's public samples"]}}}
    for k in ("television", "picture_motion", "audio_cuts", "dialogue", "metadata"):
        if k in authored: p[k] = authored[k]
    if style == "B4":
        p["voice"].update({"name": "edge-tts/VieNeu", "user_override": "Owner chose free voices (edge-tts / VieNeu) on 2026-11-15: no ElevenLabs key for the B4 Brian voice"})
    if a.ratio == "9:16" and authored.get("portrait"):
        p["portrait"] = authored["portrait"]
    pj = proj / "project.json"; pj.write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")
    rc, log = node(rt, "validate", pj, *(["--seconds", a.seconds] if a.seconds else []))
    (out / "validate.log").write_text(log, encoding="utf-8")
    if rc:
        print(log[-3000:]); raise SystemExit(f"validate FAILED for {a.ratio} (see {out / 'validate.log'}): fix the authored shots and re-run")
    print(f"validate OK: {style} {a.ratio}, {len(p['shots'])} shots, {D:.1f}s")
    if a.check: return
    secs = a.seconds or D
    rc, log = node(rt, "preview", pj, "--seconds", round(secs, 3), "--replace")
    (out / "render.log").write_text(log, encoding="utf-8")
    mp4 = proj / "output" / "preview.mp4"
    if rc and not mp4.exists():
        print(log[-3000:]); raise SystemExit(f"render FAILED for {a.ratio} (see {out / 'render.log'})")
    shutil.copy(mp4, out / "output.mp4")
    for ext in ("srt", "vtt"):
        if (proj / "output" / f"preview.{ext}").exists(): shutil.copy(proj / "output" / f"preview.{ext}", out / f"output.{ext}")
    if (proj / "output" / "preview-contact-sheet.png").exists(): shutil.copy(proj / "output" / "preview-contact-sheet.png", out / "contact-sheet.png")
    notes = [l for l in log.splitlines() if "reference review" in l.lower() or "fail" in l.lower()][-5:]
    print(f"rendered {out / 'output.mp4'} ({secs:.1f}s){' | runtime notes: ' + ' / '.join(notes) if notes else ''}")


if __name__ == "__main__":
    main()
