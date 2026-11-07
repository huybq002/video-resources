"""One-shot generator: spec.json -> a Code2Video / HyperFrames project that follows docs/hyperframes-asset-contract.md
python generate.py <spec.json> <out_dir> [--keep-srt] [--skip-bg] [--no-audio-tag] [--no-captions] [--check]

<out_dir>/                      (the project: upload this folder, or index.html + script.srt + assets)
  index.html  script.srt  compositions/scene_N.html  assets/(bg_*.png, <id>.svg, char_*.svg, props, fonts, vendor)   [assets/audio/voiceover.wav is made by the app]
<out_dir>_docs/                 (for you, outside the project)
  scene-plan.md  gemini-prompts.md (characters + backgrounds, for Gemini)  asset-checklist.md
--keep-srt   keep an existing, hand-edited script.srt (same number of cues) and rebuild the animation from its times.
"""
import argparse, json, pathlib, shutil, subprocess, sys, tempfile
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("out")
ap.add_argument("--keep-srt", action="store_true"); ap.add_argument("--skip-bg", action="store_true"); ap.add_argument("--no-audio-tag", action="store_true")
ap.add_argument("--no-captions", action="store_true"); ap.add_argument("--check", action="store_true"); ap.add_argument("--series", help="path to series-bible.json (created if missing)")
a = ap.parse_args()
spec_path = pathlib.Path(a.spec).resolve(); out = pathlib.Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
spec0 = json.load(open(spec_path, encoding="utf-8"))
import series as SER
bible = SER.load(a.series) if a.series else None
if bible:
    spec0, _w = SER.merge(spec0, bible)                           # recurring characters/settings keep their look across episodes
    for _m in _w: print("SERIES WARNING:", _m)
import coverage, srt_tools, docs_gen, spec_lint
for _m in spec_lint.lint(spec0): print(_m)                 # settings variety, cast, crowds, static scenes, wardrobe
spec = coverage.expand(spec0, spec_path.parent)            # sequences -> many shots, lib:/relative settings resolved
tmp = pathlib.Path(tempfile.mkdtemp(prefix="c2v_")); exp = tmp / "spec.expanded.json"; exp.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
py = sys.executable
def run(cmd, **k):
    if subprocess.run(cmd, **k).returncode: sys.exit(f"step failed: {' '.join(map(str, cmd))}")

if bible: print("series assets copied:", SER.copy_assets(bible, out, a.series))   # Gemini art made once is reused by every episode
# ---- 1. script.srt (planned scenes with exact times) ------------------------------------------------
plan = srt_tools.plan(spec)
srt_path = out / "script.srt"
if a.keep_srt and srt_path.exists():
    given = srt_tools.parse_srt(srt_path)
    if len(given) != len(plan["cues"]): sys.exit(f"script.srt has {len(given)} cues but the spec has {len(plan['cues'])}")
    for c, g in zip(plan["cues"], given):
        c["startMs"], c["endMs"] = g["startMs"], g["endMs"]
        speech = max(0.3, (c["endMs"] - c["startMs"]) / 1000 - 0.2); ws = c["text"].split(); wl = [len(w) + 1 for w in ws]; t = c["startMs"]; c["words"] = []
        for w, k in zip(ws, wl):
            b = t + int(round(speech * 1000 * k / sum(wl))); c["words"].append({"text": w, "startMs": t, "endMs": b}); t = b
    for s in plan["scenes"]:
        cs = [c for c in plan["cues"] if c["scene"] == s["id"]]; s["startMs"], s["endMs"] = cs[0]["startMs"], cs[-1]["endMs"]
    plan["totalMs"] = plan["cues"][-1]["endMs"]
else:
    srt_tools.write_srt(srt_path, plan["cues"], spec)
for n in plan["notes"]: print(n)
print(f"script.srt: {plan['totalMs']/1000:.1f}s, {len(plan['cues'])} cues, scenes " + ", ".join(f"{(s['endMs']-s['startMs'])/1000:.0f}s" for s in plan["scenes"]))
tl = {"durationMs": plan["totalMs"], "cues": [{"index": c["index"], "text": c["text"], "startMs": c["startMs"], "endMs": c["endMs"], "words": c["words"]} for c in plan["cues"]], "scenes": []}
for s in plan["scenes"]:
    idx = [c["index"] for c in plan["cues"] if c["scene"] == s["id"]]
    tl["scenes"].append({"sceneIndex": s["id"], "startMs": s["startMs"], "endMs": s["endMs"], "sceneDurationMs": s["endMs"] - s["startMs"], "cueRange": [idx[0], idx[-1]]})
tl_path = tmp / "timeline.tmp.json"; tl_path.write_text(json.dumps(tl, ensure_ascii=False), encoding="utf-8")

# ---- 2. 3D backgrounds ------------------------------------------------------------------------------
if not a.skip_bg:
    bgs = tmp / "settings"; bgs.mkdir()
    used = {st for sc in spec["scenes"] for sh in sc["shots"] for st in ([pn["setting"] for pn in sh["split"]] if sh.get("split") else [sh["setting"]])}
    ext = spec.get("external_bg", [])
    for sid in used:
        if (ext is True or sid in ext) and (out / "assets" / f"bg_{sid}.png").exists(): continue     # keep the Gemini picture
        s = spec["settings"][sid]
        data = dict(s if isinstance(s, dict) else json.load(open(s, encoding="utf-8")))
        if spec.get("aspect") == "9:16":                      # portrait: render 1080x1920 and pull the camera back to keep the scene readable
            data["width"], data["height"] = 1080, 1920; cam = dict(data["camera"]); lk = cam["look"]
            cam["pos"] = [lk[i] + (cam["pos"][i] - lk[i]) * 1.4 for i in range(3)]; cam["fov"] = cam.get("fov", 40) + 6; data["camera"] = cam
        (bgs / f"{sid}.json").write_text(json.dumps(data), encoding="utf-8")
    bgdir = HERE / "bg_renderer"
    if not (bgdir / "node_modules").exists(): run(["npm", "install", "--no-audit", "--no-fund"], cwd=bgdir, shell=(sys.platform == "win32"))
    (out / "assets").mkdir(exist_ok=True)
    run(["node", str(bgdir / "render_bgs.mjs"), str(bgs), str(out / "assets")])

# ---- 3. composition files -----------------------------------------------------------------------------
cmd = [py, str(HERE / "build_project.py"), str(exp), str(out), "--timeline", str(tl_path)]
if a.no_audio_tag: cmd.append("--no-audio-tag")
if a.no_captions: cmd.append("--no-captions")
run(cmd)

# ---- 4. docs next to the project ----------------------------------------------------------------------
docs = out.parent / (out.name + "_docs"); docs.mkdir(exist_ok=True)
docs_gen.scene_plan(spec, plan, docs / "scene-plan.md"); _set = {}
for _sid in {st for sc in spec["scenes"] for sh in sc["shots"] for st in ([pn["setting"] for pn in sh["split"]] if sh.get("split") else [sh["setting"]])}:
    _s = spec["settings"][_sid]; _set[_sid] = _s if isinstance(_s, dict) else json.load(open(_s, encoding="utf-8"))
docs_gen.character_prompts(spec, docs / "gemini-prompts.md", _set); docs_gen.checklist(spec, out, docs / "asset-checklist.md")
print("docs ->", docs)
if bible:
    SER.update(bible, json.load(open(spec_path, encoding="utf-8")), plan, a.series); print("series bible updated:", a.series)

# ---- 5. validate -----------------------------------------------------------------------------------------
run([py, str(HERE / "validate.py"), str(out)] + (["--check"] if a.check else []) + (["--no-audio"] if a.no_audio_tag else []))
