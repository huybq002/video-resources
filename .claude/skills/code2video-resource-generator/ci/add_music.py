"""Background music under the finished video, ducked under the voice (sidechain), looped, faded in/out.
python add_music.py <video.mp4> --spec spec.json [--music FILE | --music auto] [--library data/music] [--level 0.20] [--out OUT.mp4]

auto: picks a track from <library>/library.json whose moods match the spec moods (spec.mood, scene/sequence moods,
format). The library is owner-curated: only tracks whose licence allows monetised YouTube use (YouTube Audio Library,
CC0, own purchases). Each entry: {"file": "x.mp3", "moods": ["tense", "mystery"], "license": "...", "credit": "..." | null}.
No library / no matching track -> the film's own synthesised score (ci/score.py: mood from the spec, chords per scene).
Writes <video>.music.json with the track and its credit line: put a non-empty credit in the video description.
"""
import argparse, hashlib, json, pathlib, shutil, subprocess, sys

def dur(p): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).decode())

def spec_moods(spec):
    m = set()
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("mood", "format", "genre") and isinstance(v, str): m.update(x.strip().lower() for x in v.replace("|", ",").split(","))
                else: walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(spec); return m

def pick(lib_dir, spec):
    lf = lib_dir / "library.json"
    if not lf.exists(): return None
    tracks = [t for t in json.loads(lf.read_text(encoding="utf-8")) if (lib_dir / t["file"]).exists() and t.get("license")]
    if not tracks: return None
    want = spec_moods(spec)
    scored = sorted(tracks, key=lambda t: -len(want & {x.lower() for x in t.get("moods", [])}))
    best = [t for t in scored if len(want & {x.lower() for x in t.get("moods", [])}) == len(want & {x.lower() for x in scored[0].get("moods", [])})]
    seed = int(hashlib.sha1(str(spec.get("title", "")).encode()).hexdigest(), 16)   # same film -> same track, films vary
    return best[seed % len(best)]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("--spec"); ap.add_argument("--music", default="auto")
    ap.add_argument("--library", default=str(pathlib.Path(__file__).resolve().parents[4] / "data" / "music"))
    ap.add_argument("--level", type=float, default=0.20, help="music gain before ducking (0.20 is about -14 dB)"); ap.add_argument("--out")
    a = ap.parse_args(); video = pathlib.Path(a.video).resolve()
    spec = json.load(open(a.spec, encoding="utf-8")) if a.spec else {}
    if a.music == "auto":
        t = pick(pathlib.Path(a.library), spec)
        if t:
            track, info = pathlib.Path(a.library) / t["file"], t
        else:
            # no licensed track: the film gets its own synthesised score (ci/score.py), never silence (2026-11-14)
            sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); import score as S, wave
            Dv = dur(video); x = S.score(spec, Dv, S.sections_of(spec))
            track = video.with_suffix(".score.wav")
            with wave.open(str(track), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(S.SR); w.writeframes((x.clip(-1, 1) * 32767).astype("int16").tobytes())
            info = {"file": track.name, "license": "original, synthesised for this film (ci/score.py)", "credit": None,
                    "mood": S.mood_of(spec)}
            a.level = max(a.level, 0.32)     # the score is mixed quieter than a mastered track, so it gets more gain
    else:
        track, info = pathlib.Path(a.music), {"file": a.music, "license": "given on the command line", "credit": None}
    D = dur(video); fo = max(0.0, D - 3.0)
    flt = (f"[1:a]aloop=loop=-1:size=2000000000,atrim=0:{D:.3f},asetpts=N/SR/TB,volume={a.level},"
           f"afade=t=in:d=2,afade=t=out:st={fo:.3f}:d=3[m];"
           "[0:a]asplit=2[v][sc];"
           "[m][sc]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=450:makeup=1[md];"
           "[v][md]amix=inputs=2:duration=first,volume=2[a]")   # amix halves each input; volume=2 undoes it (older ffmpeg has no normalize=0)
    out = pathlib.Path(a.out).resolve() if a.out else video.with_suffix(".music.tmp.mp4")
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-i", str(track), "-filter_complex", flt,
                        "-map", "0:v", "-c:v", "copy", "-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])
    if r.returncode:   # music is optional: keep the video as it was
        out.unlink(missing_ok=True); print(f"music: ffmpeg failed on {track.name}, video left without music"); return
    if not a.out: shutil.move(str(out), str(video)); out = video
    if str(track).endswith(".score.wav"): pathlib.Path(track).unlink(missing_ok=True)
    (out.parent / (out.stem + ".music.json")).write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"music: {info['file']} under {out.name} ({info.get('license')}; credit: {info.get('credit') or 'none needed'})")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:   # never cost the night's video
        print(f"music: failed ({type(e).__name__}: {e}), video left without music")
