from __future__ import annotations

import re

from .models import Cue, Scene

_TIME = re.compile(r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})")
_TAG = re.compile(r"<[^>]+>|\{[^}]+\}")


def _to_ms(hours: str, minutes: str, seconds: str, fraction: str) -> int:
    return ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 1000 + int(fraction.ljust(3, "0"))


def parse_srt(text: str) -> list[Cue]:
    text = text.lstrip("﻿")
    text = re.sub(r"\r+\n|\r", "\n", text)
    cues: list[Cue] = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        time_index = next((index for index, line in enumerate(lines) if "-->" in line), None)
        if time_index is None:
            continue
        times = _TIME.findall(lines[time_index])
        if len(times) < 2:
            continue
        start_ms = _to_ms(*times[0])
        end_ms = _to_ms(*times[1])
        body = " ".join(_TAG.sub("", line) for line in lines[time_index + 1:]).strip()
        body = re.sub(r"\s+", " ", body)
        if not body:
            continue
        cues.append(Cue(len(cues) + 1, body, start_ms, max(start_ms + 1, end_ms)))
    cues.sort(key=lambda cue: cue.start_ms)
    for index, cue in enumerate(cues, 1):
        cue.index = index
    return cues


def cues_from_lines(text: str) -> list[Cue]:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return [Cue(index, line, 0, 0) for index, line in enumerate(lines, 1)]


def group_scenes(cues: list[Cue], target_sec: float = 30.0, min_sec: float = 25.0, max_sec: float = 35.0) -> list[Scene]:
    if not cues:
        return []
    target_ms = int(target_sec * 1000)
    min_ms = int(min_sec * 1000)
    max_ms = int(max_sec * 1000)
    scenes: list[Scene] = []
    bucket: list[Cue] = []

    def flush() -> None:
        if not bucket:
            return
        start_ms = bucket[0].start_ms
        end_ms = bucket[-1].end_ms
        scenes.append(Scene(
            scene_index=len(scenes) + 1,
            start_ms=start_ms,
            end_ms=end_ms,
            cue_range=(bucket[0].index, bucket[-1].index),
            text=" ".join(cue.text for cue in bucket),
        ))
        bucket.clear()

    for cue in cues:
        if bucket and cue.end_ms - bucket[0].start_ms > max_ms:
            flush()
        bucket.append(cue)
        span = bucket[-1].end_ms - bucket[0].start_ms
        if span >= target_ms and span >= min_ms:
            flush()
    flush()
    return scenes
