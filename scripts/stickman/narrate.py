#!/usr/bin/env python3
"""Narration for a stickman film: story.json -> narration.wav + timing.json (line times, scene times, captions).

    python scripts/stickman/narrate.py stories/<id>.json outputs/<id>/voice [--dry-run]

The pictures are fitted to the voice, never the other way round (stickman-video-director rule: never slow or squeeze
speech to fit a plan). Each line is synthesised at its natural pace and acted from its "emote" (rate / pitch / volume,
tools/code2video tts.direction_prosody); lines are joined with natural pauses (longer when the speaker changes, longest
at a scene change). Engine: edge-tts conversational voices for English (and other non-vi languages), VieNeu for vi
(tools/code2video). Each speaker keeps one voice for the whole film.

timing.json:
  {"duration": s, "lead": s, "lines": [{scene, i, who, speaker, text, emote, start, end}],
   "scenes": [{id, title, place, mood, start, end}], "captions": [{start, end, text}], "words_per_second": x}
Captions are one-line phrases (the renderer refuses wrapped captions), split at punctuation, then word boundaries,
timed by character share inside the line.
"""
import argparse, json, pathlib, re, sys, wave

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "code2video" / "src"))

SR = 48000
LEAD, GAP_SAME, GAP_OTHER, GAP_SCENE, TAIL = 0.25, 0.30, 0.45, 0.85, 0.6
CAPTION_CHARS = 38          # one caption line at the B1-B4 landscape presets (B3 is uppercase: wider letters)


def _resample(x, sr_in):
    if sr_in == SR or x.size == 0: return x.astype(np.float32)
    n = int(round(x.size * SR / sr_in))
    return np.interp(np.linspace(0, x.size - 1, n), np.arange(x.size), x).astype(np.float32)


def _trim(x, sr, thr=0.008, pad=0.06):
    f = max(1, sr // 100); n = x.size // f
    if n == 0: return x
    e = np.abs(x[: n * f].reshape(n, f)).mean(axis=1); act = np.where(e > thr)[0]
    if act.size == 0: return x
    p = int(pad * sr / f)
    return x[max(0, (act[0] - p) * f): min(x.size, (act[-1] + 1 + p) * f)]


def split_caption(text, limit=CAPTION_CHARS):
    """one-line phrases: at punctuation first, then at word boundaries"""
    parts = [p.strip() for p in re.split(r"(?<=[,.;:!?…])\s+", text.strip()) if p.strip()]
    out = []
    for p in parts:
        words, cur = p.split(), ""
        for w in words:
            if cur and len(cur) + 1 + len(w) > limit:
                out.append(cur); cur = w
            else:
                cur = f"{cur} {w}".strip()
        if cur: out.append(cur)
    return out


class _Dry:
    sample_rate = SR; voice = None; prosody = None
    def synthesize(self, text):   # 2.7 words/s of quiet tone, for offline tests only
        n = int(SR * max(0.6, len(text.split()) / 2.7)); t = np.arange(n) / SR
        return (0.05 * np.sin(2 * np.pi * 180 * t)).astype(np.float32)


def make_tts(lang, dry):
    if dry: return _Dry()
    if lang and lang != "vi":
        from code2video.tts import EdgeTTSAdapter
        return EdgeTTSAdapter(language=lang)
    from code2video.studio.engines import get_tts
    return get_tts(False, "v3turbo", "vi")


def voices_for(story, tts):
    """speaker name -> voice id, one per speaker, by gender (tools/code2video voice_assign)"""
    narr = story.get("narrator") or {}
    people = [{"name": narr.get("name", "Narrator"), "gender": narr.get("gender"), "voice": narr.get("voice")}] + \
             [{"name": c.get("name", c.get("id")), "gender": c.get("gender"), "voice": c.get("voice")} for c in story.get("cast", [])]
    explicit = {p["name"]: p["voice"] for p in people if p.get("voice")}
    if not hasattr(tts, "voice") or isinstance(tts, _Dry): return explicit
    from code2video.voice_assign import assign_voices
    g = {p["name"]: {"f": "female", "female": "female", "m": "male", "male": "male"}.get(str(p.get("gender", "")).lower()) for p in people}
    return assign_voices([p["name"] for p in people], explicit, language=story.get("lang", "en"), genders={k: v for k, v in g.items() if v})


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("story"); ap.add_argument("out"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    story = json.load(open(a.story, encoding="utf-8")); out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    tts = make_tts(story.get("lang", "en"), a.dry_run)
    try:
        from code2video.tts import direction_prosody
    except Exception:
        direction_prosody = None
    names = {c["id"]: c.get("name", c["id"]) for c in story.get("cast", [])}
    narr_name = (story.get("narrator") or {}).get("name", "Narrator")
    vmap = voices_for(story, tts)
    track = [np.zeros(int(LEAD * SR), np.float32)]; t = LEAD
    lines, scenes, caps = [], [], []
    prev_who, words = None, 0
    for si, sc in enumerate(story.get("scenes", [])):
        if si: gap = GAP_SCENE; track.append(np.zeros(int(gap * SR), np.float32)); t += gap; prev_who = None
        s_start = t
        for li, ln in enumerate(sc.get("lines", [])):
            text = str(ln.get("t", "")).strip()
            if not text: continue
            who = ln.get("who") or "narrator"; narrator = who in ("narrator", narr_name)
            speaker = narr_name if narrator else names.get(who, who)
            if prev_who is not None:
                gap = GAP_SAME if who == prev_who else GAP_OTHER
                track.append(np.zeros(int(gap * SR), np.float32)); t += gap
            if hasattr(tts, "voice") and vmap.get(speaker): tts.voice = vmap[speaker]
            if hasattr(tts, "prosody") and direction_prosody:
                tts.prosody = direction_prosody(ln.get("emote", ""), text, narrator, sc.get("mood", ""))
            clip = np.asarray(tts.synthesize(text), dtype=np.float32).reshape(-1)
            clip = _trim(_resample(clip, int(getattr(tts, "sample_rate", SR))), SR)
            d = clip.size / SR
            lines.append({"scene": sc.get("id", si + 1), "i": li, "who": who, "speaker": speaker, "text": text,
                          "emote": ln.get("emote", ""), "start": round(t, 3), "end": round(t + d, 3)})
            phrases = split_caption(text); total = sum(len(p) for p in phrases) or 1; ct = t
            for p in phrases:
                cd = d * len(p) / total; caps.append({"start": round(ct, 3), "end": round(ct + cd - 0.02, 3), "text": p}); ct += cd
            track.append(clip); t += d; prev_who = who; words += len(text.split())
        scenes.append({"id": sc.get("id", si + 1), "title": sc.get("title", ""), "place": sc.get("place", ""), "mood": sc.get("mood", ""),
                       "value": sc.get("value", ""), "start": round(s_start, 3), "end": round(t, 3)})
    track.append(np.zeros(int(TAIL * SR), np.float32)); t += TAIL
    if scenes: scenes[-1]["end"] = round(t, 3)
    x = np.concatenate(track); peak = float(np.abs(x).max() or 1)
    if peak > 0.98: x = x * (0.98 / peak)
    with wave.open(str(out / "narration.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    speech = sum(l["end"] - l["start"] for l in lines) or 1
    timing = {"duration": round(t, 3), "lead": LEAD, "lines": lines, "scenes": scenes, "captions": caps,
              "words_per_second": round(words / speech, 2), "voices": vmap, "engine": type(tts).__name__}
    (out / "timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"narration: {t:.1f}s, {len(lines)} lines, {len(caps)} captions, {timing['words_per_second']} words/s of speech, "
          f"engine {timing['engine']}, voices {vmap}")


if __name__ == "__main__":
    main()
