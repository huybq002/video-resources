from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
import wave

import numpy as np


class TTSAdapter(Protocol):
    sample_rate: int

    def synthesize(self, text: str) -> np.ndarray:
        ...


@dataclass
class VieNeuAdapter:
    voice: str | None = None
    ref_audio: str | None = None
    mode: str = "v3turbo"

    def __post_init__(self) -> None:
        try:
            from vieneu import Vieneu
        except ImportError as error:
            raise RuntimeError("VieNeu chưa được cài. Dùng `pip install -e '.[tts]'`.") from error
        self.engine = Vieneu(mode=self.mode)
        self.sample_rate = int(getattr(self.engine, "sample_rate", 48000))

    def synthesize(self, text: str) -> np.ndarray:
        kwargs: dict[str, str] = {}
        if self.voice:
            kwargs["voice"] = self.voice
        if self.ref_audio:
            kwargs["ref_audio"] = self.ref_audio
        audio = self.engine.infer(text, **kwargs)
        return np.asarray(audio, dtype=np.float32).reshape(-1)


@dataclass
class DryRunTTS:
    sample_rate: int = 48000
    milliseconds_per_character: int = 65

    def synthesize(self, text: str) -> np.ndarray:
        duration_ms = max(250, len(text) * self.milliseconds_per_character)
        return np.zeros(round(duration_ms * self.sample_rate / 1000), dtype=np.float32)


EDGE_VOICES: dict[str, list[dict[str, str]]] = {
    # The newer conversational voices come first: they breathe, stress and rise at questions like a person; the
    # older Jenny/Guy read every line in one flat tone (owner, 2026-11-14: "giọng đọc luôn bằng không biểu cảm").
    "en": [
        {"id": "en-US-AndrewMultilingualNeural", "label": "Andrew (US, nam, kể chuyện)"},
        {"id": "en-US-AvaMultilingualNeural", "label": "Ava (US, nữ)"},
        {"id": "en-US-EmmaMultilingualNeural", "label": "Emma (US, nữ)"},
        {"id": "en-US-BrianMultilingualNeural", "label": "Brian (US, nam)"},
        {"id": "en-US-AndrewNeural", "label": "Andrew (US, nam)"},
        {"id": "en-US-AvaNeural", "label": "Ava (US, nữ)"},
        {"id": "en-US-EmmaNeural", "label": "Emma (US, nữ)"},
        {"id": "en-US-BrianNeural", "label": "Brian (US, nam)"},
        {"id": "en-US-JennyNeural", "label": "Jenny (US, nữ)"},
        {"id": "en-US-GuyNeural", "label": "Guy (US, nam)"},
        {"id": "en-US-AriaNeural", "label": "Aria (US, nữ)"},
        {"id": "en-US-EricNeural", "label": "Eric (US, nam)"},
        {"id": "en-US-MichelleNeural", "label": "Michelle (US, nữ)"},
        {"id": "en-US-ChristopherNeural", "label": "Christopher (US, nam)"},
        {"id": "en-GB-SoniaNeural", "label": "Sonia (UK, nữ)"},
        {"id": "en-GB-RyanNeural", "label": "Ryan (UK, nam)"},
        {"id": "en-GB-LibbyNeural", "label": "Libby (UK, nữ)"},
        {"id": "en-US-RogerNeural", "label": "Roger (US, nam)"},
        {"id": "en-AU-NatashaNeural", "label": "Natasha (AU, nữ)"},
        {"id": "en-AU-WilliamNeural", "label": "William (AU, nam)"},
    ],
    "ja": [
        {"id": "ja-JP-NanamiNeural", "label": "Nanami"},
        {"id": "ja-JP-KeitaNeural", "label": "Keita"},
    ],
    "zh": [
        {"id": "zh-CN-XiaoxiaoNeural", "label": "Xiaoxiao"},
        {"id": "zh-CN-YunxiNeural", "label": "Yunxi"},
    ],
    "ko": [
        {"id": "ko-KR-SunHiNeural", "label": "SunHi"},
        {"id": "ko-KR-InJoonNeural", "label": "InJoon"},
    ],
}


def default_edge_voice(language: str) -> str:
    voices = EDGE_VOICES.get(language) or EDGE_VOICES["en"]
    return voices[0]["id"]


# How a feeling changes the read: (rate %, pitch Hz, volume %). Small numbers: a voice actor shifts, never shouts.
PROSODY = {
    "joy": (6, 4, 5), "happy": (6, 4, 5), "excited": (9, 6, 10), "laugh": (8, 5, 8), "proud": (3, 2, 5),
    "surprise": (8, 6, 10), "shock": (10, 7, 12), "angry": (6, -2, 15), "frustrated": (4, -1, 10),
    "worry": (-4, -1, -3), "fear": (4, 3, 0), "doubt": (-6, 0, -3), "think": (-8, -1, -5), "confused": (-5, 2, -2),
    "sad": (-10, -4, -10), "tired": (-12, -4, -10), "relief": (-4, 2, 0), "calm": (-3, -1, -3), "neutral": (0, 0, 0),
}


def direction_prosody(emote: str = "", text: str = "", narrator: bool = False, mood: str = "") -> dict[str, str]:
    """edge-tts rate/pitch/volume for one line from its feeling, punctuation and who says it"""
    r, p, v = PROSODY.get((emote or "").lower().split(":")[0], (0, 0, 0))
    t = (text or "").strip()
    if narrator:
        r, p = r * 0.5 + 1, p * 0.5 - 1           # a storyteller colours lines, the characters act them
        if mood in ("tense", "mystery", "sad"): r -= 3
    if not emote:
        if t.endswith("?"): p += 3
        if t.endswith("!"): r, p, v = r + 6, p + 3, v + 8
    if len(t.split()) <= 4 and t.endswith((".", "…")): r -= 6          # a short line lands slower: a beat
    return {"rate": f"{int(round(r)):+d}%", "pitch": f"{int(round(p)):+d}Hz", "volume": f"{int(round(v)):+d}%"}


@dataclass
class EdgeTTSAdapter:
    """TTS đa ngôn ngữ qua edge-tts (online). Dùng cho en/ja/zh/ko; vi giữ VieNeu.

    prosody: {"rate": "+5%", "pitch": "+2Hz", "volume": "+0%"} for the NEXT synthesize() call (set per line by
    voiceover.py from assets/voice_direction.json). A voice that fails (not offered in this region) falls back to the
    language's classic voice, so the night never loses its voice-over.
    """

    voice: str | None = None
    language: str = "en"
    sample_rate: int = 24000
    prosody: dict | None = None

    def __post_init__(self) -> None:
        try:
            import edge_tts  # noqa: F401
        except ImportError as error:
            raise RuntimeError("edge-tts chưa được cài. Dùng `pip install edge-tts`.") from error
        if not self.voice:
            self.voice = default_edge_voice(self.language)

    def synthesize(self, text: str) -> np.ndarray:
        import edge_tts

        with tempfile.TemporaryDirectory(prefix="code2video-edge-") as tmp:
            mp3 = Path(tmp) / "voice.mp3"
            wav = Path(tmp) / "voice.wav"
            pro = {k: v for k, v in (self.prosody or {}).items() if k in ("rate", "pitch", "volume") and v}
            tried = []
            for voice in [self.voice, *[v["id"] for v in EDGE_VOICES.get(self.language, [])][8:9]]:
                if not voice or voice in tried: continue
                tried.append(voice)
                for attempt in range(4):
                    try:
                        asyncio.run(edge_tts.Communicate(text, voice, **pro).save(str(mp3)))
                        break
                    except Exception:
                        if attempt == 1 and pro: pro = {}                 # a rejected prosody value: read it plainly
                        import time as _t; _t.sleep(1.5 + attempt)
                if mp3.exists() and mp3.stat().st_size > 0: break
            if not mp3.exists():
                raise RuntimeError(f"edge-tts gave no audio for: {text[:60]!r}")
            ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
            subprocess.run(
                [ffmpeg, "-y", "-loglevel", "error", "-i", str(mp3),
                 "-ar", str(self.sample_rate), "-ac", "1", str(wav)],
                check=True,
            )
            with wave.open(str(wav), "rb") as handle:
                frames = handle.readframes(handle.getnframes())
        return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


def write_wav(audio: np.ndarray, sample_rate: int, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.98:
        audio = audio * (0.98 / peak)
    pcm = np.clip(audio, -1.0, 1.0)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())
