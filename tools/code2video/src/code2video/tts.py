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
    "en": [
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


@dataclass
class EdgeTTSAdapter:
    """TTS đa ngôn ngữ qua edge-tts (online). Dùng cho en/ja/zh/ko; vi giữ VieNeu."""

    voice: str | None = None
    language: str = "en"
    sample_rate: int = 24000

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
            asyncio.run(edge_tts.Communicate(text, self.voice).save(str(mp3)))
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
