from __future__ import annotations

import asyncio
import hashlib
import os
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
        {"id": "en-US-AriaNeural", "label": "Aria (US)"},
        {"id": "en-US-GuyNeural", "label": "Guy (US)"},
        {"id": "en-GB-SoniaNeural", "label": "Sonia (UK)"},
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


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as handle:
        frames = handle.readframes(handle.getnframes())
        rate = handle.getframerate()
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    return audio, rate


def tts_cache_dir() -> Path:
    return Path(os.environ.get("TTS_CACHE_DIR") or (Path(__file__).resolve().parents[2] / ".cache" / "tts"))


class CachedTTS:
    """Bọc adapter TTS, cache wav theo (text, voice, ref audio) vào .cache/tts.

    Ủy quyền thuộc tính cho adapter bên trong nên việc đổi voice/ref giữa các cue
    (multi-speaker) vẫn hoạt động như không có cache.
    """

    def __init__(self, inner: TTSAdapter, cache_dir: Path | None = None, prefix: str = ""):
        self.inner = inner
        self.cache_dir = Path(cache_dir) if cache_dir is not None else tts_cache_dir()
        self.prefix = prefix

    @property
    def sample_rate(self) -> int:
        return self.inner.sample_rate

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def __setattr__(self, name, value):
        if name in ("inner", "cache_dir", "prefix"):
            object.__setattr__(self, name, value)
        else:
            setattr(self.inner, name, value)

    def _key(self, text: str) -> str:
        voice = getattr(self.inner, "voice", None) or ""
        ref = getattr(self.inner, "ref_audio", None) or ""
        if ref:
            ref_path = Path(ref)
            if ref_path.is_file():
                stat = ref_path.stat()
                ref = f"{ref}:{stat.st_size}:{int(stat.st_mtime)}"
        payload = f"{self.prefix}\0{voice}\0{ref}\0{text}"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()

    def synthesize(self, text: str) -> np.ndarray:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self.cache_dir / f"{self._key(text)}.wav"
        if path.is_file():
            audio, rate = _read_wav(path)
            if rate == self.sample_rate:
                return audio
        audio = self.inner.synthesize(text)
        write_wav(audio, self.sample_rate, path)
        return audio
