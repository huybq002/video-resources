"""Vẽ ảnh tay cầm bút (PNG trong suốt) cho whiteboard engine.

Engine neo "đầu bút" ở góc trên-trái (anchor 0,0) của ảnh đã cắt nền,
nên đầu bút phải nằm đúng pixel (0,0). Xuất: assets/whiteboard-hand.png
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "assets"
SIZE = 820
SKIN = (232, 180, 140, 255)
SKIN_LINE = (150, 105, 70, 255)
BODY = (46, 46, 50, 255)
BODY_LIGHT = (232, 232, 232, 255)
TIP = (196, 81, 54, 255)
CAP = (28, 28, 30, 255)


def main() -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ang = math.radians(45)
    fwd = (math.cos(ang), math.sin(ang))
    side = (-fwd[1], fwd[0])

    def pt(t: float, s: float) -> tuple[float, float]:
        return (fwd[0] * t + side[0] * s, fwd[1] * t + side[1] * s)

    s0, s1, hw = 70.0, 460.0, 34.0
    # thân bút
    d.polygon([pt(s0, hw), pt(s1, hw), pt(s1, -hw), pt(s0, -hw)], fill=BODY)
    # nắp đuôi
    d.polygon([pt(s1, hw * 0.8), pt(s1 + 42, hw * 0.8), pt(s1 + 42, -hw * 0.8), pt(s1, -hw * 0.8)], fill=CAP)
    # dải sáng
    d.polygon([pt(s0 + 46, hw), pt(s0 + 96, hw), pt(s0 + 96, -hw), pt(s0 + 46, -hw)], fill=BODY_LIGHT)
    # đầu bút (nón) từ gốc (0,0)
    d.polygon([(0, 0), pt(s0, hw), pt(s0, -hw)], fill=TIP)

    # bàn tay: lòng bàn tay + các ngón quấn quanh thân bút
    cx, cy = pt(230, 0)
    d.ellipse([cx - 120, cy - 108, cx + 120, cy + 108], fill=SKIN, outline=SKIN_LINE, width=6)
    for t in (160, 225, 290, 350):
        fx, fy = pt(t, 0)
        d.ellipse([fx - 42, fy - 30, fx + 42, fy + 30], fill=SKIN, outline=SKIN_LINE, width=5)
    # ngón cái
    tx, ty = pt(150, 96)
    d.ellipse([tx - 40, ty - 26, tx + 40, ty + 26], fill=SKIN, outline=SKIN_LINE, width=5)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "whiteboard-hand.png"
    img.save(path, "PNG")
    print(path)


if __name__ == "__main__":
    main()
