from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Word:
    text: str
    start_ms: int
    end_ms: int


@dataclass
class Cue:
    index: int
    text: str
    start_ms: int
    end_ms: int
    requested_start_ms: int | None = None
    words: list[Word] = field(default_factory=list)

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)


@dataclass
class Scene:
    scene_index: int
    start_ms: int
    end_ms: int
    cue_range: tuple[int, int]
    text: str

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)


@dataclass
class Timeline:
    audio: str
    duration_ms: int
    cues: list[Cue]
    scenes: list[Scene]
    sample_rate: int
    language: str = "vi"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "audio": self.audio,
            "durationMs": self.duration_ms,
            "sampleRate": self.sample_rate,
            "language": self.language,
            "cues": [
                {
                    "index": cue.index,
                    "text": cue.text,
                    "startMs": cue.start_ms,
                    "endMs": cue.end_ms,
                    "durMs": cue.duration_ms,
                    "requestedStartMs": cue.requested_start_ms,
                    "words": [
                        {"text": word.text, "startMs": word.start_ms, "endMs": word.end_ms}
                        for word in cue.words
                    ],
                }
                for cue in self.cues
            ],
            "scenes": [
                {
                    "sceneIndex": scene.scene_index,
                    "startMs": scene.start_ms,
                    "endMs": scene.end_ms,
                    "sceneDurationMs": scene.duration_ms,
                    "cueRange": list(scene.cue_range),
                    "text": scene.text,
                }
                for scene in self.scenes
            ],
            "metadata": self.metadata,
        }
