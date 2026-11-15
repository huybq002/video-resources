"""'Why Saving Feels Harder Than Spending' directed in one style: python author_real.py B1|B2|B3 -> shots-<style>.json"""
import json, math, os, sys

STYLE = sys.argv[1].upper()
os.environ["DRAW_INK"] = "#e9eaec" if STYLE == "B3" else "#2b2a28"
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'scripts'))
import draw_kit as D
from draw_kit import svg, line, blob, poly, INK, cycle

T = json.load(open("voice/timing.json")); DUR = T["duration"]
A = {}
# palettes: B1 ink figures + colored props on the runtime's white grid; B2 colored world; B3 white/grey on dark
if STYLE == "B1":
    PAL = dict(gold="#F2B632", candy=["#EC4338", "#5BA55B", "#5b8fd6", "#F2B632"], wood="#c99a6b", glass="#d9ecf7", wall=None, floor=None,
               door="#5b8fd6", chalk="#2f4a3a", chalkline="#ffffff", text="#2b2a28", accent="#EC4338", sun="#F2B632", leaf="#5BA55B", paper="#fff7e0")
    lily = dict(name="lily", style="b1", hair=INK, hair_style="ponytail", shoes=INK)
    grandpa = dict(name="grandpa", style="b1", hair_style="bald", moustache=True, moustache_color="#ffffff", shoes=INK)
    sam = dict(name="sam", style="b1", hair=INK, hair_style="short", shoes=INK)
elif STYLE == "B2":
    PAL = dict(gold="#d6a64a", candy=["#c46a4a", "#8fa58a", "#5b7fa6", "#d6a64a"], wood="#a77b52", glass="#d6e6ee", wall="#efe3cf", floor="#cfb48d",
               door="#5b7fa6", chalk="#3d5246", chalkline="#f3efe2", text="#2b2a28", accent="#c46a4a", sun="#e8b04a", leaf="#8fa58a", paper="#f6efdf")
    lily = dict(name="lily", style="b2", shirt="#c4544a", skirt="#5b7fa6", hair="#7a4b2c", hair_style="ponytail", sleeve="#c4544a", shoes="#3c3a37")
    grandpa = dict(name="grandpa", style="b2", shirt="#e9e1cf", vest="#6f8f5f", hair_style="bald", moustache=True, moustache_color="#f4f1ea", sleeve="#6f8f5f", shoes="#4a3a2e")
    sam = dict(name="sam", style="b2", shirt="#f0d9a8", apron="#4f7fb3", hair="#2d2a26", hair_style="short", sleeve="#f0d9a8", shoes="#3c3a37")
else:
    PAL = dict(gold="#c9ccd1", candy=["#e9eaec", "#a7acb3", "#d3d6db", "#7d838b"], wood="#5b6067", glass="#3a3e44", wall=None, floor=None,
               door="#4b5057", chalk="#2a2d31", chalkline="#e9eaec", text="#e9eaec", accent="#ffffff", sun="#d3d6db", leaf="#7d838b", paper="#3a3e44")
    lily = dict(name="lily", style="b2", skin="#eceef1", shirt="#7d838b", skirt="#4b5057", hair="#a7acb3", hair_style="ponytail", sleeve="#7d838b", shoes="#a7acb3")
    grandpa = dict(name="grandpa", style="b2", skin="#eceef1", shirt="#a7acb3", vest="#5b6067", hair_style="bald", moustache=True, moustache_color="#d3d6db", sleeve="#5b6067", shoes="#a7acb3")
    sam = dict(name="sam", style="b2", skin="#eceef1", shirt="#a7acb3", apron="#4b5057", hair="#d3d6db", hair_style="short", sleeve="#a7acb3", shoes="#a7acb3")
G = PAL


def img(path, x, y, w, h, lid=None, keys=None, why=None, role="prop", frm=None, to=None):
    d = {"type": "image", "path": f"assets/{path}", "x": x, "y": y, "w": w, "h": h}
    if lid: d["id"] = lid
    if keys: d["keys"] = keys; d["motion"] = {"role": role, "reason": why}
    if frm is not None: d["from"] = frm
    if to is not None: d["to"] = to
    return d


def text(t, x, y, size, color=None, **k):
    return {"type": "text", "text": t, "x": x, "y": y, "w": max(120, 1250 - x), "size": size, "bold": True, "color": color or G["text"], **k}


# ------------------------------------------------------------- drawings -----------------------------------------------
def porch_bg(summer=False):
    s = []
    if G["wall"]: s += [f'<rect width="1280" height="720" fill="{"#f6e7c8" if summer else G["wall"]}"/>', f'<rect y="500" width="1280" height="220" fill="{G["floor"]}"/>']
    s.append(line([(0, 500), (1280, 498)], 2.6, seed=1))
    s.append(poly([(840, 150), (1000, 150), (1000, 500), (840, 500)], G["door"], seed=2)); s.append(blob(980, 330, 7, 7, G["gold"], seed=3))
    s.append(poly([(800, 500), (1040, 500), (1060, 540), (780, 540)], G["wood"], seed=4))                           # the step
    s.append(poly([(1100, 430), (1160, 430), (1150, 500), (1110, 500)], G["accent"], seed=5))                        # flower pot
    for k in range(3): s.append(blob(1115 + k * 18, 410 - (k % 2) * 16, 14, 14, G["leaf"], seed=6 + k))
    if summer: s.append(blob(150, 110, 50, 50, G["sun"], seed=9)); s += [line([(150 + 70 * math.cos(a), 110 + 70 * math.sin(a)), (150 + 92 * math.cos(a), 110 + 92 * math.sin(a))], 3, G["sun"], seed=10 + i) for i, a in enumerate([k * math.pi / 4 for k in range(8)])]
    return svg(1280, 720, "".join(s))


def shop_bg():
    s = []
    if G["wall"]: s += [f'<rect width="1280" height="720" fill="#e9dcc4"/>', f'<rect y="500" width="1280" height="220" fill="{G["floor"]}"/>']
    s.append(line([(0, 500), (1280, 498)], 2.6, seed=20))
    for j, yy in enumerate((140, 230)):
        s.append(poly([(80, yy), (520, yy), (520, yy + 10), (80, yy + 10)], G["wood"], seed=21 + j))
        for i in range(5): s.append(poly([(100 + i * 82, yy - 54), (150 + i * 82, yy - 54), (150 + i * 82, yy), (100 + i * 82, yy)], G["candy"][(i + j) % 4], seed=30 + i + j * 5))
    s.append(poly([(560, 380), (1180, 380), (1180, 520), (560, 520)], G["wood"], seed=40)); s.append(poly([(550, 366), (1190, 366), (1190, 386), (550, 386)], "#8a6040" if STYLE == "B2" else G["wood"], seed=41))
    return svg(1280, 720, "".join(s))


def candy_jar():
    s = [poly([(30, 40), (190, 40), (200, 250), (20, 250)], G["glass"], seed=50), poly([(40, 10), (180, 10), (180, 42), (40, 42)], G["accent"], seed=51)]
    for i in range(14):
        s.append(blob(50 + (i % 5) * 30 + (i // 5) * 8, 225 - (i // 5) * 40 - (i % 2) * 10, 13, 13, G["candy"][i % 4], seed=60 + i))
    return svg(220, 260, "".join(s))


def coin(big=False):
    return svg(80, 80, blob(40, 40, 34, 34, G["gold"], seed=70, w=3) + blob(40, 40, 22, 22, "none", seed=71, w=2) + line([(34, 30), (46, 30), (40, 52)], 3, seed=72))


def candy():
    return svg(110, 60, poly([(30, 14), (80, 14), (84, 46), (26, 46)], G["candy"][0], seed=80) + poly([(30, 30), (6, 12), (8, 48)], G["candy"][0], seed=81) + poly([(80, 30), (104, 12), (102, 48)], G["candy"][0], seed=82))


def jar_full():
    s = [poly([(20, 40), (160, 40), (168, 240), (12, 240)], G["glass"], seed=90), poly([(30, 14), (150, 14), (150, 42), (30, 42)], G["wood"], seed=91)]
    for i in range(16): s.append(blob(40 + (i % 4) * 32, 220 - (i // 4) * 34, 14, 14, G["gold"], seed=92 + i, w=2))
    return svg(180, 250, "".join(s))


def calendar(label):
    s = [poly([(6, 6), (154, 6), (154, 184), (6, 184)], G["paper"], seed=100), poly([(6, 6), (154, 6), (154, 46), (6, 46)], G["accent"], seed=101)]
    return svg(160, 190, "".join(s))


def wrapper(i):
    return svg(70, 40, poly([(6, 8), (62, 4), (64, 34), (8, 36)], G["candy"][i % 4], seed=110 + i))


def chalkboard():
    s = [poly([(10, 10), (1010, 10), (1010, 470), (10, 470)], G["chalk"], seed=120, w=4), poly([(0, 0), (1020, 0), (1020, 18), (0, 18)], G["wood"], seed=121)]
    s.append(line([(510, 70), (512, 420)], 2.4, G["chalkline"], seed=122))
    return svg(1020, 480, "".join(s))


for k, v in {"porch.png": porch_bg(), "porch-summer.png": porch_bg(True), "shop.png": shop_bg(), "candyjar.png": candy_jar(), "coin.png": coin(),
             "candy.png": candy(), "jar.png": jar_full(), "cal.png": calendar(""), "board.png": chalkboard()}.items():
    A[k] = v
for i in range(4): A[f"wrap{i}.png"] = wrapper(i)

ln = {(l["scene"], l["i"]): l for l in T["lines"]}
shots = []


def _clean(layer, dur):
    """key times rounded, kept inside the shot, strictly increasing (the runtime refuses anything else)"""
    if layer.get("keys"):
        out = []
        for k in layer["keys"]:
            k = dict(k, t=round(min(max(0.0, k["t"]), dur), 3))
            if out and k["t"] <= out[-1]["t"]: continue
            out.append(k)
        layer["keys"] = out
        if len(out) < 2: layer.pop("keys"); layer.pop("motion", None)
    for c in layer.get("children", []): _clean(c, dur)
    return layer


def add(t0, t1, layers):
    t0, t1 = round(t0, 3), round(t1, 3)
    shots.append({"start": t0, "end": t1, "layers": [_clean(l, math.floor((t1 - t0 - 0.001) * 1000) / 1000) for l in layers]})


# S1 0-3.6 the porch: Grandpa hands Lily a coin
t0, t1 = 0, 3.6; d = t1 - t0
add(t0, t1, [img("porch.png", 0, 0, 1280, 720)]
    + D.person_layers("lily1", lily, 330, 170, 1.0, reason="Lily waits for her coin", assets=A, expr="smile",
                      arm_r=[{"t": 0, "angle": -0.2}, {"t": 1.6, "angle": -1.0}, {"t": d, "angle": -0.95}], head=[{"t": 0, "angle": 0}, {"t": 1.0, "angle": 0.1}, {"t": 2.0, "angle": 0}, {"t": d, "angle": 0.1}])
    + D.person_layers("gpa1", grandpa, 620, 160, 1.05, reason="Grandpa holds out the coin", assets=A, expr="smile",
                      arm_l=[{"t": 0, "angle": 0.2}, {"t": 0.9, "angle": 1.15}, {"t": d, "angle": 1.1}], head=[{"t": 0, "angle": 0}, {"t": 1.5, "angle": 0.08}, {"t": d, "angle": 0}])
    + [img("coin.png", 600, 300, 44, 44, "coin1", [{"t": 0.9, "x": 610, "y": 300, "alpha": 0}, {"t": 1.2, "x": 600, "y": 290, "alpha": 1}, {"t": 2.2, "x": 470, "y": 300}, {"t": d, "x": 466, "y": 296}], "the coin passes from his hand to hers"),
       text("ONE COIN.", 80, 60, 64)])
# S2 3.6-6.6 Grandpa's offer: now one, next week two
t0, t1 = 3.6, 6.6; d = t1 - t0
add(t0, t1, [img("porch.png", -200, -120, 1600, 900)]
    + D.person_layers("gpa2", grandpa, 760, 150, 1.25, reason="Grandpa explains the deal", assets=A, expr="smile",
                      arm_r=cycle(d, 0.6, -0.4, -1.1), head=cycle(d, 0.7, 0, 0.12))
    + [text("NOW:", 90, 120, 64), img("coin.png", 290, 120, 80, 80, "nowC", [{"t": 0.2, "alpha": 0, "w": 30}, {"t": 0.6, "alpha": 1, "w": 80}, {"t": d, "w": 80}], "one coin now"),
       text("NEXT WEEK:", 90, 260, 64, G["accent"], **{"from": 1.2}),
       img("coin.png", 470, 260, 80, 80, "nwC1", [{"t": 1.3, "alpha": 0, "w": 30}, {"t": 1.7, "alpha": 1, "w": 80}, {"t": d, "w": 80}], "two coins next week"),
       img("coin.png", 560, 260, 80, 80, "nwC2", [{"t": 1.6, "alpha": 0, "w": 30}, {"t": 2.0, "alpha": 1, "w": 80}, {"t": d, "w": 80}], "two coins next week")])
# S3 6.6-10.95 the shop: the candy right there, the two coins a week away
t0, t1 = 6.6, 10.95; d = t1 - t0
add(t0, t1, [img("shop.png", 0, 0, 1280, 720),
    img("candyjar.png", 800, 120, 220, 260, "jar3", cycle(d, 0.5, 120, 108, "y"), "the candy jar seems to call her")]
    + D.person_layers("lily3", lily, 420, 170, 1.0, reason="Lily stares at the candy", assets=A, expr_swaps=[(None, 2.2, "smile"), (2.2, None, "think")],
                      head=[{"t": 0, "angle": 0}, {"t": 1.2, "angle": 0.12}, {"t": 2.6, "angle": 0}, {"t": d, "angle": 0.1}], arm_r=[{"t": 0, "angle": -0.3}, {"t": 2.0, "angle": -0.9}, {"t": d, "angle": -0.85}])
    + [text("RIGHT THERE.", 640, 430, 46, "#fff7e0" if STYLE != "B3" else G["text"], **{"from": 0.3}),
       img("cal.png", 1080, 470, 110, 130, "cal3", [{"t": 2.0, "alpha": 0, "y": 500}, {"t": 2.6, "alpha": 1, "y": 470}, {"t": d, "y": 466}], "a whole week away"),
       text("7 DAYS", 1090, 610, 30, **{"from": 2.4}),
       img("coin.png", 1110, 520, 30, 30, "far3", [{"t": 2.6, "alpha": 0}, {"t": 3.2, "alpha": 1, "w": 30}, {"t": d, "w": 22}], "the later coins look tiny")])
# S4 10.95-12.6 "One now, please!" the coin slaps the counter, a candy pops out
t0, t1 = 10.95, 12.6; d = t1 - t0
add(t0, t1, [img("shop.png", -300, -220, 1920, 1080)]
    + D.person_layers("lily4", lily, 260, 140, 1.3, reason="Lily slaps the coin down", assets=A, expr="smile",
                      arm_r=[{"t": 0, "angle": -1.5}, {"t": 0.25, "angle": -0.7}, {"t": d, "angle": -0.75}], head=[{"t": 0, "angle": 0.1}, {"t": 0.3, "angle": 0}, {"t": d, "angle": 0.1}])
    + [img("coin.png", 600, 420, 60, 60, "coin4", [{"t": 0, "y": 380}, {"t": 0.25, "y": 440}, {"t": d, "y": 440}], "the coin hits the counter"),
       img("candy.png", 760, 380, 150, 82, "candy4", [{"t": 0.4, "y": 460, "alpha": 0, "angle": 0}, {"t": 0.8, "y": 330, "alpha": 1, "angle": -0.2}, {"t": d, "y": 340, "angle": 0.1}], "the candy pops up"),
       text("ONE NOW!", 820, 120, 80, G["accent"])])
# S5 12.6-15.2 week after week: Saturdays flip, wrappers pile, now won
t0, t1 = 12.6, 15.2; d = t1 - t0
L = [text("NOW WON.", 520, 120, 80, G["accent"], **{"from": 0.6})]
for k in range(4):
    L.append(img("cal.png", 160, 220, 200, 238, f"calS{k}", [{"t": k * 0.6, "alpha": 1, "y": 220}, {"t": k * 0.6 + 0.55, "alpha": 1 if k == 3 else 0, "y": 220 if k == 3 else 180}], "another Saturday",
                 frm=k * 0.6, to=(k * 0.6 + 0.6) if k < 3 else None))
    L.append(text(f"SAT {k + 1}", 190, 300, 48, **{"from": k * 0.6, **({"to": k * 0.6 + 0.6} if k < 3 else {})}))
    L.append(img(f"wrap{k}.png", 560 + k * 120, 470, 100, 57, f"wrapS{k}", [{"t": k * 0.6, "alpha": 0, "y": 400}, {"t": k * 0.6 + 0.3, "alpha": 1, "y": 470}, {"t": d, "y": 470}], "the wrappers pile up"))
add(t0, t1, L)
# S6 15.2-19.0 summer porch: Sam shakes a full jar
t0, t1 = 15.2, 19.0; d = t1 - t0
add(t0, t1, [img("porch-summer.png", 0, 0, 1280, 720)]
    + D.person_layers("sam6", sam, 640, 160, 1.05, reason="Sam shakes her jar", assets=A, expr="smile", arm_r=cycle(d, 0.25, -0.9, -1.2))
    + [img("jar.png", 740, 250, 120, 167, "jar6", cycle(d, 0.25, 740, 760, "x"), "the jar full of coins rattles")]
    + D.person_layers("lily6", lily, 280, 170, 1.0, reason="Lily watches, surprised", assets=A, expr="surprise",
                      head=[{"t": 0, "angle": 0}, {"t": 1.0, "angle": 0.12}, {"t": 2.0, "angle": 0}, {"t": 3.0, "angle": 0.12}, {"t": d, "angle": 0}])
    + [text("SAM WAITED.", 330, 60, 64)])
# S7 19.0-22.85 "Same coins. Why is waiting so hard?" close on Lily
t0, t1 = 19.0, 22.85; d = t1 - t0
add(t0, t1, [img("porch-summer.png", -400, -260, 2080, 1170)]
    + D.person_layers("lily7", lily, 480, 80, 1.6, reason="Lily throws up her hands", assets=A, expr_swaps=[(None, 1.6, "worry"), (1.6, None, "angry")],
                      arm_r=[{"t": 0, "angle": -0.3}, {"t": 1.6, "angle": -2.3}, {"t": 2.6, "angle": -2.1}, {"t": d, "angle": -2.3}],
                      arm_l=[{"t": 0, "angle": 0.3}, {"t": 1.6, "angle": 2.3}, {"t": 2.6, "angle": 2.1}, {"t": d, "angle": 2.3}])
    + [text("WHY?", 900, 140, 120, G["accent"], **{"from": 1.6})])
# S8 22.85-27.4 present bias on the board: next week's coins shrink in her head
t0, t1 = 22.85, 27.4; d = t1 - t0
add(t0, t1, [img("board.png", 130, 60, 1020, 480), text("TODAY", 280, 110, 56, G["chalkline"]), text("NEXT WEEK", 700, 110, 56, G["chalkline"]),
    img("coin.png", 300, 220, 160, 160, "todayC", [{"t": 0, "w": 140}, {"t": 1.0, "w": 170}, {"t": d, "w": 175}], "today's coin looms large"),
    img("coin.png", 720, 230, 120, 120, "nw8a", [{"t": 0.6, "w": 120}, {"t": 2.6, "w": 50}, {"t": d, "w": 46}], "later shrinks in her head"),
    img("coin.png", 860, 230, 120, 120, "nw8b", [{"t": 0.6, "w": 120}, {"t": 2.6, "w": 50}, {"t": d, "w": 46}], "later shrinks in her head"),
    {"type": "underline", "id": "ul8", "x": 330, "y": 620, "w": 620, "keys": [{"t": 0.3, "progress": 0}, {"t": 1.3, "progress": 1}], "motion": {"role": "information", "reason": "the name of the effect"}},
    text("PRESENT BIAS", 400, 560, 64, G["accent"])])
# S9 27.4-31.3 picture next week: the two coins grow, today's shrinks
t0, t1 = 27.4, 31.3; d = t1 - t0
add(t0, t1, [img("board.png", 130, 60, 1020, 480), text("TODAY", 280, 110, 56, G["chalkline"]), text("NEXT WEEK", 700, 110, 56, G["chalkline"]),
    img("coin.png", 300, 220, 175, 175, "today9", [{"t": 0.5, "w": 175}, {"t": 2.4, "w": 80}, {"t": d, "w": 76}], "today's coin looks small now"),
    img("coin.png", 690, 220, 46, 46, "nw9a", [{"t": 0.3, "w": 46}, {"t": 2.2, "w": 150}, {"t": d, "w": 154}], "picture next week's coins"),
    img("coin.png", 860, 220, 46, 46, "nw9b", [{"t": 0.5, "w": 46}, {"t": 2.4, "w": 150}, {"t": d, "w": 154}], "picture next week's coins"),
    {"type": "arrow", "id": "ar9", "x": 470, "y": 470, "w": 300, "keys": [{"t": 1.0, "alpha": 0}, {"t": 1.6, "alpha": 1}, {"t": d, "x": 490}], "motion": {"role": "information", "reason": "look forward"}}])
# S10 31.3-end the question: Lily between one coin and two
t0, t1 = 31.3, DUR; d = t1 - t0
add(t0, t1, [text("ONE TODAY?", 80, 100, 64), text("TWO NEXT WEEK?", 760, 100, 64, G["accent"]),
    img("coin.png", 200, 260, 120, 120, "q1", cycle(d, 0.6, 260, 250, "y"), "one coin today"),
    img("coin.png", 900, 260, 120, 120, "q2", cycle(d, 0.6, 250, 260, "y"), "two coins next week"), img("coin.png", 1030, 260, 120, 120)]
    + D.person_layers("lily10", lily, 540, 200, 1.0, reason="Lily looks from one side to the other", assets=A, expr="think",
                      body_motion=[{"t": 0, "angle": -0.6}, {"t": 1.2, "angle": 0.6}, {"t": 2.2, "angle": -0.3}, {"t": d, "angle": 0}]))

sfx = [{"time": 1.25, "kind": "chime", "gain": 0.2}, {"time": 4.2, "kind": "pop", "gain": 0.2}, {"time": 5.3, "kind": "pop", "gain": 0.2}, {"time": 5.6, "kind": "pop", "gain": 0.2},
       {"time": 11.2, "name": "thud", "gain": 0.4}, {"time": 11.4, "name": "boing", "gain": 0.25}] + \
      [{"time": round(12.6 + k * 0.6, 2), "kind": "paper", "gain": 0.25} for k in range(4)] + [{"time": round(15.3 + k * 0.5, 2), "kind": "jingle", "gain": 0.2} for k in range(7)] + \
      [{"time": 20.6, "name": "sting", "gain": 0.25}, {"time": 23.2, "kind": "chime", "gain": 0.15}, {"time": 28.0, "name": "rise", "gain": 0.2}, {"time": 31.5, "name": "plink", "gain": 0.2}]
out = {"shots": shots, "sfx": sfx, "assets": A}
if STYLE == "B3": out["television"] = {"enabled": True, "intensity": 0.4}
json.dump(out, open(f"shots-{STYLE}.json", "w"), indent=0)
print(STYLE, len(shots), "shots,", len(A), "drawings")
