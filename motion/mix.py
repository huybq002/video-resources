"""Mix a hezb-motion film: python motion/mix.py <film-dir> <voice-dir> <out.mp4>

  voice    narration.wav (narrate.py), compressed, the loudest layer
  score    out/score.wav (Tone.js, tools/score.mjs), ducked under the voice with a side-chain envelope
  room     room tone that follows each scene's place (scripts/media/score.py ambience_for_scenes)
  foley    film.json "events": a sound at every visible action (coins, door, knock, steps, cheer, splash, dig, thud, ...)
           from our bank (scripts/media/sfx_bank.py) or synthesised here
then muxes with out/video.mp4 and normalises to -14 LUFS (two-pass loudnorm).
"""
import json, sys, subprocess, pathlib, wave
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "media"))
import sfx_bank as B          # noqa: E402
import score as SC            # noqa: E402

SR = 44100


def read_wav(p):
    with wave.open(str(p)) as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    x = x.reshape(-1, ch).mean(axis=1) if ch > 1 else x
    # float64 indices: np.arange is int32 on Windows, and i * 48000 overflowed (the voice looped its first second)
    if sr != SR: x = np.interp(np.arange(int(len(x) * SR / sr), dtype=np.float64) * sr / SR, np.arange(len(x), dtype=np.float64), x).astype(np.float32)
    return x


def env(x, win=2048):
    k = np.ones(win) / win; return np.sqrt(np.convolve(x * x, k, mode="same"))


def noise(n, seed): return np.random.default_rng(seed).standard_normal(n).astype(np.float32)


def lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.zeros_like(x); s = 0.0
    for i in range(len(x)): s = (1 - a) * x[i] + a * s; y[i] = s
    return y


def foley(name, seed=0):
    t = lambda d: np.arange(int(SR * d)) / SR
    if name == "coins":
        out = np.zeros(int(SR * 1.2), np.float32)
        for k in range(7):
            p = B.synth("plink", seed + k); at = int(SR * (0.05 + 0.13 * k + 0.03 * np.sin(k * 7)))
            out[at:at + len(p)] += p[:len(out) - at] * (0.8 - 0.07 * k)
        return out
    if name == "knock": return B.synth("thud", seed) * 0.9
    if name == "door":
        d = t(0.9); f0 = 180 + 60 * np.sin(d * 9); return (np.sin(2 * np.pi * np.cumsum(f0) / SR) * noise(len(d), seed) * 0.25 * np.exp(-d * 2)).astype(np.float32) + np.pad(B.synth("thud", seed), (int(SR * 0.7), 0))[:len(d)] * 0.6
    if name == "cheer":
        d = t(2.2); return (lp(noise(len(d), seed), 1800) * 1.6 * np.minimum(1, d * 4) * np.exp(-d * 0.9)).astype(np.float32)
    if name == "splash":
        d = t(0.8); return (lp(noise(len(d), seed), 900) * 1.5 * np.exp(-d * 5)).astype(np.float32)
    if name == "dig":
        out = np.zeros(int(SR * 2.4), np.float32)
        for k in range(3):
            d = t(0.25); s = (lp(noise(len(d), seed + k), 700) * 1.4 * np.exp(-d * 18)).astype(np.float32); at = int(SR * 0.8 * k); out[at:at + len(s)] += s
        return out
    if name in B.NAMES: return B.synth(name, seed)
    return B.synth("tap", seed)


def place(buf, x, at, gain):
    i = int(at * SR)
    if i >= len(buf): return
    n = min(len(x), len(buf) - i); buf[i:i + n] += x[:n] * gain


def main():
    film_dir, voice_dir, out = map(pathlib.Path, sys.argv[1:4])
    film = json.load(open(film_dir / "film.json", encoding="utf-8")); timing = json.load(open(voice_dir / "timing.json", encoding="utf-8"))
    D = film["duration"]; n = int(D * SR) + SR
    voice = np.zeros(n, np.float32); v = read_wav(voice_dir / "narration.wav"); voice[:len(v)] = v[:n]
    # gentle compression on the voice
    e = env(voice) + 1e-4; g = np.minimum(1.0, (0.18 / e) ** 0.35); voice *= g * 1.6
    music = np.zeros(n, np.float32)
    sp = film_dir / "out" / "score.wav"
    if sp.exists(): m = read_wav(sp); music[:len(m)] = m[:n]
    duck = 1 - 0.65 * np.clip(env(voice, 8192) / 0.08, 0, 1)
    music *= duck * 0.55
    room = SC.ambience_for_scenes(timing["scenes"], D + 1)
    if SC.SR != SR: room = np.interp(np.arange(n, dtype=np.float64) * SC.SR / SR, np.arange(len(room), dtype=np.float64), room).astype(np.float32)
    room = room[:n] * 0.35
    fx = np.zeros(n, np.float32)
    for k, ev in enumerate(film.get("events", [])): place(fx, foley(ev["sfx"], k), ev["t"], ev.get("gain", 0.5))
    mix = voice + music + room[:n] + fx
    mix /= max(1e-6, np.abs(mix).max()) / 0.9
    wav = film_dir / "out" / "mix.wav"
    with wave.open(str(wav), "wb") as w:          # our own writer: scripts/media/score.py writes at its own rate
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    video = film_dir / "out" / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(wav), "-c:v", "libx264", "-preset", "medium", "-crf", "26", "-tune", "grain", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.89", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
    print("film", out)


if __name__ == "__main__":
    main()
