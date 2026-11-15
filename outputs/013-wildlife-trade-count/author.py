"""013 wildlife trade count, B1 news explainer: python author.py  (run in the repo root) -> shots-16x9.json, shots-9x16.json"""
import os, sys, math, json, pathlib
os.environ["DRAW_INK"] = "#2b2a28"
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_lib"))
import alib as Z
import draw_kit as D
from draw_kit import svg, line, blob, poly, INK
from alib import img, text, underline, bob

RED, BLUE, GREEN, GOLD, PAPER, WOOD, GREY = "#EC4338", "#5b8fd6", "#5BA55B", "#F2B632", "#fff7e0", "#c99a6b", "#cfcfcf"
def R(x, y, w, h, fill, seed=0, wd=2.6): return poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill, seed=seed, w=wd)

def ledger():
    s = [poly([(10, 40), (300, 20), (300, 250), (10, 270)], PAPER, seed=1), poly([(300, 20), (590, 40), (590, 270), (300, 250)], PAPER, seed=2),
         line([(300, 20), (300, 250)], 3, seed=3)]
    for i in range(6):
        s.append(line([(30, 80 + i * 28), (280, 66 + i * 28)], 1.6, GREY, seed=10 + i)); s.append(line([(320, 66 + i * 28), (570, 80 + i * 28)], 1.6, GREY, seed=20 + i))
    return svg(600, 290, "".join(s))
def desk(): return svg(1280, 200, R(0, 20, 1280, 180, WOOD, 5) + line([(0, 20), (1280, 18)], 3, seed=6))
def bar(color): return svg(160, 400, R(8, 8, 144, 384, color, 7))
def crate(kind):
    s = [R(10, 30, 240, 190, WOOD, 8), line([(10, 90), (250, 90)], 2.4, seed=9), line([(10, 150), (250, 150)], 2.4, seed=10), R(80, 100, 100, 50, PAPER, 11, 2)]
    if kind == "a": s += [blob(105, 215, 0, 0, "none", w=0)]
    return svg(260, 230, "".join(s))
def paw():
    return svg(120, 120, blob(60, 78, 26, 22, INK, seed=1) + blob(26, 46, 10, 13, INK, seed=2) + blob(48, 28, 10, 13, INK, seed=3) + blob(74, 28, 10, 13, INK, seed=4) + blob(96, 46, 10, 13, INK, seed=5))
def leaf():
    return svg(120, 120, f'<path d="M20,100 Q16,30 100,18 Q104,90 20,100 Z" fill="{GREEN}" stroke="{INK}" stroke-width="3"/>' + line([(20, 100), (80, 40)], 2.4, seed=2))
def shroom():
    return svg(120, 120, f'<path d="M14,70 Q60,-10 106,70 Z" fill="{RED}" stroke="{INK}" stroke-width="3"/>' + R(48, 70, 24, 36, PAPER, 4, 2.4) + blob(40, 52, 6, 6, "#fff", seed=5, w=1.5) + blob(72, 44, 6, 6, "#fff", seed=6, w=1.5))
def circle(color, seed): return svg(380, 380, blob(190, 190, 180, 180, color, seed=seed, w=3.4))
def folder():
    return svg(200, 150, poly([(10, 30), (80, 30), (96, 12), (190, 12), (190, 140), (10, 140)], GOLD, seed=3) + line([(24, 70), (176, 70)], 2, GREY, seed=4))
def magnifier():
    return svg(200, 220, blob(80, 80, 62, 62, "#d9ecf7", seed=2, w=4) + line([(126, 126), (186, 206)], 12, INK, seed=3))
def shelf():
    s = [line([(10, 240), (730, 240)], 4, seed=1), line([(10, 130), (730, 130)], 4, seed=2)]
    for j, y in enumerate((130, 240)):
        for i in range(6):
            if j == 1 and i == 4: continue
            s.append(R(30 + i * 115, y - 80, 90, 80, WOOD, 20 + i + j * 7, 2.4))
    return svg(740, 260, "".join(s))
def dash():
    return svg(900, 140, R(10, 20, 880, 100, "#d9d9d9", 1, 3.2) + R(10, 20, 24, 100, GREEN, 2, 3))
def puzzle(color, seed): return svg(150, 150, poly([(10, 10), (60, 10), (62, 30), (86, 30), (90, 10), (140, 10), (140, 140), (10, 140)], color, seed=seed, w=3))
def laptop(): return svg(380, 260, R(40, 10, 300, 190, "#f0f0f0", 1, 3.2) + R(60, 30, 260, 150, "#d9ecf7", 2, 2) + poly([(10, 200), (370, 200), (350, 240), (30, 240)], "#e7e7e7", seed=3))
def permit(): return svg(180, 230, R(10, 10, 160, 210, PAPER, 1, 3) + R(30, 150, 70, 50, RED, 2, 2.4) + line([(30, 50), (150, 46)], 2, GREY, seed=3) + line([(30, 80), (150, 78)], 2, GREY, seed=4))
def scanner(): return svg(320, 120, R(10, 40, 300, 70, "#bdbdbd", 1, 3.2) + line([(30, 62), (290, 62)], 4, GREEN, seed=2))
def arrow_img(): return svg(200, 60, line([(10, 30), (180, 30)], 7, RED, seed=1) + line([(150, 8), (184, 30), (150, 52)], 7, RED, seed=2))
def qmark(): return svg(90, 130, f'<path d="M14,40 Q18,8 45,8 Q74,8 74,40 Q74,60 46,76 L46,92" fill="none" stroke="{RED}" stroke-width="10" stroke-linecap="round"/>' + blob(46, 118, 7, 7, RED, stroke=RED, seed=3))

def arrive(d, y0, y1, ta, amp=8):
    ks = [{"t": 0, "y": y0, "alpha": 0}, {"t": ta, "y": y1, "alpha": 1}]
    t, i = ta + 0.5, 0
    while t < d: ks.append({"t": round(t, 3), "y": y1 + (amp if i % 2 == 0 else 0)}); t += 0.5; i += 1
    ks.append({"t": d, "y": y1}); return ks

def build(ratio):
    F = Z.Film("B1", ratio, str(HERE / "voice" / "timing.json"))
    A = F.A
    for k, v in {"ledger.png": ledger(), "desk.png": desk(), "bar50.png": bar(BLUE), "bar107.png": bar(RED), "crate.png": crate(""), "paw.png": paw(), "leaf.png": leaf(),
                 "shroom.png": shroom(), "circA.png": circle("#d9ecf7", 1), "circB.png": circle("#f6d6a8", 2), "folder.png": folder(), "mag.png": magnifier(),
                 "shelf.png": shelf(), "dash.png": dash(), "pzA.png": puzzle("#d9ecf7", 3), "pzB.png": puzzle("#f6d6a8", 4), "pzC.png": puzzle("#d8ecd0", 5),
                 "laptop.png": laptop(), "permit.png": permit(), "scanner.png": scanner(), "arrow.png": arrow_img(), "q.png": qmark()}.items():
        A[k] = v
    def T(t, x, y, size, color=INK, **k): return text(t, x, y, size, color, **k)
    desk_l = lambda: img("desk.png", 0, 540, 1280, 200, bg=True)

    def S(sc, i, builder, fx=640, s=1.3, parts=None):
        a, b = F.line(sc, i)
        # stretch to the next line's start so the shots cover everything
        n = parts or max(1, round((b - a) / 3.4))
        for p in range(n):
            t0 = a + (b - a) * p / n; t1 = a + (b - a) * (p + 1) / n
            L = builder(t1 - t0, p, n)
            if t0 < 10.2: L = L + [T("REPORTED 29 OCT - 3 NOV 2026", 270, 14, 32, RED, w=760), T("SHEFFIELD UNIVERSITY + DOWN TO EARTH", 270, 54, 28, INK, w=900)]
            F.add(t0, t1, L, fx=fx, s=s)
    # ------------------------------------------------------------------ scene 1
    def s1a(d, p, n): return [desk_l(), img("ledger.png", 340, 260, 600, 290, "led", bob(d, 0.5, 260, 252), "the ledger breathes as the number lands"), T("DOUBLED", 360, 130, 110, RED, frm=0.4 if p == 0 else 0)]
    def s1b(d, p, n): return [desk_l(), img("ledger.png", 340, 300, 600, 290, "led", bob(d, 0.5, 300, 292), "the ledger holds the count"), T("107,356", 330, 110, 150, RED), T("SPECIES", 520, 270, 60, INK)]
    def s1c(d, p, n): return [desk_l(), img("folder.png", 520, 330, 220, 165, "fol", bob(d, 0.5, 330, 322), "the study folder"), T("SCIENCE ADVANCES", 300, 140, 76, INK), T("study, reported since late October", 300, 250, 40, BLUE, frm=1.0)]
    def s1d(d, p, n): return [desk_l(), img("mag.png", 340 + p * 60, 290, 220, 240, "mg", bob(d, 0.45, 290, 270), "the magnifier hunts for the answer"), T("COUNTED", 640, 170, 70, INK), T("NOT COUNTED", 640, 270, 70, RED, frm=1.2), T("UNKNOWN", 640, 370, 70, BLUE, frm=2.4)]
    S(1, 0, s1a); S(1, 1, s1b); S(1, 2, s1c); S(1, 3, s1d)
    # news chips: first 10 s (appended to the first shots below by re-adding to layer lists is awkward: they are separate extra shots layers)
    # ------------------------------------------------------------------ scene 2: before
    def s2a(d, p, n): return [desk_l(), img("bar50.png", 460, 150, 160, 400, "b50", arrive(d, 330, 150, min(1.2, d - 0.1)), "the old estimate rises", frm=0), T("ABOUT 50,000", 360, 90, 64, BLUE)]
    def s2b(d, p, n): return [desk_l(), img("bar50.png", 460, 150, 160, 400, "b50", bob(d, 0.6, 150, 156), "the old bar"), T("2022", 720, 190, 90, INK), T("IPBES", 720, 300, 80, BLUE, frm=1.0), T("intergovernmental panel", 640, 400, 38, INK, frm=2.0)]
    def s2c(d, p, n): return [desk_l(), img("bar50.png", 380, 150, 160, 400, "b50", bob(d, 0.6, 150, 156), "the old bar"), img("bar107.png", 700, 150, 160, 400, "b107", arrive(d, 330, 150, min(2.0, d * 0.7)), "the new bar towers over the old one"), T("MORE THAN DOUBLE", 340, 60, 64, RED)]
    S(2, 0, s2a); S(2, 1, s2b); S(2, 2, s2c)
    # ------------------------------------------------------------------ scene 3: crates
    def crates(d, active, nth):
        L = [desk_l()]
        for k, (nm, ic, lab, col) in enumerate((("animals", "paw.png", "ANIMALS", INK), ("plants", "leaf.png", "PLANTS", GREEN), ("fungi", "shroom.png", "FUNGI", RED))):
            x = 90 + k * 400; y = 320 - (18 if k == active else 0)
            L.append(img("crate.png", x, y, 260, 230, f"cr{k}", bob(d, 0.5, y, y - 8) if k == active else None, "the open crate", role="prop"))
            L.append(img(ic, x + 70, y + 40, 120, 120, f"ic{k}"))
            L.append(T(lab, x + 30, y - 70, 52, col))
        return L
    def s3a(d, p, n): return crates(d, 0, 0) + [T("47,685", 60, 130, 100, INK)]
    def s3b(d, p, n): return crates(d, 1, 1) + [T("49,723+", 520, 130, 100, GREEN)]
    def s3c(d, p, n): return crates(d, 2, 2) + [T("ALL THREE, ONE LOOK", 140, 130, 62, RED, w=1000)]
    S(3, 0, s3a); S(3, 1, s3b); S(3, 2, s3c)
    # ------------------------------------------------------------------ scene 4: used or traded
    def venn(d, p, n, extra):
        return [desk_l(), img("circA.png", 330, 150, 380, 380, "cA", bob(d, 0.7, 150, 158), "the circles overlap"), img("circB.png", 520, 150, 380, 380, "cB", bob(d, 0.7, 158, 150), "the circles overlap"),
                T("USED", 380, 330, 64, BLUE), T("TRADED", 640, 330, 64, RED)] + extra
    S(4, 0, lambda d, p, n: venn(d, p, n, [T("USED OR TRADED", 330, 60, 70, INK)]))
    S(4, 1, lambda d, p, n: venn(d, p, n, [T("~60,000 plants + fungi", 300, 60, 52, INK), T("includes non-trade uses", 330, 570, 44, RED, frm=1.0)]))
    S(4, 2, lambda d, p, n: venn(d, p, n, [T("KEPT APART", 420, 60, 70, RED)]))
    # ------------------------------------------------------------------ scene 5: not a doubling of trade
    def fold(d, p, n, extra, mx=420):
        L = [desk_l()]
        for k in range(4):
            L.append(img("folder.png", 150 + k * 220, 360, 200, 150, f"f{k}", bob(d, 0.6, 360, 354) if k == min(3, p) else None, "a database folder", role="prop"))
        L.append(img("mag.png", mx, 200, 200, 220, "mg5", bob(d, 0.5, 200, 188), "the magnifier checks the folders"))
        return L + extra
    S(5, 0, lambda d, p, n: fold(d, p, n, [T("MORE TRADE?", 380, 70, 72, INK), T("NOT STATED", 420, 570, 60, RED, frm=1.2)]))
    S(5, 1, lambda d, p, n: fold(d, p, n, [T("MANY DATABASES", 330, 70, 72, BLUE), T("a better count", 450, 570, 56, INK, frm=1.5)], mx=620))
    S(5, 2, lambda d, p, n: fold(d, p, n, [T("EACH CATCHES A SLICE", 260, 70, 70, INK)], mx=820))
    # ------------------------------------------------------------------ scene 6: gaps
    def ware(d, p, n, extra, qx=-1):
        L = [desk_l(), img("shelf.png", 250, 280, 740, 260, "shf", bob(d, 0.7, 280, 286), "the shelves with a gap")]
        if qx >= 0: L.append(img("q.png", 250 + qx, 150, 90, 130, "qm", bob(d, 0.4, 150, 136), "the question mark"))
        return L + extra
    S(6, 0, lambda d, p, n: ware(d, p, n, [T("OUTSIDE CITES + FISHERIES", 250, 60, 58, RED, w=1000)], 520), s=1.1)
    S(6, 1, lambda d, p, n: ware(d, p, n, [T("WILD OR BRED?", 400, 60, 80, INK)], 520), s=1.1)
    S(6, 2, lambda d, p, n: ware(d, p, n, [T("SUSTAINABLE?", 400, 60, 80, RED)], 520), s=1.1)
    S(6, 3, lambda d, p, n: ware(d, p, n, [T("ONE COUNTRY SHARES BROAD DATA", 180, 60, 56, BLUE, w=1000), T("the United States", 440, 580, 56, INK, frm=2.0)], 520), s=1.1)
    # ------------------------------------------------------------------ scene 7: watching
    def dashb(d, p, n, extra, sl=24):
        return [desk_l(), img("dash.png", 190, 320, 900, 140, "dsh", bob(d, 0.8, 320, 326), "the gauge"), ] + extra
    S(7, 0, lambda d, p, n: dashb(d, p, n, [T("A TARGET'S INDICATOR", 230, 150, 66, INK)]), s=1.0)
    S(7, 1, lambda d, p, n: dashb(d, p, n, [T("2 to 3 %", 460, 160, 130, GREEN), T("covered", 540, 500, 60, INK, frm=1.0)]), s=1.0)
    S(7, 2, lambda d, p, n: dashb(d, p, n, [T("98 %+", 470, 140, 140, RED), T("may fall outside some monitoring", 300, 500, 48, INK, frm=1.2)]), s=1.0)
    # ------------------------------------------------------------------ scene 8: uncertain
    def puz(d, p, n, extra):
        return [desk_l(), img("pzA.png", 330, 250, 150, 150, "pa", bob(d, 0.6, 250, 242), "a puzzle piece"), img("pzB.png", 480, 250, 150, 150, "pb", bob(d, 0.6, 242, 250), "a puzzle piece"),
                img("pzC.png", 630, 250, 150, 150, "pc", bob(d, 0.6, 250, 242), "a puzzle piece")] + extra
    S(8, 0, lambda d, p, n: puz(d, p, n, [T("ESTIMATES", 400, 100, 90, RED), T("the real number could be higher", 300, 470, 50, INK, frm=1.5)]))
    S(8, 1, lambda d, p, n: puz(d, p, n, [T("TOTALS ROUND DIFFERENTLY", 220, 100, 62, INK, w=1000), T("sources listed below", 400, 470, 54, BLUE, frm=1.0)]))
    # ------------------------------------------------------------------ scene 9: proposals
    def prop(d, p, n, extra, k=0):
        L = [desk_l(), img("laptop.png", 120, 250, 380, 260, "lp", bob(d, 0.6, 250, 242) if k == 1 else None, "the laptop"), img("permit.png", 580, 300, 180, 230, "pm", bob(d, 0.6, 300, 292) if k == 0 else None, "the permit"),
             img("scanner.png", 830, 380, 320, 120, "sc", bob(d, 0.5, 380, 374) if k == 2 else None, "the scanner")]
        return L + extra
    S(9, 0, lambda d, p, n: prop(d, p, n, [T("STANDARD RECORDS", 120, 60, 58, INK, from_=None) if False else T("STANDARD RECORDS", 120, 60, 58, INK), T("E-PERMITS", 120, 150, 58, BLUE, frm=2.0), T("DOCUMENT CHECKS", 120, 560, 58, GREEN, frm=4.5, w=1000)], k=p % 3))
    S(9, 1, lambda d, p, n: prop(d, p, n, [T("RECOMMENDATIONS", 200, 90, 80, INK), T("nothing decided", 400, 570, 60, RED, frm=1.0)], k=1))
    # ------------------------------------------------------------------ scene 10: still unknown
    def fin(d, p, n, extra):
        return [desk_l(), img("ledger.png", 340, 300, 600, 290, "led", bob(d, 0.6, 300, 294), "the ledger waits"), T("107,356", 330, 110, 150, RED)] + extra
    S(10, 0, lambda d, p, n: fin(d, p, n, [T("HOW MUCH IS SUSTAINABLE?", 190, 260, 56, INK, w=1000)]))
    S(10, 1, lambda d, p, n: fin(d, p, n, [T("sources = the reference", 340, 260, 56, BLUE, w=1000)]))
    S(10, 2, lambda d, p, n: fin(d, p, n, [T("WHICH GAP FIRST?", 300, 260, 70, RED)]))
    return F

def fill_gaps(F):
    """shots cover 0..DUR with no gaps: stretch each shot to the next one's start; first starts at 0; last ends at DUR"""
    F.shots.sort(key=lambda s: s["start"])
    for a, b in zip(F.shots, F.shots[1:]): a["end"] = b["start"]
    F.shots[0]["start"] = 0.0; F.shots[-1]["end"] = F.DUR

if __name__ == "__main__":
    for ratio, name in (("16:9", "shots-16x9.json"), ("9:16", "shots-9x16.json")):
        F = build(ratio)
        # news chips on the first shots (date + source within 10 s)
        for sh in F.shots:
            if sh["start"] < 10:
                pass
        F.sfx = [{"time": 0.6, "name": "sting", "gain": 0.2}, {"time": 4.3, "kind": "chime", "gain": 0.2}]
        fill_gaps(F)
        F.write(str(HERE / name))
