"""Validate a generated project against docs/hyperframes-asset-contract.md
python validate.py <project_dir> [--check] [--no-audio]       (--check also runs `npx hyperframes check --json`)
Exit code 1 on any contract error."""
import json, pathlib, re, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import srt_tools
root = pathlib.Path(sys.argv[1]); errs, warns = [], []
if not (root / "index.html").exists(): sys.exit("missing index.html")
idx = (root / "index.html").read_text(encoding="utf-8")
def need(p):
    if not (root / p).exists(): errs.append(f"missing {p}")
need("script.srt"); need("compositions")
m = re.search(r'id="root"[^>]*data-duration="([\d.]+)"', idx)
total = float(m.group(1)) if m else 0
if not m: errs.append("index.html: #root data-duration missing")
if 'data-composition-id="story"' not in idx: errs.append("index.html: root must have data-composition-id=\"story\"")
if "window.__timelines['story']" not in idx and 'window.__timelines["story"]' not in idx: errs.append("index.html: root timeline not registered")
if "assets/audio/voiceover.wav" not in idx and "--no-audio" not in sys.argv: errs.append("index.html: <audio id=voice src=assets/audio/voiceover.wav> missing")
# scene hosts
hosts = re.findall(r"data-composition-id='(scene-\d+)' data-composition-src='(compositions/scene_\d+\.html)'\s+data-start='([\d.]+)' data-duration='([\d.]+)'", idx)
if not hosts: errs.append("index.html: no scene hosts")
t = 0.0
for cid, src, st, du in hosts:
    st, du = float(st), float(du)
    if abs(st - t) > 0.002: errs.append(f"{cid}: starts at {st} but previous scene ended at {t:.3f}")
    t = st + du
    if not (root / src).exists(): errs.append(f"missing {src}")
if hosts and abs(t - total) > 0.01: errs.append(f"scene durations add up to {t:.3f}s but root duration is {total:.3f}s")
# srt
cues = []
if (root / "script.srt").exists():
    cues = srt_tools.parse_srt(root / "script.srt")
    if not cues: errs.append("script.srt: no cue parsed (format: [Name][00:00:00,000 --> 00:00:03,500]: text)")
    prev = 0
    for i, c in enumerate(cues, 1):
        if c["startMs"] != prev: errs.append(f"script.srt cue {i}: starts {c['startMs']} but previous ended {prev}")
        prev = c["endMs"]
        need_s = 0.5 + 0.3 * len(c["text"].split())
        if (c["endMs"] - c["startMs"]) / 1000 + 0.01 < need_s: errs.append(f"script.srt cue {i}: {(c['endMs']-c['startMs'])/1000:.2f}s < reading minimum {need_s:.2f}s")
    if cues and abs(cues[-1]["endMs"] / 1000 - total) > 0.5: errs.append(f"script.srt ends {cues[-1]['endMs']/1000:.2f}s vs root duration {total:.2f}s")
# scenes
for cid, src, st, du in hosts:
    p = root / src
    if not p.exists(): continue
    h = p.read_text(encoding="utf-8")
    n = cid.split("-")[1]
    if f"<template id='{cid}-template'>" not in h and f'<template id="{cid}-template">' not in h: errs.append(f"{src}: needs <template id=\"{cid}-template\">")
    if f"data-composition-id='{cid}'" not in h and f'data-composition-id="{cid}"' not in h: errs.append(f"{src}: wrapper data-composition-id must be {cid}")
    if "window.__timelines[D.sceneId]" not in h and f"window.__timelines['{cid}']" not in h: errs.append(f"{src}: timeline not registered")
    if "gsap.timeline({ paused: true })" not in h: errs.append(f"{src}: gsap timeline must be paused")
    if "class='bg" not in h and "class='bgp" not in h: errs.append(f"{src}: no background")
    if "<svg" not in h and "-ext'" not in h: errs.append(f"{src}: no character")
    for bad in ("repeat: -1", "Date.now", "Math.random", "fetch(", "setTimeout", "setInterval", "requestAnimationFrame"):
        if bad in h: errs.append(f"{src}: forbidden {bad}")
    for ref in set(re.findall(r"""(?:src|href)=['"](/?assets/[\w./-]+)""", h)) | set(re.findall(r"url\(['\"]?(/?assets/[\w./-]+)", h)):
        if ref.startswith("/"): errs.append(f"{src}: asset path must not start with '/': {ref}")
        elif not (root / ref).exists(): errs.append(f"{src}: asset not found {ref}")
    caps = re.findall(r"class='caption clip' data-start='([\d.]+)' data-duration='([\d.]+)'", h)
    if not caps: warns.append(f"{src}: no captions")
    elif float(caps[-1][1]) < 2.0: errs.append(f"{src}: last caption stays {caps[-1][1]}s (< 2s)")
    a_ms, b_ms = round(float(st) * 1000), round((float(st) + float(du)) * 1000)
    cs = [c for c in cues if a_ms <= c["startMs"] < b_ms]
    if cs and cs[-1]["endMs"] > b_ms + 2: errs.append(f"{src}: a cue crosses the end of the scene")
    if float(du) < 12 or float(du) > 50: warns.append(f"{cid}: {du}s long (aim for 20-40 s)")
allowed = {"index.html", "script.srt", "compositions", "assets", "timeline.json", "hyperframes.json", "package.json", "meta.json", ".hyperframes"}
extra = [x.name for x in root.iterdir() if x.name not in allowed]
if extra: warns.append(f"extra files outside the contract structure: {extra}")
print("CONTRACT ERRORS:\n  " + "\n  ".join(errs) if errs else f"contract OK ({len(hosts)} scenes, {len(cues)} cues, {total:.1f}s)")
if warns: print("WARNINGS:\n  " + "\n  ".join(warns))
if "--check" in sys.argv and not errs:
    r = subprocess.run("npx --yes hyperframes check --json", cwd=root, shell=True, capture_output=True, text=True, encoding="utf-8")
    try:
        d = json.loads(r.stdout[r.stdout.find("{"):])
        found = d.get("lint", {}).get("findings", [])
        # with --no-audio the voice-over has not been made yet: a missing assets/audio/voiceover.wav
        # is expected at this point, so do not fail the build on it.
        ignored = {"audio_src_not_found"} if "--no-audio" in sys.argv else set()
        hard = [f for f in found if f.get("severity") == "error" and f.get("code") not in ignored]
        skipped = sum(1 for f in found if f.get("severity") == "error" and f.get("code") in ignored)
        lint = {k: v for k, v in d.get("lint", {}).items() if k in ("errorCount", "warningCount")}
        if skipped: lint["ignoredUntilVoiceover"] = skipped
        print("hyperframes check ok =", d.get("ok"), "| lint:", lint)
        if hard or (not d.get("ok") and not found): errs.append("hyperframes check failed")
    except Exception as e: print("could not parse check output", e); errs.append("check unparsable")
sys.exit(1 if errs else 0)
