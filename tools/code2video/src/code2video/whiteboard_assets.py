"""Thư viện doodle + dựng folder scene whiteboard; dùng chung cho generator CLI và Studio AI."""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
INK = (38, 49, 46)
RED = (196, 81, 54)
BLUE = (58, 110, 165)
PAPER = (247, 244, 234)
GRID = (232, 228, 216)
FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
FONT_REG = "C:/Windows/Fonts/segoeui.ttf"
LOCALE_FONTS = {
    "vi": (FONT_BOLD, FONT_REG),
    "en": (FONT_BOLD, FONT_REG),
    "ja": ("C:/Windows/Fonts/YuGothB.ttc", "C:/Windows/Fonts/YuGothM.ttc"),
    "zh": ("C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc"),
    "ko": ("C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"),
}
CPS = {"vi": 0.080, "en": 0.070, "ja": 0.155, "zh": 0.135, "ko": 0.150}


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size, index=0)
    except OSError:
        return ImageFont.load_default()


# ---------- doodles: vẽ trong ô (cx,cy,s) ----------
def d_mansion(d, cx, cy, s):
    w, h = s * 1.1, s * 1.5
    d.rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], outline=INK, width=6)
    d.polygon([(cx - w / 2 - 20, cy - h / 2), (cx + w / 2 + 20, cy - h / 2), (cx, cy - h / 2 - 60)], outline=INK, width=6)
    for r in range(3):
        for c in range(2):
            x = cx - w / 2 + 30 + c * (w / 2.4)
            y = cy - h / 2 + 30 + r * (h / 3.4)
            d.rectangle([x, y, x + w / 5, y + h / 6], outline=BLUE, width=4)
    d.rectangle([cx - w / 6, cy + h / 2 - 60, cx + w / 6, cy + h / 2], outline=RED, width=5)


def d_door(d, cx, cy, s):
    w, h = s * 1.0, s * 1.5
    d.rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], outline=INK, width=6)
    d.ellipse([cx + w / 2 - 26, cy - 10, cx + w / 2 - 6, cy + 10], fill=INK)
    d.rectangle([cx - 30, cy - 10, cx + 30, cy + 34], outline=RED, width=6)
    d.arc([cx - 18, cy - 44, cx + 18, cy - 4], 180, 360, fill=RED, width=6)
    d.ellipse([cx - 6, cy + 6, cx + 6, cy + 18], fill=RED)


def d_window(d, cx, cy, s):
    w, h = s * 1.3, s * 1.1
    d.rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], outline=INK, width=6)
    d.line([(cx, cy - h / 2), (cx, cy + h / 2)], fill=INK, width=5)
    d.line([(cx - w / 2, cy), (cx + w / 2, cy)], fill=INK, width=5)
    for i in range(8):
        x = cx - w / 2 + 14 + (i * 37) % int(w - 30)
        y = cy - h / 2 + 16 + (i * 53) % int(h - 30)
        d.ellipse([x, y, x + 6, y + 6], fill=(150, 150, 140))


def d_body(d, cx, cy, s):
    d.ellipse([cx - s * 0.9, cy - 20, cx - s * 0.45, cy + 25], outline=INK, width=6)
    d.line([(cx - s * 0.45, cy), (cx + s * 0.55, cy)], fill=INK, width=6)
    d.line([(cx - s * 0.1, cy), (cx - s * 0.25, cy + 34)], fill=INK, width=5)
    d.line([(cx + s * 0.2, cy), (cx + s * 0.35, cy + 30)], fill=INK, width=5)
    qf = font(FONT_BOLD, int(s * 1.1))
    d.text((cx + s * 0.5, cy - s * 0.9), "?", font=qf, fill=RED)


def d_question(d, cx, cy, s):
    qf = font(FONT_BOLD, int(s * 1.8))
    d.text((cx - s * 0.4, cy - s * 0.9), "?", font=qf, fill=RED)


def d_floorplan(d, cx, cy, s):
    w, h = s * 1.5, s * 1.15
    d.rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], outline=INK, width=6)
    d.line([(cx - w / 2, cy + h / 6), (cx + w / 2, cy + h / 6)], fill=INK, width=4)
    for i in range(4):
        x = cx - w / 2 + 30 + i * (w / 4.6)
        d.ellipse([x, cy - h / 2 + 14, x + 40, cy - h / 2 + 54], outline=BLUE, width=4)
        tf = font(FONT_BOLD, 24)
        d.text((x + 13, cy - h / 2 + 18), str(i + 1), font=tf, fill=BLUE)


def d_clock(d, cx, cy, s):
    d.ellipse([cx - s * 0.7, cy - s * 0.7, cx + s * 0.7, cy + s * 0.7], outline=INK, width=6)
    d.line([(cx, cy), (cx, cy - s * 0.45)], fill=INK, width=6)
    d.line([(cx, cy), (cx + s * 0.35, cy + s * 0.25)], fill=RED, width=6)


def d_key(d, cx, cy, s):
    d.ellipse([cx - s * 0.6, cy - s * 0.35, cx - s * 0.1, cy + s * 0.15], outline=RED, width=6)
    d.line([(cx - s * 0.12, cy - s * 0.1), (cx + s * 0.6, cy - s * 0.1)], fill=INK, width=6)
    d.line([(cx + s * 0.45, cy - s * 0.1), (cx + s * 0.45, cy + s * 0.12)], fill=INK, width=6)
    d.line([(cx + s * 0.6, cy - s * 0.1), (cx + s * 0.6, cy + s * 0.12)], fill=INK, width=6)


def d_closet(d, cx, cy, s):
    w, h = s * 0.9, s * 1.5
    d.rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], outline=INK, width=6)
    d.line([(cx, cy - h / 2), (cx, cy + h / 2)], fill=INK, width=4)
    d.arc([cx - 8, cy - h / 2 + 40, cx + 28, cy - h / 2 + 84], 180, 360, fill=BLUE, width=4)
    d.line([(cx + 10, cy - h / 2 + 62), (cx + 10, cy - h / 2 + 100)], fill=BLUE, width=4)


def d_detective(d, cx, cy, s):
    d.ellipse([cx - 30, cy - s * 0.75, cx + 30, cy - s * 0.75 + 60], outline=INK, width=6)
    d.line([(cx, cy - s * 0.45), (cx, cy + s * 0.4)], fill=INK, width=6)
    d.line([(cx, cy), (cx - s * 0.35, cy + s * 0.2)], fill=INK, width=5)
    d.line([(cx, cy), (cx + s * 0.3, cy + s * 0.15)], fill=INK, width=5)
    d.ellipse([cx + s * 0.2, cy - s * 0.55, cx + s * 0.65, cy - s * 0.15], outline=BLUE, width=5)
    d.line([(cx + s * 0.6, cy - s * 0.14), (cx + s * 0.8, cy + s * 0.1)], fill=BLUE, width=6)


def d_string(d, cx, cy, s):
    d.arc([cx - s, cy - s, cx + s, cy + s], 200, 340, fill=RED, width=5)
    d.line([(cx + s * 0.9, cy - s * 0.2), (cx + s * 0.9, cy + s * 0.3)], fill=INK, width=5)
    d.polygon([(cx + s * 0.9 - 12, cy + s * 0.3), (cx + s * 0.9 + 12, cy + s * 0.3), (cx + s * 0.9, cy + s * 0.5)], fill=INK)


def d_arrow(d, cx, cy, s):
    d.line([(cx - s * 0.8, cy + s * 0.3), (cx + s * 0.7, cy - s * 0.3)], fill=INK, width=6)
    d.polygon([(cx + s * 0.7, cy - s * 0.3), (cx + s * 0.4, cy - s * 0.35), (cx + s * 0.55, cy - s * 0.05)], fill=INK)


def d_concrete(d, cx, cy, s):
    for i in range(3):
        y = cy - s * 0.5 + i * s * 0.4
        d.rectangle([cx - s, y, cx + s, y + s * 0.34], outline=INK, width=5)


def d_ice(d, cx, cy, s):
    d.polygon([(cx - s * 0.8, cy + s * 0.6), (cx + s * 0.8, cy + s * 0.6), (cx + s * 0.2, cy - s * 0.7)], outline=BLUE, width=6)
    d.line([(cx - s * 0.2, cy + s * 0.2), (cx + s * 0.3, cy + s * 0.2)], fill=BLUE, width=3)


def d_water(d, cx, cy, s):
    d.ellipse([cx - s * 0.9, cy - s * 0.2, cx + s * 0.9, cy + s * 0.4], outline=BLUE, width=6)
    d.arc([cx - s * 0.5, cy + s * 0.02, cx + s * 0.5, cy + s * 0.3], 200, 340, fill=BLUE, width=3)


def d_ghost(d, cx, cy, s):
    d.arc([cx - s * 0.5, cy - s * 0.7, cx + s * 0.5, cy + s * 0.3], 180, 360, fill=INK, width=6)
    d.line([(cx - s * 0.5, cy - s * 0.2), (cx - s * 0.5, cy + s * 0.6)], fill=INK, width=6)
    d.line([(cx + s * 0.5, cy - s * 0.2), (cx + s * 0.5, cy + s * 0.6)], fill=INK, width=6)
    d.line([(cx - s * 0.5, cy + s * 0.6), (cx - s * 0.25, cy + s * 0.4), (cx, cy + s * 0.6), (cx + s * 0.25, cy + s * 0.4), (cx + s * 0.5, cy + s * 0.6)], fill=INK, width=6)
    d.ellipse([cx - s * 0.2, cy - s * 0.35, cx - s * 0.1, cy - s * 0.25], fill=INK)
    d.ellipse([cx + s * 0.1, cy - s * 0.35, cx + s * 0.2, cy - s * 0.25], fill=INK)


def d_zoom(d, cx, cy, s):
    d.rectangle([cx - s * 0.8, cy - s * 0.6, cx + s * 0.8, cy + s * 0.6], outline=INK, width=5)
    d.line([(cx - s * 0.8, cy - s * 0.6), (cx - s * 0.5, cy - s * 0.6)], fill=RED, width=7)
    d.line([(cx + s * 0.8, cy + s * 0.6), (cx + s * 0.5, cy + s * 0.6)], fill=RED, width=7)


def d_like(d, cx, cy, s):
    d.rectangle([cx - s * 0.5, cy - s * 0.3, cx + s * 0.5, cy + s * 0.6], outline=INK, width=6)
    d.rectangle([cx - s * 0.5, cy - s * 0.3, cx - s * 0.2, cy + s * 0.6], outline=INK, width=6)
    d.line([(cx - s * 0.1, cy - s * 0.3), (cx - s * 0.1, cy - s * 0.7)], fill=INK, width=8)


def d_bell(d, cx, cy, s):
    d.arc([cx - s * 0.5, cy - s * 0.6, cx + s * 0.5, cy + s * 0.4], 180, 360, fill=INK, width=6)
    d.line([(cx - s * 0.5, cy - s * 0.1), (cx - s * 0.5, cy + s * 0.4)], fill=INK, width=6)
    d.line([(cx + s * 0.5, cy - s * 0.1), (cx + s * 0.5, cy + s * 0.4)], fill=INK, width=6)
    d.line([(cx - s * 0.55, cy + s * 0.4), (cx + s * 0.55, cy + s * 0.4)], fill=INK, width=6)
    d.ellipse([cx - 12, cy + s * 0.4, cx + 12, cy + s * 0.4 + 24], fill=RED)


def d_wave(d, cx, cy, s):
    d.ellipse([cx - s * 0.5, cy - s * 0.5, cx + s * 0.5, cy + s * 0.5], outline=INK, width=6)
    d.ellipse([cx - s * 0.2, cy - s * 0.15, cx - s * 0.05, cy], fill=INK)
    d.ellipse([cx + s * 0.05, cy - s * 0.15, cx + s * 0.2, cy], fill=INK)
    d.arc([cx - s * 0.25, cy + s * 0.05, cx + s * 0.25, cy + s * 0.35], 200, 340, fill=INK, width=5)


DOODLES = {
    "mansion": d_mansion, "door": d_door, "window": d_window, "body": d_body,
    "question": d_question, "floorplan": d_floorplan, "clock": d_clock, "key": d_key,
    "closet": d_closet, "detective": d_detective, "string": d_string, "arrow": d_arrow,
    "concrete": d_concrete, "ice": d_ice, "water": d_water, "ghost": d_ghost,
    "zoom": d_zoom, "like": d_like, "bell": d_bell, "wave": d_wave,
}


LABEL_OFFSET = 66  # khoảng cách từ đáy ô tới đỉnh nhãn; phải đủ chứa chữ + lề 14px của vùng lộ để nhãn không bị cắt


def grid_slots(n: int) -> list[dict]:
    cols = 3 if n > 4 else (2 if n > 1 else 1)
    rows = math.ceil(n / cols)
    mx, top, bottom = 110, 240, 1000
    cw = (W - 2 * mx) / cols
    ch = (bottom - top) / rows
    slots = []
    for i in range(n):
        r, c = divmod(i, cols)
        slots.append({"x": int(mx + c * cw), "y": int(top + r * ch), "width": int(cw), "height": int(ch)})
    return slots


def locale_fonts(language: str) -> tuple[str, str]:
    return LOCALE_FONTS.get(language, (FONT_BOLD, FONT_REG))


def estimate_dur_ms(text: str, language: str) -> int:
    return round(min(10.0, max(4.5, len(text) * CPS.get(language, 0.08) + 1.4)) * 1000)


def fmt_time(ms: int) -> str:
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, msr = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{msr:03d}"


def fit_font(path: str, text: str, size: int, max_width: int) -> ImageFont.FreeTypeFont:
    while size > 28:
        candidate = font(path, size)
        if candidate.getlength(text) <= max_width:
            return candidate
        size -= 4
    return font(path, 28)


def draw_scene(title: str, items: list, bold_path: str = FONT_BOLD, regular_path: str = FONT_REG,
               label_size: int = 34) -> Image.Image:
    """items = [(kind, label, subtitle)]; vẽ tiêu đề + lưới + doodle + nhãn vào khung 1920x1080."""
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    for x in range(0, W, 64):
        d.line([(x, 0), (x, H)], fill=GRID, width=1)
    for y in range(0, H, 64):
        d.line([(0, y), (W, y)], fill=GRID, width=1)
    title_font = fit_font(bold_path, title, 64, W - 220)
    d.text((110, 90), title, font=title_font, fill=INK)
    d.line([(110, 190), (110 + int(title_font.getlength(title)), 190)], fill=RED, width=8)
    for (kind, label, _), slot in zip(items, grid_slots(len(items))):
        cx = slot["x"] + slot["width"] // 2
        cy = slot["y"] + slot["height"] // 2 - 18
        size = min(slot["width"], slot["height"]) * 0.32
        DOODLES.get(kind, DOODLES["question"])(d, cx, cy, size)
        label_font = font(regular_path, label_size)
        if label_font.getlength(label) > slot["width"] - 28:
            label_font = font(regular_path, 26)
        d.text((slot["x"] + 14, slot["y"] + slot["height"] - LABEL_OFFSET), label, font=label_font, fill=RED)
    return img


def full_grid_slots(n: int) -> list[dict]:
    """Chia cả khung 1920x1080 thành lưới đều (cho ảnh AI vẽ sẵn bố cục lưới, không chừa tiêu đề)."""
    cols = 3 if n > 4 else (2 if n > 1 else 1)
    rows = math.ceil(n / cols)
    cw, ch = W / cols, H / rows
    return [{"x": int(c * cw), "y": int(r * ch), "width": int(cw), "height": int(ch)}
            for r, c in (divmod(i, cols) for i in range(n))]


def fit_image_to_canvas(image: Image.Image) -> Image.Image:
    """Đặt ảnh vào khung 1920x1080 nền giấy, giữ nguyên tỉ lệ (không cắt)."""
    image = image.convert("RGB")
    scale = min(W / image.width, H / image.height)
    resized = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), PAPER)
    canvas.paste(resized, ((W - resized.width) // 2, (H - resized.height) // 2))
    return canvas


def build_scene_folder(scene_dir: Path, scene_id: str, title: str, items: list, language: str,
                       image: Image.Image | None = None, speakers: list[str] | None = None) -> dict:
    """Dựng <scene>.png + <scene>.annotation.json + script.srt cho một scene.

    items = [(kind, label, subtitle)]. Cửa sổ mỗi cue là ước lượng dựa trên độ dài text;
    job thật sẽ ghi đè lại bằng độ dài giọng đọc thật (build_whiteboard_from_script).
    """
    bold_path, regular_path = locale_fonts(language)
    scene_dir = Path(scene_dir)
    scene_dir.mkdir(parents=True, exist_ok=True)
    if image is None:
        draw_scene(title, items, bold_path, regular_path).save(scene_dir / f"{scene_id}.png", "PNG")
        slots = grid_slots(len(items))
    else:  # ảnh do AI tạo: dùng nguyên ảnh, lộ dần từng ô lưới theo thứ tự câu thoại
        fit_image_to_canvas(image).save(scene_dir / f"{scene_id}.png", "PNG")
        slots = full_grid_slots(len(items))
    blocks, elements, t = [], [], 0
    for seq, ((kind, label, subtitle), slot) in enumerate(zip(items, slots), 1):
        dur = estimate_dur_ms(subtitle, language)
        if speakers and speakers[seq - 1]:  # nhiều nhân vật: dạng [Tên][start --> end]: lời để voiceover chọn giọng
            blocks.append(f"[{speakers[seq - 1]}][{fmt_time(t)} --> {fmt_time(t + dur)}]: {subtitle}\n")
        else:
            blocks.append(f"{seq}\n{fmt_time(t)} --> {fmt_time(t + dur)}\n{subtitle}\n")
        pad = 14
        region = {"x": slot["x"] + pad, "y": slot["y"] + pad,
                  "width": slot["width"] - 2 * pad, "height": slot["height"] - 2 * pad}
        elements.append({
            "id": f"{scene_id}-el{seq}",
            "label": label,
            "sequence": seq,
            "narrativeRole": subtitle,
            "subtitle": subtitle,
            "type": kind,
            "region": region,
            "reveal": {
                "direction": "top_to_bottom",
                "startMs": t,
                "durationMs": max(700, dur - 120),
                "maskPaddingPx": 18,
                "protectedRegions": [],
            },
            "handPath": {
                "start": [region["x"] + region["width"] // 2, region["y"]],
                "end": [region["x"] + region["width"] // 2, region["y"] + region["height"]],
                "easing": "easeInOut",
            },
        })
        t += dur
    (scene_dir / "script.srt").write_text("\n".join(blocks), encoding="utf-8")
    (scene_dir / f"{scene_id}.annotation.json").write_text(json.dumps({
        "sceneId": scene_id,
        "canvas": {"width": W, "height": H},
        "storyBasis": title,
        "language": language,
        "sceneDurationMs": t,
        "elements": elements,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"sceneId": scene_id, "durationMs": t, "cues": len(items)}
