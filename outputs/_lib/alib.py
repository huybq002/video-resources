"""Authoring helpers shared by tonight's author.py files (stickman director pictures).

Layers are authored once on the 1280x720 landscape plane. For the 9:16 cut `Film.add` re-frames each shot as a native portrait
composition: a window of the landscape scene (centred on `fx`, scale `s`) is placed in the safe picture band of the 1280 x 2276
design plane, the layers inside it are scaled/moved, and the shot gets the portrait descriptor the runtime requires.
"""
import json, math, os, sys, pathlib
SK = pathlib.Path(__file__).resolve().parents[2] / ".claude" / "skills" / "hezb-story" / "scripts"
sys.path.insert(0, str(SK))

PW, PH = 1280, 2275.56
SAFE_L, SAFE_R = 77, 1126            # .06 / .12 of 1280
PIC_TOP, PIC_BOT = 200, 1620         # inside top .08 and caption band_top-24 (B1/B3 64 units; B2 72 -> checked by validate)


def _tf(l, left, s, ox, oy):
    """transform one landscape layer into the portrait plane (in place on a copy)"""
    l = json.loads(json.dumps(l))
    def X(v): return round(ox + (v - left) * s, 1)
    def Y(v): return round(oy + v * s, 1)
    def fix(d):
        if "x" in d: d["x"] = X(d["x"])
        if "y" in d: d["y"] = Y(d["y"])
        for k in ("w", "h"):
            if k in d: d[k] = round(d[k] * s, 1)
    fix(l)
    if l.get("type") == "text" and "size" in l:
        l["size"] = round(l["size"] * s, 1)
        l["w"] = round(max(120, min(l["w"], SAFE_R - l["x"])), 1)
    for k in l.get("keys", []): fix(k)
    for c in l.get("children", []): pass
    return l


def _box(l):
    x, y = l.get("x", 0), l.get("y", 0)
    w, h = l.get("w", 200), l.get("h", l.get("size", 60) * 1.2)
    xs = [x] + [k["x"] for k in l.get("keys", []) if "x" in k]
    ys = [y] + [k["y"] for k in l.get("keys", []) if "y" in k]
    return min(xs), min(ys), max(xs) + w, max(ys) + h


def _vbox(l):
    """visible box of a landscape layer (text: estimated from its characters, not its wide w)"""
    x0, y0, x1, y1 = _box(l)
    if any("angle" in k for k in l.get("keys", [])) and l.get("type") == "image": x0 -= l.get("h", 130) * 0.9; x1 += l.get("h", 130) * 0.9   # a swinging arm
    if l.get("type") == "text":
        est = 0.58 * l.get("size", 40) * len(l.get("text", ""))
        x1 = x0 + min(est, l.get("w", est))
    return x0, y0, x1, y1


class Film:
    def __init__(self, style, ratio, timing, sfx=None):
        self.style, self.ratio = style, ratio
        self.P = ratio == "9:16"
        self.T = json.load(open(timing))
        self.DUR = self.T["duration"]
        self.A = {}; self.shots = []; self.sfx = list(sfx or [])
        self.n = 0

    def scene(self, i):
        s = [x for x in self.T["scenes"] if x["id"] == i][0]; return s["start"], s["end"]

    def line(self, scene, i):
        l = [x for x in self.T["lines"] if x["scene"] == scene and x["i"] == i][0]; return l["start"], l["end"]

    def add(self, t0, t1, layers, fx=640, s=1.3, intent="", role="actor", y_off=None):
        """layers: landscape-authored. fx / s: portrait window centre and scale. A layer with "_bg": True is the scene background."""
        self.n += 1
        t0, t1 = round(t0, 3), round(t1, 3)
        dur = math.floor((t1 - t0 - 0.001) * 1000) / 1000
        out, bg, ids = [], [], []
        if self.P:
            bx = [_vbox(l) for l in layers if not l.get("_bg")]
            if bx:
                x0 = min(b[0] for b in bx); x1 = max(b[2] for b in bx)
                fit = (SAFE_R - SAFE_L - 24) / max(1, x1 - x0)
                if fit < s: s = max(0.6, fit)
                if fit < s * 1.0 or x1 - x0 > (SAFE_R - SAFE_L) / s - 20: fx = (x0 + x1) / 2
                else: fx = min(max(fx, x1 - ((SAFE_R - SAFE_L) / s) / 2 + 10), x0 + ((SAFE_R - SAFE_L) / s) / 2 - 10)
            ww = (SAFE_R - SAFE_L) / s; left = fx - ww / 2
            oy = y_off if y_off is not None else (PIC_TOP + PIC_BOT) / 2 - 360 * s
        for j, l in enumerate(layers):
            l = dict(l); isbg = l.pop("_bg", False)
            if self.P:
                b = _box(l)
                if not isbg and (b[2] < left + 4 or b[0] > left + ww - 4): continue       # fully outside the window
                l = _tf(l, left, s, SAFE_L, oy)
            l["id"] = f"{l.get('id', 'l')}-{self.n}-{j}"
            (bg if isbg else ids).append(l["id"])
            out.append(_clean(l, dur))
        shot = {"start": t0, "end": t1, "layers": out}
        if self.P:
            shot["portrait"] = {"intent": intent or "The focal action sits in the picture band above the caption; props and hands stay inside the safe region",
                                "background_ids": bg,
                                "regions": [{"id": f"r{self.n}", "role": role, "layer_ids": ids,
                                             "region": {"x": SAFE_L + 3, "y": PIC_TOP, "w": SAFE_R - SAFE_L - 6, "h": PIC_BOT - PIC_TOP},
                                             "intent": "The whole story action of this shot fits the picture band, with its complete movement and held result"}]}
        self.shots.append(shot)

    def write(self, path, television=None, portrait_safe=None):
        out = {"shots": self.shots, "sfx": self.sfx, "assets": self.A}
        if television: out["television"] = television
        if self.P: out["portrait"] = {"safe_area": portrait_safe or {"left": 0.06, "right": 0.12, "top": 0.08, "bottom": 0.18}}
        json.dump(out, open(path, "w"), indent=0)
        print(path, len(self.shots), "shots,", len(self.A), "drawings")


def _clean(layer, dur):
    if layer.get("keys"):
        out = []
        for k in layer["keys"]:
            k = dict(k, t=round(min(max(0.0, k["t"]), dur), 3))
            if out and k["t"] <= out[-1]["t"]: continue
            out.append(k)
        layer["keys"] = out
        if len(out) < 2: layer.pop("keys"); layer.pop("motion", None)
    for f in ("from", "to"):
        if f in layer: layer[f] = round(min(max(0.0, layer[f]), dur), 3)
    return layer


# ---- layer helpers (landscape plane)
def img(path, x, y, w, h, lid=None, keys=None, why=None, role="prop", frm=None, to=None, bg=False, angle=None):
    d = {"type": "image", "path": f"assets/{path}", "x": x, "y": y, "w": w, "h": h}
    if lid: d["id"] = lid
    if keys: d["keys"] = keys; d["motion"] = {"role": role, "reason": why or "moves with the story"}
    if frm is not None: d["from"] = frm
    if to is not None: d["to"] = to
    if angle is not None: d["angle"] = angle
    if bg: d["_bg"] = True
    return d


def text(t, x, y, size, color, w=None, frm=None, to=None, lid=None):
    d = {"type": "text", "text": t, "x": x, "y": y, "w": w or max(120, 1250 - x), "size": size, "bold": True, "color": color}
    if frm is not None: d["from"] = frm
    if to is not None: d["to"] = to
    if lid: d["id"] = lid
    return d


def underline(x, y, w, t0, t1, lid, why="the name of the effect"):
    return {"type": "underline", "id": lid, "x": x, "y": y, "w": w, "keys": [{"t": t0, "progress": 0}, {"t": t1, "progress": 1}], "motion": {"role": "information", "reason": why}}


def bob(d, step, a, b, prop="y"):
    out, t, i = [], 0.0, 0
    while t <= d + 1e-6:
        out.append({"t": round(t, 3), prop: a if i % 2 == 0 else b}); t += step; i += 1
    return out
