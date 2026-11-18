"""News explainer: Hubble photographs the dust tail of Beta Pictoris. Mia (an invented stargazer, not a researcher) asks what the viewer asks."""
import sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "motion"))
from director import Film
import worlds as Wd

f = Film(HERE.parents[1] / "stories" / "015-cats-tail-dust.json", HERE / "voice")
L, S, WD = f.line, f.next_start, f.word
f.look("mia", shirt="#4f8a5a", hair="#3a2a1e", hairStyle="long", shoes="#3c3a37", belt="#2b2622")

hill = Wd.farm("night")
hill["far"] = [{"type": "hills", "y": 660, "amp": 90, "color": "#2e3a5a"}, {"type": "hills", "y": 740, "amp": 50, "color": "#38456a"}]
hill["mid"] = [{"type": "ground", "y": 820, "color": "#3d4f62"}, {"type": "tree", "x": 220, "y": 840, "s": 1.1, "leaf": "#2f4a46"}]
hill["near"] = [{"type": "grass", "y": 950, "density": 0.3, "color": "#4a6a5a", "dark": "#2f4a46"}]
hill["ambient"] = [{"type": "glow", "lights": [[1500, 170, 220]], "color": "#cfd8ff", "depth": "far"}]
hill["particles"] = [{"preset": "fireflies", "number": 30}]
hill["look"] = {"grade": "night", "vignette": 0.5, "light": [0.5, 0.6, 0.14]}
obs = {"sky": {"top": "#10162e", "bottom": "#1b2347"},
       "far": [{"type": "wall", "y": 760, "color": "#2a3358"}],
       "mid": [{"type": "window", "x": 760, "y": 150, "w": 520, "h": 340, "glass": "#0b1030"}, {"type": "shelf", "x": 120, "y": 360, "w": 480, "n": 5},
               {"type": "planks", "y": 760, "color": "#3a3f56"}],
       "front": [{"type": "table", "x": 1180, "y": 800, "w": 640, "h": 120}],
       "near": [],
       "ambient": [{"type": "glow", "lights": [[1500, 640, 200], [400, 300, 180], [1000, 320, 200]], "color": "#8fc4ff", "depth": "mid"}],
       "particles": [{"preset": "dust", "number": 25}],
       "look": {"grade": "cool", "vignette": 0.5, "light": [0.5, 0.4, 0.14]}}
f.place("hill", hill); f.place("obs", obs)
Y = 900
f.default_cy = 640


def cut(s, i, parts):
    a = L(s, i)[0] if (s, i) != (1, 0) else 0.0
    b = S(s, i); tot = sum(p[0] for p in parts); t = a
    for k, (w, kind, kw) in enumerate(parts):
        t1 = b if k == len(parts) - 1 else round(t + (b - a) * w / tot, 3)
        sc = kw.pop("sc")
        f.shot(sc, t, t1, kind, **kw); t = t1


# 1. hilltop
t0, t1 = f.scene_span(1)
s1 = f.scene("s1", "hill", t0, t1, cast={"mia": dict(x=700, facing=1)})
f.card(0.3, 9.0, "Reported 11-13 Nov 2026: ThePrint, Nature World News", size=40, color="#e8eefc")
f.section(t0, t1, mood="mystery", motif="star", bpm=64, scale="minor", instruments=["pad", "bell"], energy=0.3)
f.prop(s1, "lant", "lantern", 560, 880, s=0.5, pop=0.8)
f.act(s1, "mia", "sit", 0.0, 3.0, emotion="neutral")
a, b = L(1, 0); cut(1, 0, [(1, "wide", dict(sc=s1, push=0.1, pan=40)), (1, "medium", dict(sc=s1, on="mia"))])
a, b = L(1, 1); cut(1, 1, [(1, "reveal", dict(sc=s1, cx=1000)), (1, "wide", dict(sc=s1, cx=800, pan=30))])
a, b = L(1, 2); f.act(s1, "mia", "look", a + 0.5, b, emotion="surprised")
cut(1, 2, [(1, "medium", dict(sc=s1, on="mia")), (1, "reveal", dict(sc=s1, cx=1100))])
a, b = L(1, 3); f.act(s1, "mia", "point", a, b, emotion="surprised")
cut(1, 3, [(1, "close", dict(sc=s1, on="mia", push=0.08)), (1, "wide", dict(sc=s1, cx=900))])

# 2. Webb saw it first
t0, t1 = f.scene_span(2)
s2 = f.scene("s2", "obs", t0, t1, cast={"mia": dict(x=900, facing=1)})
f.section(t0, t1, mood="mystery", motif="star", bpm=64, scale="minor", instruments=["pad", "bell"], energy=0.35)
f.act(s2, "mia", "walk", t0, t0 + 2.0, to=[1100, Y])
a, b = L(2, 0); cut(2, 0, [(1, "wide", dict(sc=s2, push=0.08)), (1, "medium", dict(sc=s2, on="mia"))])
a, b = L(2, 1); f.act(s2, "mia", "look", a, b, emotion="neutral")
cut(2, 1, [(1, "reveal", dict(sc=s2, cx=1000)), (1, "medium", dict(sc=s2, on="mia"))])
a, b = L(2, 2); f.act(s2, "mia", "turnAway", a + 0.5, b, emotion="worried") if False else f.act(s2, "mia", "shake", a + 0.8, b, emotion="worried")
cut(2, 2, [(1, "wide", dict(sc=s2, cx=900)), (1, "close", dict(sc=s2, on="mia"))])
a, b = L(2, 3); f.act(s2, "mia", "point", a + 0.2, b, emotion="worried")
cut(2, 3, [(1, "medium", dict(sc=s2, on="mia")), (1, "wide", dict(sc=s2, push=0.06))])

# 3. six looks
t0, t1 = f.scene_span(3)
s3 = f.scene("s3", "hill", t0, t1, cast={"mia": dict(x=1000, facing=1)})
f.section(t0, t1, mood="mystery", motif="star", bpm=68, scale="minor", instruments=["pad", "bell", "pluck"], energy=0.4)
f.prop(s3, "lant3", "lantern", 860, 880, s=0.5)
f.act(s3, "mia", "sit", t0, t0 + 1.0, emotion="neutral")
a, b = L(3, 0); f.act(s3, "mia", "count", a + 1.0, b, emotion="neutral")
cut(3, 0, [(1, "medium", dict(sc=s3, on="mia")), (1, "wide", dict(sc=s3, push=0.08))])
a, b = L(3, 1); cut(3, 1, [(1, "reveal", dict(sc=s3, cx=1100)), (1, "close", dict(sc=s3, on="mia"))])
a, b = L(3, 2); f.act(s3, "mia", "point", a + 1.5, b, emotion="neutral")
cut(3, 2, [(1, "wide", dict(sc=s3, cx=950, pan=40)), (1, "medium", dict(sc=s3, on="mia"))])
a, b = L(3, 3); f.act(s3, "mia", "armsOpen", WD(3, 3, "thousand") - 0.3, b, emotion="surprised")
cut(3, 3, [(1, "close", dict(sc=s3, on="mia", push=0.08)), (1, "reveal", dict(sc=s3, cx=900))])
f.hit(WD(3, 3, "billion"), "swell")

# 4. fluffy and dark
t0, t1 = f.scene_span(4)
s4 = f.scene("s4", "obs", t0, t1, cast={"mia": dict(x=1000, facing=1)})
f.section(t0, t1, mood="mystery", motif="star", bpm=60, scale="minor", instruments=["pad", "bell"], energy=0.3)
f.prop(s4, "grain", "pod", 1300, 700, s=1.2, pop=L(4, 1)[0] + 1.0)
a, b = L(4, 0); cut(4, 0, [(1, "wide", dict(sc=s4, push=0.08)), (1, "medium", dict(sc=s4, on="mia"))])
a, b = L(4, 1); f.act(s4, "mia", "look", a, b, emotion="neutral")
cut(4, 1, [(1, "detail", dict(sc=s4, on=(1300, 700))), (1, "medium", dict(sc=s4, on="mia"))])
a, b = L(4, 2); f.act(s4, "mia", "shake", a + 0.6, b, emotion="worried")
cut(4, 2, [(1, "close", dict(sc=s4, on="mia")), (1, "wide", dict(sc=s4, cx=1100))])

# 5. what we do not know
t0, t1 = f.scene_span(5)
s5 = f.scene("s5", "hill", t0, t1, cast={"mia": dict(x=900, facing=1)})
f.section(t0, t1, mood="hopeful", motif="star", bpm=62, scale="major", instruments=["pad", "bell"], energy=0.35)
f.act(s5, "mia", "look", t0, L(5, 2)[0], emotion="neutral")
a, b = L(5, 0); cut(5, 0, [(1, "wide", dict(sc=s5, push=0.08)), (1, "medium", dict(sc=s5, on="mia"))])
a, b = L(5, 1); f.act(s5, "mia", "crossArms", a + 0.5, b, emotion="doubt")
cut(5, 1, [(1, "close", dict(sc=s5, on="mia")), (1, "reveal", dict(sc=s5, cx=1000))])
a, b = L(5, 2); cut(5, 2, [(1, "medium", dict(sc=s5, on="mia")), (1, "wide", dict(sc=s5, cx=800, pan=30))])
a, b = L(5, 3); f.card(a, b + 1.0, "Sources and date: in the description", size=40, color="#e8eefc")
cut(5, 3, [(1, "wide", dict(sc=s5, push=0.06)), (1, "medium", dict(sc=s5, on="mia"))])
a, b = L(5, 4); f.act(s5, "mia", "nod", a + 1.0, b, emotion="happy")
cut(5, 4, [(1, "medium", dict(sc=s5, on="mia", push=0.06)), (1.3, "reveal", dict(sc=s5, cx=1100))])


# sound at every visible action, small purposeful beats where the words ask
f.sfx(0.8, "pop"); f.sfx(L(1, 2)[0] + 0.5, "sparkle"); f.sfx(L(1, 3)[0], "blip")
f.sfx(L(2, 0)[0], "whoosh"); f.sfx(L(2, 1)[0] + 1.5, "tick"); f.sfx(L(2, 2)[0] + 0.8, "blip"); f.sfx(L(2, 3)[0] + 0.2, "tap")
f.sfx(L(3, 0)[0] + 1.0, "tick"); f.sfx(L(3, 0)[0] + 2.2, "tick"); f.sfx(L(3, 2)[0] + 1.5, "tap"); f.sfx(WD(3, 3, "thousand") - 0.3, "rise")
f.sfx(L(4, 1)[0] + 1.0, "pop"); f.sfx(L(4, 2)[0] + 0.6, "blip")
f.sfx(L(5, 1)[0] + 0.5, "tap"); f.sfx(L(5, 3)[0], "tick"); f.sfx(L(5, 4)[0] + 1.0, "sparkle")
f.act(s1, "mia", "look", L(1, 0)[0] + 1.0, L(1, 0)[1], emotion="surprised")
f.act(s1, "mia", "nod", L(1, 1)[0] + 2.0, L(1, 1)[1], emotion="neutral")
f.act(s2, "mia", "look", L(2, 0)[0] + 2.5, L(2, 0)[1], emotion="neutral")
f.act(s2, "mia", "point", L(2, 2)[0] + 0.1, L(2, 2)[0] + 0.8, emotion="neutral")
f.act(s3, "mia", "look", L(3, 1)[0] + 0.5, L(3, 1)[1], emotion="neutral")
f.act(s3, "mia", "nod", L(3, 2)[0] + 0.2, L(3, 2)[0] + 1.2, emotion="neutral")
f.act(s4, "mia", "nod", L(4, 0)[0] + 1.5, L(4, 0)[1], emotion="neutral")
f.act(s4, "mia", "point", L(4, 1)[0] + 1.2, L(4, 1)[1], emotion="surprised")
f.act(s5, "mia", "nod", L(5, 0)[0] + 2.0, L(5, 0)[1], emotion="neutral")
f.act(s5, "mia", "sigh", L(5, 3)[0] + 1.0, L(5, 3)[1], emotion="neutral")
f.act(s5, "mia", "point", L(5, 4)[0] + 2.0, L(5, 4)[1], emotion="happy")
f.act(s5, "mia", "turnAway", 93.0, 95.5, emotion="neutral"); f.sfx(93.2, "step")
f.save(HERE / "film")
