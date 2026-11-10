"""Extras: the other people and the traffic that make a place believable.

An office at 9 a.m. has colleagues typing at the other desks, a street has cars and people crossing, a cafe has
customers and someone behind the counter, a beach has swimmers and people on towels. A bedroom at 2 a.m. has nobody.
Before this module every scene had only the people the script named, so places looked staged and empty.

plan(spec)   (generate.py, after coverage.expand): reads every setting's kind (set type / style / time of day) and what
             the lines in it say ("alone", "empty" -> nobody; "busy", "crowd", "colleagues" -> more), decides the extras,
             adds them to the cast (ids x_<setting>_<n>, "extra": true, wardrobe that fits the place) and stores the plan
             in spec["extras_plan"].
place(...)   (build_project.py, per shot): puts them on the set's anchors (anchors.py) - seated at the free chairs,
             behind the counter, lying on towels, swimming, walking across the floor or along the pavement - and adds
             cars that drive along the street lanes. Seated/standing extras keep the same seat in every shot of the
             setting (continuity); walkers and cars pass through and differ per shot.

Override per setting: "extras": "none" | 0 | 0.5 (fewer) | 2 (more) | [{"role": "walk"}, ...].
"""
import json
import random
import re

# role, count by time of day  (roles: sit_work, sit_drink, sit_listen, behind, browse, walk, walk_street, cross,
#                              swim, sunbathe, traffic, bench)
RULES = {
    ("room", "office"): {"day": [("sit_work", 3), ("walk", 1)], "dusk": [("sit_work", 1)], "night": []},
    ("room", "classroom"): {"day": [("sit_listen", 5)], "dusk": [("sit_listen", 2)], "night": []},
    ("room", "cafe"): {"day": [("sit_drink", 3), ("behind", 1), ("walk", 1)], "dusk": [("sit_drink", 2), ("behind", 1)], "night": [("sit_drink", 1), ("behind", 1)]},
    ("room", "shop"): {"day": [("behind", 1), ("browse", 2)], "dusk": [("behind", 1), ("browse", 1)], "night": [("behind", 1)]},
    ("room", "meeting"): {"day": [("sit_listen", 6)], "dusk": [("sit_listen", 4)], "night": [("sit_listen", 2)]},
    ("room", "laundry"): {"day": [("browse", 1), ("sit_listen", 1)], "dusk": [("sit_listen", 1)], "night": []},
    ("room", "grocery"): {"day": [("behind", 1), ("browse", 3)], "dusk": [("behind", 1), ("browse", 2)], "night": [("behind", 1), ("browse", 1)]},
    ("room", "lab"): {"day": [("browse", 1)], "dusk": [("browse", 1)], "night": []},
    ("street", None): {"day": [("walk_street", 4), ("cross", 2), ("traffic", 4)], "dusk": [("walk_street", 3), ("cross", 1), ("traffic", 3)], "night": [("walk_street", 1), ("traffic", 2)]},
    ("shopfront", None): {"day": [("walk", 3), ("bench", 1)], "dusk": [("walk", 2), ("bench", 1)], "night": [("walk", 1)]},
    ("beach", None): {"day": [("swim", 4), ("sunbathe", 3), ("walk", 2)], "dusk": [("swim", 1), ("sunbathe", 1), ("walk", 2)], "night": []},
}
PRIVATE = {"bedroom", "kitchen", "living", "bathroom"}         # homes: nobody else unless the script brings them
ALONE = re.compile(r"\b(alone|empty|nobody|no one|deserted|quiet office|by herself|by himself|on (?:her|his) own|abandoned|lonely)\b", re.I)
BUSY = re.compile(r"\b(busy|crowd(?:ed)?|packed|rush(?: hour)?|colleagues?|co-?workers?|everyone|people|customers|tourists|traffic|queue)\b", re.I)

WARDROBE = {
    "office": dict(top=["shirt", "jacket", "shirt", "coat"], tie=0.5, colors=["#3e5c8a", "#5b6f9a", "#7a7f8c", "#2f3646", "#8a5a3c", "#e9e4d8"]),
    "beach": dict(top=["tank", "tshirt", "tank"], bottom="shorts", shoes="none", colors=["#e35d4f", "#38b7c9", "#e3b341", "#3aa65a", "#f08a5d", "#ffffff"]),
    "default": dict(top=["tshirt", "hoodie", "jacket", "shirt", "coat"], colors=["#c0504d", "#3e7cb1", "#3aa65a", "#7a5c9a", "#e3b341", "#5b6f9a", "#8a5a3c", "#2f3646"]),
}


def _kind(setting, settings_lib):
    st = setting
    if isinstance(st, str):
        try:
            st = json.load(open(st, encoding="utf-8"))
        except Exception:
            return None
    if not isinstance(st, dict):
        return None
    cfg = st.get("set") if isinstance(st.get("set"), dict) else None
    if not cfg:
        return None
    return cfg.get("type", "room"), cfg.get("style") if cfg.get("type", "room") == "room" else None, cfg.get("time", "dusk"), st


def _texts_by_setting(spec):
    out = {}
    for sc in spec.get("scenes", []):
        for sh in sc.get("shots", []):
            for c in sh.get("cues", []) or []:
                out.setdefault(sh.get("setting"), []).append(c if isinstance(c, str) else c.get("t", ""))
    return out


def _rgb(h):
    h = h.lstrip("#"); return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def _mute(h, f=0.35):
    """towards grey: background people must not compete with the hero"""
    r, g, b = _rgb(h); m = (r + g + b) / 3
    return "#%02x%02x%02x" % tuple(int(v + (m - v) * f) for v in (r, g, b))


def _outfit(rnd, wardrobe_key, i, avoid=()):
    W = WARDROBE.get(wardrobe_key, WARDROBE["default"])
    top = rnd.choice(W["top"])
    pool = [c for c in W["colors"] if all(sum(abs(x - y) for x, y in zip(_rgb(c), _rgb(a))) > 150 for a in avoid)] or ["#8a8794", "#6e6a78"]
    col = _mute(rnd.choice(pool))
    female = rnd.random() < 0.5
    c = {"top": top, "top_color": col, "bottom": W.get("bottom", "none"), "shoes": W.get("shoes", rnd.choice(["sneakers", "boots"])),
         "hair_style": rnd.choice(["long", "bun", "short"]) if female else rnd.choice(["short", "spiky", "none", "tuft"]),
         "hair": rnd.choice(["#2a2230", "#5a3a28", "#8a6a3c", "#1c1626", "#b08850"]), "gender": "f" if female else "m"}
    if rnd.random() < W.get("tie", 0):
        c["tie"] = rnd.choice(["#2b4a7a", "#7a2b2b", "#2b6a4a"])
    if rnd.random() < 0.25:
        c["glasses"] = True
    return c


def plan(spec):
    """add extras to spec["cast"] and spec["extras_plan"] = {setting: [{"k", "role"}]}"""
    texts = _texts_by_setting(spec)
    used_all = {sh.get("setting") for sc in spec.get("scenes", []) for sh in sc.get("shots", [])}
    used = {(s or "").split("__")[0] for s in used_all if s} | set(used_all)
    plan_, cast_add = {}, []
    for sid in sorted(s for s in used if s and "__" not in s):
        k = _kind(spec.get("settings", {}).get(sid), None)
        if not k:
            continue
        typ, style, time, st = k
        over = st.get("extras", "auto")
        if over in ("none", 0, False):
            continue
        rules = RULES.get((typ, style)) or RULES.get((typ, None))
        if style in PRIVATE or not rules:
            rules = None
        text = " ".join(texts.get(sid, []))
        mult = 1.0
        if ALONE.search(text):
            mult = 0.0
        elif BUSY.search(text):
            mult = 1.6
        if isinstance(over, (int, float)) and not isinstance(over, bool):
            mult *= float(over)
        roles = []
        if isinstance(over, list):
            roles = [(r.get("role", "walk"), int(r.get("n", 1))) for r in over if isinstance(r, dict)]
        elif rules:
            roles = [(r, max(0, round(n * mult))) for r, n in rules.get(time, rules.get("dusk", []))]
        rnd = random.Random(f"extras-{sid}")
        avoid = [c.get("top_color") for c in spec.get("cast", []) if c.get("top_color") and not c.get("extra")]
        items = []
        for role, n in roles:
            for j in range(n):
                if role == "traffic":
                    items.append({"role": "traffic", "k": None, "color": rnd.choice(["#d8473d", "#3e7cb1", "#e3b341", "#e9e4d8", "#2f3646", "#3aa65a"])})
                    continue
                cid = f"x_{sid}_{len(items) + 1}"
                c = _outfit(rnd, "office" if style == "office" else ("beach" if typ == "beach" else "default"), j, avoid)
                c.update(id=cid, name=f"extra {len(items) + 1}", extra=True, look="background extra", blush=False)
                cast_add.append(c); items.append({"role": role, "k": cid})
        if items:
            plan_[sid] = items
    for sid in used_all:
        if sid and "__" in sid and sid.split("__")[0] in plan_:
            plan_[sid] = plan_[sid.split("__")[0]]
    spec.setdefault("cast", []).extend(cast_add)
    spec["extras_plan"] = plan_
    return spec


# ------------------------------------------------------------------------------------------------ placement
def car_svg(color, back=False):
    """a small toon car seen from the front (headlights) or the back (tail lights), 200x130 box, bottom = road"""
    light = "#fff4c8" if not back else "#ff4a3a"
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 130' width='100%' height='100%'>"
            f"<ellipse cx='100' cy='124' rx='92' ry='7' fill='#000' opacity='.3'/>"
            f"<rect x='14' y='96' width='30' height='30' rx='6' fill='#15121b'/><rect x='156' y='96' width='30' height='30' rx='6' fill='#15121b'/>"
            f"<path d='M10 112 L12 70 Q14 58 28 56 L172 56 Q186 58 188 70 L190 112 Q190 118 182 118 L18 118 Q10 118 10 112 Z' fill='{color}'/>"
            f"<path d='M38 56 L52 20 Q55 12 64 12 L136 12 Q145 12 148 20 L162 56 Z' fill='{color}'/>"
            f"<path d='M50 54 L60 24 Q62 19 68 19 L132 19 Q138 19 140 24 L150 54 Z' fill='#9ed8ff' opacity='{.55 if back else .85}'/>"
            f"<rect x='20' y='72' width='30' height='14' rx='5' fill='{light}'/><rect x='150' y='72' width='30' height='14' rx='5' fill='{light}'/>"
            f"<rect x='72' y='92' width='56' height='14' rx='3' fill='#f3eee4'/><rect x='60' y='74' width='80' height='8' rx='3' fill='#15121b' opacity='.5'/></svg>")


def place(items, A, sh, W, H, dur, cast, main_chars, scale_at, ppm_at_y, find_all):
    """-> (extra chars, vehicles) for one shot"""
    if not items or not A or not sh.get("chars") and not sh.get("establish_ok", True):
        return [], []
    foc = sh.get("focus"); close = bool(foc) and float(foc.get("zoom", 1)) >= 2.2
    rnd = random.Random(f"{sh.get('setting')}-{round(dur, 2)}-{len(main_chars)}")
    taken_x = [c.get("x", 0) for c in main_chars]
    chars, cars = [], []
    seats = sorted([a for n in ("chair", "bench", "sofa") for a in A.get(n, []) if a.get("seat") and a.get("on_screen")],
                   key=lambda a: (a["seat"][0]))
    towels = [a for a in A.get("towel", []) if a.get("on_screen")]
    counters = [a for n in ("shop_counter", "kitchen_counter") for a in A.get(n, []) if a.get("on_screen")]
    shelves = [a for n in ("shelf_goods", "bookshelf") for a in A.get(n, []) if a.get("on_screen")]
    sea = A.get("_sea"); lanes = A.get("_lanes") or []; walks = A.get("_walks") or []
    si = ti = ci = bi = 0
    for it in items:
        role, k = it["role"], it.get("k")
        if role == "traffic":
            if close or not lanes:
                continue
            ln = lanes[len(cars) % len(lanes)]; (x0, y0, p0), (x1, y1, p1) = ln["from"], ln["to"]
            d = rnd.uniform(2.2, 3.6); t = rnd.uniform(0, max(0.1, dur - 1.0))
            w0 = 1.9 * p0
            cars.append(dict(x=x0, y=y0, w=w0, dx=x1 - x0, dy=y1 - y0, k=p1 / p0, d=d, t=t, color=it["color"], back=ln.get("away", False)))
            continue
        c = {"k": k, "acts": [], "extra": True}
        if role in ("sit_work", "sit_drink", "sit_listen"):
            # not at the hero's table (a stranger opposite reads as their date), and the far side of the room first:
            # the reference films balance the hero with background people on the OTHER third of the frame
            mains_ = [m for m in main_chars if not m.get("extra")]
            free = [a for a in seats if all(abs(a["seat"][0] - x) > 0.7 * a.get("seat_ppm", 100) for x in taken_x)
                    and all(abs(a["seat"][0] - m.get("x", 0)) > 1.7 * a.get("seat_ppm", 100) or abs(a["seat"][1] - (m.get("by", 0) - 300 * m.get("s", .8))) > 1.2 * a.get("seat_ppm", 100) for m in mains_)]
            if mains_:
                hx_ = sum(m.get("x", W / 2) for m in mains_) / len(mains_)
                free.sort(key=lambda a: -abs(a["seat"][0] - hx_))
            if si >= len(free):
                continue
            a = free[si]; si += 1; s = scale_at(a.get("seat_ppm") or a["floor_ppm"])
            c.update(anchor={"pose": "sit", "to": "_seat", "seat": a["seat"], "face": "b" if a.get("face_back") else a.get("face", 1), "floor": a["floor"], "s": s, "backrest": a.get("backrest"), "back_near": a.get("back_near"), "back_col": a.get("back_col")})
            c["acts"] = [[rnd.uniform(0.2, 1.2), {"sit_work": "type", "sit_drink": "drink", "sit_listen": "look"}[role], round(max(1.5, dur - 1), 2)]]
            if role == "sit_drink": c["item"] = "cup"
            taken_x.append(a["seat"][0])
        elif role == "behind":
            if ci >= len(counters):
                continue
            a = counters[ci]; ci += 1; pt = a.get("top") or a.get("front"); ppm = a["floor_ppm"]
            c.update(x=pt[0] + rnd.uniform(-0.3, 0.3) * ppm, by=a["floor"][1] - 0.45 * ppm, s=scale_at(ppm * 0.92), clip_y=pt[1] + 0.03 * ppm)
            c["acts"] = [[rnd.uniform(0.3, 1.5), rnd.choice(["look", "nod", "type"])]]
        elif role == "browse":
            if bi >= len(shelves):
                continue
            a = shelves[bi]; bi += 1; ppm = a["floor_ppm"]
            c.update(x=a["floor"][0] + rnd.uniform(-0.4, 0.4) * ppm, by=a["floor"][1] + 0.45 * ppm, s=scale_at(ppm), back=True)
            c["acts"] = [[rnd.uniform(0.5, 1.5), "reach", "r"]]
        elif role == "sunbathe":
            if ti >= len(towels):
                continue
            towels = [t_ for t_ in towels if all(abs(t_["top"][0] - x) > 0.6 * t_.get("top_ppm", 100) for x in taken_x)]
            if ti >= len(towels):
                continue
            a = towels[ti]; ti += 1; taken_x.append(a["top"][0])
            c.update(anchor={"pose": "lie", "to": "_towel", "head": a["head"], "foot": a["foot"], "ppm": a.get("top_ppm") or a["floor_ppm"], "awake": False})
        elif role == "swim":
            if not sea or close:
                continue
            y = rnd.uniform(sea["y0"], sea["y1"]); pp = ppm_at_y(A, y) or sea["ppm"]
            c.update(x=rnd.uniform(0.08, 0.92) * W, by=y + 1.0 * pp, s=scale_at(pp), clip_y=y)
            c["acts"] = [[rnd.uniform(0.3, 2.0), rnd.choice(["wave", "look", "happy"])]]
        elif role in ("walk", "walk_street", "cross"):
            if close:
                continue
            if role == "walk_street" and walks:      # along the pavement, toward or away from the camera
                wv = walks[rnd.randrange(len(walks))]; (x0, y0, p0), (x1, y1, p1) = wv["from"], wv["to"]
                if rnd.random() < 0.5: (x0, y0, p0), (x1, y1, p1) = (x1, y1, p1), (x0, y0, p0)
                f0 = rnd.uniform(0, 0.5); xa, ya, pa = x0 + (x1 - x0) * f0, y0 + (y1 - y0) * f0, p0 + (p1 - p0) * f0
                frac = min(1, 1.3 * dur / max(1, wv["len_m"]))
                xb, yb, pb = xa + (x1 - x0) * frac, ya + (y1 - y0) * frac, pa + (p1 - p0) * frac
                # never walk down the pavement IN FRONT of the hero (nearer the camera than their feet): cut the path there
                hero_by = min([m.get("by", H) for m in main_chars if m.get("by", H) < H] or [H * 1.5])
                lim = hero_by - 0.05 * H
                if ya > lim and yb > lim:
                    continue
                if max(ya, yb) > lim and abs(yb - ya) > 1:
                    u = (lim - ya) / (yb - ya)
                    xm, pm = xa + (xb - xa) * u, pa + (pb - pa) * u
                    if yb > lim: xb, yb, pb = xm, lim, pm
                    else: xa, ya, pa = xm, lim, pm
                c.update(x=xa, by=ya, s=scale_at(pa), path={"dx": xb - xa, "dy": yb - ya, "k": pb / pa, "d": dur, "view": "f" if pb > pa else "b"})
            else:                                     # across the frame on the floor / the crosswalk
                rows = A.get("_floor") or []
                hero_by = min([m.get("by", H) for m in main_chars if m.get("by", H) < H] or [H * 0.86])
                lo = max(H * 0.56, rows[0][0] + 0.02 * H if rows else 0, (sea["y1"] + 0.03 * H) if sea else 0)   # on the floor / the sand, never on a wall or in the sky
                y = rnd.uniform(lo, max(lo + 0.02 * H, hero_by - 0.06 * H)) if role != "cross" else (A.get("_cross") or H * 0.78)
                if role == "cross" and y > hero_by - 10:
                    continue
                pp = ppm_at_y(A, y) or 120; direction = rnd.choice([-1, 1]); dx = direction * 1.3 * pp * dur
                x0 = rnd.uniform(0.2, 0.8) * W - dx / 2
                c.update(x=x0, by=y, s=scale_at(pp), path={"dx": dx, "dy": 0, "k": 1, "d": dur, "view": "s", "dir": direction})
        elif role == "bench":
            free = [a for a in seats]
            if not free:
                continue
            a = free[0]; c.update(anchor={"pose": "sit", "to": "_seat", "seat": a["seat"], "face": "b" if a.get("face_back") else a.get("face", 1), "floor": a["floor"], "s": scale_at(a.get("seat_ppm") or a["floor_ppm"]), "backrest": a.get("backrest"), "back_near": a.get("back_near"), "back_col": a.get("back_col")})
        else:
            continue
        chars.append(c)
    return _balance(chars, main_chars, W, H), cars


def _balance(chars, main_chars, W, H):
    """Background people support the hero, they never crowd them (frame study of the reference channels):
    - nobody stands at the hero's depth right beside them (that reads as a companion, or hides the hero);
    - a frame holds only a few: 3 in 9:16, 5 in 16:9 - the ones furthest from the hero stay, they fill the empty third."""
    mains = [m for m in main_chars if not m.get("extra")]
    if not mains:
        return chars
    def crowding(c):
        x, by = c.get("x", 0), c.get("by", 0)
        return min(abs(x - m.get("x", 0)) / W + 2.5 * abs(by - m.get("by", 0)) / H for m in mains)
    keep = [c for c in chars if c.get("path") or c.get("anchor") or crowding(c) > 0.09]
    cap = 3 if H > W else 5
    if len(keep) > cap:
        keep = sorted(keep, key=crowding, reverse=True)[:cap]
    return keep
