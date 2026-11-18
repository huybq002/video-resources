"""Footprints in the Snow. None Out. (B3 night mystery). The death is never shown: a shut shed door, a dry outline on a step, props named by the narrator."""
import sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "motion"))
from director import Film
import worlds as Wd

f = Film(HERE.parents[1] / "stories" / "016-footprints-in-snow.json", HERE / "voice")
L, S, WD = f.line, f.next_start, f.word
f.look("kiri", shirt="#7a8aa8", hair="#2d2a26", shoes="#3c3a37", belt="#2b2622")
f.look("hana", shirt="#3f7a52", hair="#4a3322", hairStyle="long", shoes="#3c3a37", belt="#2b2622")
f.look("dale", shirt="#6a6a72", vest="#4a4a52", hair="#9a9a9a", moustache="#9a9a9a", shoes="#2b2622", belt="#2b2622")
f.look("rosa", shirt="#e8e4da", apron="#f3f0e8", hair="#6a4a32", hairStyle="long", headscarf="#e8e4da", skirt=True, shoes="#4a3a2e")
f.look("hale", shirt="#5a2a4a", vest="#2a1a2a", hair="#1f1a1f", moustache="#1f1a1f", shoes="#1f1a1f", belt="#1f1a1f")
f.look("ben", shirt="#7a6a4a", vest="#4a5a3a", hair="#3a2a1e", headscarf="#5a5a52", shoes="#4a3a2e", belt="#3a2a1e")

SNOW_BG = "#dfe8f2"


def shed(sky="night", **o):
    p = Wd.farm("night")
    p["far"] = [{"type": "hills", "y": 640, "amp": 80, "color": "#3a4668"}, {"type": "hills", "y": 730, "amp": 50, "color": "#4a5878"}]
    p["mid"] = [{"type": "ground", "y": 800, "color": SNOW_BG}, {"type": "road", "vx": 1450, "y": 790, "color": "#c5d0de"},
                {"type": "shack", "x": 1330, "y": 840, "w": 380, "h": 250, "wall": "#5a4636", "roof": "#3a2e26"},
                {"type": "tree", "x": 220, "y": 840, "s": 1.1, "leaf": "#2f4a46"}]
    p["near"] = []
    p["ambient"] = [{"type": "glow", "lights": [[1500, 170, 220]], "color": "#cfd8ff", "depth": "far"}]
    p["particles"] = [{"preset": "snow", "number": 160, "near": True}]
    p["look"] = {"grade": "night", "vignette": 0.55, "light": [0.5, 0.5, 0.14]}
    p.update(o); return p


def room(kind):
    p = Wd.tavern()
    p["sky"] = {"top": "#1a1a24", "bottom": "#2a2430"}
    p["mid"] = [dict(e, glass="#cfd8f0") if e["type"] == "window" else e for e in p["mid"] if e["type"] != "shelf" or kind == "kitchen"]
    p["look"] = {"grade": "night", "vignette": 0.55, "light": [0.3, 0.3, 0.14]}
    p["particles"] = [{"preset": "dust", "number": 20}]
    if kind == "dining":
        p["ambient"] = [{"type": "glow", "lights": [[460, 560, 200], [960, 560, 220], [1460, 560, 200]], "depth": "mid"}]
    return p


def porch(**o):
    p = Wd.gate_night(); p["particles"] = [{"preset": "snow", "number": 150, "near": True}]
    p["mid"][0] = {"type": "ground", "y": 820, "color": SNOW_BG}; p.update(o); return p


step = shed(); step["front"] = [{"type": "trough", "x": 1020, "y": 930, "w": 520}]
f.place("shed", shed()); f.place("step", step); f.place("kitchen", room("kitchen")); f.place("dining", room("dining")); f.place("porch", porch())
f.place("terrace", porch()); f.place("garden", shed(sky="night"))
Y = 900
f.default_cy = 650

# scene -> (place, who: (x, facing) ...)
SC = {
    1: ("shed", dict(kiri=(650, 1), hana=(450, 1), dale=(880, 1))),
    2: ("kitchen", dict(kiri=(700, 1), hana=(500, 1), rosa=(1250, -1))),
    3: ("dining", dict(kiri=(650, 1), hana=(450, 1), dale=(1000, -1), hale=(1300, -1))),
    4: ("porch", dict(kiri=(700, 1), hana=(500, 1), ben=(1250, -1))),
    5: ("step", dict(kiri=(650, 1), hana=(450, 1))),
    6: ("shed", dict(kiri=(650, 1), rosa=(980, -1))),
    7: ("porch", dict(kiri=(650, 1), ben=(1000, -1))),
    8: ("garden", dict(kiri=(800, 1), hana=(560, 1), dale=(1050, -1), hale=(1250, -1), rosa=(1500, -1))),
    9: ("terrace", dict(kiri=(900, 1), hana=(700, 1))),
}
MOOD = {1: ("mystery", 60, "minor"), 2: ("mystery", 64, "minor"), 3: ("tense", 66, "minor"), 4: ("mystery", 62, "minor"), 5: ("tense", 66, "minor"),
        6: ("tense", 68, "minor"), 7: ("tense", 70, "minor"), 8: ("hopeful", 76, "major"), 9: ("sad", 58, "minor")}
VERB = {"doubt": "crossArms", "think": "look", "calm": "nod", "worry": "sigh", "worried": "sigh", "fear": "shake", "confused": "shake", "tired": "sigh", "happy": "armsOpen"}
SFX = {"crossArms": "tick", "point": "tap", "shake": "blip", "armsOpen": "whoosh"}
SCN = {}
story = f.story if hasattr(f, "story") else None
import json
ST = json.load(open(HERE.parents[1] / "stories" / "016-footprints-in-snow.json"))
lastkind = []
KINDS = [("medium", "two"), ("close", "wide"), ("over", "medium"), ("wide", "close")]
for sid, (place, cast) in SC.items():
    t0, t1 = f.scene_span(sid)
    s = SCN[sid] = f.scene(f"s{sid}", place, t0, t1, cast={w: dict(x=x, facing=d) for w, (x, d) in cast.items()})
    mood, bpm, scale = MOOD[sid]
    f.section(t0, t1, mood=mood, motif="snow", bpm=bpm, scale=scale, instruments=["pad", "bell", "pluck"] if sid != 9 else ["pad", "bell"], energy=0.35 + 0.05 * sid / 3)
    if sid == 1: f.card(0.3, 3.8, "Larkfield Manor, 10 p.m.", size=52, color="#e8eefc")
    lines = ST["scenes"][sid - 1]["lines"]; who_all = list(cast)
    for i, ln in enumerate(lines):
        a, b = L(sid, i); a = 0.0 if (sid, i) == (1, 0) else a; end = S(sid, i)
        spk = ln["who"]; on_screen = spk in cast
        k = KINDS[(sid + i) % len(KINDS)]
        if on_screen:
            others = [w for w in who_all if w != spk]; lis = others[0] if others else None
            for lo in others[:2]:
                if lo not in ("rosa", "hale", "ben") or lo == lis: f.act(SCN[sid], lo, "look", a, b, emotion="neutral")
            v = VERB.get(ln["emote"], "nod")
            f.act(s, spk, v, a + 0.5, b, emotion={"doubt": "worried", "fear": "worried", "worry": "worried", "happy": "happy"}.get(ln["emote"], "neutral"))
            if v in SFX: f.sfx(a + 0.5, SFX[v])
            parts = [(1, k[0], dict(sc=s, on=spk)), (1, k[1], dict(sc=s, on=(spk, lis)) if k[1] == "two" and lis else dict(sc=s) if k[1] == "wide" else dict(sc=s, on=lis or spk))]
            if k[0] == "over":
                parts[0] = (1, "over", dict(sc=s, on=lis or spk, **{"from": spk}))
        else:
            c = who_all[0]
            f.act(s, c, "look" if i % 2 else "nod", a + 0.4, b, emotion="neutral")
            parts = [(1, ("wide", "reveal", "medium")[(sid + i) % 3], dict(sc=s, **({"on": c} if (sid + i) % 3 == 2 else {}))), (1, "medium" if (sid + i) % 2 else "close", dict(sc=s, on=c))]
        tot = sum(p[0] for p in parts); t = a
        for j, (w, kind, kw) in enumerate(parts):
            e = end if j == len(parts) - 1 else round(t + (end - a) * w / tot, 3)
            sc_ = kw.pop("sc"); f.shot(sc_, t, e, kind, **kw); t = e

# -------- the objects the words name, big on screen when named
s5, s6, s7, s8 = SCN[5], SCN[6], SCN[7], SCN[8]
f.prop(s6, "lantern", "lantern", 1250, 800, s=1.0, from_=L(6, 0)[0]) if False else f.prop(SCN[6], "lantern", "lantern", 1250, 800, s=1.6, pop=L(6, 0)[0] + 0.3)
f.prop(SCN[1], "lantern1", "lantern", 1240, 820, s=0.6)
f.prop(SCN[7], "boots", "sandals", 1350, 900, s=2.2, pop=L(7, 0)[0] + 0.3)
f.prop(SCN[4], "lamp4", "lantern", 1050, 760, s=0.5)
f.sfx(L(5, 1)[0] + 0.5, "sparkle"); f.sfx(L(6, 2)[0] + 0.3, "blip"); f.sfx(L(7, 1)[0] + 0.3, "tick"); f.hit(L(5, 2)[0] + 2.0, "swell"); f.hit(L(8, 0)[0], "swell")
# silence before the turn
f.act(SCN[5], "kiri", "point", WD(5, 2, "outline") if False else L(5, 2)[0] + 2.5, L(5, 2)[1], emotion="neutral")
# the trick, step by step (kiri points as each step is named)
for i, w in enumerate(("one", "two", "three", "four")):
    f.act(s8, "kiri", "point", WD(8, i, "Step") - 0.1, L(8, i)[1], emotion="neutral"); f.sfx(WD(8, i, "Step"), "tap")
f.act(s8, "hale", "turnAway", L(8, 4)[0] + 1.0, L(8, 4)[1] + 1.0, emotion="ashamed")
f.act(s8, "dale", "point", L(8, 4)[0], L(8, 4)[1], emotion="angry")
f.act(SCN[7], "ben", "shout", L(7, 3)[0] + 0.3, L(7, 3)[1], emotion="worried") if False else None
sh = f.shots
for sid, pos in ((5, (1280, 900)), (6, (1250, 700)), (7, (1350, 860))):
    first = [x for x in sh if x["scene"] == f"s{sid}"][0]
    first["kind"] = "detail"; first["cam"] = dict(z=[2.2, 2.35], c=[list(pos), list(pos)])
for i in range(1, len(sh) - 1):
    if sh[i - 1]["kind"] == sh[i]["kind"] == sh[i + 1]["kind"] == "medium":
        sh[i]["kind"] = "close"; sh[i]["cam"]["z"] = [2.35, 2.43]
f.save(HERE / "film")
