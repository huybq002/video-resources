"""Luật nối card theo step: chỉ cho nối xuôi, chặn nối ngược/nhảy bước vô nghĩa.

Một nguồn sự thật cho cả backend (validate khi lưu/chạy) và UI (GET /api/flow/rules).
"""
from __future__ import annotations

STEP = {
    "idea": 1,
    "skill": 2,
    "ai-script": 3,
    "build-scenes": 4,
    "ai-image": 4,
    "ai-html": 4,
    "tts": 5,
    "render": 6,
    "merge": 7,
}

# Card nào được nối tới card nào. Tự nối vào chính nó (vòng thử lại) chỉ cho card gọi AI.
NEXT = {
    "idea": ["skill", "ai-script"],
    "skill": ["ai-script"],
    "ai-script": ["build-scenes", "ai-image", "ai-html", "ai-script"],
    "build-scenes": ["tts"],
    "ai-image": ["tts", "ai-image"],
    "ai-html": ["tts", "ai-html"],
    "tts": ["render"],
    "render": ["merge"],
    "merge": [],
}

# HyperFrames: giọng đọc chạy TRƯỚC để AI dựng HTML nhận thời lượng thật của từng câu (đồng bộ hình và tiếng).
STEP_HF = {**STEP, "tts": 4, "ai-html": 5, "render": 6}
NEXT_HF = {
    **NEXT,
    "ai-script": ["tts", "ai-script"],
    "tts": ["ai-html"],
    "ai-html": ["render", "ai-html"],
}

LABEL = {
    "idea": "Ý tưởng", "skill": "Skill", "ai-script": "AI kịch bản", "build-scenes": "Dựng scene",
    "ai-image": "AI tạo ảnh", "ai-html": "AI dựng HTML", "tts": "Voiceover", "render": "Render", "merge": "Ghép cảnh",
}


def edge_problem(from_type: str, to_type: str, engine: str = "whiteboard") -> str | None:
    """None nếu nối được, ngược lại là lý do (tiếng Việt)."""
    step, nxt = (STEP_HF, NEXT_HF) if engine == "hyperframes" else (STEP, NEXT)
    if to_type in nxt.get(from_type, []):
        return None
    a, b = LABEL.get(from_type, from_type), LABEL.get(to_type, to_type)
    sa, sb = step.get(from_type, 0), step.get(to_type, 0)
    if from_type == to_type:
        return f"'{a}' không có vòng thử lại (chỉ card gọi AI mới tự nối lại được)."
    if sb < sa:
        return f"Không nối ngược: '{a}' (bước {sa}) → '{b}' (bước {sb})."
    if sb == sa:
        return f"'{a}' và '{b}' cùng bước {sa}, chúng là hai lựa chọn thay thế nhau, không nối với nhau."
    allowed = ", ".join(LABEL[t] for t in nxt.get(from_type, [])) or "không có (card cuối)"
    return f"'{a}' (bước {sa}) chỉ nối được tới: {allowed}."


def rules_payload() -> dict:
    return {"step": STEP, "next": NEXT, "label": LABEL,
            "engines": {"whiteboard": {"step": STEP, "next": NEXT}, "hyperframes": {"step": STEP_HF, "next": NEXT_HF}}}
