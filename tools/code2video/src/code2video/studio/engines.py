from __future__ import annotations

import os
import threading

from ..alignment import FasterWhisperAligner
from ..tts import CachedTTS, DryRunTTS, EdgeTTSAdapter, VieNeuAdapter

_lock = threading.Lock()
_tts_cache: dict[str, object] = {}
_aligner_cache: dict[tuple[str, str, str, str], FasterWhisperAligner] = {}


def get_tts(dry_run: bool, mode: str = "v3turbo", language: str = "vi", voice: str | None = None):
    """vi -> VieNeu (cache theo mode); ngôn ngữ khác -> edge-tts (tạo mới, nhẹ).

    Adapter được bọc CachedTTS (cache wav theo text+voice+ref) trừ khi TTS_CACHE=0.
    """
    if dry_run:
        return DryRunTTS()
    if language and language != "vi":
        adapter: object = EdgeTTSAdapter(voice=voice, language=language)
    else:
        with _lock:
            adapter = _tts_cache.get(mode)
            if adapter is None:
                adapter = VieNeuAdapter(mode=mode)
                _tts_cache[mode] = adapter
    if os.environ.get("TTS_CACHE", "1") != "0":
        return CachedTTS(adapter, prefix=f"{language}:{mode}")
    return adapter


def get_aligner(model: str, device: str, compute_type: str, language: str = "vi") -> FasterWhisperAligner:
    key = (model, device, compute_type, language)
    with _lock:
        aligner = _aligner_cache.get(key)
        if aligner is None:
            aligner = FasterWhisperAligner(model, device, compute_type, language=language)
            _aligner_cache[key] = aligner
        return aligner
