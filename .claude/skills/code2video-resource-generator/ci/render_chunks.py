"""Render a long project in parallel slices (GitHub matrix jobs or local loop), then assemble + add the voice-over.
python render_chunks.py plan     <project> [--chunk 120]      -> chunks.json  [{"i":0,"start":0,"end":118.4}, ...]   (cuts on scene boundaries)
python render_chunks.py render   <project> --i N              -> <project>/_chunks/chunk_NN.mp4  (silent)
python render_chunks.py assemble <project> [--out final.mp4]  -> concat of all chunks + assets/audio/voiceover.wav
"""
import argparse, json, pathlib, re, subprocess, sys

def hosts(proj):
    idx = (proj / "index.html").read_text(encoding="utf-8")
    h = [(float(a), float(b)) for a, b in re.findall(r"data-composition-src='compositions/scene_\d+\.html'\s+data-start='([\d.]+)' data-duration='([\d.]+)'", idx)]
    fps = int(re.search(r'data-fps="(\d+)"', idx).group(1)); total = float(re.search(r'id="root"[^>]*data-duration="([\d.]+)"', idx).group(1))
    return h, fps, total

def plan(proj, chunk):
    h, fps, total = hosts(proj); out = []; start = 0.0; end = 0.0
    for st, du in h:
        end = st + du
        if end - start >= chunk: out.append({"i": len(out), "start": round(start, 3), "end": round(end, 3)}); start = end
    if end - start > 0.01: out.append({"i": len(out), "start": round(start, 3), "end": round(total, 3)})
    return out

def sh(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, shell=(sys.platform == "win32"))
    if r.returncode: sys.exit(f"failed: {' '.join(map(str, cmd))}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["plan", "render", "assemble"]); ap.add_argument("project")
    ap.add_argument("--chunk", type=float, default=120); ap.add_argument("--i", type=int); ap.add_argument("--out", default="final.mp4"); ap.add_argument("--workers", default="auto")
    a = ap.parse_args(); proj = pathlib.Path(a.project).resolve()
    if a.cmd == "plan":
        c = plan(proj, a.chunk); (proj / "chunks.json").write_text(json.dumps(c)); print(json.dumps(c))
    elif a.cmd == "render":
        c = json.loads((proj / "chunks.json").read_text())[a.i]; _, fps, _ = hosts(proj); d = proj / "_chunks"; d.mkdir(exist_ok=True)
        # the slice must start/end on whole frames; the app's render command is the contract's own: npx hyperframes render
        sh(["npx", "--yes", "hyperframes", "render", "--start", str(c["start"]), "--end", str(c["end"]), "-f", str(fps), "-w", str(a.workers), "-o", str(d / f"chunk_{a.i:02d}.mp4")], cwd=str(proj))
    else:
        _, fps, total = hosts(proj); d = proj / "_chunks"; files = sorted(d.glob("chunk_*.mp4"))
        lst = d / "list.txt"; lst.write_text("\n".join(f"file '{f.as_posix()}'" for f in files))
        silent = d / "video_silent.mp4"
        sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(fps), "-pix_fmt", "yuv420p", str(silent)])
        wav = proj / "assets" / "audio" / "voiceover.wav"
        cmd = ["ffmpeg", "-y", "-i", str(silent)] + (["-i", str(wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest"] if wav.exists() else ["-c:v", "copy"]) + ["-movflags", "+faststart", str(proj / a.out)]
        sh(cmd); print("final:", proj / a.out)
