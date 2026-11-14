"""The director's pass on the FINISHED video: measure what a viewer would notice, and make a contact sheet to look at.

python director_pass.py <video.mp4> [--out DIR] [--sheet-every 4] [--json]

Idea taken from kaomei/stickman-video-director (MIT): acceptance is judged on the actual encoded film, never on
the plan or on passing code tests. Measured here (ffmpeg only):
  silence   : the share of the film in 0.5 s windows below -50 dB (over 10 % is dead air: no room tone, no music), plus 5 s windows
  contrast  : the quietest and loudest 5 s windows (a flat mix has under 4 dB between them)
  frozen    : the picture frozen for 2 s or more (a character or scene hung)
  black     : black frames inside the film (not the final fade)
  sheet     : out/director_sheet_N.jpg, one frame every --sheet-every seconds, labelled with its time, to LOOK at

Exit 0 always; prints PROBLEM lines (verify_bundle turns them into errors) and writes director_pass.json.
"""
import argparse, json, pathlib, re, shutil, subprocess, sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def duration(v):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(v)])
    return float(r.stdout.strip() or 0)


def windows_db(video, win=5):
    """RMS level in dB of each win-second window of the mix"""
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True)
    x = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float64) / 32768
    n = 16000 * win
    return [round(float(20 * np.log10(np.sqrt((x[i:i + n] ** 2).mean()) + 1e-9)), 1) for i in range(0, max(0, len(x) - n // 2), n)]


def dead_share(video, win=0.5, floor_db=-50.0):
    """share of the film (0-1) whose 0.5 s windows are below floor_db: digital silence between the voice lines.
    A film with room tone and a score has none; video 007 (no music, no room tone) had 44 %."""
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True)
    x = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float64) / 32768
    n = int(16000 * win); k = len(x) // n
    if k < 4: return 0.0
    rms = np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(axis=1))
    db = 20 * np.log10(rms + 1e-9)
    keep = db[: max(1, k - int(4 / win))]                  # the closing fade may be quiet
    return float((keep < floor_db).mean())


def frozen(video, min_s=2.0):
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-an", "-vf", f"freezedetect=n=0.001:d={min_s}", "-f", "null", "-"])
    starts = [float(m) for m in re.findall(r"freeze_start: ([\d.]+)", r.stderr)]
    durs = [float(m) for m in re.findall(r"freeze_duration: ([\d.]+)", r.stderr)]
    return [(s, d) for s, d in zip(starts, durs)]


def black(video):
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-an", "-vf", "blackdetect=d=0.5:pic_th=0.98", "-f", "null", "-"])
    return [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)]


def sheets(video, out, every, D):
    """contact sheets of 20 frames each; the time of each frame is burnt in"""
    out.mkdir(parents=True, exist_ok=True); files = []
    per = 20; step = every * per
    for k, t0 in enumerate(range(0, int(D), step)):
        f = out / f"director_sheet_{k + 1}.jpg"
        vf = (f"fps=1/{every},scale=384:-1,drawtext=text='%{{pts\\:hms}}':x=6:y=h-22:fontcolor=white:box=1:boxcolor=black@0.55:fontsize=16,"
              f"tile=5x4")
        r = run(["ffmpeg", "-v", "error", "-y", "-ss", str(t0), "-t", str(step), "-i", str(video), "-vf", vf, "-frames:v", "1", str(f)])
        if r.returncode:   # drawtext needs a font on some builds: fall back to no label
            run(["ffmpeg", "-v", "error", "-y", "-ss", str(t0), "-t", str(step), "-i", str(video), "-vf", f"fps=1/{every},scale=384:-1,tile=5x4", "-frames:v", "1", str(f)])
        if f.exists(): files.append(str(f))
    return files


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("--out"); ap.add_argument("--sheet-every", type=int, default=4)
    ap.add_argument("--json", action="store_true"); ap.add_argument("--silence-db", type=float, default=-50.0)
    a = ap.parse_args(); video = pathlib.Path(a.video)
    if not shutil.which("ffmpeg"): print("director_pass: no ffmpeg, skipped"); return
    out = pathlib.Path(a.out) if a.out else video.parent / "director_pass"
    D = duration(video); problems = []; res = {"video": str(video), "duration_s": round(D, 1)}
    try:
        db = windows_db(video); res["loudness_5s_db"] = db
        dead = [i * 5 for i, v in enumerate(db) if v < a.silence_db and (i + 1) * 5 < D - 4]     # the closing fade may be quiet
        if dead: problems.append(f"PROBLEM: dead air: {len(dead)} window(s) of 5 s below {a.silence_db:.0f} dB at {dead[:6]} s: add room tone / score (references/sound-script.md)")
        ds = dead_share(video, floor_db=a.silence_db); res["dead_share"] = round(ds, 3)
        if ds > 0.10: problems.append(f"PROBLEM: dead air: {ds * 100:.0f}% of the film is digital silence (0.5 s windows below {a.silence_db:.0f} dB): no room tone / score under the voice (references/sound-script.md)")
        if db and max(db) - min(db) < 4: problems.append(f"PROBLEM: flat mix: only {max(db) - min(db):.1f} dB between the quietest and loudest 5 s")
    except Exception as e:
        print(f"director_pass: loudness skipped ({type(e).__name__}: {e})")
    fz = [(s, d) for s, d in frozen(video) if s > 0.5 and s + d < D - 1.5]      # a held title card at the very start/end is fine
    res["frozen"] = fz
    if fz: problems.append("PROBLEM: frozen picture for 2+ s at " + ", ".join(f"{s:.1f}s ({d:.1f}s)" for s, d in fz[:6]) + ": a character or scene hung")
    bl = [(s, e) for s, e in black(video) if s > 1 and e < D - 3]
    res["black"] = bl
    if bl: problems.append("PROBLEM: black frames inside the film at " + ", ".join(f"{s:.1f}-{e:.1f}s" for s, e in bl[:5]))
    res["sheets"] = sheets(video, out, a.sheet_every, D)
    res["problems"] = problems
    out.mkdir(parents=True, exist_ok=True); (out / "director_pass.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"director_pass: {D:.0f}s, loudness {min(res.get('loudness_5s_db', [0]))}..{max(res.get('loudness_5s_db', [0]))} dB, "
          f"{len(fz)} frozen, {len(bl)} black, sheets: {', '.join(res['sheets']) or 'none'}")
    for p in problems: print(p)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"director_pass: failed ({type(e).__name__}: {e})")
