from __future__ import annotations

from pathlib import Path

import numpy as np

from .alignment import fallback_word_timing
from .models import Cue, Timeline
from .srt import group_scenes
from .tts import TTSAdapter, write_wav


def synthesize_cues(cues: list[Cue], tts: TTSAdapter, audio_path: Path, language: str = "vi") -> Timeline:
    if not cues:
        raise ValueError("Không có cue để tổng hợp.")
    clips: list[np.ndarray] = []
    starts: list[int] = []
    cursor_ms = 0
    for cue in cues:
        requested_start = cue.start_ms
        start_ms = max(requested_start, cursor_ms)
        clip = tts.synthesize(cue.text)
        duration_ms = round(len(clip) * 1000 / tts.sample_rate)
        cue.requested_start_ms = requested_start
        cue.start_ms = start_ms
        cue.end_ms = start_ms + duration_ms
        starts.append(start_ms)
        clips.append(clip)
        cursor_ms = cue.end_ms

    total_samples = max(start * tts.sample_rate // 1000 + len(clip) for start, clip in zip(starts, clips))
    track = np.zeros(total_samples + tts.sample_rate // 2, dtype=np.float32)
    for start_ms, clip in zip(starts, clips):
        start_sample = round(start_ms * tts.sample_rate / 1000)
        track[start_sample:start_sample + len(clip)] += clip
    write_wav(track, tts.sample_rate, audio_path)
    for cue in cues:
        if not cue.words:
            fallback_word_timing([cue])
    scenes = group_scenes(cues)
    return Timeline(
        audio=audio_path.name,
        duration_ms=round(len(track) * 1000 / tts.sample_rate),
        cues=cues,
        scenes=scenes,
        sample_rate=tts.sample_rate,
        language=language,
    )
