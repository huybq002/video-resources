"""Prompt và kiểm duyệt kịch bản AI cho whiteboard engine."""
from __future__ import annotations

from .whiteboard_assets import DOODLES

MAX_CUES_PER_SCENE = 6

SCHEMA_NOTE = (
    'Trả về DUY NHẤT một object JSON, không kèm chú thích, đúng cấu trúc:\n'
    '{"scenes":[{"title":"<tiêu đề scene>","cues":[{"text":"<câu thoại>",'
    '"doodle":"<một trong các loại doodle ở trên>","label":"<nhãn ngắn dưới hình, tối đa 4 từ>"}]}]}\n'
    "Mỗi scene có từ 2 đến 6 cues; mỗi cue là 1-2 câu ngắn (8-25 từ)."
)


MAX_CHARACTERS = 4


def clean_characters(names) -> list[str]:
    """Tên nhân vật hợp lệ (bỏ ký tự phá định dạng script `[Tên][..]: lời`), không trùng, tối đa 4."""
    import re

    result: list[str] = []
    for raw in names or []:
        name = re.sub(r"[\[\]:\r\n]", "", str(raw)).strip()
        if name and name not in result:
            result.append(name)
    return result[:MAX_CHARACTERS]


def character_note(characters: list[str]) -> str:
    names = ", ".join(characters)
    return (f"ĐÂY LÀ HỘI THOẠI GIỮA {len(characters)} NHÂN VẬT: {names}. Quy tắc bắt buộc: (1) MỖI cue phải có trường "
            f'"speaker" là đúng một tên trong danh sách; (2) lời thoại là cuộc đối đáp thật: các nhân vật đổi lượt nói sau '
            f"mỗi 1-2 cue, người này hỏi/phản hồi người kia, không để một người nói liền quá 2 cue; (3) tất cả nhân vật "
            f"đều phải xuất hiện trong mỗi scene; (4) câu xưng hô (tôi, bạn, anh...) phải đúng với người đang nói.")


def system_prompt(skill_content: str, language: str, characters: list[str] | None = None) -> str:
    extra = f"\n\n{character_note(characters)}" if characters and len(characters) >= 2 else ""
    return f"{skill_content}\n\nDoodle khả dụng (chỉ chọn từ danh sách): {', '.join(sorted(DOODLES))}\n\n{SCHEMA_NOTE}{extra}\n"


def user_prompt(topic: str, language: str, minutes: float, characters: list[str] | None = None) -> str:
    cue_count = round(minutes * 60 / 4.5)
    cast = f" Viết dưới dạng đối thoại giữa: {', '.join(characters)}." if characters and len(characters) >= 2 else ""
    return (
        f"Viết kịch bản video whiteboard bằng tiếng {language} về chủ đề: {topic}.{cast} "
        f"Tổng thời lượng khoảng {minutes} phút (khoảng {cue_count} cue thoại)."
    )


def parse_script_payload(payload: dict, characters: list[str] | None = None) -> dict:
    multi = bool(characters) and len(characters) >= 2
    last_speaker = characters[0] if multi else ""
    scenes = payload.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Kịch bản AI thiếu trường scenes.")
    result = []
    for scene_index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            raise ValueError(f"Scene {scene_index} không hợp lệ.")
        title = str(scene.get("title") or f"Phần {scene_index}").strip()
        cues = scene.get("cues")
        if not isinstance(cues, list) or not cues:
            raise ValueError(f"Scene {title} cần 1-{MAX_CUES_PER_SCENE} cue thoại.")
        parsed_cues = []
        for cue in cues:
            if not isinstance(cue, dict):
                raise ValueError(f"Scene {title} có cue không hợp lệ.")
            text = str(cue.get("text") or "").strip()
            doodle = str(cue.get("doodle") or "question").strip().lower()
            label = str(cue.get("label") or "").strip()
            if not text:
                raise ValueError(f"Scene {title} có cue thiếu text.")
            if doodle not in DOODLES:
                raise ValueError(f"Doodle không hợp lệ trong scene {title}: {doodle}")
            item = {"text": text, "doodle": doodle, "label": label or text[:40]}
            if multi:  # speaker thiếu/lạ: giữ người nói trước đó thay vì báo lỗi
                said = str(cue.get("speaker") or "").strip()
                match = next((c for c in characters if c.lower() == said.lower()), None)
                last_speaker = match or last_speaker
                item["speaker"] = last_speaker
            parsed_cues.append(item)
        # model nhỏ hay viết quá nhiều câu cho một scene: tách thành nhiều scene thay vì báo lỗi
        chunks = [parsed_cues[i:i + MAX_CUES_PER_SCENE] for i in range(0, len(parsed_cues), MAX_CUES_PER_SCENE)]
        for part, chunk in enumerate(chunks, 1):
            result.append({"title": title if part == 1 else f"{title} ({part})", "cues": chunk})
    return {"scenes": result}


def demo_script(topic: str, language: str, minutes: float, characters: list[str] | None = None) -> dict:
    """Kịch bản mẫu không cần gọi model — dùng để test luồng offline và demo UI."""
    lines = [
        (f"Chào mừng bạn đến với video về {topic}.", "wave", "Chào mừng"),
        (f"Vì sao {topic} lại quan trọng với bạn?", "question", "Vì sao?"),
        (f"Thời điểm tốt nhất để bắt đầu là ngay bây giờ.", "clock", "Bắt đầu"),
        (f"Từng bước nhỏ mỗi ngày sẽ tạo ra thay đổi lớn.", "arrow", "Từng bước"),
        (f"Đừng quên áp dụng ngay điều vừa học hôm nay.", "like", "Áp dụng"),
        (f"Cảm ơn bạn đã theo dõi, hẹn gặp lại!", "wave", "Hẹn gặp lại"),
    ]
    cue_count = max(2, min(12, round(minutes * 60 / 4.5)))
    cues = [
        {"text": text, "doodle": doodle, "label": label}
        for text, doodle, label in lines[:cue_count]
    ]
    if characters and len(characters) >= 2:  # thử luồng đa giọng offline: các nhân vật nói luân phiên
        for i, cue in enumerate(cues):
            cue["speaker"] = characters[i % len(characters)]
    half = (len(cues) + 1) // 2
    return {"scenes": [
        {"title": "Mở đầu", "cues": cues[:half]},
        {"title": "Nội dung & kết", "cues": cues[half:]},
    ]}
