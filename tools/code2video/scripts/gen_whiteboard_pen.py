"""Vẽ ảnh cây bút (PNG trong suốt, không có bàn tay) cho whiteboard engine.

Engine neo "đầu bút" ở góc trên-trái (anchor 0,0) của ảnh đã cắt nền,
nên mũi bút phải nằm đúng pixel (0,0). Xuất: assets/whiteboard-pen.png
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "assets"
SIZE = 600
SS = 4
BODY = (46, 46, 50, 255)
BODY_LIGHT = (226, 226, 228, 255)
GRIP = (74, 74, 80, 255)
CAP = (26, 26, 29, 255)
TIP = (196, 81, 54, 255)
TIP_DARK = (132, 47, 31, 255)

HW = 22.0
CONE = 74.0
GRIP_END = 188.0
BODY_END = 566.0
CAP_END = 608.0


def main() -> None:
    img = Image.new("RGBA", (SIZE * SS, SIZE * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ang = math.radians(45)
    fwd = (math.cos(ang), math.sin(ang))
    side = (-fwd[1], fwd[0])

    def draw_pen(dx: float, dy: float, colors: tuple) -> None:
        body, light, grip, cap, tip, tip_dark = colors

        def p(t: float, s: float) -> tuple[float, float]:
            return ((fwd[0] * t + side[0] * s + dx) * SS,
                    (fwd[1] * t + side[1] * s + dy) * SS)

        def poly(points, fill) -> None:
            d.polygon([p(t, s) for t, s in points], fill=fill)

        poly([(0, 0), (CONE, HW), (CONE, -HW)], tip)
        poly([(0, 0), (15, 5), (15, -5)], tip_dark)
        poly([(CONE, HW), (GRIP_END, HW), (GRIP_END, -HW), (CONE, -HW)], grip)
        for t in (104, 128, 152, 176):
            poly([(t, HW), (t + 6, HW), (t + 6, -HW), (t, -HW)], body)
        poly([(GRIP_END, HW), (BODY_END, HW), (BODY_END, -HW), (GRIP_END, -HW)], body)
        poly([(GRIP_END, HW * 0.78), (BODY_END - 26, HW * 0.78),
              (BODY_END - 26, HW * 0.34), (GRIP_END, HW * 0.34)], light)
        poly([(BODY_END, HW), (CAP_END, HW), (CAP_END, -HW), (BODY_END, -HW)], cap)
        poly([(BODY_END - 150, HW), (BODY_END - 46, HW),
              (BODY_END - 46, HW + 7), (BODY_END - 150, HW + 7)], cap)

    draw_pen(0, 0, (BODY, BODY_LIGHT, GRIP, CAP, TIP, TIP_DARK))

    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "whiteboard-pen.png"
    img.save(path, "PNG")
    print(path)


if __name__ == "__main__":
    main()
