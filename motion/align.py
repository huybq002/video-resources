"""Word timings with faster-whisper: python motion/align.py <voice-dir> [--model base.en] [--lang en]

Reads <voice-dir>/narration.wav and timing.json (line start/end and speaker from narrate.py), transcribes the narration
with word timestamps, and writes <voice-dir>/words.json:
  [{"w": "Father,", "t0": 3.12, "t1": 3.48, "who": "younger", "line": 4}, ...]
Each word is given to the line whose time span holds its middle, so the film knows who says which word and when:
mouths move on the speaker's words only, captions light up word by word, and an action can land on its word
("he RAN" -> the run starts on "ran"). It also reports lines that transcribe badly (a TTS slip) so they can be redone.
"""
import json, sys, argparse, difflib, re, pathlib


def _load(path):
    """Decode with ffmpeg to 16 kHz mono float32 (faster-whisper's own decoder breaks with the newest PyAV)."""
    import subprocess, numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("voice"); ap.add_argument("--model", default="base.en"); ap.add_argument("--lang", default="en")
    ap.add_argument("--device", default="cpu"); ap.add_argument("--compute", default="int8")
    a = ap.parse_args()
    vd = pathlib.Path(a.voice); timing = json.load(open(vd / "timing.json", encoding="utf-8"))
    from faster_whisper import WhisperModel
    model = WhisperModel(a.model if a.lang == "en" else a.model.replace(".en", ""), device=a.device, compute_type=a.compute)
    segs, _ = model.transcribe(_load(vd / "narration.wav"), language=a.lang, word_timestamps=True, vad_filter=False, beam_size=5)
    words = [{"w": w.word.strip(), "t0": round(w.start, 3), "t1": round(w.end, 3)} for s in segs for w in (s.words or []) if w.word.strip()]
    lines = timing["lines"]
    for w in words:
        mid = (w["t0"] + w["t1"]) / 2
        for i, ln in enumerate(lines):
            if ln["start"] - 0.15 <= mid <= ln["end"] + 0.15:
                w["line"] = i; w["who"] = ln.get("who") or ln.get("speaker") or "narrator"; break
    # check: each line should transcribe back to its text
    norm = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower())
    bad = []
    for i, ln in enumerate(lines):
        heard = " ".join(w["w"] for w in words if w.get("line") == i)
        r = difflib.SequenceMatcher(None, norm(ln.get("text", "")), norm(heard)).ratio()
        if r < 0.7: bad.append((i, round(r, 2), ln.get("text", "")[:60], heard[:60]))
    json.dump(words, open(vd / "words.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"words: {len(words)} over {len(lines)} lines -> {vd / 'words.json'}")
    for b in bad: print("CHECK line", b)
    return 0


if __name__ == "__main__":
    sys.exit(main())
