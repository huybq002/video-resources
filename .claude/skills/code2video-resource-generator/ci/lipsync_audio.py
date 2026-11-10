"""Mouth movements read from the real voice-over (Rhubarb Lip Sync, MIT), run after tts.py and before the render.
python lipsync_audio.py <project> [--lang en] [--jobs 4]

build_project.py can only guess the mouth from the text (word timings are estimated before any audio exists).
This step cuts assets/audio/voiceover.wav per script.srt cue, runs Rhubarb on each cut with the cue text as the
dialog hint, and swaps the shapes into every compositions/scene_N.html (shots[].lip[] entries carry the cue index `ci`).
Rhubarb shapes -> rig mouths (engine.js viseme: a wide, e spread, o round, m closed), jaw amount scaled by loudness.
No Rhubarb binary (RHUBARB env or `rhubarb` on PATH) -> prints a note and leaves the text-based lip-sync in place.
English uses the PocketSphinx recognizer; any other language uses Rhubarb's language-independent phonetic recognizer.
"""
import argparse, concurrent.futures as cf, json, os, pathlib, re, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import srt_tools, lipsync as LS

# Rhubarb mouth -> (rig shape, base jaw). A=M/B/P closed, B=K/S/T/EE slightly open, C=EH/AE open, D=AA wide,
# E=AO/ER rounded, F=UW/OW/W puckered, G=F/V teeth on lip, H=L tongue, X=rest.
SHAPE = {"A": ("m", 1.0), "B": ("e", 0.45), "C": ("e", 0.75), "D": ("a", 1.05), "E": ("o", 0.75),
         "F": ("o", 0.5), "G": ("e", 0.32), "H": ("a", 0.6), "X": ("m", 1.0)}

def find_rhubarb():
    p = os.environ.get("RHUBARB") or shutil.which("rhubarb")
    return p if p and os.path.exists(p) else None

def run_cue(rb, wav, tmp, i, c, lang):
    a, b = c["startMs"] / 1000.0, c["endMs"] / 1000.0
    cut, dlg = tmp / f"c{i:04d}.wav", tmp / f"c{i:04d}.txt"
    try:   # one bad cue keeps its text mouths; it never stops the film
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(wav), "-ac", "1", "-ar", "16000", str(cut)], check=True, timeout=120)
        dlg.write_text(c["text"], encoding="utf-8")
        cmd = [rb, "-q", "-f", "json", "--extendedShapes", "GHX", "-d", str(dlg)] + ([] if lang == "en" else ["-r", "phonetic"]) + [str(cut)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if r.returncode: return i, None
        return i, [(a + m["start"], m["value"]) for m in json.loads(r.stdout)["mouthCues"]]
    except Exception:
        return i, None

def events(mouth, env, shot_abs, shot_len):
    """absolute Rhubarb cues -> engine events [t_rel_shot, shape, open], clipped to the shot."""
    out = []
    for k, (t, v) in enumerate(mouth):
        nxt = mouth[k + 1][0] if k + 1 < len(mouth) else t + 0.12
        shape, base = SHAPE.get(v, ("m", 1.0))
        op = 1.0 if shape == "m" else max(0.3, min(1.25, base * (0.55 + 0.7 * LS._amp(env, t, nxt)) if env else base))
        tr = t - shot_abs
        if -0.05 <= tr <= shot_len + 0.05: out.append([round(max(tr, 0.0), 3), shape, round(op, 2)])
    if out and out[-1][1] != "m": out.append([round(out[-1][0] + 0.08, 3), "m", 1.0])
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--lang", default="en"); ap.add_argument("--jobs", type=int, default=max(1, min(6, os.cpu_count() or 2)))
    a = ap.parse_args(); proj = pathlib.Path(a.project).resolve()
    rb = find_rhubarb()
    if not rb: print("lipsync: rhubarb not found (set RHUBARB or put it on PATH), kept the text-based lip-sync"); return
    wav = next((p for p in (proj / "assets" / "audio" / "voiceover.wav", proj / "voiceover.wav") if p.exists()), None)
    if not wav: print("lipsync: no voiceover.wav, kept the text-based lip-sync"); return
    # timeline.json holds where the voice really is (the app writes it after TTS/alignment); script.srt otherwise
    tlp = proj / "timeline.json"
    if tlp.exists():
        cues = [(c["index"], c) for c in json.loads(tlp.read_text(encoding="utf-8"))["cues"]]
    else:
        cues = list(enumerate(srt_tools.parse_srt(proj / "script.srt"), 1))
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="lipsync_")); mouth = {}
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for i, m in ex.map(lambda ic: run_cue(rb, wav, tmp, ic[0], ic[1], a.lang), cues):
            if m: mouth[i] = m
    shutil.rmtree(tmp, ignore_errors=True)
    env = LS.load_env(wav)
    idx = (proj / "index.html").read_text(encoding="utf-8")
    starts = {int(n): float(s) for n, s in re.findall(r"data-composition-src='compositions/scene_(\d+)\.html'\s+data-start='([\d.]+)'", idx)}
    swapped = kept = 0
    for n, s0 in sorted(starts.items()):
        f = proj / "compositions" / f"scene_{n}.html"; doc = f.read_text(encoding="utf-8")
        k = doc.find("const D = ")
        if k < 0: continue
        D, end = json.JSONDecoder().raw_decode(doc, k + len("const D = "))
        for sh in D.get("shots", []):
            for L in sh.get("lip", []):
                m = mouth.get(L.get("ci"))
                ev = events(m, env, s0 + sh["t0"], sh["t1"] - sh["t0"]) if m else None
                if ev: L["ev"] = ev; L["src"] = "rhubarb"; swapped += 1
                else: kept += 1
        new = json.dumps(D, ensure_ascii=False).replace("</", "<\\/")
        f.write_text(doc[:k + len("const D = ")] + new + doc[end:], encoding="utf-8")
    print(f"lipsync: {len(mouth)}/{len(cues)} cues read by rhubarb, {swapped} mouth tracks swapped, {kept} kept from text")

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:   # lip-sync is polish: a failure here must never cost the night's render
        print(f"lipsync: failed ({type(e).__name__}: {e}), kept the text-based lip-sync")
