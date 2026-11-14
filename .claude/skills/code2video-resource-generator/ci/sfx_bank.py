"""Cartoon sound effects, synthesised (numpy only): no samples, no licence to track, same sound every run.

The approach of ZzFX / jsfxr (MIT / Unlicense, the procedural game-sfx generators on GitHub) applied to film beats:
each effect is a few lines of oscillators, filtered noise and envelopes. An owner-supplied recording wins over the
synth: put `<name>.wav` (CC0 / own licence, e.g. a Kenney pack) in `data/sfx/` and it is used instead.

python sfx_bank.py OUT_DIR      writes every effect as OUT_DIR/<name>.wav to listen to them
"""
import math, pathlib, subprocess, sys
import numpy as np

SR = 48000
NAMES = ["whoosh", "swoosh", "hit", "impact", "pop", "tick", "boing", "sting", "sparkle", "plink", "thud", "step",
         "key", "blip", "rise", "flash", "tap", "bounce", "riser"]


def _t(d): return np.arange(int(SR * d)) / SR


def _env(n, a=0.005, decay=6.0):
    t = np.arange(n) / SR
    att = np.clip(t / max(a, 1e-4), 0, 1)
    return att * np.exp(-decay * t)


def _noise(n, seed):
    return np.random.default_rng(seed).uniform(-1, 1, n)


def _lp(x, fc):
    """one-pole low-pass; fc may be an array (sweeping filter)"""
    fc = np.broadcast_to(np.asarray(fc, dtype=float), x.shape)
    a = 1 - np.exp(-2 * math.pi * fc / SR)
    y = np.empty_like(x); s = 0.0
    for i in range(len(x)):
        s += a[i] * (x[i] - s); y[i] = s
    return y


def _hp(x, fc): return x - _lp(x, fc)


def _bp(x, fc, q=1.0): return _lp(_hp(x, fc / (1 + q)), fc * (1 + q))


def _sweep(f0, f1, d, curve=1.0):
    t = _t(d); f = f0 + (f1 - f0) * (t / d) ** curve
    return np.sin(2 * math.pi * np.cumsum(f) / SR)


def _norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1.0
    return (x / m * peak).astype(np.float32)


def synth(name, seed=0):
    if name == "whoosh":                       # air past the lens: band noise sweeping up then down
        d = 0.5; n = int(SR * d); t = _t(d)
        fc = 400 + 2600 * np.sin(math.pi * t / d) ** 2
        x = _bp(_noise(n, 11 + seed), fc, 0.6) * np.sin(math.pi * t / d) ** 1.5
        return _norm(x, 0.7)
    if name == "swoosh":                       # short rising swish (zoom in, a title arriving)
        d = 0.3; n = int(SR * d); t = _t(d)
        x = _bp(_noise(n, 12 + seed), 600 + 5000 * (t / d) ** 2, 0.5) * np.sin(math.pi * t / d)
        return _norm(x, 0.6)
    if name == "hit":                          # the keyword slamming in: punch + click + a short body
        d = 0.4; n = int(SR * d)
        body = _sweep(140, 55, d, 0.5) * _env(n, 0.002, 11)
        click = _hp(_noise(n, 13 + seed), 2500) * _env(n, 0.0005, 70)
        return _norm(body + 0.5 * click, 0.9)
    if name == "impact":                       # the big moment: sub boom, crack, a dark tail
        d = 1.2; n = int(SR * d)
        boom = _sweep(90, 32, d, 0.4) * _env(n, 0.003, 3.5)
        crack = _lp(_noise(n, 14 + seed), 3500) * _env(n, 0.001, 18)
        tail = _lp(_noise(n, 15 + seed), 700) * _env(n, 0.05, 3.0) * 0.35
        return _norm(boom + 0.6 * crack + tail, 0.95)
    if name == "pop":                          # cartoon bloop: fast pitch-up sine
        d = 0.12; n = int(SR * d)
        return _norm(_sweep(380, 1150, d, 0.6) * _env(n, 0.002, 30), 0.6)
    if name == "tick":
        d = 0.03; n = int(SR * d)
        return _norm(np.sin(2 * math.pi * 2100 * _t(d)) * _env(n, 0.0005, 160), 0.45)
    if name == "boing":                        # spring: wobbling pitch, slow decay
        d = 0.55; t = _t(d); n = len(t)
        f = 210 + 90 * np.exp(-4 * t) * np.sin(2 * math.pi * 14 * t) + 60 * t
        return _norm(np.sin(2 * math.pi * np.cumsum(f) / SR) * _env(n, 0.003, 5), 0.6)
    if name == "sting":                        # shock / realisation: a tense stacked chord stab
        d = 0.9; t = _t(d); n = len(t)
        x = sum(np.sign(np.sin(2 * math.pi * f * t)) * w for f, w in ((185, 1), (196, .8), (277, .7), (370, .5)))
        x = _lp(x, 2200 * np.exp(-3 * t) + 300) * _env(n, 0.004, 3.2)
        return _norm(x + 0.3 * _lp(_noise(n, 16 + seed), 1500) * _env(n, 0.001, 25), 0.75)
    if name == "sparkle":                      # joy, an idea: a quick rising arpeggio of bells
        out = np.zeros(int(SR * 0.7))
        for i, f in enumerate((1320, 1760, 2090, 2640, 3520)):
            d = 0.35; n = int(SR * d); s = int(SR * 0.06 * i)
            out[s:s + n] += np.sin(2 * math.pi * f * _t(d)) * _env(n, 0.002, 9) * (1 - 0.1 * i)
        return _norm(out, 0.45)
    if name == "plink":                        # a tear drop
        d = 0.25; n = int(SR * d)
        return _norm(_sweep(1900, 900, d, 0.3) * _env(n, 0.001, 18), 0.4)
    if name == "thud":                         # a body, a fist on the table, a fall
        d = 0.3; n = int(SR * d)
        return _norm(_sweep(110, 45, d, 0.5) * _env(n, 0.002, 14) + 0.3 * _lp(_noise(n, 17 + seed), 400) * _env(n, 0.001, 30), 0.8)
    if name == "step":                         # soft footstep, varied by seed
        d = 0.09; n = int(SR * d); r = np.random.default_rng(100 + seed)
        x = _lp(_noise(n, 18 + seed), 900 + 500 * r.random()) * _env(n, 0.001, 55) + 0.5 * np.sin(2 * math.pi * (70 + 20 * r.random()) * _t(d)) * _env(n, 0.001, 40)
        return _norm(x, 0.35 + 0.1 * r.random())
    if name == "key":                          # one keystroke
        d = 0.025; n = int(SR * d)
        return _norm(_hp(_noise(n, 19 + seed), 1800) * _env(n, 0.0003, 220), 0.25)
    if name == "blip":                         # a screen coming on
        d = 0.09; t = _t(d); n = len(t)
        return _norm(np.sign(np.sin(2 * math.pi * np.where(t < 0.045, 880, 1320) * t)) * _env(n, 0.002, 18), 0.3)
    if name == "rise":                         # a number / a graph going up
        d = 0.8; n = int(SR * d)
        return _norm(_sweep(300, 900, d, 1.4) * np.sin(math.pi * _t(d) / d) ** 0.7, 0.35)
    if name == "riser":                        # tension building into the power moment
        d = 1.2; n = int(SR * d); t = _t(d)
        x = _bp(_noise(n, 20 + seed), 300 + 4000 * (t / d) ** 2, 0.7) * (t / d) ** 2 + 0.4 * _sweep(120, 480, d, 2) * (t / d) ** 2
        return _norm(x, 0.55)
    if name == "flash":                        # white flash shimmer
        d = 0.5; n = int(SR * d)
        x = _hp(_noise(n, 21 + seed), 5000) * _env(n, 0.001, 8) + 0.4 * np.sin(2 * math.pi * 3200 * _t(d)) * _env(n, 0.001, 10)
        return _norm(x, 0.4)
    if name == "tap":                          # an object put down
        d = 0.06; n = int(SR * d)
        return _norm(_bp(_noise(n, 22 + seed), 1400, 0.6) * _env(n, 0.0005, 70), 0.4)
    if name == "bounce":                       # an object dropping in and bouncing twice
        out = np.zeros(int(SR * 0.7)); th = synth("thud", seed)
        for i, (s, g) in enumerate(((0.0, 1.0), (0.22, 0.45), (0.38, 0.2))):
            a = int(SR * s); out[a:a + len(th)] += th[:len(out) - a] * g
        return _norm(out, 0.6)
    raise KeyError(name)


def load(name, lib_dir=None, seed=0):
    """owner recording (data/sfx/<name>.wav, any format ffmpeg reads) if present, else the synth"""
    if lib_dir:
        for ext in (".wav", ".mp3", ".ogg", ".flac"):
            p = pathlib.Path(lib_dir) / (name + ext)
            if p.exists():
                raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(p), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"])
                return np.frombuffer(raw, dtype=np.float32).copy()
    return synth(name, seed)


def write_wav(path, x):
    import wave
    x = np.clip(x, -1, 1); pcm = (x * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "sfx_preview"); out.mkdir(parents=True, exist_ok=True)
    for nm in NAMES:
        write_wav(out / f"{nm}.wav", synth(nm)); print(nm)
