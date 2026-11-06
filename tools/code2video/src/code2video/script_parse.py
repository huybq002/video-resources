from __future__ import annotations

import re
from dataclasses import dataclass

_TIME = re.compile(r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})")
# Dạng của skill khi có nhiều người nói: [Tên][start --> end][nhãn giới tính]: lời (nhãn là tùy chọn).
_MULTI = re.compile(r"^\[(?P<name>[^\]]+)\]\s*\[(?P<times>[^\]]+)\](?:\s*\[(?P<gender>[^\]]*)\])?\s*:\s*(?P<text>.*)$", re.S)

_FEMALE_LABELS = {"f", "female", "woman", "girl", "nu", "nữ", "mujer", "femme", "weiblich", "feminino", "femmina",
                  "wanita", "女性", "女", "여성", "หญิง", "жен", "महिला"}
_MALE_LABELS = {"m", "male", "man", "boy", "nam", "hombre", "homme", "männlich", "masculino", "maschio", "pria",
                "男性", "男", "남성", "ชาย", "муж", "पुरुष"}


def normalize_gender(label: str) -> str:
    """'female' | 'male' | '' từ nhãn giới tính trong script (nhiều ngôn ngữ)."""
    value = (label or "").strip().lower()
    if value in _FEMALE_LABELS:
        return "female"
    if value in _MALE_LABELS:
        return "male"
    return ""


def _to_ms(hours: str, minutes: str, seconds: str, fraction: str) -> int:
    return ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 1000 + int(fraction.ljust(3, "0"))


@dataclass
class ScriptLine:
    index: int
    speaker: str
    text: str
    start_ms: int
    end_ms: int
    gender: str = ""


def _normalize(text: str) -> str:
    text = text.lstrip("\ufeff")
    return re.sub(r"\r+\n|\r", "\n", text)


def _strip_leading_comments(block: str) -> str:
    rows = block.split("\n")
    while rows and rows[0].lstrip().startswith("#"):
        rows.pop(0)
    return "\n".join(rows).strip()


def parse_script(text: str) -> tuple[list[ScriptLine], list[str]]:
    """Đọc script -> (danh sách line có nhân vật/timing, danh sách nhân vật).

    Nhiều nhân vật: mỗi block cách nhau bằng dòng trống, dạng
        [Tên][00:00:00,000 --> 00:00:03,000]: lời thoại
    Một nhân vật: SRT chuẩn (speaker = "") hoặc text thường (timing tự tính sau).
    """
    text = _normalize(text)
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    # dòng chú thích '# SCENE ...' đứng đầu block (kể cả dính liền trên [Tên][..]: lời) chỉ là ghi chú, bỏ đi
    cleaned = [c for c in (_strip_leading_comments(b) for b in blocks) if c]
    is_multi = any(_MULTI.match(block) for block in cleaned)

    lines: list[ScriptLine] = []
    if is_multi:
        for block in cleaned:
            match = _MULTI.match(block)
            if not match:  # không im lặng bỏ lời thoại: báo rõ để sửa script
                preview = block[:80].replace("\n", " ")
                raise ValueError(f"Script nhiều nhân vật có block sai định dạng '[Tên][00:00:00,000 --> 00:00:03,000]: lời': {preview}")
            times = _TIME.findall(match.group("times"))
            if len(times) < 2:
                raise ValueError(f"Block thiếu mốc thời gian 'start --> end': {block[:80]}".replace("\n", " "))
            start_ms = _to_ms(*times[0])
            end_ms = _to_ms(*times[1])
            body = " ".join(part.strip() for part in match.group("text").splitlines()).strip()
            body = re.sub(r"\s+", " ", body)
            if not body:
                continue
            lines.append(ScriptLine(len(lines) + 1, match.group("name").strip(), body, start_ms, max(start_ms + 1, end_ms),
                                    normalize_gender(match.group("gender") or "")))
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


def speaker_genders(lines: list[ScriptLine]) -> dict[str, str]:
    """Nhân vật → 'female'/'male' khi script có ghi nhãn giới tính (bỏ qua nhân vật không có)."""
    result: dict[str, str] = {}
    for line in lines:
        if line.speaker and line.gender and line.speaker not in result:
            result[line.speaker] = line.gender
    return result
