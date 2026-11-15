"""Drawing kit for B1/B2/B3 films (hezb-story): colored hand-inked SVG characters in parts, props helpers.

Usage (see examples/saving-feels-harder/author.py): put this folder on sys.path, `import draw_kit as D`;
`D.person_layers(id, character, x, y, scale, expr=..., arm_r=[{t, angle}], body_motion=..., assets=ASSETS)` returns image layers
(left arm, body, head drawings swapped by `expr_swaps`, right arm) and fills ASSETS (file -> svg) for the shots file.
Set env DRAW_INK to the line colour before import (B3: a light ink on its dark field). Features stay dark ink for readable eyes.

Original docstring: SVG drawing kit for B1/B2 demos: hand-inked colored characters (parts for local motion) and props.

Characters are cut into parts so the runtime can move them separately (image layers with pivots):
  body (legs, torso, clothes), head (one image per expression), right arm, left arm.
Every part is drawn on its own canvas in design units (1 unit = 1 px of the 1280-wide design plane at scale 1).
"""
import math, random

import os
INK = os.environ.get("DRAW_INK", "#2b2a28")


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<g stroke-linecap="round" stroke-linejoin="round">{body}</g></svg>')


def wob(points, amp=1.2, seed=0):
    """a slightly irregular hand-drawn polyline through points -> path d (quadratic smoothing)"""
    r = random.Random(seed)
    pts = [(x + r.uniform(-amp, amp), y + r.uniform(-amp, amp)) for x, y in points]
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(1, len(pts) - 1):
        mx, my = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
        d += f" Q{pts[i][0]:.1f},{pts[i][1]:.1f} {mx:.1f},{my:.1f}"
    d += f" L{pts[-1][0]:.1f},{pts[-1][1]:.1f}"
    return d


def line(points, w=3, color=INK, seed=0, amp=1.0):
    return f'<path d="{wob(points, amp, seed)}" fill="none" stroke="{color}" stroke-width="{w}"/>'


def blob(cx, cy, rx, ry, fill, stroke=INK, w=2.6, seed=0, n=30, amp=0.5):
    r = random.Random(seed)
    pts = [(cx + rx * math.cos(2 * math.pi * k / n) + r.uniform(-amp, amp), cy + ry * math.sin(2 * math.pi * k / n) + r.uniform(-amp, amp)) for k in range(n)]
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{w}"/>'


def poly(points, fill, stroke=INK, w=2.6, seed=0, amp=0.8):
    r = random.Random(seed)
    d = "M" + " L".join(f"{x + r.uniform(-amp, amp):.1f},{y + r.uniform(-amp, amp):.1f}" for x, y in points) + " Z"
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{w}"/>'


# ------------------------------------------------------------------ characters ---------------------------------------
# canvas 200 x 340; head centre (100, 46) r 36; neck to 84; shoulders at y 96; hips 200; feet 330
CW, CH = 200, 340
SHOULDER = (100, 98)
HEAD_C = (100, 46)


def body_svg(c):
    """legs + torso + clothes. c: dict(style b1|b2, shirt, apron, vest, trousers, skirt, shoes)"""
    s = []
    b1 = c.get("style") == "b1"
    lw = 3.2 if b1 else 3.4
    # legs
    if c.get("skirt"):
        s.append(line([(90, 250), (82, 328)], lw, seed=11)); s.append(line([(110, 250), (118, 328)], lw, seed=12))
    else:
        s.append(line([(96, 200), (80, 328)], lw, seed=11)); s.append(line([(104, 200), (120, 328)], lw, seed=12))
    s.append(blob(76, 330, 12, 6, c.get("shoes", INK), seed=13, w=2)); s.append(blob(124, 330, 12, 6, c.get("shoes", INK), seed=14, w=2))
    # neck
    s.append(line([(100, 82), (100, 98)], lw, seed=15))
    if b1 and not c.get("shirt"):
        s.append(line([(100, 96), (100, 202)], lw, seed=16))              # B1: a single slender ink torso line
    else:
        sh = c.get("shirt", "#ffffff")
        s.append(poly([(76, 100), (124, 100), (130, 206), (70, 206)], sh, seed=17))                    # shirt / top
        if c.get("skirt"):
            s.append(poly([(70, 200), (130, 200), (142, 262), (58, 262)], c["skirt"], seed=18))
        if c.get("apron"):
            s.append(poly([(82, 124), (118, 124), (122, 236), (78, 236)], c["apron"], seed=19))
            s.append(line([(82, 124), (90, 100)], 2, seed=20)); s.append(line([(118, 124), (110, 100)], 2, seed=21))
            s.append(line([(90, 196), (110, 196)], 2, "#ffffff", seed=22))                                # apron pocket
        if c.get("vest"):
            s.append(poly([(76, 102), (98, 104), (98, 204), (72, 204)], c["vest"], seed=23))
            s.append(poly([(102, 104), (124, 102), (128, 204), (102, 204)], c["vest"], seed=24))
            for yy in (130, 156, 182): s.append(blob(108, yy, 2.4, 2.4, INK, seed=yy, w=0))
        if c.get("badge"): s.append(poly([(108, 136), (122, 136), (122, 152), (108, 152)], c["badge"], seed=25, w=1.8))
    return svg(CW, CH, "".join(s))


def head_svg(c, expr="neutral"):
    """100 x 100 canvas, head centre (50, 50) r 36"""
    s = []
    skin = c.get("skin", "#fdfaf3")
    hair = c.get("hair")
    if c.get("hair_style") == "bun" and hair:
        s.append(blob(50, 12, 13, 12, hair, seed=31))
    if c.get("hair_style") == "ponytail" and hair:
        s.append(f'<path d="M78,30 Q98,40 92,70 Q88,58 80,50 Z" fill="{hair}" stroke="{INK}" stroke-width="2.2"/>')
    s.append(blob(50, 52, 34, 36, skin, seed=32, w=2.8))
    if hair and c.get("hair_style") in ("bun", "short", "ponytail"):
        s.append(f'<path d="M17,46 Q20,16 50,15 Q80,16 83,46 Q74,30 50,29 Q28,30 17,46 Z" fill="{hair}" stroke="{INK}" stroke-width="2.4"/>')
    if c.get("hair_style") == "bald":
        s.append(line([(30, 30), (38, 22)], 1.6, "#d8cfc0", seed=33))
    # cheeks
    s.append(f'<ellipse cx="30" cy="62" rx="6" ry="3.5" fill="#f2a59a" opacity=".55"/><ellipse cx="70" cy="62" rx="6" ry="3.5" fill="#f2a59a" opacity=".55"/>')
    b1 = c.get("style") == "b1"
    ey = 50
    eyes = {"closed": [line([(33, ey), (41, ey + 2)], 2.6, seed=34), line([(59, ey + 2), (67, ey)], 2.6, seed=35)]}.get(expr)
    if not eyes:
        rx, ry = (3.4, 4.6) if b1 or expr in ("surprise", "shout") else (3.0, 3.6)
        eyes = [f'<ellipse cx="37" cy="{ey}" rx="{rx}" ry="{ry}" fill="{INK}"/>', f'<ellipse cx="63" cy="{ey}" rx="{rx}" ry="{ry}" fill="{INK}"/>']
    brows = {"neutral": [((30, 39), (42, 38)), ((58, 38), (70, 39))], "doubt": [((30, 40), (42, 40)), ((58, 34), (70, 38))],
             "worry": [((30, 37), (42, 41)), ((58, 41), (70, 37))], "angry": [((30, 35), (43, 42)), ((57, 42), (70, 35))],
             "surprise": [((30, 33), (42, 31)), ((58, 31), (70, 33))], "shout": [((30, 35), (43, 42)), ((57, 42), (70, 35))],
             "smile": [((30, 38), (42, 36)), ((58, 36), (70, 38))], "think": [((30, 38), (42, 40)), ((58, 36), (70, 34))],
             "closed": [((30, 41), (42, 40)), ((58, 40), (70, 41))]}[expr]
    for i, (a, b) in enumerate(brows): s.append(line([a, b], 2.6, '#1f2124', seed=40 + i))
    mouth = {"neutral": line([(42, 72), (58, 72)], 2.6, seed=50), "doubt": line([(42, 73), (58, 69)], 2.6, seed=50),
             "worry": f'<path d="M41,75 Q50,68 59,75" fill="none" stroke="{INK}" stroke-width="2.6"/>',
             "angry": f'<path d="M41,76 Q50,69 59,76" fill="none" stroke="{INK}" stroke-width="3"/>',
             "surprise": f'<ellipse cx="50" cy="73" rx="5" ry="6.5" fill="{INK}"/>',
             "shout": f'<path d="M40,68 Q50,64 60,68 Q58,82 50,82 Q42,82 40,68 Z" fill="{INK}"/>',
             "smile": f'<path d="M40,69 Q50,79 60,69" fill="none" stroke="{INK}" stroke-width="2.8"/>',
             "think": line([(44, 73), (56, 72)], 2.6, seed=50), "closed": f'<path d="M42,71 Q50,76 58,71" fill="none" stroke="{INK}" stroke-width="2.6"/>'}[expr]
    # facial features are always dark ink, whatever the style's line colour: a light B3 line on a white face made the
    # eyes disappear (owner, 2026-11-15: "mất mắt")
    FACE = "#1f2124"
    s += [p.replace(INK, FACE) for p in eyes + [mouth]]
    if c.get("moustache"):
        mc = c.get("moustache_color", "#5a4636")
        s.append(f'<path d="M36,66 Q43,61 50,65 Q57,61 64,66 Q57,69 50,67 Q43,69 36,66 Z" fill="{mc}" stroke="#1f2124" stroke-width="1.6"/>')
    if c.get("pencil"): s.append(line([(78, 30), (92, 14)], 4, "#e2b44a", seed=60))
    if expr == "worry": s.append(f'<path d="M80,36 Q83,42 80,45 Q77,42 80,36 Z" fill="#9cc7e4" stroke="{INK}" stroke-width="1.2"/>')   # sweat drop
    return svg(100, 100, "".join(s))


def arm_svg(c, side="r"):
    """60 x 130 canvas; the shoulder sits at (8, 6), next to the top-left corner, because the runtime rotates B1/B2
    images about their top-left corner (no pivot outside B3). The arm hangs straight down: a negative angle swings it
    to the viewer's right, a positive angle to the left."""
    sleeve = c.get("sleeve"); s = []
    sh, elbow, hand = (8, 6), (13, 56), (10, 104)
    if sleeve:
        s.append(f'<path d="{wob([sh, elbow], 0.5, 70)}" fill="none" stroke="{INK}" stroke-width="12"/>')
        s.append(f'<path d="{wob([sh, elbow], 0.5, 70)}" fill="none" stroke="{sleeve}" stroke-width="8"/>')
        s.append(line([elbow, hand], 3.2, seed=71))
    else:
        s.append(line([sh, elbow, hand], 3.2, seed=72))
    s.append(blob(hand[0] + 4, hand[1] + 8, 6.5, 7.5, c.get("skin", "#fdfaf3"), seed=73, w=2.2))
    return svg(60, 130, "".join(s))


def _at(keys, prop, t, default):
    """value of prop at time t from a key list (linear between keys, held outside)"""
    ks = [k for k in (keys or []) if prop in k]
    if not ks: return default
    if t <= ks[0]["t"]: return ks[0][prop]
    for a, b in zip(ks, ks[1:]):
        if a["t"] <= t <= b["t"]:
            u = (t - a["t"]) / max(1e-6, b["t"] - a["t"]); return a[prop] + (b[prop] - a[prop]) * u
    return ks[-1][prop]


def person_layers(pid, c, x, y, s=1.0, expr="neutral", reason="", arm_r=None, arm_l=None, head=None, expr_swaps=None,
                  body_motion=None, assets=None, flip=False):
    """image layers for a standing character drawn in a 200x340 box at (x, y), scale s. Returns layers; fills `assets`.
    arm_r / arm_l: shot-relative keys with an ABSOLUTE 'angle' of the arm (0 = hanging straight down; right arm negative
    = swings out to the viewer's right / up; left arm positive = out to the left / up). Defaults -0.28 / 0.28.
    head: 'angle' keys become a small nod (y). body_motion: 'angle' keys become a lean (x shift) that moves the WHOLE
    figure (body, head and both arms together), so limbs never come apart from the body (owner, 2026-11-15)."""
    nm = c["name"]
    assets[f"{nm}-body.png"] = body_svg(c)
    assets[f"{nm}-armr.png"] = arm_svg(c, "r"); assets[f"{nm}-arml.png"] = arm_svg(c, "l")
    clothed = bool(c.get("shirt"))
    sh_r = (118, 106) if clothed else (100, 100)          # where each arm joins the body (drawing units)
    sh_l = (82, 106) if clothed else (100, 100)
    dx = lambda t: _at(body_motion, "angle", t, 0.0) * 70 * s
    times = sorted({0.0, *[k["t"] for k in (body_motion or [])]})
    def merged(own, prop_fn):
        ts = sorted(set(times) | {k["t"] for k in (own or [])})
        return [dict({"t": round(t, 3)}, **prop_fn(t)) for t in ts]
    def img(lid, file, lx, ly, w, h, keys=None, why=None, frm=None, to=None, angle=None):
        d = {"type": "image", "path": f"assets/{file}", "x": round(lx, 1), "y": round(ly, 1), "w": round(w, 1), "h": round(h, 1)}
        if lid: d["id"] = lid
        if keys and len(keys) > 1: d["keys"] = keys; d["motion"] = {"role": "actor", "reason": why or reason}
        elif angle is not None: d["angle"] = angle
        if frm is not None: d["from"] = frm
        if to is not None: d["to"] = to
        return d
    moving = bool(body_motion)
    def arm(lid, file, sh, keys, default, why):
        ax, ay = x + (sh[0] - 8) * s, y + (sh[1] - 6) * s
        if not keys and not moving: return img(lid, file, ax, ay, 60 * s, 130 * s, angle=default)
        k = merged(keys, lambda t: {"x": round(ax + dx(t), 1), "angle": round(_at(keys, "angle", t, default), 3)})
        return img(lid, file, ax, ay, 60 * s, 130 * s, k, why, angle=default)
    L = [arm(f"{pid}-armL", f"{nm}-arml.png", sh_l, arm_l, 0.28, "the other hand moves too")]
    L.append(img(f"{pid}-body", f"{nm}-body.png", x, y, CW * s, CH * s,
                 merged(None, lambda t: {"x": round(x + dx(t), 1)}) if moving else None, "the whole body leans with the feeling"))
    hx, hy = x + (HEAD_C[0] - 50) * s, y + (HEAD_C[1] - 50) * s
    hk = (merged(head, lambda t: {"x": round(hx + dx(t), 1), "y": round(hy + abs(_at(head, "angle", t, 0.0)) * 40 * s, 1)})
          if (head or moving) else None)
    for i, (frm, to, ex) in enumerate(expr_swaps or [(None, None, expr)]):
        assets[f"{nm}-head-{ex}.png"] = head_svg(c, ex)
        L.append(img(f"{pid}-head{i}", f"{nm}-head-{ex}.png", hx, hy, 100 * s, 100 * s, hk, "the head nods with the line", frm, to))
    L.append(arm(f"{pid}-armR", f"{nm}-armr.png", sh_r, arm_r, -0.28, "the hand acts the line"))
    return L


def cycle(dur, step, a, b, prop="angle"):
    out, t, i = [], 0.0, 0
    while t <= dur + 1e-6:
        out.append({"t": round(t, 3), prop: a if i % 2 == 0 else b}); t += step; i += 1
    return out
