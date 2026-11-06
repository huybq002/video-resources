"""Sinh resource cho engine Whiteboard (srt-whiteboard-animation).

Mỗi scene = PNG (1920x1080, nét vẽ bảng trắng) + <scene>.annotation.json + script.srt.
Chủ đề: "Vì sao ta trì hoãn?" — 2 cảnh, 3 phần tử/cảnh, ~12s/cảnh.

Chạy: python scripts/gen_whiteboard_engine.py
Xuất: examples/whiteboard-engine/scene-0N/
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "examples" / "whiteboard-engine"
W, H = 1920, 1080
INK = (38, 49, 46)
RED = (196, 81, 54)
BLUE = (58, 110, 165)
PAPER = (247, 244, 234)
GRID = (232, 228, 216)

FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
FONT_REG = "C:/Windows/Fonts/segoeui.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def f_title(s: int) -> ImageFont.FreeTypeFont:
    return font(FONT_BOLD, s)


def f_label(s: int) -> ImageFont.FreeTypeFont:
    return font(FONT_REG, s)


def draw_grid(d: ImageDraw.ImageDraw) -> None:
    for x in range(0, W, 64):
        d.line([(x, 0), (x, H)], fill=GRID, width=1)
    for y in range(0, H, 64):
        d.line([(0, y), (W, y)], fill=GRID, width=1)


# ---- doodles (vẽ trong region) ----
def doodle_clock(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int) -> None:
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=INK, width=6)
    d.line([(cx, cy), (cx, cy - r * 0.6)], fill=INK, width=6)
    d.line([(cx, cy), (cx + r * 0.45, cy + r * 0.3)], fill=RED, width=6)
    for ang_pt in [(-r, 0), (r, 0), (0, -r), (0, r)]:
        d.line([(cx + ang_pt[0] * 0.86, cy + ang_pt[1] * 0.86),
                (cx + ang_pt[0] * 0.94, cy + ang_pt[1] * 0.94)], fill=INK, width=4)


def doodle_phone(d: ImageDraw.ImageDraw, cx: int, cy: int, w: int, h: int) -> None:
    d.rounded_rectangle([cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2], radius=28, outline=INK, width=6)
    d.line([(cx - w // 4, cy - h // 2 + 40), (cx + w // 4, cy - h // 2 + 40)], fill=INK, width=5)
    d.line([(cx - w // 4, cy + h // 2 - 34), (cx + w // 4, cy + h // 2 - 34)], fill=INK, width=5)
    # tiny heart on screen
    d.arc([cx - 40, cy - 30, cx + 10, cy + 20], 200, 340, fill=RED, width=5)
    d.arc([cx - 10, cy - 30, cx + 40, cy + 20], 200, 340, fill=RED, width=5)


def doodle_worry(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int) -> None:
    # đám mây lo lắng = chuỗi cung
    d.arc([cx - r, cy - r * 0.7, cx, cy + r * 0.3], 180, 330, fill=INK, width=6)
    d.arc([cx - r // 2, cy - r, cx + r // 2, cy], 200, 360, fill=INK, width=6)
    d.arc([cx, cy - r * 0.7, cx + r, cy + r * 0.3], 210, 360, fill=INK, width=6)
    qf = f_title(120)
    d.text((cx - 20, cy - 40), "?", font=qf, fill=RED)


def doodle_checklist(d: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
    d.rounded_rectangle([x, y, x + w, y + h], radius=18, outline=INK, width=6)
    for i in range(3):
        yy = y + 60 + i * 90
        d.rectangle([x + 40, yy - 22, x + 84, yy + 22], outline=INK, width=4)
        d.line([(x + 44, yy - 2), (x + 60, yy + 16), (x + 82, yy - 18)], fill=BLUE, width=6)
        d.line([(x + 110, yy), (x + w - 40, yy)], fill=INK, width=5)


def doodle_timer(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int) -> None:
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=INK, width=6)
    d.line([(cx, cy), (cx + r * 0.4, cy - r * 0.4)], fill=RED, width=6)
    tf = f_title(int(r * 0.9))
    d.text((cx - r * 0.28, cy - r * 0.1), "2'", font=tf, fill=INK)


def doodle_heart(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int) -> None:
    d.arc([cx - r, cy - r, cx, cy], 180, 360, fill=RED, width=7)
    d.arc([cx, cy - r, cx + r, cy], 180, 360, fill=RED, width=7)
    d.line([(cx - r + 3, cy - r // 2), (cx, cy + r)], fill=RED, width=7)
    d.line([(cx + r - 3, cy - r // 2), (cx, cy + r)], fill=RED, width=7)
    d.arc([cx - r, cy + r * 0.2, cx + r, cy + r * 1.4], 200, 340, fill=INK, width=6)  # smile


SCENES = [
    {
        "id": "scene-01",
        "title": "Cái bẫy trì hoãn",
        "lines": [
            ("Hạn chót đến gần, và ta bắt đầu thấy nặng.", "clock"),
            ("Thay vì bắt đầu, ta mở điện thoại để trốn cảm giác đó.", "phone"),
            ("Càng trốn, nỗi lo càng lớn. Đó là cái bẫy trì hoãn.", "worry"),
        ],
    },
    {
        "id": "scene-02",
        "title": "Cách thoát",
        "lines": [
            ("Chia việc lớn thành từng bước nhỏ, đủ nhỏ để không còn sợ.", "check"),
            ("Chỉ cần bắt đầu trong hai phút. Phần còn lại thường tự chảy.", "timer"),
            ("Và tha thứ cho lần trượt. Tự trách chỉ khiến ta trốn lâu hơn.", "heart"),
        ],
    },
]

REGIONS = [
    {"x": 150, "y": 230, "width": 440, "height": 560},
    {"x": 740, "y": 210, "width": 440, "height": 600},
    {"x": 1330, "y": 230, "width": 440, "height": 560},
]

CUE_MS = 4000
REVEAL_MS = 1400


def fmt_time(ms: int) -> str:
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, msr = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{msr:03d}"


def draw_scene(scene: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    draw_grid(d)
    d.text((120, 90), scene["title"], font=f_title(72), fill=INK)
    d.line([(120, 190), (120 + int(f_title(72).getlength(scene["title"])), 190)], fill=RED, width=8)

    for line, region, kind in zip(scene["lines"], REGIONS, [l[1] for l in scene["lines"]]):
        text, _ = line
        cx = region["x"] + region["width"] // 2
        cy = region["y"] + region["height"] // 2
        if kind == "clock":
            doodle_clock(d, cx, cy, 150)
        elif kind == "phone":
            doodle_phone(d, cx, cy, 220, 420)
        elif kind == "worry":
            doodle_worry(d, cx, cy, 160)
        elif kind == "check":
            doodle_checklist(d, region["x"] + 30, region["y"] + 60, 380, 440)
        elif kind == "timer":
            doodle_timer(d, cx, cy, 150)
        elif kind == "heart":
            doodle_heart(d, cx, cy, 150)
        # label dưới region
        d.text((region["x"] + 10, region["y"] + region["height"] - 10),
               {"clock": "Đồng hồ", "phone": "Điện thoại", "worry": "Lo lắng",
                "check": "Chia nhỏ", "timer": "Bắt đầu 2 phút", "heart": "Tha thứ"}[kind],
               font=f_label(44), fill=RED)
    return img


def build_scene(scene: dict) -> dict:
    scene_dir = OUT / scene["id"]
    scene_dir.mkdir(parents=True, exist_ok=True)

    img = draw_scene(scene)
    png_path = scene_dir / f"{scene['id']}.png"
    img.save(png_path, "PNG")

    blocks, elements = [], []
    t = 0
    for seq, ((text, kind), region) in enumerate(zip(scene["lines"], REGIONS), 1):
        start = t
        end = start + CUE_MS
        blocks.append(f"{seq}\n{fmt_time(start)} --> {fmt_time(end)}\n{text}\n")
        cx = region["x"] + region["width"] // 2
        elements.append({
            "id": f"{scene['id']}-el{seq}",
            "label": {"clock": "Đồng hồ", "phone": "Điện thoại", "worry": "Lo lắng",
                      "check": "Chia nhỏ", "timer": "Bắt đầu 2 phút", "heart": "Tha thứ"}[kind],
            "sequence": seq,
            "narrativeRole": text,
            "subtitle": text,
            "type": {"clock": "concept", "phone": "action", "worry": "concept",
                     "check": "action", "timer": "action", "heart": "result"}[kind],
            "region": region,
            "reveal": {
                "direction": "top_to_bottom",
                "startMs": start + 200,
                "durationMs": REVEAL_MS,
                "maskPaddingPx": 24,
                "protectedRegions": [],
            },
            "handPath": {
                "start": [cx, region["y"]],
                "end": [cx, region["y"] + region["height"]],
                "easing": "easeInOut",
            },
        })
        t = end

    (scene_dir / "script.srt").write_text("\n".join(blocks), encoding="utf-8")
    annotation = {
        "sceneId": scene["id"],
        "canvas": {"width": W, "height": H},
        "storyBasis": scene["title"],
        "sceneDurationMs": t,
        "elements": elements,
    }
    (scene_dir / f"{scene['id']}.annotation.json").write_text(
        json.dumps(annotation, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"scene": scene["id"], "png": str(png_path), "durationMs": t, "elements": len(elements)}


def main() -> None:
    results = [build_scene(scene) for scene in SCENES]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
