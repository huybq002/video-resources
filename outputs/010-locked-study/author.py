"""010 locked study, B3 fair-play mystery: python outputs/010-locked-study/author.py -> shots-16x9.json, shots-9x16.json"""
import os, sys, math, json, pathlib
os.environ["DRAW_INK"] = "#e9eaec"
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_lib"))
import alib as Z
import draw_kit as D
from draw_kit import svg, line, blob, poly, INK, cycle
from alib import img, text, bob

STORY = json.load(open(HERE.parents[1] / "stories" / "010-locked-study.json"))
KEEP = {int(k): v for k, v in json.load(open(HERE / "keep.json")).items()}   # short cut: new line index -> original index (overlay texts are keyed by the original)
SCN = {x["id"]: x for x in STORY["scenes"]}
G1, G2, G3, G4, G5, G6, G7 = "#e9eaec", "#d3d6db", "#a7acb3", "#7d838b", "#5b6067", "#3a3e44", "#2a2d31"
EXPR = {"surprise": "surprise", "shock": "surprise", "worry": "worry", "fear": "worry", "angry": "angry", "frustrated": "angry", "doubt": "doubt", "confused": "doubt",
        "think": "think", "happy": "smile", "joy": "smile", "excited": "smile", "laugh": "smile", "proud": "smile", "relief": "smile", "sad": "worry", "tired": "neutral", "calm": "neutral", "neutral": "neutral"}
def ch(name, **k): return dict(name=name, style="b2", skin="#eceef1", **k)
CAST = {
    "kiri": ch("kiri", shirt=G1, sleeve=G1, hair=G2, hair_style="short", shoes=G2),
    "hana": ch("hana", shirt=G3, sleeve=G3, skirt=G5, hair=G2, hair_style="ponytail", shoes=G3),
    "dale": ch("dale", shirt=G4, sleeve=G4, vest=G6, hair_style="bald", moustache=True, moustache_color=G2, shoes=G3),
    "mara": ch("mara", shirt=G3, sleeve=G3, skirt=G6, hair=G3, hair_style="bun", shoes=G3),
    "felix": ch("felix", shirt=G5, sleeve=G5, hair=G1, hair_style="short", shoes=G4),
    "voss": ch("voss", shirt=G2, sleeve=G2, vest=G5, hair_style="bald", moustache=True, moustache_color=G1, shoes=G4),
}
def R(x, y, w, h, fill, seed=0, wd=2.6): return poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill, seed=seed, w=wd)
def floor(extra=""): return svg(1280, 720, line([(0, 500), (1280, 498)], 2.6, seed=1) + extra)

def hall(): return floor(R(820, 110, 210, 390, G5, 2) + R(850, 140, 70, 150, G6, 3) + R(930, 140, 70, 150, G6, 4) + R(850, 310, 70, 150, G6, 5) + R(930, 310, 70, 150, G6, 6)
                         + blob(1005, 330, 8, 8, G2, seed=7) + R(1012, 346, 4, 14, G1, 8, 1) + line([(150, 100), (150, 330)], 3, seed=9) + poly([(110, 330), (190, 330), (170, 380), (130, 380)], G4, seed=10)
                         + R(300, 130, 120, 160, G6, 11) + blob(360, 210, 30, 40, G4, seed=12))
def study(): return floor(R(380, 380, 560, 36, G5, 2) + R(400, 416, 26, 84, G5, 3) + R(894, 416, 26, 84, G5, 4) + R(560, 366, 160, 14, G3, 5, 2) + R(700, 312, 40, 54, G4, 6) + line([(720, 312), (720, 270)], 3, seed=7) + poly([(690, 270), (750, 270), (736, 240), (704, 240)], G3, seed=8)
                          + R(1000, 160, 220, 14, G5, 9) + blob(1110, 120, 36, 36, G2, seed=10) + line([(1110, 120), (1110, 96)], 2.4, seed=11) + line([(1110, 120), (1130, 130)], 2.4, seed=12)
                          + R(80, 120, 220, 220, G6, 13) + line([(190, 120), (190, 340)], 2.4, seed=14) + line([(80, 230), (300, 230)], 2.4, seed=15) + R(180, 224, 20, 12, G2, 16, 2))
def hall2(): return floor(R(640, 340, 260, 24, G5, 2) + R(660, 364, 20, 136, G5, 3) + R(860, 364, 20, 136, G5, 4) + R(720, 300, 80, 40, G4, 5) + blob(760, 290, 14, 14, G2, seed=6)
                          + R(950, 380, 200, 120, G6, 7) + R(970, 330, 160, 60, G5, 8) + R(100, 120, 200, 260, G6, 9) + blob(200, 200, 40, 50, G4, seed=10))
def kitchen(): return floor(R(380, 380, 560, 30, G5, 2) + R(400, 410, 26, 90, G5, 3) + R(894, 410, 26, 90, G5, 4) + blob(560, 360, 50, 24, G3, seed=5) + R(540, 340, 100, 20, G4, 6) + line([(760, 100), (760, 220)], 3, seed=7) + blob(760, 250, 40, 40, G4, seed=8)
                            + line([(900, 100), (900, 200)], 3, seed=9) + blob(900, 230, 32, 32, G3, seed=10) + "".join(blob(700 + i * 36, 372, 5, 14, G2, seed=20 + i, w=1.6) for i in range(4)))
def cinema(): return floor(R(780, 200, 400, 300, G5, 2) + R(810, 240, 340, 90, G6, 3) + R(830, 350, 300, 20, G4, 4) + R(100, 110, 150, 230, G6, 5) + R(280, 110, 150, 230, G4, 6) + R(460, 110, 150, 230, G6, 7))
def stub(): return svg(160, 100, poly([(10, 14), (150, 10), (150, 90), (10, 86)], G2, seed=1) + line([(70, 12), (70, 88)], 2, G4, seed=2))
def key_img(): return svg(200, 100, blob(40, 50, 28, 28, "none", seed=1, w=5) + line([(68, 50), (186, 50)], 7, G2, seed=2) + line([(150, 50), (150, 74)], 6, G2, seed=3) + line([(172, 50), (172, 70)], 6, G2, seed=4))
def wax(): return svg(120, 120, blob(60, 60, 30, 24, G1, seed=1, w=3) + blob(54, 52, 10, 8, G3, stroke=G3, seed=2, w=1))
def watch_img(): return svg(300, 300, blob(150, 150, 90, 90, G6, seed=1, w=5) + blob(150, 150, 74, 74, G1, seed=2, w=3) + line([(150, 150), (150, 100)], 6, G7, seed=3) + line([(150, 150), (190, 170)], 6, G7, seed=4) + R(130, 20, 40, 40, G4, 5, 3) + R(130, 240, 40, 40, G4, 6, 3))
def clock_img(): return svg(300, 300, blob(150, 150, 120, 120, G4, seed=1, w=5) + blob(150, 150, 100, 100, G1, seed=2, w=3) + line([(150, 150), (150, 80)], 6, G7, seed=3) + line([(150, 150), (210, 180)], 6, G7, seed=4))
def spool(): return svg(120, 140, R(20, 10, 80, 14, G3, 1) + R(20, 116, 80, 14, G3, 2) + R(34, 24, 52, 92, G2, 3) + line([(34, 40), (86, 50)], 2, G4, seed=4))
def bag(): return svg(260, 200, R(20, 70, 220, 120, G5, 1) + line([(60, 70), (80, 20), (180, 20), (200, 70)], 8, G3, seed=2) + R(110, 110, 40, 30, G3, 3, 2))
def manuscript(): return svg(300, 220, R(10, 10, 280, 200, G1, 1, 3) + "".join(line([(34, 50 + i * 26), (266, 46 + i * 26)], 1.8, G4, seed=5 + i) for i in range(6)))
def frame_close(): return svg(520, 640, R(60, 20, 120, 600, G5, 1, 3.4) + R(180, 220, 300, 24, G3, 2, 3.4) + blob(180, 234, 18, 18, G1, seed=3, w=3) + blob(168, 226, 5, 5, G3, stroke=G3, seed=4, w=1))
def trick(state):
    th = []
    s = [R(40, 20, 40, 480, G5, 1, 3), R(80, 20, 300, 480, G6, 2, 3.4), R(80, 14, 300, 14, G7, 3), blob(366, 280, 8, 8, G2, seed=4)]
    ang = {1: -0.5, 2: -0.5, 3: 0, 4: 0}[state]
    bx, by = 120, 260; ex = bx + 140 * math.cos(ang); ey = by + 140 * math.sin(ang)
    s.append(line([(bx, by), (ex, ey)], 12, G2, seed=5)); s.append(blob(bx, by, 7, 7, G3, seed=6, w=2))
    s.append(blob(60, 14, 14, 14, G1, seed=7, w=2.6))            # wax guide on the frame
    if state in (1, 2): th = [(ex, ey), (ex + 10, 150), (60, 14), (20, 14), (20, 120)]
    if state == 3: th = [(ex, ey), (ex + 40, 160), (60, 14), (20, 14), (20, 60)]
    if th: s.append(line(th, 3, "#9fc2ff" if False else G2, seed=8, amp=0.4))
    ky = {1: 190, 2: 190, 3: 120, 4: 440}[state]
    if state != 4: s.append(blob(ex + 4, ky + 40, 20, 20, "none", seed=9, w=4))
    else: s.append(R(90, 470, 260, 24, G4, 10, 3)); s.append(blob(150, 458, 20, 14, "none", seed=9, w=4)); s.append(line([(170, 458), (230, 458)], 5, G2, seed=11))
    return svg(420, 520, "".join(s))

def build(ratio):
    F = Z.Film("B3", ratio, str(HERE / "voice" / "timing.json")); A = F.A
    for k, v in {"hall.png": hall(), "study.png": study(), "hall2.png": hall2(), "kitchen.png": kitchen(), "cinema.png": cinema(), "stub.png": stub(), "key.png": key_img(), "wax.png": wax(),
                 "watch.png": watch_img(), "clock.png": clock_img(), "spool.png": spool(), "bag.png": bag(), "ms.png": manuscript(), "frame.png": frame_close(),
                 "t1.png": trick(1), "t2.png": trick(2), "t3.png": trick(3), "t4.png": trick(4)}.items(): A[k] = v
    lines = {(s["id"], i): l for s in STORY["scenes"] for i, l in enumerate(s["lines"])}
    def T(t, x, y, size, color=G1, **k): return text(t, x, y, size, color, **k)

    def people(d, who, e, pos, s=1.0, ys=170):
        L = []
        for nm, x in pos.items():
            sp = (who == nm); ex = EXPR.get(e, "neutral") if sp else "neutral"
            L += D.person_layers(nm, CAST[nm], x, ys, s, expr=ex, reason=f"{nm} acts" if sp else f"{nm} listens", assets=A,
                                 arm_r=cycle(d, 0.55, -0.4, -1.1) if sp else cycle(d, 1.1, -0.28, -0.4), head=cycle(d, 0.8, 0, 0.12 if sp else 0.05))
        return L

    def beats(sc, i):
        a, b = F.line(sc, i); n = max(1, round((b - a) / 3.4))
        return [(a + (b - a) * p / n, a + (b - a) * (p + 1) / n, p, n) for p in range(n)]

    def scene(sc, bg, pos, extras=None, s=1.0, ps=1.2, bgxy=(0, 0, 1280, 720)):
        for i in range(len(SCN[sc]["lines"])):
            l = lines[(sc, i)]; ex = (extras or {}).get(KEEP[sc][i])
            for t0, t1, p, n in beats(sc, i):
                d = t1 - t0
                F.add(t0, t1, [img(bg, *bgxy, bg=True)] + people(d, l["who"], l["emote"], pos, s) + (ex(d, p, n) if ex else []), fx=640, s=ps)

    def close(sc, i, layers_fn, ps=1.2):
        for t0, t1, p, n in beats(sc, i): F.add(t0, t1, layers_fn(t1 - t0, p, n), fx=640, s=ps)

    CH = lambda t, x=40, y=30, size=52, col=G1, w=1200: T(t, x, y, size, col, w=w)
    # 1 the locked door: Dale, Hana, Kiri in the hallway
    P1 = {"dale": 150, "hana": 380, "kiri": 580}
    scene(1, "hall.png", P1, {0: lambda d, p, n: [CH("LOCKED FROM INSIDE")], 1: lambda d, p, n: [CH("HE NEVER OPENED IT")], 2: lambda d, p, n: [CH("9:00 - 10:30")],
                              3: lambda d, p, n: [CH("THE DOOR WAS FORCED")], 4: lambda d, p, n: [CH("KEY ON THE DESK · WINDOW SHUT", size=44)], 5: lambda d, p, n: [CH("IMPOSSIBLE?")], 6: lambda d, p, n: [CH("SOMETHING IS HIDDEN")]})
    # 2 the study
    P2 = {"hana": 160, "kiri": 450, "dale": 1000}
    scene(2, "study.png", P2, {0: lambda d, p, n: [CH("KIRI, 12")], 1: lambda d, p, n: [img("key.png", 600, 330, 80, 40, "k2", bob(d, 0.5, 330, 322), "the key on the desk"), CH("DESK · KEY · CLOCK · DOOR", size=44)],
                               2: lambda d, p, n: [CH("A TIDY DESK")], 3: lambda d, p, n: [CH("A THIN GAP ABOVE THE DOOR", size=44)], 4: lambda d, p, n: [CH("WATCH STOPPED: 9:40")], 5: lambda d, p, n: [CH("THE CLOCK STILL RUNS")],
                               6: lambda d, p, n: [CH("DIFFERENT CLOCKS?")], 7: lambda d, p, n: [CH("REMEMBER THE WATCH")]})
    # 3 Dr. Voss
    P3 = {"hana": 160, "voss": 420}
    scene(3, "hall2.png", P3, {0: lambda d, p, n: [CH("THREE ALIBIS")], 1: lambda d, p, n: [CH("DR. VOSS · LEFT AT 9:20")], 2: lambda d, p, n: [CH("GOODNIGHT IN THE HALL")], 3: lambda d, p, n: [CH("PHONE LOG: 9:40")],
                              4: lambda d, p, n: [img("bag.png", 960, 340, 200, 154, "bag", bob(d, 0.6, 340, 332), "the doctor's bag"), img("spool.png", 1020, 230, 70, 82, "sp", bob(d, 0.5, 230, 222), "a spool of blue thread"), CH("BOTTLES · THREAD · WAX")],
                              5: lambda d, p, n: [CH("A PHONE LOG. SOLID.")]})
    P4 = {"hana": 160, "mara": 480}
    scene(4, "kitchen.png", P4, {0: lambda d, p, n: [CH("MARA · SECRETARY")], 1: lambda d, p, n: [CH("9:00 - 10:00 · KITCHEN")], 2: lambda d, p, n: [CH("A LETTER, UNSEEN")], 3: lambda d, p, n: [CH("WHAT WAS IN IT?")],
                                 4: lambda d, p, n: [CH("THE COOK AGREES")], 5: lambda d, p, n: [CH("EVERYONE IS COVERED?")], 6: lambda d, p, n: [CH("NOT YET")]})
    P5 = {"dale": 160, "felix": 470, "kiri": 800}
    scene(5, "cinema.png", P5, {0: lambda d, p, n: [CH("FELIX · NEPHEW")], 1: lambda d, p, n: [CH("LEFT AT 8:50")], 2: lambda d, p, n: [CH("MOTIVE + ALIBI")],
                                3: lambda d, p, n: [img("stub.png", 440, 90, 160, 100, "st", bob(d, 0.6, 90, 82), "the ticket stub"), CH("TICKET: 9:00", 640, 100)], 4: lambda d, p, n: [CH("THE USHER CONFIRMS")],
                                5: lambda d, p, n: [CH("3 PEOPLE · 3 ALIBIS · 1 DOOR", size=44)], 6: lambda d, p, n: [CH("SOMEONE MADE A PLAN")]})
    # 6 three clues: big close-ups appear one by one
    def clue_scene(sc, i, show):
        def f(d, p, n):
            L = [CH(show[0])]
            if "wax" in show[1]: L += [img("frame.png", 380, 40, 420, 518, "fr", bob(d, 0.6, 40, 32), "the door frame with the wax drop"), img("wax.png", 520, 215, 90, 90, "wx", bob(d, 0.4, 215, 207), "the wax drop")]
            if "key" in show[1]: L += [img("key.png", 400, 280, 480, 240, "ky", bob(d, 0.6, 280, 270), "the key and its blue fibre"), CH("BLUE FIBRE", 520, 560, 54, G2)]
            if "watch" in show[1]: L += [img("watch.png", 240, 150, 360, 360, "wt", bob(d, 0.6, 150, 142), "the stopped watch"), img("clock.png", 700, 150, 360, 360, "ck", bob(d, 0.5, 150, 158), "the clock still runs"), CH("STOPPED", 290, 560, 50, G2, w=360), CH("RUNNING", 740, 560, 50, G2, w=360)]
            if "none" in show[1]: L += [img("frame.png", 140, 70, 300, 370, "f6", bob(d, 0.6, 70, 62), "clue one"), img("key.png", 480, 230, 300, 150, "k6", bob(d, 0.6, 230, 222), "clue two"), img("watch.png", 860, 120, 220, 220, "w6", bob(d, 0.6, 120, 112), "clue three")]
            return L
        close(sc, i, f)
    N = lambda sc, o: KEEP[sc].index(o)
    clue_scene(6, N(6, 2), ("CLUE 1 · RED WAX", "wax")); clue_scene(6, N(6, 3), ("CLUE 2 · BLUE FIBRE", "key"))
    clue_scene(6, N(6, 4), ("CLUE 3 · THE WATCH", "watch")); clue_scene(6, N(6, 5), ("WHO MADE A PLAN?", "none"))
    P7 = {"hana": 160, "kiri": 450}
    for i, o in enumerate(KEEP[7]):
        t = ["THE WAX FIRST", "NOT BY ACCIDENT", "THE DOCTOR'S BAG?", "WHAT ELSE?"][o]; l = lines[(7, i)]
        for t0, t1, p, n in beats(7, i):
            d = t1 - t0
            F.add(t0, t1, [img("frame.png", 760, 30, 340, 420, "fr7", bob(d, 0.6, 30, 24), "the door frame with the wax"), img("wax.png", 855, 185, 70, 70, "wx7", bob(d, 0.4, 185, 179), "the wax drop"), CH(t, 40, 30, 54, G1, w=700)]
                  + people(d, l["who"], l["emote"], P7), fx=640, s=1.2)
    for i, o in enumerate(KEEP[8]):
        t = ["THE FIBRE", "A SPOOL LIKE HIS", "THE THREAD TOUCHED THE KEY", "WHY THE RING?"][o]; l = lines[(8, i)]
        for t0, t1, p, n in beats(8, i):
            d = t1 - t0
            F.add(t0, t1, [img("key.png", 760, 250, 400, 200, "k8", bob(d, 0.6, 250, 242), "the key with its blue fibre"), img("spool.png", 1000, 80, 100, 117, "s8", bob(d, 0.5, 80, 72), "the matching spool"), CH(t, 40, 30, 54, G1, w=700)]
                  + people(d, l["who"], l["emote"], P7), fx=640, s=1.2)
    for i, o in enumerate(KEEP[9]):
        t = ["STOPPED AT 9:40", "STOPPED BY HAND", "WHO NEEDS 9:40?", "FELIX · MARA: SAFE", "VOSS: ALIBI FROM 9:40", "THE TRUE TIME IS HIDDEN"][o]
        l = lines[(9, i)]; pos = {"hana": 120, "kiri": 400} if o < 5 else {"dale": 120, "kiri": 400}
        for t0, t1, p, n in beats(9, i):
            d = t1 - t0
            F.add(t0, t1, [img("watch.png", 700, 120, 300, 300, "w9", bob(d, 0.6, 120, 112), "the stopped watch"), img("clock.png", 1000, 150, 220, 220, "c9", bob(d, 0.5, 150, 158), "the clock runs"), CH(t, 40, 30, 54, G1, w=700)]
                  + people(d, l["who"], l["emote"], pos), fx=640, s=1.1)
    # 10 the trick: four states of the re-enactment drawing, stepping through the lines
    stepmap = {0: 1, 1: 2, 2: 2, 3: 3, 4: 4, 5: 4, 6: 4, 7: 4, 8: 4}; steptxt = {0: "STEP 1 · THE BAR IS LIFTED", 1: "STEP 2 · THREAD THROUGH THE RING", 2: "OVER THE WAX GUIDE", 3: "STEP 3 · PULL: THE BAR DROPS", 4: "STEP 4 · LET GO", 5: "A FIBRE · A DROP OF WAX", 6: "A HARMLESS TRICK", 7: "NEVER LOCKED FROM INSIDE", 8: "HARD TO FOOL A CLOCK"}
    for i, o in enumerate(KEEP[10]):
        l = lines[(10, i)]
        for t0, t1, p, n in beats(10, i):
            d = t1 - t0; st = stepmap[o]
            L = [img(f"t{st}.png", 760, 90, 420, 520, "trk", bob(d, 0.5, 90, 82), "the re-enactment drawing"), CH(steptxt[o], 40, 30, 50, G1, w=1200)]
            pos = {"kiri": 250} if o < 6 else ({"hana": 150, "kiri": 420} if o == 6 else ({"dale": 150, "kiri": 420}))
            F.add(t0, t1, L + people(d, l["who"], l["emote"], pos), fx=640, s=1.1)
    P11 = {"dale": 140, "voss": 440, "kiri": 740}
    scene(11, "hall2.png", P11, {0: lambda d, p, n: [CH("OPEN YOUR BAG")], 1: lambda d, p, n: [img("spool.png", 1010, 240, 90, 105, "sp11", bob(d, 0.5, 240, 232), "the matching spool"), CH("SAME THREAD · SAME WAX")], 2: lambda d, p, n: [CH("THE PHONE CALL AT 9:40")],
                                 3: lambda d, p, n: [CH("THE CLOCK IS HONEST")], 4: lambda d, p, n: [CH("HALF THE VILLAGE?")], 5: lambda d, p, n: [CH("NOT THAT WAX")]})
    P12 = {"hana": 150, "kiri": 430}
    scene(12, "study.png", P12, {0: lambda d, p, n: [CH("THE MOTIVE")], 1: lambda d, p, n: [img("ms.png", 700, 250, 300, 220, "ms", bob(d, 0.6, 250, 242), "the manuscript"), CH("NOT HIS OWN WORK")], 2: lambda d, p, n: [CH("A CONFESSION")],
                                 3: lambda d, p, n: [CH("A DOOR NOBODY COULD OPEN")], 4: lambda d, p, n: [CH("ALL BECAUSE OF A THREAD")], 5: lambda d, p, n: [CH("WHICH CLUE FIRST?")]})
    return F

def fill_gaps(F):
    F.shots.sort(key=lambda s: s["start"])
    for a, b in zip(F.shots, F.shots[1:]): a["end"] = b["start"]
    F.shots[0]["start"] = 0.0; F.shots[-1]["end"] = F.DUR

if __name__ == "__main__":
    for ratio, name in (("16:9", "shots-16x9.json"), ("9:16", "shots-9x16.json")):
        F = build(ratio); F.sfx = [{"time": 1.0, "name": "sting", "gain": 0.25}]
        fill_gaps(F); F.write(str(HERE / name), television={"enabled": True, "intensity": 0.4})
