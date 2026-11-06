from __future__ import annotations

import re
from dataclasses import dataclass

_TIME = re.compile(r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})")
_MULTI = re.compile(r"^\[(?P<name>[^\]]+)\]\s*\[(?P<times>[^\]]+)\]\s*:\s*(?P<text>.*)$", re.S)


def _to_ms(hours: str, minutes: str, seconds: str, fraction: str) -> int:
    return ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 1000 + int(fraction.ljust(3, "0"))


@dataclass
class ScriptLine:
    index: int
    speaker: str
    text: str
    start_ms: int
    end_ms: int


def _normalize(text: str) -> str:
    text = text.lstrip("\ufeff")
    return re.sub(r"\r+\n|\r", "\n", text)


def parse_script(text: str) -> tuple[list[ScriptLine], list[str]]:
    """Đọc script -> (danh sách line có nhân vật/timing, danh sách nhân vật).

    Nhiều nhân vật: mỗi block cách nhau bằng dòng trống, dạng
        [Tên][00:00:00,000 --> 00:00:03,000]: lời thoại
    Một nhân vật: SRT chuẩn (speaker = "") hoặc text thường (timing tự tính sau).
    """
    text = _normalize(text)
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    is_multi = any(_MULTI.match(block) for block in blocks)

    lines: list[ScriptLine] = []
    if is_multi:
        for block in blocks:
            match = _MULTI.match(block)
            if not match:
                continue
            times = _TIME.findall(match.group("times"))
            if len(times) < 2:
                continue
            start_ms = _to_ms(*times[0])
            end_ms = _to_ms(*times[1])
            body = " ".join(part.strip() for part in match.group("text").splitlines()).strip()
            body = re.sub(r"\s+", " ", body)
            if not body:
                continue
            lines.append(ScriptLine(len(lines) + 1, match.group("name").strip(), body, start_ms, max(start_ms + 1, end_ms)))
    else:
        from .srt import cues_from_lines, parse_srt

        cues = parse_srt(text) if "-->" in text else cues_from_lines(text)
        for cue in cues:
            lines.append(ScriptLine(len(lines) + 1, "", cue.text, cue.start_ms, cue.end_ms))

    lines.sort(key=lambda line: line.start_ms)
    for position, line in enumerate(lines, 1):
        line.index = position
    speakers: list[str] = []
    for line in lines:
        if line.speaker and line.speaker not in speakers:
            speakers.append(line.speaker)
    return lines, speakers
