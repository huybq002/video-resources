"""Sinh tài nguyên whiteboard engine cho "Vụ án phòng kín bất khả thi".

Xuất examples/whiteboard-mystery/scene-0N/: <scene>.png + <scene>.annotation.json + script.srt
Mỗi phần tử (item) = 1 cue thoại + 1 hình vẽ + 1 region annotation.
Thư viện doodle nằm ở code2video.whiteboard_assets (dùng chung với Studio AI).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from code2video.whiteboard_assets import draw_scene, fmt_time, grid_slots, locale_fonts

OUT = Path(__file__).resolve().parents[1] / "examples" / "whiteboard-mystery"
W, H = 1920, 1080
INK = (38, 49, 46)
RED = (196, 81, 54)

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


def dur_ms(text: str) -> int:
    return round(min(9.0, max(5.0, len(text) * 0.08 + 1.5)) * 1000)


def build() -> dict:
    summary = []
    OUT.mkdir(parents=True, exist_ok=True)
    for s_idx, (title, items) in enumerate(SCENES, 1):
        sid = f"scene-{s_idx:02d}"
        scene_dir = OUT / sid
        scene_dir.mkdir(parents=True, exist_ok=True)
        draw_scene(title, items, *locale_fonts("vi"), label_size=36).save(scene_dir / f"{sid}.png", "PNG")

        slots = grid_slots(len(items))
        blocks, elements, t = [], [], 0
        for seq, ((kind, label, subtitle), slot) in enumerate(zip(items, slots), 1):
            dur = dur_ms(subtitle)
            blocks.append(f"{seq}\n{fmt_time(t)} --> {fmt_time(t + dur)}\n{subtitle}\n")
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
