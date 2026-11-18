"""Director's toolkit: write a hezb-motion film.json from a story, its voice timing and its word timings.

A film is directed beat by beat. For every line you decide WHAT HAPPENS (a verb with a purpose: he packs, he walks out,
the father hands over the bag, coins spill, the door is locked, he counts the last coin), WHO WE SEE and HOW WE SEE IT
(wide to place us, medium for an action, close for a feeling, an insert for an object, a tracking shot for a journey),
and what the WORLD does around it (rain starts, birds scatter, the lanterns swing when the door slams).

    from director import Film
    f = Film("outputs/<id>/story.json", "outputs/<id>/voice")
    f.place("farm", FARM_SPEC)
    s1 = f.scene("s1", "farm", *f.scene_span(1), cast={"father": dict(x=1250), "younger": dict(x=600)})
    a, b = f.line(1, 4)                                   # start/end of scene 1 line 4
    f.act(s1, "younger", "beg", a, b, emotion="worried")
    f.shot(s1, a, b, "medium", on="younger")
    f.save("outputs/<id>/film")                           # writes film.json (+ copies models)

Verbs (rig.js): walk run (to=[x,y], open=True arms open, carry=True), give take beg point wave cheer toast drink eat count
sigh shout armsOpen carry look nod shake turnAway crossArms dig kneel sit despair hug face(dir=+-1).
Shot kinds: wide, two, medium, close, insert3d, track, over (over the shoulder), reveal (pull out), detail (a point).
"""
import json, math, os, re, shutil, pathlib

ACTOR_H = 360


class Film:
    def __init__(self, story, voice, fps=30, size=(1920, 1080)):
        self.story = json.load(open(story, encoding="utf-8"))
        vd = pathlib.Path(voice)
        self.timing = json.load(open(vd / "timing.json", encoding="utf-8"))
        wp = vd / "words.json"
        self.words = json.load(open(wp, encoding="utf-8")) if wp.exists() else []
        self.fps, self.size = fps, list(size)
        self.duration = round(self.timing["duration"], 3)
        self.places, self.scenes, self.shots, self.captions, self.cards, self.events, self.models = {}, [], [], [], [], [], {}
        self.cast = {}
        self.score = {"root": 50, "sections": [], "hits": []}
        # index lines per scene
        self.lines, k = {}, 0
        for sc in self.story["scenes"]:
            for i, ln in enumerate(sc["lines"]):
                tl = self.timing["lines"][k]
                self.lines[(sc["id"], i)] = dict(t0=round(tl["start"], 3), t1=round(tl["end"], 3), who=ln["who"], text=ln["t"], emote=ln.get("emote", ""), k=k)
                k += 1
        self._k_end = k

    # ---------------------------------------------------------------- time
    def line(self, scene, i):
        L = self.lines[(scene, i)]; return L["t0"], L["t1"]

    def next_start(self, scene, i):
        L = self.lines[(scene, i)]; k = L["k"] + 1
        return round(self.timing["lines"][k]["start"], 3) if k < len(self.timing["lines"]) else self.duration

    def word(self, scene, i, text, which=0):
        """time (t0) of a spoken word in a line, e.g. f.word(6, 0, 'ran') -> the run starts on 'ran'"""
        k = self.lines[(scene, i)]["k"]; hits = [w for w in self.words if w.get("line") == k and re.sub(r"\W", "", w["w"].lower()) == text.lower()]
        if hits: return hits[min(which, len(hits) - 1)]["t0"]
        a, b = self.line(scene, i); toks = self.lines[(scene, i)]["text"].lower().split()
        idx = next((j for j, tk in enumerate(toks) if re.sub(r"\W", "", tk) == text.lower()), 0)
        return round(a + (b - a) * idx / max(1, len(toks)), 3)

    def scene_span(self, scene):
        idx = [v for (s, i), v in self.lines.items() if s == scene]
        t0 = min(v["t0"] for v in idx); last = max(idx, key=lambda v: v["k"])
        k = last["k"] + 1; t1 = round(self.timing["lines"][k]["start"], 3) if k < len(self.timing["lines"]) else self.duration
        return (0.0 if scene == self.story["scenes"][0]["id"] else t0), t1

    # ---------------------------------------------------------------- world
    def look(self, who, **look): self.cast[who] = look

    def place(self, name, spec): self.places[name] = spec

    def scene(self, sid, place, t0, t1, cast, **kw):
        sc = dict(id=sid, place=place, t0=round(t0, 3), t1=round(t1, 3), cast={k: {"y": 900, **v} for k, v in cast.items()}, actions=[], props=[], spills=[], hangers=[], ambient=[], particles=[], **kw)
        self.scenes.append(sc); return sc

    def act(self, sc, who, verb, t0, t1, **kw):
        sc["actions"].append(dict(who=who, verb=verb, t0=round(t0, 3), t1=round(t1, 3), **kw)); return sc["actions"][-1]

    def prop(self, sc, pid, prop, x, y, s=0.4, **kw):
        sc["props"].append(dict(id=pid, prop=prop, x=x, y=y, s=s, **kw)); return sc["props"][-1]

    def spill(self, sc, sid, t, prop="coin", n=6, frm=(960, 600), vel=(0, -200), floor=905, **kw):
        sc["spills"].append(dict(id=sid, t=round(t, 3), prop=prop, n=n, **{"from": list(frm)}, vel=list(vel), floor=floor, **kw)); self.sfx(t + 0.35, "coins")

    def hanger(self, sc, hid, x, y, length=120, gusts=(), **kw):
        sc["hangers"].append(dict(id=hid, x=x, y=y, len=length, gusts=[dict(t=round(t, 3), force=f) for t, f in gusts], **kw))

    def model(self, name, url): self.models[name] = url

    # ---------------------------------------------------------------- camera
    def _pos(self, sc, who, t=None):
        """where the actor is at time t (walks and runs are followed along their path, so a shot that starts mid-walk aims at him)"""
        c = sc["cast"][who]; x, y, s = c["x"], c.get("y", 900), c.get("s", 1)
        for a in sorted(sc["actions"], key=lambda a: a["t0"]):
            if a["who"] != who or a["verb"] not in ("walk", "run") or "to" not in a: continue
            tx, ty = a["to"]
            if t is None or a["t1"] <= t: x, y = tx, ty
            elif a["t0"] < t:
                u = (t - a["t0"]) / max(0.01, a["t1"] - a["t0"]); x, y = x + (tx - x) * u, y + (ty - y) * u
        return x, y, s

    def shot(self, sc, t0, t1, kind="wide", on=None, push=0.08, pan=0, transition=None, look=None, hide=None, **kw):
        W, H = self.size
        tm = (t0 + t1) / 2                       # aim where people are in the middle of the shot
        cam = {}
        if kind in ("wide", "reveal"):
            cx = kw.get("cx", 960); cy = kw.get("cy", getattr(self, "default_cy", 560))
            z0, z1 = (1.0, 1.0 + push) if kind == "wide" else (1.6, 1.0)
            cam = dict(z=[z0, z1], c=[[cx - pan, cy], [cx + pan, cy]])
        elif kind in ("medium", "close", "detail", "over"):
            who = on if isinstance(on, str) else None
            if who: x, y, s = self._pos(sc, who, tm)
            else: x, y, s = on[0], on[1], 1
            z = {"medium": 1.55, "close": 2.35, "detail": 2.8, "over": 1.7}[kind]
            fy = y - ACTOR_H * s * (0.55 if kind == "medium" else 0.86 if kind == "close" else 0.6) if who else y
            if kind == "over" and kw.get("from"): fx0 = self._pos(sc, kw["from"], tm)[0]; x = x + (fx0 - x) * 0.32
            cam = dict(z=[z, z + push * (1.6 if kind == "close" else 1)], c=[[x - pan, fy], [x + pan, fy]])
        elif kind == "two":
            a, b = on; xa, ya, sa = self._pos(sc, a, tm); xb, yb, sb = self._pos(sc, b, tm)
            mx, my = (xa + xb) / 2, (ya + yb) / 2 - ACTOR_H * 0.5
            z = max(1.0, min(1.6, 1500 / max(300, abs(xa - xb) + 520)))
            cam = dict(z=[z, z + push], c=[[mx - pan, my], [mx + pan, my]])
        elif kind == "track":
            cam = dict(z=[kw.get("z", 1.45)] * 2, follow=on, lead=kw.get("lead", 160), c=[[960, 540]])
        if kw.get("shake"): cam["shake"] = kw["shake"]
        if kw.get("ease"): cam["ease"] = kw["ease"]
        s = dict(t0=round(t0, 3), t1=round(t1, 3), scene=sc["id"], cam=cam, kind=kind)
        if transition: s["transition"] = transition if isinstance(transition, dict) else dict(name=transition, dur=0.6)
        if look: s["look"] = look
        if hide: s["hide"] = hide
        self.shots.append(s); return s

    def insert3d(self, sc, t0, t1, model, transition="fade", **kw):
        s = dict(t0=round(t0, 3), t1=round(t1, 3), scene=sc["id"], insert3d=dict(model=model, **kw), kind="insert3d")
        if transition: s["transition"] = dict(name=transition, dur=0.5) if isinstance(transition, str) else transition
        self.shots.append(s); return s

    # ---------------------------------------------------------------- words, sound
    def card(self, t0, t1, text, **kw): self.cards.append(dict(t0=round(t0, 3), t1=round(t1, 3), text=text, **kw))

    def sfx(self, t, name, gain=0.5): self.events.append(dict(t=round(t, 3), sfx=name, gain=gain))

    def section(self, t0, t1, **kw): self.score["sections"].append(dict(t0=round(t0, 3), t1=round(t1, 3), **kw))

    def hit(self, t, kind): self.score["hits"].append(dict(t=round(t, 3), kind=kind))

    def _captions(self, max_words=7):
        caps = []
        for (sid, i), L in sorted(self.lines.items(), key=lambda kv: kv[1]["k"]):
            ws = [w for w in self.words if w.get("line") == L["k"]]
            if not ws:      # no word timings: spread the text over the line
                toks = L["text"].split(); n = len(toks)
                ws = [dict(w=tk, t0=L["t0"] + (L["t1"] - L["t0"]) * j / n, t1=L["t0"] + (L["t1"] - L["t0"]) * (j + 1) / n) for j, tk in enumerate(toks)]
            chunk = []
            for j, w in enumerate(ws):
                chunk.append(w)
                end = w["w"].endswith((".", "!", "?", ",", ":")) and len(chunk) >= 3
                if len(chunk) >= max_words or end or j == len(ws) - 1:
                    caps.append(dict(t0=round(chunk[0]["t0"], 3), t1=round(max(chunk[-1]["t1"], chunk[0]["t0"] + 1.0), 3), text=" ".join(c["w"] for c in chunk), words=[dict(w=c["w"], t0=round(c["t0"], 3), t1=round(c["t1"], 3)) for c in chunk]))
                    chunk = []
        for a, b in zip(caps, caps[1:]): a["t1"] = min(a["t1"], b["t0"] - 0.02)
        return caps

    def save(self, out_dir=None):
        """writes film.json into out_dir; `python direct.py <dir>` (make_film.py) overrides it"""
        import sys
        out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else out_dir); out.mkdir(parents=True, exist_ok=True)
        self.shots.sort(key=lambda s: s["t0"])
        # who speaks: map voice speakers to cast ids (the story's `who`)
        words = [dict(who=w.get("who"), t0=w["t0"], t1=w["t1"]) for w in self.words if w.get("who") and w.get("who") != "narrator"]
        film = dict(fps=self.fps, size=self.size, duration=self.duration, cast=self.cast, places=self.places, scenes=self.scenes, shots=self.shots,
                    captions=self._captions(), words=words, cards=self.cards, events=sorted(self.events, key=lambda e: e["t"]), score=self.score, models=self.models,
                    theme=dict(size=44))
        problems = self.check(film)
        json.dump(film, open(out / "film.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"film.json: {len(self.shots)} shots, {len(self.scenes)} scenes, {sum(len(s['actions']) for s in self.scenes)} actions, {len(film['captions'])} captions, {len(self.events)} sound events")
        for p in problems: print("CHECK", p)
        return film

    # ---------------------------------------------------------------- direction checks
    def check(self, film):
        """the rules the owner asked for: a new picture often, no shot without a purpose, no idle stretches"""
        P = []
        sh = film["shots"]
        if sh and sh[0]["t0"] > 0.01: P.append("first shot does not start at 0")
        for a, b in zip(sh, sh[1:]):
            if b["t0"] - a["t1"] > 0.05: P.append(f"gap {a['t1']}-{b['t0']}")
        for s in sh:
            s["t1"] = s.get("t1") or 0
        for s in sh:
            d = s["t1"] - s["t0"]
            if d > 6.5: P.append(f"shot {s['t0']}-{s['t1']} lasts {d:.1f}s (> 6.5 s: cut or move)")
        # every 8 s of film must contain a story action, a world event or an insert
        acts = sorted([a["t0"] for sc in film["scenes"] for a in sc["actions"]] + [x["t"] for sc in film["scenes"] for x in sc["spills"]] + [s["t0"] for s in sh if s.get("kind") == "insert3d"])
        t = 0
        while t < film["duration"] - 8:
            if not any(t <= x < t + 8 for x in acts): P.append(f"no action between {t:.0f}s and {t + 8:.0f}s")
            t += 4
        kinds = [s.get("kind") for s in sh]
        for i in range(len(kinds) - 2):
            if kinds[i] == kinds[i + 1] == kinds[i + 2] and kinds[i] not in ("track",): P.append(f"three {kinds[i]} shots in a row at {sh[i]['t0']}")
        return P
