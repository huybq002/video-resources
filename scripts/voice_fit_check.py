#!/usr/bin/env python3
"""Name the voice-over lines that will be (or were) rushed or cut, instead of only counting them.

    python scripts/voice_fit_check.py pre  outputs/<id>/landscape/script.srt   # before the voice: risky cues
    python scripts/voice_fit_check.py post outputs/<id>/landscape               # after the voice: cut cues

Why (2026-11-15, videos 008/009): voiceover_fit.json only says "5 rushed, 7 cut". Finding the lines by hand took
three re-renders (~15 min each). Measured on 008 and 009:
 * a line is cut when its speech is still running at the end of its time window: `post` finds it by the energy in
   the last 120..50 ms of the window against the middle of the window (cut lines scored 0.45-2.2, the rest 0.0-0.35);
 * `pre` estimates the speech time as (0.19 s x syllables + 0.4 s x sentence breaks) / 1.16 and lists cues whose window
   is shorter than 85 % of that. It flagged all 3 failing lines of the first 008 render and every cut line of the
   first 009 render, plus a few lines that turned out fine: treat it as a list to read, not a gate.
Short sentences cost the most: each sentence break adds ~0.4 s of pause in the TTS.
"""
import json, re, sys, wave
from pathlib import Path

SRT = re.compile(r"\[(.*?)\]\[(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)\](?:\[[^\]]*\])?:?\s*(.*)")


def syl(w):
    return max(1, len(re.findall(r"[aeiouy]+", w.lower())))


def pre(srt, k=1.16, limit=0.85):
    n = 0
    for line in Path(srt).read_text(encoding="utf-8").splitlines():
        m = SRT.match(line)
        if not m:
            continue
        g = m.groups()
        a = int(g[1]) * 3600 + int(g[2]) * 60 + int(g[3]) + int(g[4]) / 1000
        b = int(g[5]) * 3600 + int(g[6]) * 60 + int(g[7]) + int(g[8]) / 1000
        text = g[9]
        s = sum(syl(w) for w in text.split())
        breaks = len(re.findall(r"[.?!:…]+(\s|$)", text))
        need = (0.19 * s + 0.4 * breaks) / k
        if need > (b - a) * limit:
            n += 1
            print(f"risky {need / (b - a):.2f}  {b - a:.1f}s  {s} syl {breaks} breaks  [{g[0]}] {text}")
    print(f"voice_fit pre: {n} risky cue(s)")
    return n


def post(project):
    import numpy as np
    d = Path(project)
    w = wave.open(str(d / "voiceover.wav"))
    sr, ch = w.getframerate(), w.getnchannels()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    if ch > 1:
        a = a.reshape(-1, ch).mean(1)
    tl = json.loads((d / "timeline.json").read_text(encoding="utf-8"))
    cues = tl["cues"] if isinstance(tl, dict) else tl
    starts = sorted(int(c["startMs"]) for c in cues)
    n = 0
    for i, c in enumerate(cues):
        s, e = int(c["startMs"]), int(c["endMs"])
        nxt = min([x for x in starts if x > s] or [e + 400])
        room = max(e, nxt - 60)
        seg = a[int(s * sr / 1000):int(room * sr / 1000)]
        if len(seg) < sr // 2:
            continue
        tail = seg[-int(0.12 * sr):-int(0.05 * sr)]
        mid = seg[len(seg) // 4:3 * len(seg) // 4]
        r = float(np.sqrt((tail ** 2).mean()) / (np.sqrt((mid ** 2).mean()) + 1e-6))
        if r > 0.4:
            n += 1
            print(f"cut? {r:.2f}  cue {i}  window {(room - s) / 1000:.1f}s  {c.get('text', '')}")
    print(f"voice_fit post: {n} cue(s) still speaking at the end of their window")
    return n


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("pre", "post"):
        sys.exit(__doc__)
    sys.exit(0 if (pre if sys.argv[1] == "pre" else post)(sys.argv[2]) == 0 else 1)
