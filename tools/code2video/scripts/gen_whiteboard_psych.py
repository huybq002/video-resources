"""Sinh resource whiteboard cho video tâm lý hành vi: "Cái bẫy Dopamine".

Xuất examples/whiteboard-psych/: index.html + assets/board.svg + script.srt
App Code2Video sẽ tự dựng timeline + voiceover (đa nhân vật) và render.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "examples" / "whiteboard-psych"

# (speaker, text) theo từng cảnh. Speaker: "Dẫn" | "Nam" | "Não"
SCENES = [
    ("Thức dậy", [
        ("Dẫn", "Bảy giờ sáng, Nam mở mắt. Việc đầu tiên không phải nhìn ra cửa sổ."),
        ("Nam", "Chỉ một phút thôi, lướt chút rồi dậy."),
        ("Dẫn", "Một phút đó sẽ kéo dài gần bốn mươi lăm phút."),
        ("Não", "Mở điện thoại đi, có gì đó mới đang chờ."),
        ("Dẫn", "Nam không yếu đuối. Bộ não đang làm đúng việc nó được lập trình."),
        ("Nam", "Sao mình cứ cầm lấy nó mãi thế này?"),
        ("Dẫn", "Câu trả lời bắt đầu từ một chất nhỏ trong não."),
        ("Não", "Dopamine. Nghe quen chứ?"),
        ("Dẫn", "Dopamine không phải hóa chất hạnh phúc. Nó là hóa chất của khao khát."),
        ("Dẫn", "Và khao khát mạnh hơn thỏa mãn rất nhiều lần."),
    ], ["phone", "brain"]),
    ("Vòng lặp thói quen", [
        ("Dẫn", "Mỗi thói quen đi qua bốn bước: tín hiệu, khao khát, phản ứng, phần thưởng."),
        ("Não", "Tín hiệu: màn hình sáng lên."),
        ("Não", "Khao khát: có gì mới không?"),
        ("Não", "Phản ứng: mở khóa, lướt xuống."),
        ("Não", "Phần thưởng: một video vui. Ít thôi, nhưng đủ."),
        ("Dẫn", "Càng lặp, vòng lặp càng nhanh. Đến lúc ta không còn nhận ra."),
        ("Nam", "Mình mở điện thoại lúc nào mà không nhớ nữa."),
        ("Dẫn", "Đó là lúc thói quen đã thành phản xạ."),
        ("Dẫn", "Và phản xạ thì không cần lý trí đồng ý."),
        ("Dẫn", "Mỗi lần lướt, não học được một điều: làm thế này là đúng."),
    ], ["loop", "stick", "phone"]),
    ("Phần thưởng ngẫu nhiên", [
        ("Dẫn", "Vì sao cuộn mãi không dừng? Vì phần thưởng xuất hiện ngẫu nhiên."),
        ("Dẫn", "Khi bạn không biết cái nào sẽ hay, bạn thử cái tiếp theo."),
        ("Não", "Có thể cái sau sẽ tốt hơn cái trước."),
        ("Dẫn", "Đây là cơ chế giống máy đánh bạc, nhưng không cần đồng xu."),
        ("Dẫn", "Phần thưởng bất định tạo dopamine mạnh hơn phần thưởng chắc chắn."),
        ("Não", "Chỉ thêm một cái nữa thôi, rồi mình dừng."),
        ("Dẫn", "Một cái nữa là câu nói dối não tự nói với chính nó."),
        ("Nam", "Mình biết là nên dừng, mà tay vẫn bấm."),
        ("Dẫn", "Không phải thiếu ý chí. Là bẫy được thiết kế quá khéo."),
        ("Dẫn", "Cuộn vô hạn không có điểm kết thúc. Nên não không có tín hiệu để dừng."),
    ], ["dice", "phone", "brain"]),
    ("So sánh xã hội", [
        ("Dẫn", "Rồi Nam thấy bạn học cũ đăng ảnh đẹp trên bãi biển."),
        ("Não", "Người ta sống vui thế. Còn mình thì sao?"),
        ("Dẫn", "Đây là so sánh xã hội, và nó rẻ như một lần lướt tay."),
        ("Dẫn", "Ta so phần đời thật của mình với phần đẹp nhất của người khác."),
        ("Nam", "Mình thấy mình kém cỏi hơn, dù chẳng ai so sánh cả."),
        ("Dẫn", "Không ai chấm điểm bạn trong khoảnh khắc đó. Chỉ có bạn."),
        ("Dẫn", "Não ghi lại: thua kém. Và muốn lướt thêm để tìm an ủi."),
        ("Não", "Lướt nữa đi, biết đâu thấy điều dễ chịu hơn."),
        ("Dẫn", "Vòng lặp khép kín: buồn vì lướt, lướt để hết buồn."),
        ("Dẫn", "Mỗi lần như thế, lòng tự trọng mòn đi một chút."),
    ], ["heart", "stick", "eye"]),
    ("Sợ bỏ lỡ", [
        ("Dẫn", "Con người sợ mất mát mạnh gấp đôi mong được điều gì đó."),
        ("Dẫn", "Nên ta khó bỏ lỡ, hơn là khó từ chối."),
        ("Não", "Nếu không xem, biết đâu mình bỏ lỡ chuyện quan trọng."),
        ("Dẫn", "Sợ bỏ lỡ khiến ta ở lại, dù chẳng có gì đáng xem."),
        ("Nam", "Mình cứ nghĩ nếu đặt xuống là mình sẽ tụt lại phía sau."),
        ("Dẫn", "Nhưng tụt lại so với ai? Với một dòng chảy không có đích."),
        ("Dẫn", "Thứ ta sợ mất thường không phải thời gian. Mà là cảm giác thuộc về."),
        ("Não", "Ở lại đi, đám đông vẫn đang ở đây."),
        ("Dẫn", "Và nỗi sợ ấy được nuôi bằng chính những lần lướt."),
        ("Dẫn", "Càng ở lại, ta càng tin rằng rời đi là mất."),
    ], ["crowd", "clock", "heart"]),
    ("Hiệu ứng đám đông", [
        ("Dẫn", "Khi mọi người cùng làm một việc, ta mặc định đó là việc đúng."),
        ("Dẫn", "Đó là hiệu ứng đám đông."),
        ("Não", "Ai cũng xem, ai cũng chia sẻ. Chắc nó quan trọng."),
        ("Dẫn", "Số lượt xem trở thành bằng chứng cho giá trị."),
        ("Nam", "Mình bấm vào vì thấy nó nổi, không phải vì mình cần."),
        ("Dẫn", "Ta không chọn nội dung. Ta chọn theo ánh mắt của người khác."),
        ("Dẫn", "Và thuật toán thấy điều đó. Nó đưa ta thêm những gì đám đông thích."),
        ("Não", "Đi theo số đông thì an toàn hơn."),
        ("Dẫn", "Nhưng an toàn của đám đông không phải hạnh phúc của riêng bạn."),
        ("Dẫn", "Đôi khi đông người chỉ có nghĩa là nhiều người cùng mệt mỏi."),
    ], ["crowd", "eye", "stick"]),
    ("Thiên kiến hiện tại", [
        ("Dẫn", "Con người ưu tiên phần thưởng hôm nay hơn phần thưởng ngày mai."),
        ("Dẫn", "Đó là thiên kiến hiện tại."),
        ("Não", "Một video bây giờ, hay một giờ học sau này? Bây giờ đi."),
        ("Dẫn", "Não đặt nặng hiện tại, vì tổ tiên ta chỉ cần sống qua hôm nay."),
        ("Dẫn", "Nhưng bạn sống trong một thế giới mà ngày mai có thật."),
        ("Nam", "Mình biết mình nên học. Nhưng mười phút nữa thôi đã."),
        ("Dẫn", "Mười phút nữa là cách ta vay thời gian từ chính mình."),
        ("Dẫn", "Cái giá trả sau, nhưng khoái cảm nhận ngay."),
        ("Dẫn", "Đó là lý do ta trì hoãn điều tốt và chọn điều dễ."),
        ("Dẫn", "Không phải vì ta không hiểu. Mà vì hiện tại luôn to hơn."),
    ], ["clock", "phone", "brain"]),
    ("Cái giá", [
        ("Dẫn", "Và cái giá đến, chầm chậm, không ồn ào."),
        ("Dẫn", "Sự tập trung vỡ thành nhiều mảnh nhỏ."),
        ("Não", "Mình vừa đọc gì nhỉ?"),
        ("Dẫn", "Giấc ngủ ngắn lại. Lo âu dài ra."),
        ("Nam", "Mình mệt, mà chẳng làm được gì ra hồn."),
        ("Dẫn", "Không phải lười. Là bộ não quá tải vì chuyển đổi liên tục."),
        ("Dẫn", "Mỗi lần đổi tab, một chút tập trung bị bỏ lại phía sau."),
        ("Dẫn", "Thời gian không mất một cục. Nó mất từng giọt."),
        ("Nam", "Cả ngày trôi qua, mình chẳng nhớ mình đã làm gì."),
        ("Dẫn", "Đó là dấu hiệu bạn đã sống trong vòng lặp, chứ không sống thật."),
    ], ["clock", "heart", "stick"]),
    ("Cách thoát", [
        ("Dẫn", "Nhưng vòng lặp không phải nhà tù. Nó là thói quen, và thói quen đổi được."),
        ("Dẫn", "Bước một: làm tín hiệu khó hơn. Đặt điện thoại ra khỏi phòng."),
        ("Não", "Nếu nó xa tầm tay, mình sẽ bớt mở."),
        ("Dẫn", "Bước hai: tạo khoảng dừng. Hít vào, đếm đến mười, rồi quyết định."),
        ("Dẫn", "Khoảng dừng nhỏ đủ để lý trí chen vào."),
        ("Dẫn", "Bước ba: thay phần thưởng. Đi bộ, viết, nói chuyện thật."),
        ("Nam", "Mình thay bằng một trang sách mỗi sáng."),
        ("Não", "Phần thưởng mới. Yếu hơn, nhưng không làm mình kiệt sức."),
        ("Dẫn", "Bước bốn: tha thứ cho lần tái phạm. Tự trách chỉ làm vòng lặp mạnh hơn."),
        ("Dẫn", "Bạn không cần hoàn hảo. Bạn cần quay lại nhanh hơn."),
    ], ["check", "arrow", "heart"]),
    ("Kết", [
        ("Dẫn", "Sáng hôm sau, Nam mở mắt. Điện thoại vẫn ở trên bàn."),
        ("Nam", "Mình sẽ ra ngoài trước đã."),
        ("Dẫn", "Một phút lưỡng lự. Rồi Nam đứng dậy."),
        ("Dẫn", "Không có tiếng nhạc hùng tráng. Chỉ là một lựa chọn nhỏ."),
        ("Dẫn", "Nhưng tự do không đến từ một lần thay đổi lớn."),
        ("Dẫn", "Nó đến từ những lần bạn chọn hiện tại thay vì trì hoãn."),
        ("Não", "Mở điện thoại đi. Chỉ một phút thôi."),
        ("Nam", "Không phải hôm nay."),
        ("Dẫn", "Và đó, là cách con người bắt đầu làm chủ bộ não của mình."),
        ("Dẫn", "Cảm ơn bạn đã ở lại đến câu chuyện cuối cùng."),
    ], ["brain", "check"]),
]

GAP_MS = 350  # khoảng lặng giữa câu


def _dur_ms(text: str) -> int:
    seconds = min(7.0, max(4.0, len(text) * 0.06 + 1.3))
    return round(seconds * 1000)


def fmt_time(ms: int) -> str:
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, msr = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{msr:03d}"


# ---- doodle SVG (line-art whiteboard; pathLength=1 để vẽ bằng stroke-dashoffset) ----
def svg(inner: str) -> str:
    return f"<svg viewBox='0 0 200 200' preserveAspectRatio='xMidYMid meet'>{inner}</svg>"


DOODLES = {
    "brain": svg(
        "<path class='draw' pathLength='1' d='M62 58 C32 58 26 98 46 114 C36 140 62 162 88 150 "
        "C104 172 140 166 150 144 C182 150 190 112 168 98 C188 78 170 48 144 54 C134 28 92 28 82 50 "
        "C72 44 64 50 62 58 Z'/>"
        "<path class='draw ink-red' pathLength='1' d='M82 70 C70 84 78 104 92 108'/>"
        "<path class='draw ink-red' pathLength='1' d='M120 66 C132 80 124 104 110 110'/>"
        "<path class='draw ink-blue' pathLength='1' d='M100 56 L100 148'/>"
    ),
    "phone": svg(
        "<rect class='draw' pathLength='1' x='66' y='26' width='68' height='148' rx='14'/>"
        "<path class='draw' pathLength='1' d='M84 52 L116 52'/>"
        "<path class='draw ink-red' pathLength='1' d='M84 80 C96 74 108 92 100 104 C92 116 78 104 84 86'/>"
        "<path class='draw' pathLength='1' d='M84 140 L116 140'/>"
    ),
    "loop": svg(
        "<path class='draw' pathLength='1' d='M100 34 A66 66 0 0 1 166 100'/>"
        "<path class='draw' pathLength='1' d='M158 84 L166 100 L150 104'/>"
        "<path class='draw' pathLength='1' d='M166 100 A66 66 0 0 1 100 166'/>"
        "<path class='draw' pathLength='1' d='M116 158 L100 166 L96 150'/>"
        "<path class='draw' pathLength='1' d='M100 166 A66 66 0 0 1 34 100'/>"
        "<path class='draw' pathLength='1' d='M42 116 L34 100 L50 96'/>"
        "<path class='draw' pathLength='1' d='M34 100 A66 66 0 0 1 100 34'/>"
        "<path class='draw' pathLength='1' d='M84 42 L100 34 L104 50'/>"
    ),
    "stick": svg(
        "<circle class='draw' pathLength='1' cx='100' cy='52' r='26'/>"
        "<path class='draw' pathLength='1' d='M100 78 L100 140'/>"
        "<path class='draw' pathLength='1' d='M100 96 L66 118'/>"
        "<path class='draw' pathLength='1' d='M100 96 L134 118'/>"
        "<path class='draw' pathLength='1' d='M100 140 L74 184'/>"
        "<path class='draw' pathLength='1' d='M100 140 L126 184'/>"
    ),
    "heart": svg(
        "<path class='draw ink-red' pathLength='1' d='M100 168 C40 126 34 78 66 62 "
        "C86 52 98 66 100 80 C102 66 114 52 134 62 C166 78 160 126 100 168 Z'/>"
    ),
    "clock": svg(
        "<circle class='draw' pathLength='1' cx='100' cy='100' r='66'/>"
        "<path class='draw' pathLength='1' d='M100 100 L100 56'/>"
        "<path class='draw ink-red' pathLength='1' d='M100 100 L132 118'/>"
        "<path class='draw' pathLength='1' d='M100 34 L100 42 M100 158 L100 166 M34 100 L42 100 M158 100 L166 100'/>"
    ),
    "crowd": svg(
        "<circle class='draw' pathLength='1' cx='60' cy='70' r='20'/><path class='draw' pathLength='1' d='M60 92 L60 140'/>"
        "<circle class='draw' pathLength='1' cx='100' cy='60' r='22'/><path class='draw' pathLength='1' d='M100 84 L100 138'/>"
        "<circle class='draw' pathLength='1' cx='140' cy='72' r='20'/><path class='draw' pathLength='1' d='M140 94 L140 142'/>"
    ),
    "eye": svg(
        "<path class='draw' pathLength='1' d='M28 100 C60 60 140 60 172 100 C140 140 60 140 28 100 Z'/>"
        "<circle class='draw ink-blue' pathLength='1' cx='100' cy='100' r='24'/>"
        "<circle class='draw ink-red' pathLength='1' cx='100' cy='100' r='9'/>"
    ),
    "dice": svg(
        "<rect class='draw' pathLength='1' x='48' y='48' width='104' height='104' rx='14'/>"
        "<circle class='draw ink-red' pathLength='1' cx='78' cy='78' r='7'/>"
        "<circle class='draw ink-red' pathLength='1' cx='122' cy='78' r='7'/>"
        "<circle class='draw ink-red' pathLength='1' cx='100' cy='100' r='7'/>"
        "<circle class='draw ink-red' pathLength='1' cx='78' cy='122' r='7'/>"
        "<circle class='draw ink-red' pathLength='1' cx='122' cy='122' r='7'/>"
    ),
    "check": svg(
        "<circle class='draw ink-blue' pathLength='1' cx='100' cy='100' r='66'/>"
        "<path class='draw ink-blue' pathLength='1' d='M68 102 L90 126 L134 74'/>"
    ),
    "arrow": svg(
        "<path class='draw' pathLength='1' d='M34 150 C70 150 70 70 166 70'/>"
        "<path class='draw' pathLength='1' d='M146 52 L166 70 L146 88'/>"
    ),
}

SLOTS = [
    {"left": "7%", "top": "9%", "width": "21%"},
    {"left": "72%", "top": "8%", "width": "21%"},
    {"left": "6%", "top": "46%", "width": "20%"},
    {"left": "73%", "top": "45%", "width": "20%"},
]

CSS = """
*{box-sizing:border-box}
html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#f7f4ea}
#root{position:relative;width:1920px;height:1080px;overflow:hidden;
  background:radial-gradient(1200px 700px at 50% 0%,#fffdf7,#f3efe2);}
.board-grid{position:absolute;inset:0;z-index:0;opacity:.5;
  background-image:linear-gradient(rgba(38,49,46,.05) 1px,transparent 1px),
    linear-gradient(90deg,rgba(38,49,46,.05) 1px,transparent 1px);background-size:64px 64px}
.scene{position:absolute;inset:0}
.doodle{position:absolute;z-index:2}
.doodle svg{width:100%;height:auto;display:block}
.doodle .draw{fill:none;stroke:#26312e;stroke-width:5;stroke-linecap:round;stroke-linejoin:round;
  stroke-dasharray:1;stroke-dashoffset:1}
.doodle .ink-red{stroke:#c45136}
.doodle .ink-blue{stroke:#3a6ea5}
.title{position:absolute;left:8%;top:6%;z-index:3;font-family:"Patrick Hand",cursive;
  font-size:64px;color:#26312e;border-bottom:6px solid #c45136;padding-bottom:6px;opacity:0}
.cap{position:absolute;left:12%;right:12%;bottom:7%;z-index:5;text-align:center}
.cap span{display:inline-block;max-width:1500px;background:#fffdf7;border:4px dashed #26312e;
  border-radius:18px;color:#26312e;font-family:"Patrick Hand",cursive;
  font-size:54px;line-height:1.28;padding:16px 30px;box-shadow:0 8px 0 rgba(38,49,46,.08);opacity:0}
.cap .who{display:block;margin-top:6px;font:600 26px "IBM Plex Mono",monospace;letter-spacing:.1em;
  color:#c45136;text-transform:uppercase;opacity:0}
"""


def build():
    cues = []
    t = 0
    for sidx, (title, lines, _) in enumerate(SCENES, 1):
        for speaker, text in lines:
            dur = _dur_ms(text)
            cues.append({"scene": sidx, "title": title, "speaker": speaker, "text": text, "start": t, "dur": dur})
            t += dur + GAP_MS
    total_ms = t

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    (OUT / "assets" / "board.svg").write_text(
        "<svg xmlns='http://www.w3.org/2000/svg' width='1920' height='1080'><rect width='1920' height='1080' fill='#f7f4ea'/></svg>",
        encoding="utf-8",
    )

    # script.srt (multi-speaker)
    blocks = []
    for cue in cues:
        blocks.append(f"[{cue['speaker']}][{fmt_time(cue['start'])} --> {fmt_time(cue['start'] + cue['dur'])}]: {cue['text']}")
    (OUT / "script.srt").write_text("\n\n".join(blocks) + "\n", encoding="utf-8")

    # scene spans
    scene_spans = {}
    for cue in cues:
        s = scene_spans.setdefault(cue["scene"], {"start": cue["start"], "end": cue["start"] + cue["dur"]})
        s["end"] = max(s["end"], cue["start"] + cue["dur"])

    # HTML: scene clips (doodles + captions), absolute times
    scene_html = []
    gsap = ["const tl = gsap.timeline({ paused: true });"]
    for sidx, (title, lines, doodle_kinds) in enumerate(SCENES, 1):
        span = scene_spans[sidx]
        s_s = span["start"] / 1000
        s_d = (span["end"] - span["start"]) / 1000
        parts = [f"<div id='sc{sidx}' class='clip scene' data-start='{s_s:.3f}' data-duration='{s_d:.3f}'>",
                 "<div class='board-grid'></div>",
                 f"<div id='title{sidx}' class='title'>{title}</div>"]
        # doodles distributed across the scene
        n = len(doodle_kinds)
        doodle_times = []
        for k, kind in enumerate(doodle_kinds):
            slot = SLOTS[(sidx + k) % len(SLOTS)]
            did = f"d{sidx}-{k}"
            parts.append(
                f"<div id='{did}' class='doodle' style='left:{slot['left']};top:{slot['top']};width:{slot['width']}'>{DOODLES[kind]}</div>"
            )
            frac = 0.12 + (k / max(1, n)) * 0.7
            doodle_times.append((did, s_s + frac * s_d))
        # captions
        scene_cues = [c for c in cues if c["scene"] == sidx]
        for ci, cue in enumerate(scene_cues):
            cid = f"cap{cue['start']}"
            parts.append(
                f"<div id='{cid}' class='clip cap' data-start='{cue['start']/1000:.3f}' data-duration='{cue['dur']/1000:.3f}'>"
                f"<span>{cue['text']}</span><em class='who'>{cue['speaker']}</em></div>"
            )
            gsap.append(
                f"tl.fromTo('#{cid} span', {{opacity:0,y:16}}, {{opacity:1,y:0,duration:0.3,ease:'power2.out'}}, {cue['start']/1000:.3f});"
                f"tl.fromTo('#{cid} .who', {{opacity:0}}, {{opacity:1,duration:0.3}}, {cue['start']/1000 + 0.1:.3f});"
            )
        parts.append("</div>")
        scene_html.append("".join(parts))
        # title + doodle draw animations
        gsap.append(f"tl.fromTo('#title{sidx}', {{opacity:0,y:-10}}, {{opacity:1,y:0,duration:0.4}}, {s_s:.3f});")
        for did, at in doodle_times:
            gsap.append(
                f"tl.fromTo('#{did} .draw', {{strokeDashoffset:1}}, "
                f"{{strokeDashoffset:0,duration:1.0,stagger:0.06,ease:'power1.out'}}, {at:.3f});"
            )
    gsap.append("window.__timelines = window.__timelines || {};")
    gsap.append("window.__timelines['whiteboard_psych'] = tl;")

    html = (
        "<!doctype html><html lang='vi'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=1920, height=1080'>"
        "<title>Dopamine — whiteboard</title>"
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link href='https://fonts.googleapis.com/css2?family=Patrick+Hand&family=IBM+Plex+Mono:wght@500;600&display=swap' rel='stylesheet'>"
        "<script src='https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js'></script>"
        f"<style>{CSS}</style></head><body>"
        f"<div id='root' data-composition-id='whiteboard_psych' data-width='1920' data-height='1080' "
        f"data-start='0' data-duration='{total_ms/1000:.3f}'>"
        + "".join(scene_html) +
        f"<script>{''.join(gsap)}</script></div></body></html>"
    )
    (OUT / "index.html").write_text(html, encoding="utf-8")

    return {
        "out": str(OUT),
        "durationMs": total_ms,
        "durationMin": round(total_ms / 60000, 2),
        "cues": len(cues),
        "scenes": len(SCENES),
        "speakers": sorted({c["speaker"] for c in cues}),
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
