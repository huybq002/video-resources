from __future__ import annotations

import threading

from ..alignment import FasterWhisperAligner
from ..tts import DryRunTTS, EdgeTTSAdapter, VieNeuAdapter

_lock = threading.Lock()
_tts_cache: dict[str, object] = {}
_aligner_cache: dict[tuple[str, str, str, str], FasterWhisperAligner] = {}


def get_tts(dry_run: bool, mode: str = "v3turbo", language: str = "vi", voice: str | None = None):
    """vi -> VieNeu (cache theo mode); ngôn ngữ khác -> edge-tts (tạo mới, nhẹ)."""
    if dry_run:
        return DryRunTTS()
    if language and language != "vi":
        return EdgeTTSAdapter(voice=voice, language=language)
    with _lock:
        adapter = _tts_cache.get(mode)
        if adapter is None:
            adapter = VieNeuAdapter(mode=mode)
            _tts_cache[mode] = adapter
        return adapter


def get_aligner(model: str, device: str, compute_type: str, language: str = "vi") -> FasterWhisperAligner:
    key = (model, device, compute_type, language)
    with _lock:
        aligner = _aligner_cache.get(key)
        if aligner is None:
            aligner = FasterWhisperAligner(model, device, compute_type, language=language)
            _aligner_cache[key] = aligner
        return aligner
