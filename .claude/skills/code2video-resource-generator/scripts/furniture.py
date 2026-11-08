"""Furniture and street objects for the 3D settings, built from the renderer's primitives.

In a setting's "objects" list write  {"t": "furn", "n": "bed", "x": 2, "z": -5, "ry": 0.3, "s": 1, "c": "#5b6f9a"}
and generate.py expands it into boxes, cylinders, spheres and glows before three.js renders the
background. Units are metres, ground at y = 0, the object's base at (x, z), "ry" turns it, "s" scales
it, "c" is its main colour, "c2" a second colour where the object has one.

Why: the Kenney kit only has nature models (cliffs, trees, tents). Without real furniture every room
was a few grey boxes, so a line about going to bed had no bed in it. Now a bedroom has a bed, a
kitchen has an oven, an office has a desk and a screen, and `spec_lint.py` checks that a line which
mentions one of these is shot in a setting that contains it.
"""
import math

INK = 0.03


def _rot(dx, dz, ry):
    c, s = math.cos(ry), math.sin(ry)
    return dx * c + dz * s, -dx * s + dz * c


def _parts(n, c, c2):
    """parts in local metres, base-anchored like the renderer (box/cylinder y = bottom, sphere y = centre)."""
    wood, dark, glass, light = "#8a5a3c", "#2a2730", "#9ed8ff", "#f3eee4"
    B = lambda x, y, z, w, h, d, col, **k: dict(t="box", x=x, y=y, z=z, w=w, h=h, d=d, c=col, **k)
    C = lambda x, y, z, r, h, col, **k: dict(t="cylinder", x=x, y=y, z=z, r=r, h=h, c=col, **k)
    P = {
        "bed": [B(0, 0, 0, 1.6, .38, 2.1, c2 or wood), B(0, .38, .05, 1.5, .2, 1.95, light),
                B(0, .58, .35, 1.52, .1, 1.35, c), B(0, .58, -.78, .9, .14, .34, "#ffffff"),
                B(0, 0, -1.08, 1.7, 1.05, .1, c2 or wood)],
        "bedside_table": [B(0, 0, 0, .5, .55, .45, c or wood), B(0, .55, 0, .14, .32, .14, dark),
                          dict(t="sphere", x=0, y=1.0, z=0, r=.18, c="#ffe27a", ink=0)],
        "desk": [B(0, .72, 0, 1.6, .06, .75, c or wood)] + [B(sx * .72, 0, sz * .3, .07, .72, .07, c2 or dark)
                 for sx in (-1, 1) for sz in (-1, 1)],
        "computer": [B(0, .78, -.1, .7, .45, .05, dark), dict(t="glow", x=0, y=1.005, z=-.07, w=.62, h=.36, c=glass),
                     B(0, .72, -.1, .08, .06, .08, dark), B(0, .72, .18, .55, .03, .18, "#c9ccd6")],
        "chair": [B(0, .45, 0, .5, .07, .5, c or "#3e5c8a"), B(0, .52, -.22, .5, .55, .06, c or "#3e5c8a")]
                 + [C(sx * .2, 0, sz * .2, .03, .45, dark) for sx in (-1, 1) for sz in (-1, 1)],
        "sofa": [B(0, 0, 0, 2.1, .45, .95, c or "#7a5c9a"), B(0, .45, -.36, 2.1, .55, .24, c or "#7a5c9a"),
                 B(-1.0, .45, 0, .2, .3, .95, c2 or "#694d86"), B(1.0, .45, 0, .2, .3, .95, c2 or "#694d86")],
        "table": [B(0, .74, 0, 1.6, .06, .9, c or wood)] + [B(sx * .7, 0, sz * .36, .07, .74, .07, c2 or wood)
                  for sx in (-1, 1) for sz in (-1, 1)],
        "bookshelf": [B(0, 0, 0, 1.2, 2.0, .35, c or wood)] + [B(0, y, .05, 1.1, .04, .3, c2 or "#6e452c") for y in (.45, .9, 1.35)]
                     + [B(-.45 + .16 * k, y + .04, .06, .12, .32, .25, ["#d8473d", "#4f6bd8", "#e3b341", "#3aa65a", "#7a5c9a", "#f08a5d"][k % 6])
                        for y in (.45, .9, 1.35) for k in range(6)],
        "kitchen_counter": [B(0, 0, 0, 2.4, .88, .62, c or "#e9e4d8"), B(0, .88, 0, 2.5, .05, .66, c2 or "#6d6a72"),
                            B(-.6, .93, 0, .5, .02, .4, "#9aa3ad"), C(.6, .93, 0, .14, .02, dark), C(.95, .93, 0, .14, .02, dark)],
        "oven": [B(0, 0, 0, .65, .88, .62, c or "#d8d4cc"), dict(t="glow", x=0, y=.42, z=.315, w=.5, h=.32, c="#ff9a3c"),
                 B(0, .88, 0, .65, .05, .62, dark)] + [dict(t="sphere", x=-.2 + .13 * k, y=.8, z=.32, r=.035, c=dark, ink=0) for k in range(4)],
        "fridge": [B(0, 0, 0, .75, 1.85, .7, c or "#eef0f2"), B(.28, .9, .36, .04, .5, .04, dark), B(0, 1.2, .355, .74, .02, .01, "#b9bfc6")],
        "window": [B(0, 1.0, 0, 1.4, 1.2, .08, c2 or "#e9e4d8"), dict(t="glow", x=0, y=1.6, z=.05, w=1.2, h=1.0, c=c or "#8fc3ff"),
                   B(0, 1.6, .07, .05, 1.0, .02, c2 or "#e9e4d8"), B(0, 1.6, .07, 1.2, .05, .02, c2 or "#e9e4d8")],
        "night_window": [B(0, 1.0, 0, 1.4, 1.2, .08, c2 or "#3a3550"), dict(t="glow", x=0, y=1.6, z=.05, w=1.2, h=1.0, c=c or "#1b2350"),
                         dict(t="disc", x=.3, y=1.85, z=.06, r=.12, c="#f4efe0")],
        "door": [B(0, 0, 0, .95, 2.05, .07, c or wood), dict(t="sphere", x=.36, y=1.0, z=.06, r=.04, c="#e3b341", ink=0)],
        "tv": [B(0, .55, 0, 1.3, .75, .06, dark), dict(t="glow", x=0, y=.925, z=.035, w=1.2, h=.65, c=c or glass),
               B(0, 0, 0, 1.2, .55, .4, c2 or wood)],
        "lamp_floor": [C(0, 0, 0, .03, 1.5, dark), C(0, 0, 0, .2, .03, dark),
                       dict(t="cylinder", x=0, y=1.45, z=0, rt=.14, rb=.25, h=.3, c=c or "#ffe9b0"),
                       dict(t="light", x=0, y=1.5, z=.3, c="#ffcf8a", I=40, dist=8)],
        "plant": [C(0, 0, 0, .22, .4, c2 or "#b5523a"), dict(t="sphere", x=0, y=.75, z=0, r=.36, c=c or "#4e8a4a")],
        "rug": [B(0, 0, 0, 2.6, .02, 1.7, c or "#c96f5a", ink=0)],
        "picture": [B(0, 1.5, 0, .8, .6, .04, c2 or wood), dict(t="glow", x=0, y=1.8, z=.025, w=.68, h=.48, c=c or "#e7c79a")],
        "wall_clock": [dict(t="disc", x=0, y=2.1, z=.02, r=.3, c="#fbf8f1"), B(0, 2.1, .03, .03, .22, .01, dark)],
        "shop_counter": [B(0, 0, 0, 2.4, 1.0, .65, c or "#3e7cb1"), B(0, 1.0, 0, 2.5, .06, .7, c2 or "#e9e4d8"),
                         B(.7, 1.06, 0, .45, .25, .35, dark), dict(t="glow", x=.7, y=1.28, z=.18, w=.36, h=.15, c="#9effa8")],
        "shelf_goods": [B(0, 0, 0, 2.0, 1.9, .45, c or "#e9e4d8")] + [B(-.8 + .27 * k, y, .05, .2, .28, .3, ["#d8473d", "#ffd166", "#4f6bd8", "#3aa65a", "#f08a5d", "#7a5c9a", "#e3b341"][k % 7])
                       for y in (.1, .65, 1.2) for k in range(7)],
        "car": [B(0, .25, 0, 1.8, .6, 4.0, c or "#d8473d"), B(0, .85, -.2, 1.6, .55, 2.0, c or "#d8473d"),
                dict(t="glow", x=0, y=1.1, z=.81, w=1.4, h=.4, c="#bfe6ff")]
               + [dict(t="cylinder", x=sx * .9, y=0, z=sz * 1.3, r=.33, h=.3, c=dark, rz=math.pi / 2) for sx in (-1, 1) for sz in (-1, 1)],
        "bench": [B(0, .42, 0, 1.8, .07, .45, c or wood), B(0, .5, -.2, 1.8, .4, .06, c or wood)]
                 + [B(sx * .8, 0, 0, .07, .42, .4, dark) for sx in (-1, 1)],
        "trash_bin": [dict(t="cylinder", x=0, y=0, z=0, rt=.3, rb=.25, h=.85, c=c or "#4e6a62")],
        "building": [B(0, 0, 0, 6, 12, 6, c or "#3b3550")] + [dict(t="glow", x=-2.1 + 1.4 * i, y=1.6 + 2.2 * j, z=3.01, w=.8, h=1.1,
                     c=("#ffd27a" if (i * 7 + j * 3) % 4 == 0 else "#2a2a45")) for i in range(4) for j in range(5)],
        "street_sign": [C(0, 0, 0, .05, 2.4, dark), B(0, 2.2, 0, 1.0, .35, .05, c or "#3aa65a")],
        "fence": [B(0, .5, 0, 3.0, .08, .06, c or wood), B(0, .9, 0, 3.0, .08, .06, c or wood)]
                 + [B(-1.4 + .7 * k, 0, 0, .1, 1.1, .1, c or wood) for k in range(5)],
        "crate": [B(0, 0, 0, .8, .8, .8, c or "#a8743f")],
        "barrel": [C(0, 0, 0, .35, .95, c or "#7a4e32")],
        "towel": [B(0, 0, 0, .8, .02, 1.8, c or "#e35d4f", ink=0), B(0, .021, -.5, .8, .004, .12, c2 or "#ffffff", ink=0),
                  B(0, .021, .5, .8, .004, .12, c2 or "#ffffff", ink=0)],
        "umbrella": [C(0, 0, 0, .03, 2.1, "#f3eee4"), dict(t="cylinder", x=0, y=1.85, z=0, rt=.02, rb=1.15, h=.45, c=c or "#e35d4f", seg=12)],
        "palm": [dict(t="cylinder", x=0, y=0, z=0, rt=.1, rb=.18, h=4.2, c=c2 or "#8a6a3c")]
                + [dict(t="cylinder", x=math.cos(a) * .9, y=4.0, z=math.sin(a) * .9, rt=.02, rb=.35, h=.12, c=c or "#3aa65a", ink=.02, rz=0)
                   for a in [i * math.pi / 3 for i in range(6)]] + [dict(t="sphere", x=0, y=4.2, z=0, r=.45, c=c or "#3aa65a")],
        "whiteboard": [B(0, .9, 0, 1.8, 1.1, .05, "#f6f6f2"), B(0, .85, .03, 1.8, .06, .1, c2 or "#9aa3ad"),
                       B(-.3, 1.5, .03, .9, .04, .01, c or "#4f6bd8"), B(-.1, 1.3, .03, 1.1, .04, .01, c or "#4f6bd8")],
    }
    return P.get(n)


FURNITURE = sorted([
    "bed", "bedside_table", "desk", "computer", "chair", "sofa", "table", "bookshelf", "kitchen_counter", "oven", "fridge",
    "window", "night_window", "door", "tv", "lamp_floor", "plant", "rug", "picture", "wall_clock", "shop_counter",
    "shelf_goods", "car", "bench", "trash_bin", "building", "street_sign", "fence", "crate", "barrel", "whiteboard", "towel", "umbrella", "palm"])


def expand(objects):
    """replace every {"t": "furn"} entry by its primitives, in world coordinates; unknown names are dropped with a note."""
    out = []
    for o in objects or []:
        if o.get("t") != "furn":
            out.append(o)
            continue
        parts = _parts(o.get("n", ""), o.get("c"), o.get("c2"))
        if not parts:
            print(f"furniture: unknown '{o.get('n')}' skipped (known: {', '.join(FURNITURE)})")
            continue
        s, ry = float(o.get("s", 1)), float(o.get("ry", 0))
        bx, by, bz = float(o.get("x", 0)), float(o.get("y", 0)), float(o.get("z", 0))
        for p in parts:
            q = dict(p)
            dx, dz = _rot(q.get("x", 0) * s, q.get("z", 0) * s, ry)
            q["x"], q["z"] = round(bx + dx, 3), round(bz + dz, 3)
            q["y"] = round(by + q.get("y", 0) * s, 3)
            for k in ("w", "h", "d", "r", "rt", "rb"):
                if k in q: q[k] = round(q[k] * s, 3)
            if ry and q["t"] in ("box", "cylinder", "glow"): q["ry"] = round(q.get("ry", 0) + ry, 4)
            q.setdefault("ink", INK) if q["t"] in ("box", "cylinder", "sphere") else None
            out.append(q)
    return out


def contents(setting):
    """names of the furniture a setting contains (used by spec_lint to match lines to places)."""
    return {o.get("n") for o in (setting or {}).get("objects", []) if o.get("t") == "furn"}
