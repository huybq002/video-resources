"""Lip-sync for Vietnamese: word timings (timeline.json) -> viseme events; optional real-audio loudness for jaw opening.
Each Vietnamese word is one syllable, so the vowel nucleus decides the mouth shape:
  a ă â -> 'a' (wide)   e ê i y -> 'e' (spread)   o ô ơ u ư -> 'o' (round)   b m p onset/coda -> 'm' (closed)
Events are [seconds_relative_to_shot_start, shape, open] with open = jaw amount (scaleY of the mouth, 0.3-1.25).
With a real voiceover.wav (48 kHz PCM16 from the app) the jaw amount follows the speech loudness inside each word.
"""
import re, unicodedata, wave, pathlib
try:
    import numpy as np
except Exception:   # numpy is optional (only needed for audio loudness)
    np = None

VOWELS = "aăâeêioôơuưy"
BASE = {"a": ("a", 1.0), "ă": ("a", 0.8), "â": ("a", 0.75), "e": ("e", 0.65), "ê": ("e", 0.6), "i": ("e", 0.45), "y": ("e", 0.45),
        "o": ("o", 0.8), "ô": ("o", 0.72), "ơ": ("o", 0.68), "u": ("o", 0.55), "ư": ("o", 0.5)}

def _clean(word):
    d = unicodedata.normalize("NFD", word.lower())
    d = "".join(ch for ch in d if ch not in "̣̀́̃̉")   # drop tone marks, keep ă â ê ô ơ ư
    d = unicodedata.normalize("NFC", d)
    return re.sub(r"[^a-zăâđêôơư]", "", d)

def load_env(wav_path, hop=0.01):
    """RMS loudness envelope (list per hop seconds, normalised to the 95th percentile) or None."""
    p = pathlib.Path(wav_path)
    if np is None or not p.exists():
        return None
    try:
        with wave.open(str(p), "rb") as w:
            sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
            if sw != 2: return None
            x = np.frombuffer(w.readframes(n), dtype="<i2").astype("float32") / 32768.0
        if ch > 1: x = x.reshape(-1, ch).mean(axis=1)
        h = max(1, int(sr * hop)); m = len(x) // h
        rms = np.sqrt((x[: m * h].reshape(m, h) ** 2).mean(axis=1))
        ref = float(np.percentile(rms[rms > 1e-4], 95)) if (rms > 1e-4).any() else 1.0
        return {"hop": hop, "v": (rms / max(ref, 1e-6)).clip(0, 1.6).tolist()}
    except Exception:
        return None

def _amp(env, t0, t1):
    if not env: return 1.0
    a, b = int(t0 / env["hop"]), max(int(t1 / env["hop"]), int(t0 / env["hop"]) + 1)
    seg = env["v"][a:b] or [0.5]
    return max(0.0, min(1.4, sum(seg) / len(seg)))

def word_events(word, t0, t1, env=None):
    w = _clean(word)
    if not w or t1 <= t0: return []
    vs = [i for i, ch in enumerate(w) if ch in VOWELS]
    d = t1 - t0
    if not vs:
        return [(t0, "m", 1.0), (t1, "m", 1.0)]
    i0 = vs[0]; main = w[i0]
    if len(vs) > 1 and vs[1] == vs[0] + 1 and main in "ou" and w[vs[1]] in "aăâeêy":    # oa, oe, uy, uê ...
        main = w[vs[1]]
    elif len(vs) > 1 and vs[1] == vs[0] + 1 and main == "i" and w[vs[1]] in "eêaăâơ":      # iê, ia
        main = w[vs[1]]
    shape, base = BASE.get(main, ("a", 0.8))
    onset, coda = w[:i0], w[vs[-1] + 1:]
    amp = 0.55 + 0.7 * _amp(env, t0, t1) if env else 1.0
    op = max(0.3, min(1.25, base * amp))
    ev = []
    t_on = t0
    if onset and onset[-1] in "bmp" or onset == "ph":
        ev.append((t0, "m", 1.0)); t_on = t0 + 0.18 * d
    ev.append((t_on, shape, op))
    t_end = t1
    if coda and coda[0] in "mp":
        ev.append((t1 - 0.2 * d, "m", 1.0))
    elif w[-1] in "uo" and len(vs) == 1 and i0 < len(w) - 1:
        ev.append((t1 - 0.25 * d, "o", 0.55))
    elif coda and coda[0] in "ntc":
        ev.append((t1 - 0.2 * d, "e", 0.35))
    ev.append((t_end, "m", 1.0))
    return ev

def cue_events(words, shot_t0, shot_t1, scene_start, env=None, env_offset=0.0):
    """words: timeline words [{text,startMs,endMs}] (absolute ms). Returns events relative to shot start, clipped to the shot."""
    out = []
    prev_end = None
    for w in words:
        a, b = w["startMs"] / 1000.0, w["endMs"] / 1000.0
        evs = word_events(w["text"], a, b, env)
        for t, sh, op in evs:
            tr = (t - scene_start) - shot_t0
            if -0.05 <= tr <= (shot_t1 - shot_t0) + 0.05:
                out.append([round(max(tr, 0), 3), sh, round(op, 2)])
    if out and out[-1][1] != "m": out.append([out[-1][0] + 0.05, "m", 1.0])
    # de-duplicate events with identical time (keep the last)
    res = []
    for e in sorted(out, key=lambda e: e[0]):
        if res and abs(res[-1][0] - e[0]) < 1e-3: res[-1] = e
        else: res.append(e)
    return res
