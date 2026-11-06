"""Sinh tài nguyên whiteboard engine cho "Vụ án phòng kín bất khả thi".

Xuất examples/whiteboard-mystery/scene-0N/: <scene>.png + <scene>.annotation.json + script.srt
Mỗi phần tử (item) = 1 cue thoại + 1 hình vẽ + 1 region annotation.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "examples" / "whiteboard-mystery"
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
    # ổ khóa đỏ
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

SCENES = [
    ("Mở đầu — Hook", [
        ("mansion", "Tầng 10", "Một căn phòng khách sạn sang trọng, nằm ở tầng 10."),
        ("door", "Cửa khóa trái", "Cửa ra vào khóa trái từ bên trong bằng chốt sắt kiên cố."),
        ("window", "Cửa sổ nguyên vẹn", "Cửa sổ hoàn toàn nguyên vẹn, bị kẹt cứng và không có ban công."),
        ("body", "Nạn nhân", "Khi cảnh sát phá cửa vào, nạn nhân đã tử vong."),
        ("question", "Hung thủ?", "Không có bóng dáng hung thủ hay bất kỳ lối thoát nào."),
        ("question", "Phòng kín", "Làm sao kẻ sát nhân biến mất khỏi một phòng kín tuyệt đối?"),
    ]),
    ("Hiện trường & Sơ đồ", [
        ("floorplan", "Phòng 1004", "Đó là vụ án tại phòng 1004."),
        ("body", "Ông David", "Nạn nhân là ông David, một nhà sưu tầm đồ cổ."),
        ("clock", "21:00", "Vào lúc 21 giờ tối, tiếng hét vang lên."),
        ("door", "Chốt sắt", "Người quản gia phá cửa, nhưng chốt sắt bên trong đã sập."),
        ("key", "Chìa trong ổ", "Thứ nhất: chìa khóa vẫn nằm ở ổ khóa bên trong phòng."),
        ("window", "Bụi dày", "Thứ hai: mọi cửa sổ đóng kín từ bên trong, bụi dày nhiều ngày."),
        ("closet", "Không chỗ trốn", "Thứ ba: gầm giường trống, tủ quá nhỏ để trốn."),
        ("question", "Bế tắc", "Cảnh sát bế tắc và gọi đây là một vụ tự sát."),
        ("question", "Chi tiết thứ tư", "Cho đến khi họ phát hiện ra chi tiết thứ tư."),
    ]),
    ("Giả thuyết & Nút thắt", [
        ("detective", "Thám tử", "Ban đầu, người ta nghĩ đến mẹo dùng sợi chỉ."),
        ("string", "Sợi chỉ", "Một sợi chỉ hoặc dây cước để sập chốt từ bên ngoài."),
        ("door", "Chốt nặng", "Nhưng với loại chốt nặng này, không sợi chỉ nào đủ lực."),
        ("arrow", "Vết xước", "Thực nghiệm cho thấy không thể sập chốt mà không để lại vết xước."),
        ("floorplan", "Mật đạo?", "Giả thuyết hai: có đường mật đạo bí mật dưới sàn nhà?"),
        ("concrete", "Bê tông đặc", "Đội kỹ thuật lật từng tấm ván: bê tông cốt thép đặc nguyên khối."),
        ("question", "Ngõ cụt", "Vụ án rơi vào ngõ cụt."),
        ("ghost", "Siêu nhiên?", "Mọi người bắt đầu tin rằng có thế lực siêu nhiên nhúng tay."),
    ]),
    ("Cú twist & Lời giải", [
        ("detective", "Không tin ma quỷ", "Nhưng thám tử chính trực không tin vào ma quỷ."),
        ("water", "Vũng nước", "Anh ta nhìn kỹ chốt cửa và vũng nước nhỏ dưới sàn phòng tắm."),
        ("ice", "Chêm băng", "Thủ thuật chính là một chiếc chêm bằng băng đá lớn."),
        ("ice", "Giữ chốt mở", "Khối băng giữ chốt ở trạng thái mở trong vài phút ngắn ngủi."),
        ("string", "Rút dây", "Hung thủ rút sợi dây mảnh kéo khối băng ra ngoài, hoặc để nó tan."),
        ("water", "Tan thành nước", "Khi băng tan hết, chiếc chốt tự sập xuống do trọng lực."),
        ("door", "Phòng kín hoàn hảo", "Căn phòng trở thành một phòng kín bất khả thi hoàn hảo."),
    ]),
    ("Kết luận & CTA", [
        ("zoom", "Sơ đồ hoàn chỉnh", "Một thủ đoạn tinh vi dựa vào vật lý và sự đánh lừa thị giác."),
        ("question", "Chưa lời giải", "Tội phạm hoàn hảo không có thật, chỉ có chi tiết chưa tìm ra lời giải."),
        ("like", "Like", "Bạn có ấn tượng với cú twist này không? Hãy để lại bình luận."),
        ("bell", "Đăng ký + chuông", "Bấm đăng ký kênh để không bỏ lỡ vụ án tiếp theo."),
        ("wave", "Hẹn gặp lại", "Xin chào và hẹn gặp lại!"),
    ]),
]


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


def dur_ms(text: str) -> int:
    return round(min(9.0, max(5.0, len(text) * 0.08 + 1.5)) * 1000)


def fmt(ms: int) -> str:
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, msr = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{msr:03d}"


def draw_scene(title: str, items: list) -> Image.Image:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    for x in range(0, W, 64):
        d.line([(x, 0), (x, H)], fill=GRID, width=1)
    for y in range(0, H, 64):
        d.line([(0, y), (W, y)], fill=GRID, width=1)
    d.text((110, 90), title, font=font(FONT_BOLD, 64), fill=INK)
    d.line([(110, 190), (110 + int(font(FONT_BOLD, 64).getlength(title)), 190)], fill=RED, width=8)
    slots = grid_slots(len(items))
    for (kind, label, _), slot in zip(items, slots):
        cx = slot["x"] + slot["width"] // 2
        cy = slot["y"] + slot["height"] // 2 - 18
        size = min(slot["width"], slot["height"]) * 0.32
        DOODLES.get(kind, d_question)(d, cx, cy, size)
        d.text((slot["x"] + 14, slot["y"] + slot["height"] - 44), label, font=font(FONT_REG, 36), fill=RED)
    return img


def build() -> dict:
    summary = []
    OUT.mkdir(parents=True, exist_ok=True)
    for s_idx, (title, items) in enumerate(SCENES, 1):
        sid = f"scene-{s_idx:02d}"
        scene_dir = OUT / sid
        scene_dir.mkdir(parents=True, exist_ok=True)
        draw_scene(title, items).save(scene_dir / f"{sid}.png", "PNG")

        slots = grid_slots(len(items))
        blocks, elements, t = [], [], 0
        for seq, ((kind, label, subtitle), slot) in enumerate(zip(items, slots), 1):
            dur = dur_ms(subtitle)
            blocks.append(f"{seq}\n{fmt(t)} --> {fmt(t + dur)}\n{subtitle}\n")
            pad = 14
            region = {"x": slot["x"] + pad, "y": slot["y"] + pad,
                      "width": slot["width"] - 2 * pad, "height": slot["height"] - 2 * pad}
            elements.append({
                "id": f"{sid}-el{seq}",
                "label": label,
                "sequence": seq,
                "narrativeRole": subtitle,
                "subtitle": subtitle,
                "type": kind,
                "region": region,
                "reveal": {
                    "direction": "top_to_bottom",
                    "startMs": t + 100,
                    "durationMs": min(1400, max(800, round(dur * 0.3))),
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
        (scene_dir / f"{sid}.annotation.json").write_text(json.dumps({
            "sceneId": sid,
            "canvas": {"width": W, "height": H},
            "storyBasis": title,
            "sceneDurationMs": t,
            "elements": elements,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        summary.append({"scene": sid, "title": title, "durationMs": t, "cues": len(items)})
    return {"totalMs": sum(s["durationMs"] for s in summary), "scenes": summary}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
