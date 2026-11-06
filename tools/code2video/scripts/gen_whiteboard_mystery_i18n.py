"""Sinh tài nguyên whiteboard engine cho "Vụ án phòng kín" bằng tiếng Anh và tiếng Nhật.

Hai bộ: examples/whiteboard-mystery-en/ và examples/whiteboard-mystery-ja/
Mỗi scene-0N/ gồm <scene>.png + <scene>.annotation.json + script.srt.
Tiếng Nhật phải vẽ bằng Yu Gothic vì Segoe UI không có glyph CJK đầy đủ.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from code2video.whiteboard_assets import H, W, draw_scene, estimate_dur_ms, fmt_time, grid_slots

ROOT = Path(__file__).resolve().parents[1]
YUGOTH_BOLD = "C:/Windows/Fonts/YuGothB.ttc"
YUGOTH_REG = "C:/Windows/Fonts/YuGothM.ttc"
SEGOE_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
SEGOE_REG = "C:/Windows/Fonts/segoeui.ttf"

LOCALES = {
    "en": {
        "out": "whiteboard-mystery-en",
        "bold": SEGOE_BOLD,
        "regular": SEGOE_REG,
        "scenes": [
            ("Opening - the hook", [
                ("mansion", "Floor 10", "A luxury hotel suite on the tenth floor."),
                ("door", "Bolted inside", "The door was bolted from the inside with a heavy iron latch."),
                ("window", "Windows sealed", "Every window was shut tight, and there was no balcony."),
                ("body", "The victim", "When police broke the door down, the guest was already dead."),
                ("question", "The killer?", "No sign of a killer, and no way out anywhere."),
                ("question", "Locked room", "So how did a murderer vanish from a perfectly sealed room?"),
            ]),
            ("The scene and the clues", [
                ("floorplan", "Room 1004", "This is the case of room 1004."),
                ("body", "Mr. David", "The victim was Mr. David, a collector of antiques."),
                ("clock", "21:00", "At nine in the evening, a scream tore across the floor."),
                ("door", "The iron latch", "The butler broke the door, but the iron latch had already dropped."),
                ("key", "Key inside", "Clue one: the key was still in the lock, on the inside."),
                ("window", "Thick dust", "Clue two: the windows were closed from within, coated in days of dust."),
                ("closet", "Nowhere to hide", "Clue three: the space under the bed was empty, the wardrobe far too small."),
                ("question", "Dead end", "The police stalled, and called it a suicide."),
                ("question", "A fourth detail", "Until they found the fourth detail."),
            ]),
            ("Theories and dead ends", [
                ("detective", "The detective", "At first, everyone assumed the classic thread trick."),
                ("string", "A thread", "A thin thread or fishing line, used to drop the latch from outside."),
                ("door", "Far too heavy", "But this latch is heavy, and no thread can hold that much force."),
                ("arrow", "No scratches", "The test showed the latch cannot drop without leaving a scratch."),
                ("floorplan", "A secret tunnel?", "Theory two: a hidden tunnel running under the floorboards."),
                ("concrete", "Solid concrete", "The crew lifted every plank: solid reinforced concrete underneath."),
                ("question", "Nowhere to go", "The case ran into a wall."),
                ("ghost", "Supernatural?", "People began to believe something beyond nature was at work."),
            ]),
            ("The twist and the answer", [
                ("detective", "No ghosts", "But an honest detective does not believe in ghosts."),
                ("water", "A puddle", "He looked closely at the latch, and at the small puddle by the bath."),
                ("ice", "A wedge of ice", "The trick was a large wedge carved out of ice."),
                ("ice", "Holding it up", "The ice held the latch raised for a few short minutes."),
                ("string", "Pulled away", "The killer drew the ice out on a thin line, or simply let it melt."),
                ("water", "Melted to nothing", "Once the ice was gone, gravity dropped the latch on its own."),
                ("door", "A perfect seal", "The room became an impossible locked room, sealed without a trace."),
            ]),
            ("Closing and call to action", [
                ("zoom", "The full diagram", "A clever trick built on physics, and on what the eye expects."),
                ("question", "No perfect crime", "There is no perfect crime, only details you have not explained yet."),
                ("like", "Your turn", "Did that twist fool you? Tell us in the comments."),
                ("bell", "Subscribe", "Subscribe so you never miss the next case."),
                ("wave", "See you", "Thank you for watching, and see you in the next one."),
            ]),
        ],
    },
    "ja": {
        "out": "whiteboard-mystery-ja",
        "bold": YUGOTH_BOLD,
        "regular": YUGOTH_REG,
        "scenes": [
            ("冒頭 - 引き", [
                ("mansion", "10階", "高級ホテルの10階にあるスイートルーム。"),
                ("door", "内側から錠", "ドアは内側から重い鉄のかんぬりで閉ざされていました。"),
                ("window", "窓は閉じたまま", "窓はすべて内側から施錠され、ベランダもありません。"),
                ("body", "犠牲者", "警察がドアを破ると、客はすでに死亡していました。"),
                ("question", "犯人は？", "犯人の姿も、逃げ出せる道も見当たりません。"),
                ("question", "密室", "ではどうやって殺人者が完璧な密室から消えたのか。"),
            ]),
            ("現場と四つの手がかり", [
                ("floorplan", "1004号室", "これが1004号室の事件です。"),
                ("body", "ダヴィッド氏", "犠牲者は骨董品コレクターのダヴィッド氏でした。"),
                ("clock", "21時", "夜9時、フロアに悲鳴が響き渡りました。"),
                ("door", "鉄のかんぬり", "執事がドアを破りましたが、かんぬりはすでに下りていました。"),
                ("key", "鍵は内側で", "手がかりその一。鍵は内側の錠前に入ったまま。"),
                ("window", "厚い埃", "その二。窓は閉じられ、何日分もの埃が積もっていました。"),
                ("closet", "隠れる場所なし", "その三。ベッドの下は空で、クローゼットは人間には狭すぎます。"),
                ("question", "行き詰まり", "警察は行き詰まり、これを自殺と結論づけました。"),
                ("question", "四つ目", "四つ目の手がかりを見つけるまで。"),
            ]),
            ("仮説と袋小路", [
                ("detective", "探偵", "まず疑われたのは、有名な糸のトリックでした。"),
                ("string", "一本の糸", "細い糸やテグスを使って、外からかんぬりを下げる手口です。"),
                ("door", "重すぎる", "しかしこのかんぬりは重すぎます。糸にそこまでの力は出せません。"),
                ("arrow", "傷は残らない", "検証の結果、傷をつけずにかんぬりを下げることは不可能でした。"),
                ("floorplan", "隠し通路？", "二つ目の仮説。床板の下に隠し通路があるのではないか。"),
                ("concrete", "鉄筋コンクリート", "技術班が床板をすべて剥がすと、打ちっぱなしの鉄筋コンクリート。"),
                ("question", "袋小路", "事件は完全に袋小路に陥りました。"),
                ("ghost", "超常現象？", "人々は、人間の仕業ではないと思い始めます。"),
            ]),
            ("仕掛けと答え", [
                ("detective", "幽霊は信じるな", "しかし誠実な探偵に、幽霊は信じられません。"),
                ("water", "水たまり", "彼はかんぬりと、浴室の床の小さな水たまりを詳しく見ました。"),
                ("ice", "氷のくさび", "仕掛けの正体は、大きな氷で作られたくさびでした。"),
                ("ice", "開けたまま", "氷が、かんぬりを数分間だけ持ち上げていたのです。"),
                ("string", "糸で引き出す", "犯人は細い糸で氷を外へ引き出すか、ただ溶かしました。"),
                ("water", "水に還る", "氷が溶け切ると、重力だけでかんぬりが下りました。"),
                ("door", "完璧な密室", "こうして、完璧な不可能密室が完成したのです。"),
            ]),
            ("まとめと行動", [
                ("zoom", "全体の図", "物理と、目の錯覚を利用した巧妙な手口でした。"),
                ("question", "完璧な犯罪はない", "完璧な犯罪はありません。解明されていない詳細があるだけです。"),
                ("like", "あなたの意見", "このトリックにだまされましたか？コメントで教えてください。"),
                ("bell", "登録とベル", "次の事件を逃さないよう、チャンネル登録をお願いします。"),
                ("wave", "また次回", "ご視聴ありがとうございました。また次回お会いしましょう。"),
            ]),
        ],
    },
}


def build_locale(code: str, cfg: dict) -> dict:
    out_dir = ROOT / "examples" / cfg["out"]
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for s_idx, (title, items) in enumerate(cfg["scenes"], 1):
        sid = f"scene-{s_idx:02d}"
        scene_dir = out_dir / sid
        scene_dir.mkdir(parents=True, exist_ok=True)
        draw_scene(title, items, cfg["bold"], cfg["regular"]).save(scene_dir / f"{sid}.png", "PNG")

        slots = grid_slots(len(items))
        blocks, elements, t = [], [], 0
        for seq, ((kind, label, subtitle), slot) in enumerate(zip(items, slots), 1):
            dur = estimate_dur_ms(subtitle, code)
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
            "language": code,
            "sceneDurationMs": t,
            "elements": elements,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        summary.append({"scene": sid, "title": title, "durationMs": t, "cues": len(items)})
    return {"language": code, "folder": cfg["out"],
            "totalSec": round(sum(s["durationMs"] for s in summary) / 1000, 1),
            "cues": sum(s["cues"] for s in summary), "scenes": summary}


if __name__ == "__main__":
    report = [build_locale(code, cfg) for code, cfg in LOCALES.items()]
    print(json.dumps(report, ensure_ascii=False, indent=2))
