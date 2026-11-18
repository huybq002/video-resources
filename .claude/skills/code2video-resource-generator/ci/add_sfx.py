"""Sound effects on the finished video, on the beats the picture already has (assets/sfx_cues.json, written by
build_project.py): cuts and transitions, the keyword slamming in, reactions, footsteps, typing, objects popping in,
counters ticking, the power moment. Mixed under the voice; music (add_music.py) is added after this and ducks under both.

python add_sfx.py <video.mp4> --project <project_dir> [--level 0.55] [--library data/sfx] [--out OUT.mp4]

Effects are synthesised (sfx_bank.py) unless the owner puts a recording with the same name in data/sfx/.
spec "sfx": false switches them off (build_project then writes no cues). Never costs the night's video: any
failure prints a note and leaves the video as it was.
"""
import argparse, json, pathlib, shutil, subprocess, sys
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sfx_bank as B


def dur(p): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).decode())


def stem(cues, D, lib, level):
    out = np.zeros(int(B.SR * (D + 2)), dtype=np.float32); cache = {}
    for i, c in enumerate(sorted(cues, key=lambda c: c["t"])):
        nm = c["name"]
        if nm not in B.NAMES: continue
        var = (i % 4) if nm in ("step", "key", "tick") else 0      # small variation on repeated sounds
        key = (nm, var)
        if key not in cache: cache[key] = B.load(nm, lib, var)
        x = cache[key] * float(c.get("gain", 1.0)) * level
        a = int(max(0.0, c["t"]) * B.SR)
        if a >= len(out): continue
        n = min(len(x), len(out) - a); out[a:a + n] += x[:n]
    out = np.tanh(out * 1.2) / 1.2                                    # soft limit: stacked hits never clip
    return out[:int(B.SR * D)]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("--project", required=True)
    ap.add_argument("--level", type=float, default=0.55, help="effects gain under the voice (0.55 is about -5 dB)")
    ap.add_argument("--library", default=str(pathlib.Path(__file__).resolve().parents[4] / "data" / "sfx")); ap.add_argument("--out")
    a = ap.parse_args(); video = pathlib.Path(a.video).resolve()
    cf = pathlib.Path(a.project) / "assets" / "sfx_cues.json"
    if not cf.exists(): print("sfx: no assets/sfx_cues.json (spec sfx off or old build), video left as it is"); return
    cues = json.loads(cf.read_text(encoding="utf-8"))
    if not cues: print("sfx: no cues"); return
    D = dur(video); wav = video.with_suffix(".sfx.wav")
    B.write_wav(wav, stem(cues, D, a.library if pathlib.Path(a.library).exists() else None, a.level))
    out = pathlib.Path(a.out).resolve() if a.out else video.with_suffix(".sfx.tmp.mp4")
    has_audio = bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(video)],
                                    capture_output=True, text=True).stdout.strip())
    flt = "[0:a][1:a]amix=inputs=2:duration=first,volume=2[a]" if has_audio else "[1:a]anull[a]"
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-i", str(wav), "-filter_complex", flt,
                        "-map", "0:v", "-c:v", "copy", "-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])
    wav.unlink(missing_ok=True)
    if r.returncode:
        out.unlink(missing_ok=True); print("sfx: ffmpeg failed, video left without effects"); return
    if not a.out: shutil.move(str(out), str(video)); out = video
    names = sorted({c["name"] for c in cues})
    print(f"sfx: {len(cues)} effects ({', '.join(names)}) under {out.name}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:   # never cost the night's video
        print(f"sfx: failed ({type(e).__name__}: {e}), video left without effects")
