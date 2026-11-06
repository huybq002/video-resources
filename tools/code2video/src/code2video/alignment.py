from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import Cue, Word


@dataclass
class FasterWhisperAligner:
    model_size: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "vi"

    def __post_init__(self) -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as error:
            raise RuntimeError("faster-whisper chưa được cài. Dùng `pip install -e '.[alignment]'`.") from error
        self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)

    def align(self, audio_path: Path, cues: list[Cue]) -> None:
        segments, _ = self.model.transcribe(
            str(audio_path),
            language=self.language,
            word_timestamps=True,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        words = [
            Word(word.word.strip(), round(word.start * 1000), round(word.end * 1000))
            for segment in segments
            for word in (segment.words or [])
            if word.word.strip()
        ]
        for cue in cues:
            cue.words = [word for word in words if word.end_ms > cue.start_ms and word.start_ms < cue.end_ms]


def fallback_word_timing(cues: list[Cue]) -> None:
    for cue in cues:
        tokens = cue.text.split()
        if not tokens or cue.duration_ms <= 0:
            continue
        step = cue.duration_ms / len(tokens)
        cue.words = [
            Word(token, round(cue.start_ms + index * step), round(cue.start_ms + (index + 1) * step))
            for index, token in enumerate(tokens)
        ]
