"""014 eleven small charges, B2 money story: python outputs/014-eleven-small-charges/author.py -> shots-16x9.json, shots-9x16.json"""
import os, sys, math, json, pathlib
os.environ["DRAW_INK"] = "#2b2a28"
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_lib"))
import alib as Z
import draw_kit as D
from draw_kit import svg, line, blob, poly, INK, cycle
from alib import img, text, bob

STORY = json.load(open(HERE.parents[1] / "stories" / "014-eleven-small-charges.json"))
RED, BLUE, GREEN, GOLD, PAPER, WOOD = "#c46a4a", "#5b7fa6", "#8fa58a", "#d6a64a", "#f6efdf", "#a77b52"
EXPR = {"surprise": "surprise", "shock": "surprise", "worry": "worry", "fear": "worry", "angry": "angry", "frustrated": "angry", "doubt": "doubt", "confused": "doubt",
        "think": "think", "happy": "smile", "joy": "smile", "excited": "smile", "laugh": "smile", "proud": "smile", "relief": "smile", "sad": "worry", "tired": "neutral", "calm": "neutral", "neutral": "neutral"}
arlo = dict(name="arlo", style="b2", shirt="#d6a64a", sleeve="#d6a64a", hair="#2d2a26", hair_style="short", shoes="#3c3a37")
jo = dict(name="jo", style="b2", shirt="#4a9d9a", sleeve="#4a9d9a", skirt="#5b6f8a", hair="#7a4b2c", hair_style="bun", shoes="#3c3a37")
def R(x, y, w, h, fill, seed=0, wd=2.6): return poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill, seed=seed, w=wd)

def room(wall, floor, extra=""):
    return svg(1280, 720, f'<rect width="1280" height="720" fill="{wall}"/><rect y="500" width="1280" height="220" fill="{floor}"/>' + line([(0, 500), (1280, 498)], 2.6, seed=1) + extra)
def living(): return room("#efe3cf", "#cfb48d", R(120, 120, 120, 200, "#d6e6ee", 2) + line([(180, 120), (180, 320)], 2, seed=3) + line([(120, 220), (240, 220)], 2, seed=4)
                         + poly([(900, 380), (1240, 380), (1240, 500), (900, 500)], "#b8795a", seed=5) + poly([(900, 330), (1240, 330), (1240, 390), (900, 390)], "#c88b6c", seed=6)
                         + R(560, 440, 260, 60, WOOD, 7) + blob(1100, 160, 26, 26, "#f2d27a", seed=8) + line([(1100, 186), (1100, 330)], 3, seed=9))
def kitchen(): return room("#f3e4c0", "#c9b08a", R(140, 120, 360, 200, "#fff7e0", 2) + R(160, 140, 150, 160, "#d6e6ee", 3) + R(900, 150, 260, 350, "#e9e9e9", 4) + line([(900, 330), (1160, 330)], 3, seed=5)
                                  + R(520, 430, 300, 70, WOOD, 6) + blob(700, 410, 40, 24, "#e08a50", seed=7) + blob(750, 410, 30, 22, "#c46a4a", seed=8))
def desk_room(): return room("#dfe7ea", "#b9a07c", R(120, 100, 380, 300, "#9fc2da", 2) + line([(310, 100), (310, 400)], 3, seed=3) + R(700, 400, 440, 30, WOOD, 4) + R(720, 430, 26, 70, WOOD, 5) + R(1090, 430, 26, 70, WOOD, 6))
def sunday(): return room("#f6e7c8", "#d0b28c", R(100, 110, 240, 190, "#fff7e0", 2) + R(900, 150, 270, 350, "#e9e9e9", 4) + line([(900, 330), (1170, 330)], 3, seed=5) + R(480, 440, 320, 60, WOOD, 6)
                                 + R(540, 380, 90, 60, "#c46a4a", 7) + R(650, 380, 90, 60, "#d6a64a", 8))
def board_room(): return room("#e6e0cf", "#c3ac84", R(150, 70, 980, 400, "#bcd1c0", 2, 4) + line([(640, 100), (640, 440)], 2.4, "#2b2a28", seed=3))
def fridge_room(): return room("#f1e6cf", "#cfb48d", R(780, 90, 340, 420, "#e9e9e9", 2) + line([(780, 270), (1120, 270)], 3, seed=3) + R(1090, 170, 14, 60, "#9a9a9a", 4) + R(120, 300, 460, 200, WOOD, 5))
def laptop(): return svg(420, 290, R(40, 10, 340, 210, "#f0f0f0", 1, 3.2) + R(62, 30, 296, 170, "#d9ecf7", 2, 2) + poly([(10, 220), (410, 220), (386, 270), (34, 270)], "#e0e0e0", seed=3))
def phone(col="#d9ecf7"): return svg(160, 300, R(10, 10, 140, 280, "#3c3a37", 1, 3) + R(22, 30, 116, 230, col, 2, 1.6) + blob(80, 276, 8, 8, "#cfcfcf", seed=3, w=1.6))
def paper(): return svg(300, 400, R(10, 10, 280, 380, "#fffdf5", 1, 3) + "".join(line([(34, 60 + i * 28), (266, 56 + i * 28)], 1.8, "#9a9a9a", seed=10 + i) for i in range(11)))
def banner(): return svg(520, 150, R(8, 8, 504, 134, GOLD, 1, 3.4))
def cal(): return svg(200, 220, R(8, 8, 184, 204, PAPER, 1, 3) + R(8, 8, 184, 50, RED, 2, 3))
def coin(): return svg(100, 100, blob(50, 50, 42, 42, GOLD, seed=1, w=3.4) + blob(50, 50, 27, 27, "none", seed=2, w=2.2) + line([(42, 38), (58, 38), (50, 66)], 3, seed=3))
def envelope(): return svg(200, 140, R(8, 8, 184, 124, PAPER, 1, 3) + line([(8, 8), (100, 80), (192, 8)], 3, seed=2))
def magnet(): return svg(40, 40, blob(20, 20, 16, 16, RED, seed=1, w=2.4))
def ring(): return svg(120, 120, blob(60, 60, 50, 50, "none", stroke=RED, seed=1, w=6))

def build(ratio):
    F = Z.Film("B2", ratio, str(HERE / "voice" / "timing.json")); A = F.A
    for k, v in {"living.png": living(), "kitchen.png": kitchen(), "deskroom.png": desk_room(), "sunday.png": sunday(), "board.png": board_room(), "fridge.png": fridge_room(),
                 "laptop.png": laptop(), "phone.png": phone(), "phone-warn.png": phone("#f6d6a8"), "paper.png": paper(), "banner.png": banner(), "cal.png": cal(), "coin.png": coin(),
                 "env.png": envelope(), "magnet.png": magnet(), "ring.png": ring()}.items(): A[k] = v
    def T(t, x, y, size, color="#2b2a28", **k): return text(t, x, y, size, color, **k)
    lines = {(s["id"], i): l for s in STORY["scenes"] for i, l in enumerate(s["lines"])}

    def people(d, who, e, ax=330, jx=700, ys=170, s=1.0, a_expr=None, j_expr=None):
        """both characters; the speaker gestures, the other listens with a nod"""
        ex = EXPR.get(e, "neutral")
        ae = a_expr or (ex if who == "arlo" else "neutral"); je = j_expr or (ex if who == "jo" else "neutral")
        L = D.person_layers("arlo", arlo, ax, ys, s, expr=ae, reason="Arlo acts the line", assets=A,
                            arm_r=cycle(d, 0.55, -0.4, -1.1) if who == "arlo" else cycle(d, 1.0, -0.28, -0.4), head=cycle(d, 0.8, 0, 0.12 if who == "arlo" else 0.06))
        L += D.person_layers("jo", jo, jx, ys, s, expr=je, reason="Jo reacts", assets=A,
                             arm_r=cycle(d, 0.55, -0.4, -1.1) if who == "jo" else cycle(d, 1.0, -0.28, -0.4), head=cycle(d, 0.8, 0, 0.12 if who == "jo" else 0.06))
        return L

    def shots_for(sc, i, build_fn, **kw):
        a, b = F.line(sc, i); l = lines[(sc, i)]
        n = max(1, round((b - a) / 3.2))
        for p in range(n):
            t0 = a + (b - a) * p / n; t1 = a + (b - a) * (p + 1) / n
            F.add(t0, t1, build_fn(t1 - t0, p, n, l), **kw)

    def scene(sc, bg, extras, ax=330, jx=700, s=1.0, ys=170, fx=640, ps=1.2):
        for i in range(len(STORY["scenes"][sc - 1]["lines"])):
            ex = extras[i] if i < len(extras) else (lambda d, p, n: [])
            shots_for(sc, i, lambda d, p, n, l, ex=ex: [img(bg, 0, 0, 1280, 720, bg=True)] + people(d, l["who"], l["emote"], ax, jx, ys, s) + ex(d, p, n), fx=fx, s=ps)

    chip = lambda t, x=60, y=70: T(t, x, y, 56, RED)
    L0 = lambda d, p, n: [img("laptop.png", 620, 330, 300, 207, "lap", bob(d, 0.6, 330, 324), "the laptop shows the statement"), chip("11 CHARGES", 40, 40)]
    scene(1, "living.png", [L0, lambda d, p, n: [chip("UNDER $16 EACH", 40, 40)], lambda d, p, n: [T("READ THEM OUT", 40, 40, 56, BLUE)],
                            lambda d, p, n: [T("FILM · MUSIC · CLOUD · MEAL BOX", 40, 40, 44, RED, w=1200)], lambda d, p, n: [T("THE ONE NUMBER?", 40, 40, 60, RED)]], ax=250, jx=600)
    def cupd(d, p, n, txt, txt2=None, prop="phone.png"):
        L = [img(prop, 560, 180, 160, 300, "ph", bob(d, 0.55, 180, 170), "the phone with the offer"), T(txt, 40, 40, 56, RED)]
        if txt2: L.append(T(txt2, 40, 120, 48, BLUE, frm=1.0))
        return L
    scene(2, "kitchen.png", [lambda d, p, n: [img("banner.png", 380, 40, 520, 150, "ban", bob(d, 0.6, 40, 34), "the free trial banner"), T("7 DAYS FREE", 440, 80, 60, "#2b2a28")],
                             lambda d, p, n: cupd(d, p, n, "I'LL CANCEL BEFORE IT RENEWS"), lambda d, p, n: cupd(d, p, n, "$5 / MONTH", "same day, every month"),
                             lambda d, p, n: [T("NOTHING FELT DIFFERENT", 40, 40, 56, BLUE), img("coin.png", 600, 200, 100, 100, "coin", bob(d, 0.5, 200, 190), "a coin leaves quietly")]], ax=250, jx=800)
    scene(3, "deskroom.png", [lambda d, p, n: cupd(d, p, n, "STORAGE FULL", None, "phone-warn.png"), lambda d, p, n: cupd(d, p, n, "$12 FOR SPACE", "fine. it's just space."),
                              lambda d, p, n: [T("ONE TAP", 40, 40, 70, GREEN)], lambda d, p, n: [T("MUSIC APP + MEAL BOX", 40, 40, 56, RED, w=1200)], lambda d, p, n: [T("10 SECONDS PER YES", 40, 40, 62, BLUE)]], ax=300, jx=780)
    scene(4, "sunday.png", [lambda d, p, n: [img("banner.png", 380, 40, 520, 150, "ban", bob(d, 0.6, 40, 34), "the half-price banner"), T("HALF PRICE", 450, 80, 60, "#2b2a28")],
                            lambda d, p, n: [T("I'LL PAUSE IT AFTER", 40, 40, 56, BLUE)], lambda d, p, n: [img("cal.png", 560, 170, 200, 220, "cal", bob(d, 0.6, 170, 162), "the same date every month"), T("SAME DATE", 40, 40, 64, RED)],
                            lambda d, p, n: [T("STILL PAYING", 40, 40, 64, RED)], lambda d, p, n: [T("10 SMALL YESES", 40, 40, 64, BLUE)]], ax=250, jx=800)
    # scene 5: the name, no people (board)
    def board(d, p, n, extra):
        return [img("board.png", 0, 0, 1280, 720, bg=True), img("coin.png", 250, 230, 100, 100, "bc", bob(d, 0.55, 230, 218), "cash leaves a sting"), img("env.png", 850, 240, 200, 140, "be", bob(d, 0.55, 240, 228), "the auto charge")] + extra
    for i in range(3):
        a, b = F.line(5, i); n = max(1, round((b - a) / 3.2))
        extras = [[T("THE PAIN OF PAYING", 250, 100, 76, "#2b2a28", w=900)], [T("CASH  STINGS", 190, 380, 56, "#2b2a28", w=500), T("AUTO  BARELY", 740, 380, 56, "#2b2a28", w=500, frm=1.2)], [T("THE STING FADES", 330, 100, 76, "#2b2a28", w=800)]][i]
        for p in range(n): F.add(a + (b - a) * p / n, a + (b - a) * (p + 1) / n, board((b - a) / n, p, n, extras), fx=640, s=1.2)
    def sumlist(d, p, n, txt, big=None):
        L = [img("paper.png", 560, 100, 300, 400, "pap", bob(d, 0.6, 100, 94), "the list of eleven"), T(txt, 40, 40, 60, RED)]
        if big: L.append(T(big, 900, 200, 80, BLUE))
        return L
    scene(6, "living.png", [lambda d, p, n: [img("laptop.png", 620, 330, 300, 207, "lap", bob(d, 0.6, 330, 324), "adding the lines")], lambda d, p, n: [T("5 · 14 · 26 ...", 40, 40, 70, BLUE)],
                            lambda d, p, n: [T("$91 / MONTH", 40, 40, 90, RED)], lambda d, p, n: [T("$91?!", 40, 40, 100, RED)], lambda d, p, n: [T("$1,092 / YEAR", 40, 40, 90, RED)]], ax=250, jx=600)
    scene(7, "living.png", [lambda d, p, n: [T("USED THIS MONTH?", 40, 40, 60, BLUE)], lambda d, p, n: [T("MUSIC · CLOUD · FILM (ONCE)", 40, 40, 50, RED, w=1200)], lambda d, p, n: [T("3 OF 11 USED", 40, 40, 80, RED)],
                            lambda d, p, n: [T("$91 AT ONCE?", 40, 40, 80, BLUE)], lambda d, p, n: [T("NO. NEVER.", 40, 40, 80, RED)], lambda d, p, n: [T("SPREAD ACROSS ELEVEN DATES", 40, 40, 52, BLUE, w=1200)],
                            lambda d, p, n: [T("5 CROSSED OUT", 40, 40, 80, GREEN)], lambda d, p, n: [T("IT WAS THE ADDING", 40, 40, 70, RED)]], ax=250, jx=600)
    # scene 8: fridge close
    def fr(d, p, n, txt):
        return [img("fridge.png", 0, 0, 1280, 720, bg=True), img("paper.png", 860, 110, 220, 290, "fp", bob(d, 0.6, 110, 104), "the list on the fridge"), img("magnet.png", 960, 100, 40, 40, "mg"), T(txt, 80, 80, 70, RED, w=650)] + \
               D.person_layers("arlo", arlo, 400, 170, 1.0, expr="think", reason="Arlo looks at the list", assets=A, arm_r=cycle(d, 0.7, -0.5, -1.0), head=cycle(d, 0.8, 0, 0.1))
    for i, txt in enumerate(["ONE YEAR OF YESES", "ON THE FRIDGE", "WHICH WOULD YOU KEEP?"]):
        a, b = F.line(8, i); n = max(1, round((b - a) / 3.2))
        for p in range(n): F.add(a + (b - a) * p / n, a + (b - a) * (p + 1) / n, fr((b - a) / n, p, n, txt), fx=640, s=1.2)
    return F

def fill_gaps(F):
    F.shots.sort(key=lambda s: s["start"])
    for a, b in zip(F.shots, F.shots[1:]): a["end"] = b["start"]
    F.shots[0]["start"] = 0.0; F.shots[-1]["end"] = F.DUR

if __name__ == "__main__":
    for ratio, name in (("16:9", "shots-16x9.json"), ("9:16", "shots-9x16.json")):
        F = build(ratio); F.sfx = [{"time": 4.0, "name": "pop", "gain": 0.2}]
        fill_gaps(F); F.write(str(HERE / name))
