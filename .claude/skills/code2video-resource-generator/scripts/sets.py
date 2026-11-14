"""Whole sets for the 3D backgrounds: a dressed room, a street, a shop front. One line in a setting builds them.

    "bedroom": {"set": {"type": "room", "style": "bedroom", "time": "dusk"}, "objects": [ ...extras... ]}
    "street":  {"set": {"type": "street", "time": "dusk"}}
    "cafe_ext":{"set": {"type": "shopfront", "style": "cafe", "time": "night"}}

Why: in the reference films (IfverseTales) every frame is a full place, never a colour block. Frame study:
- one strong light source in frame: a big window with a city skyline and a low sun, or a lit building at night;
- warm light against cool shadow (dusk violet walls, orange window light, a light pool on the floor);
- dense set dressing on every wall (posters, clock, shelves, screens, ceiling light strips), so even a
  close-up crop shows a real room behind the character;
- depth: blurred foreground objects at the frame edges, the room, then the city behind the glass in haze;
- exteriors in one-point perspective (street, crosswalk, buildings with lit windows, lamps, trees, poles);
- night establishing shots of a lit building with nobody in it.
Our earlier rooms were a floor box, a wall box and one piece of furniture: close-ups showed an empty purple wall.

expand(setting) returns a full setting (sky/bg, fog, lights, camera, layers, objects) with the set built from
primitives and {"t":"furn"} macros; the setting's own keys and objects are kept and win over the defaults.
Keys of "set": type, style, time (day|dusk|night), window ("left"|"right"|"center"|"none"), fg (true/false),
seed, w (room width, m), key ({"x": .., "z": ..} where the style's key furniture stands).
"""
import math
import random

TIMES = {
    "dusk": dict(sky=["#3a2d5e", "#f3a465"], sun="#ffd79a", glow="#ffb36b", wall="#4b3c5e", wall2="#3d3150", floor="#5b4537",
                 ceil="#2e2640", amb=("#9a7fb8", 0.9), key=("#ffc27a", 70), city="#4a3a5e", lit="#ffd27a", fog=(22, 60)),
    "night": dict(sky=["#0d1230", "#2b2858"], sun="#e9ecff", glow="#ffcf8a", wall="#4a4170", wall2="#3a335c", floor="#4a3f5a",
                  ceil="#2a2542", amb=("#6a74c8", 1.05), key=("#ffcf8a", 60), city="#1d1f3a", lit="#ffd27a", fog=(20, 55)),
    "day": dict(sky=["#7fb6ef", "#e6f1fb"], sun="#fff6d8", glow="#fff1c8", wall="#b9ab95", wall2="#a3967f", floor="#8e6446",
                ceil="#cfc6b6", amb=("#f4ecff", 0.75), key=("#fff1d0", 45), city="#9fb3c8", lit="#eef4ff", fog=(26, 80)),
}
STYLE_PAL = {   # day colours of the place itself; dusk/night mix them with the time palette so the light still reads
    "bathroom": dict(wall="#dfeaf0", wall2="#c9d9e2", floor="#b9c4cc"), "laundry": dict(wall="#a9adb5", wall2="#959aa3", floor="#7d8088"),
    "grocery": dict(wall="#e9ece6", wall2="#d5dad2", floor="#c9c6bc"), "meeting": dict(wall="#cfd5dc", wall2="#b9c1ca", floor="#6e6a74"),
    "kitchen": dict(wall="#e6d6bf", wall2="#d3c2aa", floor="#9a7a5a"), "office": dict(wall="#c9c3b6", wall2="#b4ad9e", floor="#8e6446"),
    "bedroom": dict(wall="#b8a6c9", wall2="#a493b6", floor="#8e6446"), "living": dict(wall="#d6b9a0", wall2="#c2a48b", floor="#7a5a40"),
    "cafe": dict(wall="#a87a5a", wall2="#946a4c", floor="#5b4537"), "classroom": dict(wall="#d9d2b8", wall2="#c5bea3", floor="#9a7a5a"),
    "lab": dict(wall="#d5dde0", wall2="#c0c9cd", floor="#8a9096"), "shop": dict(wall="#e3e0d6", wall2="#cfccc2", floor="#b0aca2"),
}



def _mix(a, b, t):
    a = [int(a[i:i + 2], 16) for i in (1, 3, 5)]; b = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


POSTER = ["#e35d4f", "#4f7be3", "#e3b341", "#3aa65a", "#9a5cd8", "#f08a5d", "#38b7c9"]


def _box(x, y, z, w, h, d, c, **k):
    return dict(t="box", x=round(x, 3), y=round(y, 3), z=round(z, 3), w=round(w, 3), h=round(h, 3), d=round(d, 3), c=c, **k)


def _f(n, x, z, **k):
    return dict(t="furn", n=n, x=round(x, 3), z=round(z, 3), **k)


def _glow(x, y, z, w, h, c, **k):
    return dict(t="glow", x=round(x, 3), y=round(y, 3), z=round(z, 3), w=round(w, 3), h=round(h, 3), c=c, **k)


def _skyline(P, rnd, x0, x1, z0, z1, hmin, hmax, lit_p, base=0.0):
    """city blocks behind a window or at the end of a street: dark boxes with a few lit windows."""
    out, x = [], x0
    while x < x1:
        w = rnd.uniform(2.2, 4.5); h = rnd.uniform(hmin, hmax); z = rnd.uniform(z0, z1)
        out.append(_box(x + w / 2, base, z, w, h, 3, P["city"], ink=0))
        for j in range(int(h // 1.6)):
            for i in range(int(w // 0.9)):
                if rnd.random() < lit_p:
                    out.append(_glow(x + 0.5 + i * 0.9, base + 0.9 + j * 1.6, z + 1.52, 0.42, 0.6, P["lit"]))
        if rnd.random() < 0.25:   # antenna / crane silhouettes
            out.append(_box(x + w / 2, base + h, z, 0.08, rnd.uniform(1.5, 3.5), 0.08, P["city"], ink=0))
        x += w + rnd.uniform(0.1, 0.8)
    return out


def _sky_and_sun(P, x, z, w, h, sun_x, sun_y, time):
    out = [dict(t="grad", x=x, y=h / 2 - 2, z=z, w=w, h=h, c=P["sky"], fog=False)]
    if time == "night":
        out.append(dict(t="disc", x=sun_x, y=sun_y + 2, z=z + 1, r=1.3, c=P["sun"]))
    else:
        out += [dict(t="disc", x=sun_x, y=sun_y, z=z + 1, r=r, c=P["glow"] if r > 3 else P["sun"], op=op)
                for r, op in ((7.5, 0.18), (4.5, 0.32), (2.4, 1.0))]
    return out


# small things on every surface and wall: what makes a set read as somebody's place, not a showroom
# (frame study 2026-11-09, IfverseTales "Would You Sit at This Table?": poker chips and cards on the table, a pizza box,
#  an evidence board with red strings, mugs, a lamp on the desk; every set carries objects of the story)
TOPS = {"desk": .75, "table": .77, "kitchen_counter": .93, "bedside_table": .57, "folding_table": .91, "shop_counter": 1.06}
DRESS = {
    "desk": [("laptop_open", .45, -.05), ("mug", -.55, .15), ("papers", -.2, .2), ("desk_lamp", -.65, -.25), ("books_stack", .65, -.2), ("sticky_notes", .1, -.25)],
    "table": [("mug", -.4, .1), ("fruit_bowl", .2, -.1), ("papers", .5, .2)],
    "kitchen_counter": [("kettle", -.9, -.05), ("pot", .3, .1), ("fruit_bowl", 1.0, -.1), ("mug", -.4, .15)],
    "bedside_table": [("alarm_clock", .1, .1), ("books_stack", -.1, -.05)],
    "folding_table": [("clothes_pile", -.5, 0), ("clothes_pile", .4, .1)],
    "shop_counter": [("papers", -.6, .1)],
}
STYLE_EXTRA = {"bedroom": ["clothes_pile", "shoes", "cardboard_box"], "living": ["shoes", "coat_rack"], "office": ["cardboard_box", "coat_rack"],
               "kitchen": ["trash_bin"], "cafe": ["coat_rack"], "classroom": ["cardboard_box"], "lab": ["cardboard_box"]}


def _dress(objs, style, time, rnd, hw, BZ, ww, wx):
    out = []
    for o in list(objs):
        n = o.get("n")
        if o.get("t") != "furn" or n not in DRESS or abs(float(o.get("ry", 0))) > 0.01:
            continue
        s_ = float(o.get("s", 1)); top = TOPS[n] * s_ + float(o.get("y", 0))
        items = DRESS[n][:]
        if n == "desk" and any(p.get("n") == "computer" and abs(p["x"] - o["x"]) < .1 and abs(p["z"] - o["z"]) < .1 for p in objs):
            items = [i for i in items if i[0] != "laptop_open"]     # the desk already has a screen
        rnd.shuffle(items)
        for nm, dx, dz in items[:rnd.randint(min(2, len(items)), len(items))]:
            out.append(_f(nm, o["x"] + dx * s_, o["z"] + dz * s_, y=round(top, 3)))
    # walls: a door, a shelf, framed photos (the room has a way in and a history)
    if style not in ("grocery", "shop", "meeting"):
        free = [x for x in (-hw + 1.0, hw - 1.0) if not ww or abs(x - wx) > ww / 2 + 1.0]
        if free:
            out.append(_f("door_frame", free[0], BZ + 0.17, c=rnd.choice(["#8a5a3c", "#6e5a8a", "#e9e4d8"])))
    if style in ("bedroom", "living", "kitchen", "office", "cafe"):
        x = rnd.choice([-hw + 2.4, hw - 2.4])
        if not ww or abs(x - wx) > ww / 2 + 0.9:
            out.append(_f("wall_shelf", x, BZ + 0.18))
    for nm in STYLE_EXTRA.get(style, []):
        if rnd.random() < 0.8:
            out.append(_f(nm, rnd.choice([-1, 1]) * rnd.uniform(hw - 2.2, hw - 1.0), BZ + rnd.uniform(1.2, 2.4)))
    return out


VOID_TINT = {"mind": "#7a6ad8", "dream": "#c78ad8", "memory": "#e3b07a", "void": "#9fb3c8"}


def _void(cfg, P, rnd):
    """an abstract place (inside a mind, a dream, a memory, nowhere): the black-box stage the reference channels use.
    Dark endless floor, no walls, one pool of light where the people stand, slow dust in the beam. The objects the lines
    name stand in the light (layout.py puts them on the same room grid, so anchors and poses work as in any room)."""
    BZ = -6.0; tint = VOID_TINT.get(cfg.get("mood", "mind"), VOID_TINT["mind"]); o = []
    o.append(_box(0, -0.1, -10, 80, 0.1, 60, "#16131d", ink=0))
    for r, op in ((4.6, 0.10), (3.4, 0.16), (2.3, 0.26), (1.4, 0.32)):           # the pool of light, soft edge
        o.append(_glow(0, 0.004 + r * 0.0001, 0.8, r * 2.2, r * 1.6, tint, rx=-math.pi / 2, op=op))
    for k in range(5):                                                             # the beam: faint vertical sheets
        o.append(_glow(-1.2 + 0.6 * k, 3.0, 0.4 - 0.15 * k, 0.9, 6.0, tint, op=0.035))
    for _ in range(40):                                                            # dust in the beam
        o.append(_glow(rnd.uniform(-3, 3), rnd.uniform(0.3, 4.5), rnd.uniform(-1.5, 2.5), 0.035, 0.035, "#ffffff", op=rnd.uniform(0.3, 0.8)))
    for _ in range(26):                                                            # far points, so the dark has depth
        o.append(_glow(rnd.uniform(-14, 14), rnd.uniform(0.5, 7), rnd.uniform(-20, -9), 0.06, 0.06, tint, op=rnd.uniform(0.2, 0.6)))
    o.append(dict(t="light", x=0, y=5.5, z=1.0, c=tint, I=60, dist=11))
    o.append(dict(t="light", x=0, y=2.0, z=6.0, c="#ffffff", I=6, dist=12))
    base = dict(bg="#0d0b12", fog={"near": 10, "far": 28, "c": "#0d0b12"}, exposure=1.15, ambient={"c": "#b9b0e0", "i": 0.35},
                sun={"c": tint, "i": 0.15, "pos": [0, 8, 2]}, camera={"pos": [0, 2.0, 8.4], "look": [0, 1.65, -3], "fov": 46}, layers=None)
    return base, o


def room(cfg, P, rnd):
    style = cfg.get("style", "bedroom"); time = cfg.get("time", "dusk")
    if style == "void":
        return _void(cfg, P, rnd)
    W = float(cfg.get("w", 14)); hw = W / 2; BZ = -6.0; CH = 4.0; FRONT = 9.5
    win = cfg.get("window", {"bedroom": "left", "office": "center", "lab": "center", "kitchen": "right", "living": "left",
                             "classroom": "left", "cafe": "center", "shop": "none", "laundry": "none", "meeting": "left", "bathroom": "none",
                             "grocery": "none"}.get(style, "left"))
    wx = {"left": -2.8, "right": 2.8, "center": 0.0}.get(win, 0.0)
    ww = {"center": 6.0}.get(win, 4.2) if win != "none" else 0
    sill, top = 0.95, 3.2
    o = []
    # the room's SHELL differs per film (2026-11-14: every film's rooms had the same ceiling panels, the same plain walls
    # and the same straight-on camera, so a kitchen in one story looked like the living room of the last one).
    # Only when the film gives a seed (generate.py always does), so old specs render as before.
    sh_ = random.Random(f"shell-{cfg['seed']}-{style}") if "seed" in cfg else None
    ceiling = sh_.choice(["panels", "pendants", "beams", "plain", "panels"]) if sh_ else "panels"
    if cfg.get("ceiling"): ceiling = cfg["ceiling"]          # the designer may choose it: panels|pendants|beams|plain
    finish = (sh_.choice(["plain", "wainscot", "tiles", "stripes", "brick", "plain"]) if sh_ else "plain")
    if style == "bathroom": finish = "tiles"
    if cfg.get("finish"): finish = cfg["finish"]             # plain|wainscot|tiles|stripes|brick
    floor_c = P["floor"]
    # floor with planks, ceiling with light strips, side walls, baseboards
    o.append(_box(0, -0.1, (BZ + FRONT) / 2, W, 0.1, FRONT - BZ, floor_c, ink=0))
    for k in range(int(W / 0.7)):
        o.append(_box(-hw + 0.35 + k * 0.7, 0.001, (BZ + FRONT) / 2, 0.02, 0.004, FRONT - BZ, "#000000", ink=0, op=0.18))
    o.append(_box(0, CH, (BZ + FRONT) / 2, W, 0.12, FRONT - BZ, P["ceil"], ink=0))
    if ceiling == "panels":
        for zz in (-4.0, -0.8):
            for xx in (-3.0, 3.0):   # ceiling light panels
                o.append(_box(xx, CH - 0.06, zz, 2.2, 0.06, 0.7, "#2a2533", ink=0))
                o.append(_glow(xx, CH - 0.07, zz, 2.0, 0.5, "#fff3dc" if time != "night" else "#ffe2b0", rx=math.pi / 2))
    elif ceiling == "pendants":
        for xx, zz in ((-3.2, -3.0), (0.0, -1.2), (3.2, -3.0)):
            o.append(dict(t="lamp_hang", x=xx, z=zz, y=CH, c="#ffcf8a"))
    elif ceiling == "beams":
        for zz in (-5.0, -3.0, -1.0, 1.0):
            o.append(_box(0, CH - 0.3, zz, W, 0.3, 0.25, _mix(P["ceil"], "#6e4b35", 0.5), ink=0.02))
        o.append(dict(t="lamp_hang", x=0.0, z=-2.0, y=CH - 0.3, c="#ffcf8a"))
    for sx in (-1, 1):
        o.append(_box(sx * (hw + 0.1), 0, (BZ + FRONT) / 2, 0.2, CH, FRONT - BZ, P["wall2"], ink=0.02))
        o.append(_box(sx * (hw - 0.02), 0, (BZ + FRONT) / 2, 0.04, 0.14, FRONT - BZ, "#1e1a26", ink=0))
    # back wall around the window opening, frame and mullions
    d = 0.3
    if ww:
        l, r = wx - ww / 2, wx + ww / 2
        o.append(_box((-hw + l) / 2, 0, BZ, l + hw, CH, d, P["wall"], ink=0.02))
        o.append(_box((r + hw) / 2, 0, BZ, hw - r, CH, d, P["wall"], ink=0.02))
        o.append(_box(wx, 0, BZ, ww, sill, d, P["wall"], ink=0.02))
        o.append(_box(wx, top, BZ, ww, CH - top, d, P["wall"], ink=0.02))
        fc = "#1c1824" if time != "day" else "#f2eee6"
        o.append(_box(wx, sill - 0.06, BZ + 0.2, ww + 0.2, 0.06, 0.3, fc, ink=0.015))
        for k in range(1, int(ww // 1.5) + 1):
            o.append(_box(l + k * ww / (int(ww // 1.5) + 1), sill, BZ, 0.07, top - sill, 0.12, fc, ink=0))
        o.append(_box(wx, sill + (top - sill) * 0.62, BZ, ww, 0.06, 0.12, fc, ink=0))
        # the outside: sky, sun, city in haze
        o += _sky_and_sun(P, wx, -60, 120, 50, wx + rnd.uniform(-1.5, 1.5), 5.2, time)
        o += _skyline(P, rnd, wx - 22, wx + 22, -26, -20, 9.0, 10.8, 0.14 if time != "day" else 0.0, base=-10)
        o += _skyline(P, rnd, wx - 34, wx + 34, -44, -36, 11.3, 13.0, 0.08 if time != "day" else 0.0, base=-11)
        # light coming in: a pool on the floor and a warm light at the window
        o.append(_glow(wx, 0.006, BZ + 3.2, ww * 1.1, 5.0, P["glow"], rx=-math.pi / 2, op=0.16))
        o.append(dict(t="light", x=wx, y=2.0, z=BZ + 1.2, c=P["glow"], I=P["key"][1] * (1.2 if time != "night" else 0.6), dist=14))
        if style not in ("shop", "cafe", "kitchen", "lab", "office"):     # curtains
            cc = {"bedroom": "#8a4d6e", "living": "#6e5a8a"}.get(style, "#55506a")
            for sx in (-1, 1):
                o.append(_box(wx + sx * (ww / 2 + 0.25), 0.2, BZ + 0.3, 0.45, top + 0.25, 0.08, cc, ink=0.015))
    else:
        o.append(_box(0, 0, BZ, W, CH, d, P["wall"], ink=0.02))
    o.append(_box(0, 0, BZ + 0.17, W, 0.14, 0.04, "#1e1a26", ink=0))
    # wall finish on the back wall (below the window line) and the side walls
    if finish == "wainscot":
        o.append(_box(0, 0, BZ + 0.16, W, 1.0, 0.03, _mix(P["wall"], "#ffffff", 0.18), ink=0.015))
        o.append(_box(0, 1.0, BZ + 0.18, W, 0.05, 0.05, _mix(P["wall"], "#1e1a26", 0.5), ink=0))
    elif finish == "tiles":
        for x in [-hw + 0.3 * k for k in range(int(W / 0.3) + 1)]:
            o.append(_box(x, 0, BZ + 0.16, 0.01, 1.3, 0.005, "#ffffff", ink=0, op=0.3))
        for y in (0.3, 0.6, 0.9, 1.2):
            o.append(_box(0, y, BZ + 0.16, W, 0.01, 0.005, "#ffffff", ink=0, op=0.3))
        o.append(_box(0, 1.3, BZ + 0.17, W, 0.04, 0.03, _mix(P["wall"], "#3e7cb1", 0.4), ink=0))
    elif finish == "stripes":
        for k in range(int(W / 0.6)):
            if k % 2: o.append(_box(-hw + 0.3 + k * 0.6, 0, BZ + 0.16, 0.3, CH, 0.005, _mix(P["wall"], "#000000", 0.08), ink=0, op=0.8))
    elif finish == "brick":
        for j in range(int(CH / 0.25)):
            for k in range(int(W / 0.5) + 1):
                if (j * 3 + k) % 5 == 0:
                    o.append(_box(-hw + k * 0.5 + (0.25 if j % 2 else 0), j * 0.25, BZ + 0.16, 0.46, 0.21, 0.01, _mix(P["wall"], "#a0523d", 0.35), ink=0, op=0.7))
    # wall dressing on the free wall either side of the window
    free = [x for x in (-hw + 1.4, -hw + 3.0, hw - 1.4, hw - 3.0) if not ww or abs(x - wx) > ww / 2 + 0.9]
    rnd.shuffle(free)
    for i, x in enumerate(free[:3]):
        if i == 0:
            o.append(_f("wall_clock", x, BZ + 0.16, y=0.2))
        else:
            c = POSTER[rnd.randrange(len(POSTER))]
            o.append(_box(x, 1.55, BZ + 0.17, 0.95, 1.2, 0.03, "#15121c", ink=0))
            o.append(_glow(x, 2.15, BZ + 0.19, 0.83, 1.08, c, op=0.85))
            o.append(_glow(x, 2.3, BZ + 0.2, 0.5, 0.06, "#ffffff", op=0.7))
    # what makes the room this room
    kx = float((cfg.get("key") or {}).get("x", 1.8)); kz = float((cfg.get("key") or {}).get("z", 0.6))
    side = -1 if kx > 0 else 1   # second pieces go to the other side
    tx_ = kx if abs(kx - wx) > 2.6 and abs(kx - wx - 1.6) > 2.6 else (wx - 4.2 if wx > 0 else wx + 4.2)
    S = {
        "bedroom": [_f("bed", kx, kz, ry=math.pi / 2, s=1.2, c="#5b6f9a", c2="#6e4b35"), _f("bedside_table", kx + 1.9, kz - 0.5, s=1.1),
                    _f("rug", 0.0, 1.0, c="#7a4d6e"), _f("bookshelf", side * (hw - 1.0), BZ + 0.6),
                    _f("desk", side * 2.6, BZ + 1.1), _f("computer", side * 2.6, BZ + 1.1), _f("chair", side * 2.6, BZ + 1.8, ry=math.pi),
                    _f("plant", side * (hw - 2.3), BZ + 0.6)],
        "office": [_f("desk", kx, kz), _f("computer", kx, kz), _f("chair", kx, kz + 0.75, ry=math.pi),
                   _f("whiteboard", side * 3.6, BZ + 0.2), _f("bookshelf", -side * (hw - 0.9), BZ + 0.6),
                   _f("plant", side * (hw - 0.9), BZ + 0.7), _f("plant", -side * (hw - 2.1), BZ + 0.6, s=0.8)]
                  + [_f(n, x, BZ + 2.2) for x in (-3.2, 0.0, 3.2) for n in ("desk", "computer")]
                  + [_f("chair", x - 1.0, BZ + 2.2, ry=math.pi / 2) for x in (-3.2, 0.0, 3.2)],   # colleagues sit here (extras.py)
        "lab": [_box(0, 0, BZ + 1.6, ww + 2.5 if ww else 8, 0.95, 0.9, "#2a2633", ink=0.02),
                _box(0, 0.95, BZ + 1.6, (ww + 2.5 if ww else 8) + 0.1, 0.05, 0.95, "#4a4456", ink=0.015),
                _f("computer", side * 2.4, BZ + 1.75, y=0.28), _f("whiteboard", -side * (hw - 1.6), BZ + 0.2), _f("bookshelf", side * (hw - 0.9), BZ + 0.6)]
               + [dict(t="cylinder", x=-2 + 0.55 * k, y=1.0, z=BZ + 1.5, rt=0.05, rb=0.13, h=0.32, c=POSTER[k % 7]) for k in range(6)],
        "kitchen": [_f("kitchen_counter", wx, BZ + 0.6), _f("oven", wx + 1.6, BZ + 0.6), _f("fridge", -side * (hw - 1.0), BZ + 0.7),
                    # the dining table stands on the side away from the counter and oven, so the way to them stays clear
                    # (a table in front of the oven put a cook "walking to the oven" on top of the table, night 003)
                    _f("table", tx_, kz), _f("chair", tx_ - 1.0, kz, ry=math.pi / 2), _f("chair", tx_ + 1.0, kz, ry=-math.pi / 2)]
                   + [_box(wx + sx * (ww / 2 + 1.1), 2.1, BZ + 0.35, 1.6, 0.7, 0.4, "#d9d2c3" if time == "day" else "#5a4f6e", ink=0.02) for sx in (-1, 1)],
        "living": [_f("sofa", kx, kz, c="#7a5c9a"), _f("tv", side * 2.8, BZ + 0.8), _f("lamp_floor", kx + 1.6, kz - 0.4),
                   _f("rug", kx * 0.6, kz + 0.6, c="#c96f5a"), _f("plant", side * (hw - 1.0), BZ + 0.7), _f("bookshelf", -side * (hw - 0.9), BZ + 0.6)],
        "classroom": [_f("whiteboard", 1.5, BZ + 0.2, s=1.4)] + [_f(n, x, z) for x in (-3.4, 0.0, 3.4) for z in (-2.8, -0.6)
                                                                 for n in ("desk", "chair")],
        "cafe": [_f("shop_counter", side * 3.0, BZ + 1.0, c="#6e4b35"), _f("table", kx, kz, s=0.75), _f("chair", kx - 0.8, kz, ry=math.pi / 2),
                 _f("chair", kx + 0.8, kz, ry=-math.pi / 2), _f("table", -kx, kz - 2.2, s=0.75), _f("plant", -side * (hw - 0.9), BZ + 0.7)]
                + [dict(t="lamp_hang", x=x, z=z, y=CH, c="#ffcf8a") for x, z in ((kx, kz), (-kx, kz - 2.2))],
        "laundry": [_f("washer", -hw + 1.2 + 0.8 * k, BZ + 0.5, c="#eef0f2" if k % 3 else "#dfe3e8") for k in range(int(W // 0.8) - 3)]
                   + [_f("washer", -hw + 1.2 + 0.8 * k, BZ + 0.5, y=0.92, c="#e4e8ec") for k in range(0, int(W // 0.8) - 3, 2)]
                   + [_f("folding_table", kx, kz), _f("laundry_basket", kx - 1.3, kz + 0.3), _f("laundry_basket", kx + 1.1, kz + 0.6, c="#c96f5a"),
                      _f("bench", -kx, kz - 0.4, c="#5a6070"), _f("wall_shelf", side * 3.4, BZ + 0.2), _f("trash_bin", -side * (hw - 0.8), BZ + 1.6),
                      _glow(0, 2.6, BZ + 0.2, 2.6, 0.5, "#fff1c8", op=0.9), _glow(0, 2.62, BZ + 0.21, 2.2, 0.12, "#2a2730", op=0.8)],
        # the presenter's end of the room is the back wall: screen and podium there, the audience rows face it from the
        # front, the aisle between them stays clear, so a presenter is never drawn among the audience (2026-11-09)
        "meeting": [_f("projector_screen", 1.2, BZ + 0.3), _f("podium", -1.5, BZ + 1.7), _f("plant", -hw + 1.0, BZ + 0.7),
                    _f("wall_clock", hw - 1.6, BZ + 0.16, y=0.2), _f("coat_rack", hw - 0.8, BZ + 1.6)]
                   + [_f("chair", x, z, ry=math.pi, c="#3e5c8a") for z in (0.4, 1.6) for x in (-3.6, -2.6, -1.6, 1.6, 2.6, 3.6)],
        "bathroom": [_f("sink", kx, BZ + 0.5), _f("mirror", kx, BZ + 0.18), _f("bathtub", -side * 2.6, BZ + 0.6),
                     _f("toilet", side * 0.6 + kx * 0.4, BZ + 0.45), _f("towel_rail", -side * 0.6, BZ + 0.18), _f("wall_shelf", -side * 2.6, BZ + 0.18),
                     _f("rug", kx * 0.5, kz, c="#5b8fb9")]
                    + [_box(x, 0, BZ + 0.16, 0.01, 2.0, 0.005, "#ffffff", ink=0, op=0.35) for x in [-hw + 0.4 * k for k in range(int(W / 0.4))]]
                    + [_box(0, y, BZ + 0.16, W, 0.01, 0.005, "#ffffff", ink=0, op=0.35) for y in (0.4, 0.8, 1.2, 1.6, 2.0)],
        "grocery": [_f("shelf_goods", sx * x, z, c="#e9e4d8") for sx in (-1, 1) for x, z in ((2.4, -3.4), (4.6, -3.4), (2.6, -0.8), (4.9, -0.8))]
                   + [_f("fridge_display", x, BZ + 0.4) for x in (-3.2, -1.7, 1.7, 3.2)]
                   + [_f("shop_counter", side * 4.6, 2.2, ry=side * math.pi / 2, c="#3e7cb1"), _f("cardboard_box", -side * 1.2, 1.5),
                      _f("cardboard_box", -side * 1.4, 1.7, y=0.4, s=0.8), _glow(0, 3.3, BZ + 0.2, 3.6, 0.5, "#e35d4f"),
                      _glow(0, 3.32, BZ + 0.21, 2.6, 0.12, "#ffffff", op=0.9)]
                   + [_glow(0, CH - 0.07, z, 0.4, 3.0, "#f4fbff", rx=math.pi / 2) for z in (-4.0, -1.0, 2.0)],
        "generic": [],      # layout.py furnishes it from catalog.PLACES or the objects the lines name
        "shop": [_f("shop_counter", kx, kz), _f("shelf_goods", -3.5, BZ + 0.4), _f("shelf_goods", 0.0, BZ + 0.4), _f("shelf_goods", 3.5, BZ + 0.4),
                 _glow(0, 3.0, BZ + 0.2, 3.0, 0.45, "#ff5a5a")],
    }
    o += S.get(style, S["bedroom"])
    o += _dress(o, style, time, rnd, hw, BZ, ww, wx)
    # warm interior lamp near the key piece, cool fill from the front
    o.append(dict(t="light", x=kx + 0.5, y=2.4, z=kz + 1.0, c=P["key"][0], I=P["key"][1], dist=9))
    if cfg.get("fg", True):   # blurred foreground at the frame edges (rendered on the near layer)
        o += [_box(-2.25, 0, 5.4, 1.0, 0.8, 0.6, "#1b1722", ink=0.02), _f("plant", -2.1, 5.4, y=0.8, s=0.55),
              _box(2.3, 0, 5.4, 1.0, 0.7, 0.6, "#1b1722", ink=0.02),
              dict(t="cylinder", x=2.0, y=0.7, z=5.4, rt=0.05, rb=0.12, h=0.3, c=P["glow"]),
              dict(t="cylinder", x=2.25, y=0.7, z=5.35, r=0.07, h=0.42, c="#6fb3a8")]
    base = dict(bg=P["wall2"], fog={"near": P["fog"][0], "far": P["fog"][1], "c": P["sky"][1]}, exposure=0.95 if time == "day" else 1.15,
                ambient={"c": P["amb"][0], "i": P["amb"][1]}, sun={"c": P["sun"], "i": 0.35, "pos": [wx, 5, -10]},
                camera=({"pos": [0, 2.0, 8.4], "look": [0, 1.65, -3], "fov": 46} if not sh_ else
                        (lambda dx, fv: {"pos": [dx, 2.0 + sh_.uniform(-0.15, 0.25), 8.4], "look": [-dx * 0.35, 1.65, -3], "fov": fv})(
                            sh_.choice([-1.1, -0.6, 0.0, 0.6, 1.1]), sh_.choice([42, 44, 46, 48]))),
                layers=[6.0, 15.0] if cfg.get("fg", True) else None, _win=(wx if ww else None))
    return base, o


def street(cfg, P, rnd):
    time = cfg.get("time", "dusk"); o = []
    o.append(_box(0, -0.05, -30, 8.5, 0.05, 120, "#3b3a45" if time != "day" else "#5a5c66", ink=0))
    for z in range(8, -80, -6):
        o.append(_box(0, 0.002, z, 0.16, 0.004, 2.6, "#e9e4d8", ink=0, op=0.85))
    for k in range(8):   # crosswalk
        o.append(_box(-3.5 + k, 0.003, 3.0, 0.55, 0.004, 3.0, "#ece7dc", ink=0, op=0.9))
    for sx in (-1, 1):
        o.append(_box(sx * 6.0, 0, -30, 3.4, 0.16, 120, "#8a8794" if time != "day" else "#b9b5ad", ink=0.01))
        o.append(_box(sx * 4.3, 0, -30, 0.12, 0.17, 120, "#5c5965", ink=0))
        z = 6.0
        while z > -75:   # building row facing the road
            dz = rnd.uniform(6, 10); h = rnd.uniform(7, 15)
            c = rnd.choice(["#6a5f7a", "#5a5068", "#7a6a7e", "#4f4a62"] if time != "day" else ["#d8cfc0", "#c9bfae", "#e4dccd", "#b7aea0"])
            o.append(_box(sx * (7.7 + 3), 0, z - dz / 2, 6, h, dz - 0.2, c, ink=0.025))
            for j in range(int((h - 1) // 2.2)):
                for i in range(int((dz - 1) // 1.5)):
                    lit = rnd.random() < (0.35 if time != "day" else 0.0)
                    o.append(_glow(sx * 7.69, 1.6 + j * 2.2, z - 0.9 - i * 1.5, 0.75, 1.0, P["lit"] if lit else ("#2a2638" if time != "day" else "#8fb4d8"),
                                   ry=-sx * math.pi / 2))
            if rnd.random() < 0.5 and z > -30:   # shop awning at street level
                o.append(_box(sx * 7.2, 2.6, z - dz / 2, 1.0, 0.12, dz * 0.7, rnd.choice(["#c0504d", "#3e7cb1", "#3aa65a"]), ink=0.02, rz=sx * 0.25))
                o.append(_glow(sx * 7.68, 1.2, z - dz / 2, dz * 0.6, 1.4, P["glow"] if time != "day" else "#cfe3f5", ry=-sx * math.pi / 2, op=0.9))
            z -= dz
        for z in (4.0, -8.0, -20.0, -32.0):
            o.append(dict(t="lamp", x=sx * 4.8, z=z + (3 if sx > 0 else 0), h=4.4, c="#ffb45a", I=16 if time != "day" else 0.01, dist=12))
        for z in (-2.0, -14.0, -26.0):
            o.append(dict(t="prop", n="tree_oak", x=sx * 5.5, y=0.16, z=z, s=1.6, tint="#6a8a6a" if time == "day" else "#4e5a6a"))
        o.append(_box(sx * 4.6, 0, -4.5, 0.18, 7.5, 0.18, "#2b2830", ink=0.01))   # power pole
    o.append(_box(0, 7.1, -4.5, 9.2, 0.03, 0.03, "#1b1a1f", ink=0))
    o.append(_box(0, 6.8, -4.5, 9.2, 0.03, 0.03, "#1b1a1f", ink=0))
    o.append(_f("car", -2.0, -14.0, ry=0, c="#d8473d")); o.append(_f("street_sign", 4.8, 1.0))
    o += _sky_and_sun(P, 0, -110, 220, 90, rnd.uniform(-4, 4), 7, time)
    o += _skyline(P, rnd, -40, 40, -100, -85, 10, 30, 0.1 if time != "day" else 0)
    base = dict(sky=P["sky"], fog={"near": P["fog"][0] + 10, "far": P["fog"][1] + 60, "c": P["sky"][1]}, exposure=1.2,
                ambient={"c": P["amb"][0], "i": P["amb"][1] * 1.1}, sun={"c": P["sun"], "i": 0.6, "pos": [-4, 8, -20]},
                stars=120 if time == "night" else 0, camera={"pos": [1.2, 1.8, 10.5], "look": [0, 2.4, -20], "fov": 46},
                layers=None)
    return base, o


def shopfront(cfg, P, rnd):
    time = cfg.get("time", "night"); style = cfg.get("style", "cafe"); o = []
    o.append(_box(0, -0.05, 0, 80, 0.05, 40, "#34323e" if time != "day" else "#5a5c66", ink=0))
    o.append(_box(0, 0, -2.0, 40, 0.16, 5, "#77737f" if time != "day" else "#b9b5ad", ink=0.01))
    for k in range(0, 40, 3):
        o.append(_box(-20 + k, 0.002, 4.5, 1.6, 0.004, 0.14, "#e9e4d8", ink=0, op=0.8))
    fc = {"cafe": "#3b2e2a", "shop": "#2e3b4a", "office": "#3a3d4c"}.get(style, "#3b2e2a")
    o.append(_box(0, 0, -6.5, 12, 7.5, 4, fc, ink=0.03))
    for i in range(4):   # big lit shop windows
        o.append(_glow(-4.2 + i * 2.8, 1.55, -4.49, 2.3, 2.1, P["glow"], op=0.95))
        o.append(_box(-4.2 + i * 2.8, 0.45, -4.4, 2.5, 0.08, 0.1, "#15121c", ink=0))
    for j in range(2):
        for i in range(5):
            o.append(_glow(-4.4 + i * 2.2, 4.4 + j * 1.6, -4.49, 1.1, 1.0, P["lit"] if rnd.random() < 0.5 else "#221e30"))
    o.append(_box(0, 2.9, -4.0, 11.6, 0.14, 1.2, {"cafe": "#c0504d", "shop": "#3e7cb1"}.get(style, "#3aa65a"), ink=0.02, rz=0))
    for k in range(12):
        o.append(_box(-5.5 + k, 2.75, -3.42, 0.5, 0.2, 0.04, "#f3eee4", ink=0))
    o.append(_glow(0, 3.6, -4.48, 4.0, 0.6, "#ffe9b0"))
    o.append(dict(t="light", x=0, y=1.6, z=-2.5, c=P["glow"], I=120, dist=12))
    o.append(_glow(0, 0.17, -1.2, 11, 3.5, P["glow"], rx=-math.pi / 2, op=0.22))
    for sx in (-1, 1):
        o.append(_f("building", sx * 9.5, -7.0, c=rnd.choice(["#3b3550", "#45405a"]) if time != "day" else "#cfc6b6"))
        o.append(dict(t="lamp", x=sx * 7.2, z=-0.6, h=4.2, c="#ffb45a", I=16, dist=12))
        o.append(dict(t="prop", n="tree_oak", x=sx * 5.4, y=0.16, z=-1.2, s=1.4, tint="#3e4a56"))
    o.append(_f("bench", 3.6, -1.5, c="#5a4030"))
    o += _sky_and_sun(P, 0, -60, 160, 70, -12, 9, time)
    o += _skyline(P, rnd, -50, 50, -40, -30, 10, 24, 0.1 if time != "day" else 0)
    base = dict(sky=P["sky"], fog={"near": 25, "far": 90, "c": P["sky"][1]}, exposure=1.2, stars=140 if time == "night" else 0,
                ambient={"c": P["amb"][0], "i": P["amb"][1]}, sun={"c": P["sun"], "i": 0.4, "pos": [-6, 8, 6]},
                camera={"pos": [0, 1.9, 11.5], "look": [0, 2.6, -5], "fov": 44}, layers=None)
    return base, o


def beach(cfg, P, rnd):
    time = cfg.get("time", "day"); o = []
    sand = {"day": "#e8cf9a", "dusk": "#d9a878", "night": "#5a5068"}.get(time, "#e8cf9a")
    sea = {"day": "#3fa7c9", "dusk": "#7a6aa8", "night": "#232a55"}.get(time, "#3fa7c9")
    o.append(_box(0, -0.05, 10, 120, 0.05, 50, sand, ink=0))                      # sand from behind the 9:16 camera (z~30) to the waterline at z=-15
    o.append(_box(0, -0.02, -60, 260, 0.03, 90, sea, ink=0))                      # sea to the horizon
    for k in range(7):                                                             # foam lines
        o.append(_box(rnd.uniform(-20, 20), 0.012, -15.2 - k * 2.6, rnd.uniform(4, 12), 0.004, 0.25, "#f3f7fa", ink=0, op=0.7))
    o.append(_box(0, 0.011, -15.1, 120, 0.004, 0.5, "#f3f7fa", ink=0, op=0.85))
    for i, x in enumerate((-6.5, -2.0, 3.0, 7.0)):                                 # umbrellas and towels on the sand
        o.append(_f("umbrella", x, -6.5 + (i % 2) * 2.5, c=POSTER[(i * 3) % 7]))
        o.append(_f("towel", x + 0.9, -6.0 + (i % 2) * 2.5, ry=0.15 * (i - 1.5), c=POSTER[(i * 2 + 1) % 7]))
    for x, z in ((-11, -4), (12, -6), (-14, -12)):
        o.append(_f("palm", x, z))
    o.append(_f("towel", 0.6, 2.6, ry=1.5708, c="#3e7cb1"))       # the hero's spot, near the camera (lie@towel picks it)
    o.append(_f("umbrella", -1.0, 2.0, c="#e3b341"))
    o += _sky_and_sun(P, 0, -140, 300, 120, 6, 9 if time != "dusk" else 4, time)
    base = dict(sky=P["sky"] if time != "day" else ["#5aa6e8", "#d8eef8"], fog={"near": 40, "far": 160, "c": P["sky"][1]}, exposure=1.15,
                ambient={"c": P["amb"][0], "i": P["amb"][1] * 1.1}, sun={"c": P["sun"], "i": 0.7, "pos": [-6, 10, 4]},
                stars=120 if time == "night" else 0, camera={"pos": [0, 2.8, 10.0], "look": [0, 0.6, -20], "fov": 46}, layers=None)   # flat: distant swimmers and walkers must move with the picture (no parallax drift)
    return base, o


TYPES = {"room": room, "street": street, "shopfront": shopfront, "beach": beach}
STYLES = ["bedroom", "office", "lab", "kitchen", "living", "classroom", "cafe", "shop", "laundry", "meeting", "bathroom", "grocery", "generic", "void"]


def expand(setting):
    """setting with a "set" key -> full setting; anything else unchanged."""
    if not isinstance(setting, dict) or not isinstance(setting.get("set"), dict):
        return setting
    cfg = setting["set"]
    P = dict(TIMES.get(cfg.get("time", "dusk"), TIMES["dusk"]))
    sp = STYLE_PAL.get(cfg.get("style")) if cfg.get("type", "room") == "room" else None
    if sp:
        # how much the time of day tints the walls: an interior at night is lit by its own lamps, so it keeps its colour
        # (at .55 every night room of every film turned the same violet, 2026-11-14)
        t = {"day": 0.0, "dusk": 0.3, "night": 0.3}.get(cfg.get("time", "dusk"), 0.3)
        for k in ("wall", "wall2", "floor"):
            P[k] = _mix(sp[k], P[k], t)
    rnd = random.Random(cfg.get("seed", 7))
    if sp and "seed" in cfg:     # the film's own seed: a different wall/floor colour and window side for the same style
        vr = random.Random(f"look-{cfg['seed']}")
        tints = ["#c9a27a", "#8fa8c8", "#a8c49a", "#c48f9a", "#d8c890", "#9a8fc4", "#b0b0b0"]
        tw, tf = vr.choice(tints), vr.choice(tints)
        P["wall"] = _mix(P["wall"], tw, vr.uniform(0.15, 0.3)); P["wall2"] = _mix(P["wall2"], tw, vr.uniform(0.15, 0.3))
        P["floor"] = _mix(P["floor"], tf, vr.uniform(0.1, 0.22))
        if "window" not in cfg and cfg.get("style") not in ("shop", "laundry", "bathroom", "grocery"):
            cfg = dict(cfg, window=vr.choice(["left", "right", "center"]))
        if "key" not in cfg:
            cfg = dict(cfg, key={"x": vr.choice([-1, 1]) * vr.uniform(1.4, 2.4), "z": vr.uniform(0.3, 0.9)})
    for k_ in ("wall", "wall2", "floor", "ceil"):      # the set designer chooses the colours of THIS place
        if isinstance(cfg.get(k_), str) and cfg[k_].startswith("#"): P[k_] = cfg[k_]
    if isinstance(cfg.get("wall"), str) and not cfg.get("wall2"): P["wall2"] = _mix(P["wall"], "#000000", 0.12)   # side walls follow
    fn = TYPES.get(cfg.get("type", "room"))
    if not fn:
        raise ValueError(f"unknown set type {cfg.get('type')} (known: {', '.join(TYPES)})")
    base, objs = fn(cfg, P, rnd)
    out = {k: v for k, v in base.items() if v is not None}
    for k, v in setting.items():
        if k not in ("set", "objects"):
            out[k] = v
    out["objects"] = objs + list(setting.get("objects", []))
    out["_kind"] = {"type": cfg.get("type", "room"), "style": cfg.get("style"), "time": cfg.get("time", "dusk")}   # anchors/extras read this
    return out


def contents(setting):
    """furniture names a set puts in (so spec_lint matches a line about a bed to a bedroom set)."""
    if not isinstance(setting, dict) or not isinstance(setting.get("set"), dict):
        return set()
    full = expand(setting)
    names = {o.get("n") for o in full["objects"] if o.get("t") == "furn"}
    t = setting["set"].get("type", "room")
    if t == "room" and setting["set"].get("style") != "void" and setting["set"].get("window", "left") != "none" and not (setting["set"].get("style") in ("shop", "laundry", "bathroom", "grocery") and "window" not in setting["set"]):
        names.add("window")
    if t == "street":
        names |= {"street", "car", "building", "street_sign", "road"}
    if t == "shopfront":
        names |= {"building", "shop", "bench"}
    if setting["set"].get("style") in ("shop", "cafe", "grocery"):
        names |= {"shop_counter", "shelf_goods"}
    return names
