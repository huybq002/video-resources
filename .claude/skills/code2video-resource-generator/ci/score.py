"""Original film score and room tone, synthesised per film (numpy only): no samples, no licence, no credit line.

Why (2026-11-14, video 007): the music library was empty, so every film went out with no music and no room tone;
44 % of the soundtrack was digital silence between voice lines. A short film is never silent: under the dialogue
there is always a room (air, hum, traffic) and, between beats, a score that tells the viewer how to feel.

  score(spec, duration_s, sections)  -> float32 mono at SR: a chord bed that follows the story.
      mood comes from the spec (tense / mystery / warm / sad / upbeat / hopeful); every scene gets its own chord
      progression and intensity from its `value` (+/-) and position (the last third builds, the ending resolves).
      Instruments: warm pad (additive, slow attack, gentle vibrato), soft plucked arpeggio, sub bass on roots,
      a muted pulse in upbeat/tense parts. Same film -> same music (seeded by the title); films differ.
  ambience(kind, duration_s, seed)   -> room tone for one place: room / office / street / cafe / hospital / grocery /
      bedroom / classroom / cinema / park / void. Air and hum, plus the place's small events (cars passing, cups,
      monitor beeps, scanner beeps, a clock), all very quiet: it is felt, not heard.
  ambience_track(project_dir, duration_s) -> the room tone of every shot's place, crossfaded at the cuts
      (reads assets/shots_debug.json written by build_project).

python score.py <spec.json> <seconds> OUT.wav      writes the score alone, to listen to it
"""
import hashlib, json, math, pathlib, sys
import numpy as np

SR = 48000
NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}

# progressions as (root semitone from the key, quality); one chord per bar
PROG = {
    "warm":    [[(0, "maj"), (7, "maj"), (9, "min"), (5, "maj")], [(0, "maj"), (5, "maj"), (9, "min"), (7, "sus")]],
    "hopeful": [[(5, "maj"), (7, "maj"), (9, "min"), (0, "maj")], [(0, "add9"), (7, "maj"), (5, "maj7"), (5, "maj")]],
    "sad":     [[(9, "min"), (5, "maj7"), (0, "maj"), (7, "maj")], [(9, "min"), (2, "min"), (5, "maj"), (4, "min")]],
    "tense":   [[(9, "min"), (5, "maj"), (2, "min"), (4, "maj")], [(9, "min"), (10, "maj"), (9, "min"), (8, "aug")]],
    "mystery": [[(9, "min"), (6, "dim"), (5, "maj7"), (4, "sus")], [(9, "min9"), (5, "maj7"), (2, "min9"), (4, "sus")]],
    "upbeat":  [[(0, "maj"), (9, "min"), (5, "maj"), (7, "maj")], [(0, "maj"), (4, "min"), (5, "maj"), (7, "sus")]],
}
QUAL = {"maj": [0, 4, 7], "min": [0, 3, 7], "sus": [0, 5, 7], "dim": [0, 3, 6], "aug": [0, 4, 8], "maj7": [0, 4, 7, 11],
        "min9": [0, 3, 7, 14], "add9": [0, 4, 7, 14]}
MOOD_WORDS = {"tense": ["tense", "danger", "anxious", "panic", "dark", "suspense", "fear", "conflict", "worry"],
              "mystery": ["mystery", "puzzle", "secret", "curious", "night", "strange", "investigation"],
              "sad": ["sad", "loss", "lonely", "melancholy", "regret", "grief", "tired"],
              "warm": ["warm", "calm", "cozy", "gentle", "tender", "home", "neutral", "reflective"],
              "hopeful": ["hope", "hopeful", "relief", "resolve", "inspire", "bright", "triumph"],
              "upbeat": ["upbeat", "fun", "comedy", "playful", "energetic", "happy", "joy", "light"]}
TEMPO = {"warm": 76, "hopeful": 84, "sad": 66, "tense": 92, "mystery": 72, "upbeat": 104}


def _seed(*parts):
    return int(hashlib.sha1("/".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def mood_of(spec):
    """the film's mood: explicit spec.mood, else counted from scene/sequence moods and the format"""
    words = []
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("mood", "genre", "format", "tone") and isinstance(v, str): words.append(v.lower())
                else: walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(spec)
    count = {m: sum(any(w in x for w in ws) for x in words) for m, ws in MOOD_WORDS.items()}
    if isinstance(spec.get("mood"), str):
        for m, ws in MOOD_WORDS.items():
            if any(w in spec["mood"].lower() for w in ws): return m
    best = max(count, key=lambda m: count[m])
    return best if count[best] else "warm"


def _hz(semi): return 440.0 * 2 ** ((semi - 9) / 12)          # semitone 0 = C4


def _adsr(n, a, r):
    e = np.ones(n, dtype=np.float32); na = min(n, int(a * SR)); nr = min(n - na, int(r * SR))
    if na: e[:na] = np.linspace(0, 1, na, dtype=np.float32)
    if nr: e[n - nr:] *= np.linspace(1, 0, nr, dtype=np.float32)
    return e


def _pad(freqs, n, bright=0.5, seed=0):
    """warm pad: a few harmonics per note, two detuned voices, slow vibrato"""
    t = np.arange(n, dtype=np.float32) / SR; rng = np.random.default_rng(seed); out = np.zeros(n, dtype=np.float32)
    for f in freqs:
        for det in (-0.12, 0.12):
            ph = rng.uniform(0, 2 * math.pi); vib = 0.0025 * np.sin(2 * math.pi * rng.uniform(4.5, 5.5) * t + ph)
            for h, amp in ((1, 1.0), (2, 0.35 * bright), (3, 0.16 * bright), (4, 0.07 * bright)):
                out += amp * np.sin(2 * math.pi * f * h * (1 + det / 100 + vib) * t + ph * h)
    return out / max(1, len(freqs) * 2)


def _pluck(f, n, decay=3.2):
    t = np.arange(n, dtype=np.float32) / SR
    x = (np.sin(2 * math.pi * f * t) + 0.3 * np.sin(4 * math.pi * f * t) + 0.12 * np.sin(6 * math.pi * f * t))
    return (x * np.exp(-decay * t) * np.minimum(1, t / 0.004)).astype(np.float32)


def _kick(n):
    t = np.arange(n, dtype=np.float32) / SR
    return (np.sin(2 * math.pi * (55 + 90 * np.exp(-t * 30)) * t) * np.exp(-t * 9)).astype(np.float32)


def score(spec, duration_s, sections=None):
    """sections: [(start_s, end_s, value '+'|'-'|'')] from the scenes; None -> one section"""
    mood = mood_of(spec); title = spec.get("title", spec.get("id", "film"))
    rnd = np.random.default_rng(_seed("score", title))
    key = int(rnd.integers(0, 12)) - 12 if mood in ("sad", "mystery", "tense") else int(rnd.integers(0, 7)) - 5
    bpm = TEMPO[mood] + int(rnd.integers(-4, 5)); beat = 60.0 / bpm; bar = 4 * beat
    N = int(duration_s * SR); out = np.zeros(N + SR * 4, dtype=np.float32)
    sections = [(a_, min(b_, duration_s), v_) for a_, b_, v_ in (sections or [(0.0, duration_s, "")]) if a_ < duration_s] or [(0.0, duration_s, "")]
    # (a spec longer than the video, or a video cut shorter than its scenes, never overruns the buffer)
    progs = PROG[mood]
    for si, (s0, s1, val) in enumerate(sections):
        pos = s0 / max(1.0, duration_s)
        prog = progs[(si + (1 if val == "-" else 0)) % len(progs)]
        if val == "-" and mood in ("warm", "upbeat", "hopeful"): prog = PROG["sad"][si % 2]       # a setback darkens it
        if pos > 0.85 and mood in ("tense", "mystery", "sad"): prog = PROG["hopeful"][0]          # the ending resolves
        intensity = 0.55 + 0.45 * min(1.0, pos / 0.8) if pos < 0.9 else 0.5                        # builds, then settles
        t = s0; bi = 0
        while t < s1 - 0.05:
            root, q = prog[bi % len(prog)]; nb = int(min(bar, s1 - t) * SR); a = int(t * SR)
            nb = min(nb, len(out) - a)
            if nb < SR // 4: break
            notes = [key + root + iv for iv in QUAL[q]]
            pad = _pad([_hz(n_) for n_ in notes], nb, bright=0.35 + 0.4 * intensity, seed=_seed(title, si, bi))
            out[a:a + nb] += 0.30 * pad * _adsr(nb, 0.9, 0.9)
            bass = np.sin(2 * math.pi * _hz(key + root - 24) * np.arange(nb, dtype=np.float32) / SR)
            out[a:a + nb] += 0.20 * bass * _adsr(nb, 0.05, 0.4)
            # arpeggio: eighths in upbeat/hopeful, quarters otherwise; quieter in the opening and the last bars
            step = beat / 2 if mood in ("upbeat", "hopeful") else beat
            arp = notes + [notes[1] + 12, notes[2] + 12]
            k = 0
            while k * step < min(bar, s1 - t) - 0.05:
                pn = arp[[0, 2, 1, 3, 2, 4][k % 6] % len(arp)] + 12
                pa = a + int(k * step * SR); ln = int(min(1.6, 4 * step) * SR)
                if pa + ln < len(out):
                    out[pa:pa + ln] += 0.11 * intensity * _pluck(_hz(pn), ln, decay=3.0 if mood != "upbeat" else 5.0)
                k += 1
            if mood in ("upbeat", "tense") and intensity > 0.6:          # a muted pulse on the beats
                for b in range(4):
                    pa = a + int(b * beat * SR); ln = int(0.35 * SR)
                    if pa + ln < len(out): out[pa:pa + ln] += (0.16 if mood == "upbeat" else 0.10) * _kick(ln)
            t += bar; bi += 1
    out = out[:N]
    fi, fo = int(min(3, duration_s / 4) * SR), int(min(4, duration_s / 4) * SR)
    if fi: out[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
    if fo: out[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)
    return (np.tanh(out * 1.4) / 1.4 * 0.8).astype(np.float32)


# ---------------------------------------------------------------- room tone ------------------------------------------

def _shaped_noise(n, seed, lo, hi, tilt=-3.0):
    """noise with energy between lo and hi Hz, falling tilt dB/octave above lo (FFT shaping, fast)"""
    rng = np.random.default_rng(seed); X = np.fft.rfft(rng.standard_normal(n)); f = np.fft.rfftfreq(n, 1 / SR)
    g = np.where((f >= lo) & (f <= hi), 1.0, 0.0) * (np.maximum(f, lo) / lo) ** (tilt / 6.02)
    y = np.fft.irfft(X * g, n).astype(np.float32)
    return y / (np.abs(y).max() + 1e-9)


def _loop(x, n):
    """repeat a bed to n samples with 1 s crossfades so the seam is not heard"""
    if len(x) >= n: return x[:n]
    xf = SR; out = np.zeros(n, dtype=np.float32); p = 0
    while p < n:
        seg = x.copy(); m = min(len(seg), n - p)
        if p: seg[:xf] *= np.linspace(0, 1, xf, dtype=np.float32); out[p - xf:p] *= np.linspace(1, 0, xf, dtype=np.float32)[:min(xf, p)]
        out[p:p + m] += seg[:m]; p += len(seg) - xf
    return out


def _events(n, every_s, make, seed, jitter=0.5):
    rng = np.random.default_rng(seed); out = np.zeros(n, dtype=np.float32); t = rng.uniform(0.3, every_s)
    while t * SR < n:
        x = make(rng); a = int(t * SR); m = min(len(x), n - a); out[a:a + m] += x[:m]
        t += every_s * rng.uniform(1 - jitter, 1 + jitter)
    return out


def _beep(f, d):
    t = np.arange(int(d * SR), dtype=np.float32) / SR
    return (np.sin(2 * math.pi * f * t) * np.minimum(1, t / 0.005) * np.minimum(1, (d - t) / 0.02)).astype(np.float32)


def _car(rng):
    d = rng.uniform(2.5, 4.5); n = int(d * SR); x = _shaped_noise(n, int(rng.integers(1e9)), 60, 900, -6)
    env = np.exp(-((np.arange(n) / n - 0.5) ** 2) / 0.03).astype(np.float32)
    return x * env * 0.8


def _clink(rng):
    f = rng.uniform(2200, 3600); t = np.arange(int(0.25 * SR), dtype=np.float32) / SR
    return (np.sin(2 * math.pi * f * t) + 0.5 * np.sin(2 * math.pi * f * 2.7 * t)) * np.exp(-t * 28) * 0.35


def _murmur(n, seed):
    """a room of people talking far away: speech-band noise, syllable-rate wobble"""
    x = _shaped_noise(n, seed, 250, 2500, -4); t = np.arange(n, dtype=np.float32) / SR
    rng = np.random.default_rng(seed + 1); w = np.zeros(n, dtype=np.float32)
    for _ in range(5): w += np.abs(np.sin(2 * math.pi * rng.uniform(2.5, 5.0) * t + rng.uniform(0, 6)))
    return x * (0.3 + w / 5)


KIND_OF = {"street": "street", "shopfront": "street", "beach": "park", "park": "park", "cafe": "cafe", "restaurant": "cafe",
           "office": "office", "meeting": "office", "lab": "office", "bank": "office", "classroom": "classroom",
           "hospital": "hospital", "ward": "hospital", "clinic": "hospital", "grocery": "grocery", "shop": "grocery",
           "laundry": "grocery", "bedroom": "bedroom", "bathroom": "bedroom", "living": "room", "kitchen": "room",
           "cinema": "cinema", "void": "void", "generic": "room"}


def ambience(kind, duration_s, seed=0):
    n = int(duration_s * SR); bed_n = min(n, 12 * SR)
    air = _loop(_shaped_noise(bed_n, seed, 40, 6000, -5), n) * 0.10                        # every place has air
    if kind == "void": return air * 0.4
    out = air
    if kind in ("office", "classroom", "hospital", "grocery", "cinema"):                      # ventilation hum
        t = np.arange(n, dtype=np.float32) / SR
        out = out + 0.05 * np.sin(2 * math.pi * 60 * t) + 0.025 * np.sin(2 * math.pi * 120 * t) \
            + _loop(_shaped_noise(bed_n, seed + 3, 80, 700, -6), n) * 0.08
    if kind == "street":
        out = out + _loop(_shaped_noise(bed_n, seed + 5, 35, 500, -6), n) * 0.22 + _events(n, 6.0, _car, seed + 7) * 0.35
    if kind == "park":
        out = out + _loop(_shaped_noise(bed_n, seed + 5, 400, 5000, -3), n) * 0.10 \
            + _events(n, 3.5, lambda r: _beep(r.uniform(2600, 4200), 0.07) * 0.25, seed + 9)       # birds, sparse
    if kind == "cafe":
        out = out + _loop(_murmur(bed_n, seed + 11), n) * 0.20 + _events(n, 4.0, _clink, seed + 13) * 0.5
    if kind == "hospital":
        out = out + _events(n, 1.0, lambda r: _beep(960, 0.09) * 0.18, seed + 15, jitter=0.0) \
            + _loop(_murmur(bed_n, seed + 17), n) * 0.06
    if kind == "grocery":
        out = out + _events(n, 5.0, lambda r: _beep(1800, 0.12) * 0.25, seed + 19) + _loop(_murmur(bed_n, seed + 21), n) * 0.08
    if kind == "office":
        out = out + _events(n, 2.5, lambda r: _clink(r) * 0.25, seed + 23)                      # keys / a cup now and then
    if kind == "bedroom":
        out = out * 0.6 + _events(n, 1.0, lambda r: _beep(2400, 0.012) * 0.10, seed + 25, jitter=0.0)   # a clock
    return out.astype(np.float32)


def ambience_track(project_dir, duration_s):
    """room tone of every shot's place, crossfaded over 0.3 s at changes of place"""
    dbg = pathlib.Path(project_dir) / "assets" / "shots_debug.json"
    n = int(duration_s * SR); out = np.zeros(n, dtype=np.float32)
    if not dbg.exists(): return out
    shots = json.loads(dbg.read_text(encoding="utf-8")).get("shots", [])
    kinds = {}
    for sh in shots:
        sid = (sh.get("setting") or "").split("__")[0]
        kinds[sid] = kinds.get(sid) or _kind(project_dir, sid)
    beds = {}
    runs = []
    for sh in shots:
        sid = (sh.get("setting") or "").split("__")[0]; t0 = float(sh.get("t0", 0))
        if runs and runs[-1][0] == sid: continue
        runs.append([sid, t0])
    for i, (sid, t0) in enumerate(runs):
        t1 = runs[i + 1][1] if i + 1 < len(runs) else duration_s
        k = kinds.get(sid, "room")
        if k not in beds: beds[k] = ambience(k, min(duration_s, 40.0), _seed("amb", k))
        a, b = int(t0 * SR), min(n, int(t1 * SR) + int(0.3 * SR))
        if b <= a: continue
        seg = _loop(beds[k], b - a).copy(); xf = min(int(0.3 * SR), len(seg) // 2)
        if xf: seg[:xf] *= np.linspace(0, 1, xf, dtype=np.float32); seg[-xf:] *= np.linspace(1, 0, xf, dtype=np.float32)
        out[a:b] += seg[:b - a]
    return out


AMB_WORDS = [("hospital", r"hospital|ward|clinic|patient|nurse"), ("street", r"street|road|pavement|sidewalk|bus stop|outside|crosswalk"),
             ("cafe", r"cafe|café|coffee|restaurant|diner|bar|pub|canteen|bakery"), ("grocery", r"shop|store|supermarket|grocery|market|till|checkout"),
             ("office", r"office|bank|meeting|lab|desk|reception|lobby"), ("classroom", r"class|school|lecture|library"),
             ("cinema", r"cinema|theat|screen"), ("park", r"park|garden|beach|field|forest|farm"), ("bedroom", r"bedroom|bed|night room")]


def _kind(project_dir, sid):
    """place kind of a setting for its room tone: the designed "place" text (assets/places.json), its set, else the id"""
    import re as _re
    pf = pathlib.Path(project_dir) / "assets" / "places.json"
    if pf.exists():
        try:
            txt = str(json.loads(pf.read_text(encoding="utf-8")).get(sid, "")).lower()
            for k, rx in AMB_WORDS:
                if _re.search(rx, txt): return k
        except Exception:
            pass
    f = pathlib.Path(project_dir) / "assets" / f"anchors_{sid}.json"
    k = {}
    if f.exists():
        try: k = json.loads(f.read_text(encoding="utf-8")).get("_kind") or {}
        except Exception: k = {}
    for word in (k.get("style"), k.get("type"), sid):
        for part in str(word or "").lower().replace("-", "_").split("_"):
            if part in KIND_OF: return KIND_OF[part]
    return "room"


def sections_of(spec):
    out = []; t = 0.0
    for sc in spec.get("scenes", []):
        d = float(sc.get("target_s", 0) or 0)
        if d > 0: out.append((t, t + d, str(sc.get("value", "")).strip()[:1])); t += d
    return out or None


if __name__ == "__main__":
    sp = json.load(open(sys.argv[1], encoding="utf-8")); D = float(sys.argv[2])
    x = score(sp, D, sections_of(sp)); import wave
    with wave.open(sys.argv[3], "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    print(f"score: {mood_of(sp)} {D:.0f}s -> {sys.argv[3]}")
