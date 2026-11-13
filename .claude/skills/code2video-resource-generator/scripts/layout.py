"""Put any catalog object into a room without hand-placing it: zone + footprint + free space.

    layout.add(setting_dict, ["washer", "podium"])   -> appends {"t":"furn", ...} entries at free spots
    layout.room_from(names, cfg)                      -> a generic dressed room built from a furniture list (PLACES)

Rooms from sets.room(): width W (default 14 m, x in [-W/2, W/2]), back wall at z = -6, characters stand around
x in [-3, 3], z in [0, 3] (camera at z = 8.4). The free walkway in front of the camera is kept empty so nothing hides
the people; wall pieces go on the back wall beside the window, centre pieces into the middle band, surface pieces on top
of a desk/table/counter, floor pieces near the side walls.
"""
import math

try:
    import catalog as CAT
except ImportError:
    from scripts import catalog as CAT

BZ = -6.0
TOPS = {"desk": .75, "table": .77, "kitchen_counter": .93, "bedside_table": .57, "folding_table": .91, "shop_counter": 1.06, "oven": .93}
WALKWAY = (-1.6, 1.6, 0.0, 4.0)      # x0, x1, z0, z1: kept clear for the characters


def _rect(o):
    e = CAT.C.get(o.get("n"), {}); s = float(o.get("s", 1))
    w, d = e.get("w", .8) * s, e.get("d", .8) * s
    if abs(abs(float(o.get("ry", 0))) - math.pi / 2) < 0.2:
        w, d = d, w
    x, z = float(o.get("x", 0)), float(o.get("z", 0))
    return (x - w / 2, x + w / 2, z - d / 2, z + d / 2)


def _hit(a, b, pad=0.15):
    return not (a[1] + pad <= b[0] or b[1] + pad <= a[0] or a[3] + pad <= b[2] or b[3] + pad <= a[2])


def _free(rect, taken, hw):
    if rect[0] < -hw + 0.2 or rect[1] > hw - 0.2 or rect[2] < BZ + 0.1:
        return False
    return not any(_hit(rect, t) for t in taken)


def _window(setting):
    k = (setting.get("set") or {})
    win = k.get("window")
    if win == "none":
        return None
    return {"left": (-2.8, 4.2), "right": (2.8, 4.2), "center": (0.0, 6.0)}.get(win or "left", (-2.8, 4.2))


def add(setting, names, key_near=None):
    """append the named catalog objects to setting["objects"] at free spots. Returns the names added."""
    objs = setting.setdefault("objects", [])
    cfg = setting.get("set") or {}
    hw = float(cfg.get("w", 14)) / 2
    try:                       # the set's own furniture is only there after expansion: avoid it too
        import sets as SETS
        full = SETS.expand(setting)["objects"] if isinstance(setting.get("set"), dict) else objs
    except ImportError:
        from scripts import sets as SETS
        full = SETS.expand(setting)["objects"] if isinstance(setting.get("set"), dict) else objs
    taken = [_rect(o) for o in full if o.get("t") == "furn" and CAT.C.get(o.get("n"), {}).get("zone") not in ("surface", "wall")]
    if isinstance(setting.get("set"), dict):
        objs_all = full            # surface hosts may belong to the set
    else:
        objs_all = objs
    win = _window(setting)
    added = []
    for n in names:
        e = CAT.C.get(n)
        if not e:
            continue
        zone = e["zone"]
        if cfg.get("style") == "void" and zone in ("back", "wall", "side", "floor"):
            zone = "center"       # an abstract stage has no walls: everything stands in the pool of light
        if zone == "surface":
            ons = (e.get("on") or "desk table").split()
            hosts = sorted([o for o in objs_all + objs if o.get("t") == "furn" and o.get("n") in ons], key=lambda o: ons.index(o["n"]))
            if not hosts:
                k0 = len(objs); add(setting, [ons[0]]); taken += [_rect(o) for o in objs[k0:]]
                hosts = [o for o in objs if o.get("n") == ons[0]]
            if not hosts:
                continue
            h = hosts[0]
            objs.append(dict(t="furn", n=n, x=round(float(h["x"]) + 0.35 * (len(added) % 3 - 1), 3), z=round(float(h["z"]) + 0.1, 3),
                             y=round(TOPS.get(h["n"], .76) * float(h.get("s", 1)) + float(h.get("y", 0)), 3)))
            added.append(n); continue
        cands = []
        if zone in ("back", "wall"):
            z = BZ + (0.17 if zone == "wall" else 0.2 + e["d"] / 2)
            y = 0.2 if n in ("wall_clock",) else 0.0
            for x in [i * 0.5 for i in range(-int(hw * 2), int(hw * 2) + 1)]:
                if win and abs(x - win[0]) < win[1] / 2 + e["w"] / 2 + 0.2:
                    continue
                cands.append(dict(x=x, z=z, ry=0.0, y=y))
            cands.sort(key=lambda c: abs(c["x"]))
        elif zone == "side":
            for z in (-4.5, -3.0, -1.5, 0.0):
                for sx in (-1, 1):
                    cands.append(dict(x=sx * (hw - e["d"] / 2 - 0.25), z=z, ry=-sx * math.pi / 2))
        elif zone == "floor":
            for z in (BZ + 0.6, -3.5, -1.5, 0.5):
                for sx in (-1, 1):
                    cands.append(dict(x=sx * (hw - 0.6), z=z, ry=0.0))
        else:   # center: middle band first, near where the action is
            for z in (-1.0, -2.6, 0.6, -4.0, 1.8):
                for x in (2.4, -2.4, 3.8, -3.8, 0.0, 1.2, -1.2, 5.0, -5.0):
                    cands.append(dict(x=x, z=z, ry=0.0))
            if key_near is not None:
                cands.sort(key=lambda c: abs(c["x"] - key_near))
        near = [o for o in full + objs if o.get("t") == "furn" and o.get("n") == e.get("near")]
        if near:      # a bedside table goes beside the bed, a mirror over the sink
            nx, nz = float(near[0].get("x", 0)), float(near[0].get("z", 0))
            cands = [dict(x=nx + dx, z=nz + dz, ry=0.0, **({"y": 0.0} if zone == "wall" else {}))
                     for dx in (1.3, -1.3, 1.0, -1.0, 0.0) for dz in ((0.0,) if zone == "wall" else
                                                                      (1.7, 1.3, 2.1) if CAT.C.get(e["near"], {}).get("zone") in ("wall", "back")
                                                                      else (-0.7, -0.3, 0.0))] + cands
            if zone == "wall":
                cands = [dict(x=nx, z=BZ + 0.17, ry=0.0)] + cands
        for c in cands:
            o = dict(t="furn", n=n, **{k: round(v, 3) for k, v in c.items() if v or k in ("x", "z")})
            r = _rect(o)
            if zone == "center" and _hit(r, WALKWAY, pad=0) and n not in ("rug",):
                continue
            if _free(r, taken, hw) or n == "rug":
                objs.append(o); taken.append(r); added.append(n)
                if n in ("desk", "table") and not any(p.get("n") == "chair" and _hit(_rect(p), (r[0] - .6, r[1] + .6, r[2] - .6, r[3] + .9)) for p in objs):
                    # a work surface comes with a chair turned to it, on a FREE side: in front, then left, right, behind.
                    # (2026-11-12, video 005: it was put in front without a check and landed inside the sofa, so the
                    # heroine sat in the middle of the sofa with only her head and feet showing)
                    for cx_, cz_, cr_ in ((o["x"], r[3] + 0.4, math.pi), (r[0] - 0.45, o["z"], math.pi / 2), (r[1] + 0.45, o["z"], -math.pi / 2), (o["x"], r[2] - 0.4, 0.0)):
                        ch = dict(t="furn", n="chair", x=round(cx_, 3), z=round(cz_, 3), ry=round(cr_, 4))
                        if _free(_rect(ch), taken, hw):
                            objs.append(ch); taken.append(_rect(ch)); break
                break
    return added


def room_from(names, cfg):
    """a generic room (walls, window, lights, dressing from sets.room with style 'generic') plus the listed pieces."""
    import sets as SETS
    base = SETS.expand({"set": dict(cfg, style="generic")})
    add(base, names)
    return base
