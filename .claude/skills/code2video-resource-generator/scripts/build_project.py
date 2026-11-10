"""Build the Code2Video project files (docs hyperframes-asset-contract) from spec.json + a timing JSON derived from script.srt.
python build_project.py <spec.json> <out_dir> [--no-audio-tag] [--no-captions]
Writes ONLY: index.html, compositions/scene_N.html, assets/* (script.srt is written by generate.py). No timeline.json / hyperframes.json / package.json: the app adds them.
Re-run it after the app replaces timeline.json with real TTS timings (cue count/order must be unchanged).
"""
import json, html, pathlib, shutil, sys, argparse
HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))
import characters as CH
import lipsync as LS

CAMS = {  # preset -> [scale0, x0, y0, scale1, x1, y1]
    "push": [1.04, 0, 0, 1.14, -30, -10], "push_slow": [1.02, 0, 0, 1.10, 0, -8], "pull": [1.16, 0, -10, 1.04, 0, 0],
    "pan_left": [1.08, 60, 0, 1.08, -60, 0], "pan_right": [1.08, -60, 0, 1.08, 60, 0], "punch": [1.10, 100, 0, 1.28, 220, -30],
    "static_drift": [1.06, 0, 0, 1.08, 10, 0],
}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("out")
    ap.add_argument("--no-audio-tag", action="store_true"); ap.add_argument("--no-captions", action="store_true")
    ap.add_argument("--bg-dir", help="dir with bg_<setting>.png (default: <out>/assets)"); ap.add_argument("--timeline", required=True, help="timing JSON derived from script.srt")
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8")); out = pathlib.Path(a.out)
    TL = json.load(open(a.timeline, encoding="utf-8"))
    cast = {c["id"]: c for c in spec["cast"]}
    W, H = (1080, 1920) if spec.get("aspect", "16:9") == "9:16" else (1920, 1080)
    assets = out / "assets"; (assets / "fonts").mkdir(parents=True, exist_ok=True); (assets / "vendor").mkdir(exist_ok=True)
    (out / "compositions").mkdir(exist_ok=True)
    shutil.copy(SKILL / "assets/vendor/gsap.min.js", assets / "vendor/gsap.min.js")
    shutil.copy(SKILL / "assets/fonts/BeVietnamPro-Bold.ttf", assets / "fonts/BeVietnamPro-Bold.ttf")
    CH.write_all(spec["cast"], out)
    RIGS = json.load(open(assets / "character-rigs.json", encoding="utf-8"))
    for sc in spec["scenes"]:
        for sh in sc["shots"]:
          for setting in ([pn["setting"] for pn in sh["split"]] if sh.get("split") else [sh["setting"]]):
            bg = pathlib.Path(a.bg_dir or assets) / f"bg_{setting}.png"
            if not bg.exists(): sys.exit(f"missing background {bg} (render settings first)")
            if bg.parent != assets:
                shutil.copy(bg, assets / bg.name)
                for suf in ("_far", "_mid", "_near"):
                    lp = bg.parent / f"bg_{setting}{suf}.png"
                    if lp.exists(): shutil.copy(lp, assets / lp.name)
          if True:
            for p in sh.get("props", []):
                # the words writers use for the objects we draw (a missing alias used to stop the build)
                p["id"] = {"money": "cash", "cup": "coffee", "mug": "coffee", "tea": "coffee", "keys": "key", "letter": "envelope", "mail": "envelope",
                           "ticket": "card", "id": "card", "bill": "receipt", "notes": "document", "report": "document", "paper": "document",
                           "smartphone": "phone", "mobile": "phone", "computer": "laptop", "present": "gift", "bag": "shopping_bag",
                           "purse": "wallet", "watch": "clock", "alarm": "clock", "picture": "photo"}.get(p["id"], p["id"])
                src = SKILL / "assets/props" / f"{p['id']}.svg"
                if src.exists(): (assets / "props").mkdir(exist_ok=True); shutil.copy(src, assets / "props" / src.name)
                elif not (assets / "props" / f"{p['id']}.svg").exists(): sys.exit(f"unknown prop {p['id']}")
    cues = {c["index"]: c for c in TL["cues"]}
    sc_by = {s["sceneIndex"]: s for s in TL["scenes"]}
    n_cues = sum(len(sh.get("cues", [])) for sc in spec["scenes"] for sh in sc["shots"])
    cue_who = {}; _i = 1
    for sc in spec["scenes"]:
        for sh in sc["shots"]:
            for cu in sh.get("cues", []):
                if isinstance(cu, dict) and cu.get("who"): cue_who[_i] = cu["who"]
                _i += 1
    env = LS.load_env(out / "assets" / "audio" / "voiceover.wav")   # real loudness when the app's voiceover.wav is present
    if n_cues != len(TL["cues"]): sys.exit(f"spec has {n_cues} cues but timeline.json has {len(TL['cues'])}")
    engine = (HERE / "engine.js").read_text(encoding="utf-8")
    sec = lambda ms: f"{ms/1000:.3f}"
    GS = "assets/vendor/gsap.min.js"
    next_cue = 1; root_hosts = []

    import anchors as AN, characters_stick as CS, catalog as CAT
    _anch = {}
    def anchors_of(sid):
        if sid not in _anch:
            f = assets / f"anchors_{sid}.json"
            _anch[sid] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        return _anch[sid]

    import extras as EX

    def held_item(svg, item):
        """draw a phone / cup INSIDE the right hand of every view, so it rises with the arm (to the ear, to the mouth)."""
        import re as _re

        def put(m):     # groups: 1 forearm..hand, 2 hand circle, 3 cx, 4 cy
            x, y = float(m.group(3)), float(m.group(4)) + 9
            if item == "phone":     # big enough to read at wide-shot scale
                g = (f'<rect x="{x - 17:.0f}" y="{y - 52:.0f}" width="34" height="60" rx="7" fill="#2b2f3a" stroke="#15121b" stroke-width="4"/>'
                     f'<rect x="{x - 11:.0f}" y="{y - 45:.0f}" width="22" height="42" rx="3" fill="#8fd3ff"/>')
            else:
                g = (f'<path d="M{x - 21:.0f} {y - 50:.0f} L{x + 21:.0f} {y - 50:.0f} L{x + 16:.0f} {y + 6:.0f} L{x - 16:.0f} {y + 6:.0f} Z" fill="#f4efe0" stroke="#15121b" stroke-width="4"/>'
                     f'<rect x="{x - 19:.0f}" y="{y - 34:.0f}" width="38" height="14" fill="#b0623d"/>'
                     f'<path d="M{x + 19:.0f} {y - 40:.0f} q17 3 14 17 q-3 11 -16 9" fill="none" stroke="#15121b" stroke-width="5"/>')
            return m.group(1)[:-len(m.group(2))] + g + m.group(2)
        return _re.sub(r'(<g id="[^"]*-forearm-r">(?:(?!</g>).)*?(<circle cx="([-\d.]+)" cy="([-\d.]+)" r="1[12]" fill="[^"]+"/>))',
                       put, svg, flags=_re.S)

    def back_sit(seat_y, floor_y, sc_, hip, knee, k_=0.12):
        """seated, seen from behind (engine sit dir "b"): feet on the floor under the seat, hips on the seat, the shins
        stretched to reach (a stick figure's legs are shorter than a chair is high); thighs point away, scaled by k_."""
        u_seat = 782 - (floor_y - seat_y) / sc_
        # the chair is part of the background and cannot cover the person: cut the figure at the seat instead, so the
        # chair's legs show below the body as they would under someone sitting in it
        return dict(by=round(floor_y, 1), seatDrop=round(u_seat - hip, 1), clip_y=round(seat_y + 22 * sc_, 1),
                    shinK=round(max(0.6, (760 - (u_seat + k_ * (knee - hip))) / max(1, 760 - knee)), 3))

    def add_extras(sh, A, dur):
        """the colleagues, customers, passers-by, swimmers and cars of this place (extras.py)"""
        items = (spec.get("extras_plan") or {}).get(sh.get("setting"))
        if not items or sh.get("split") or any(p_.get("mode") == "static" for p_ in sh.get("props", [])):
            return sh
        ex, cars = EX.place(items, A, sh, W, H, dur, cast, sh.get("chars", []), AN.scale_at, AN.ppm_at_y, None)
        out_chars = []
        for c in ex:
            cc = cast.get(c["k"], {}); an = c.pop("anchor", None)
            if an and an["pose"] == "sit":
                hip, knee = CS.leg_geo(cc); s_ = an["s"]
                c.update(x=round(an["seat"][0], 1), by=round(an["seat"][1] - knee * s_ + 782 * s_, 1), s=s_, hold="sit", holdDir=an["face"])
                if an["face"] == "b" and an.get("floor"):
                    c.update(back_sit(an["seat"][1], an["floor"][1], s_, hip, knee))
                if an.get("back_near") and an.get("backrest"):
                    c["occl"] = {"pts": an["backrest"], "col": an.get("back_col", "#3e5c8a")}
            elif an and an["pose"] == "lie":
                (hx, hy), (fx, fy) = an["head"], an["foot"]; s_ = min(AN.scale_at(an["ppm"]), abs(fx - hx) * 0.95 / 706 + 0.02)
                c.update(x=round(fx, 1), by=round((hy + fy) / 2 + 40 * s_, 1), s=round(s_, 3), flip=hx > fx, hold="lie", awake=False)
            out_chars.append(c)
        sh = dict(sh); sh["chars"] = out_chars + list(sh.get("chars", [])); sh["vehicles"] = cars
        return sh

    def _rim_col(sid):
        st = spec.get("settings", {}).get((sid or "").split("__")[0])
        tm = (st.get("set") or {}).get("time") if isinstance(st, dict) and isinstance(st.get("set"), dict) else None
        return {"night": "rgba(150,195,255,.92)", "day": "rgba(255,240,215,.9)"}.get(tm, "rgba(255,214,160,.9)")

    def declutter(sh):
        """LOGIC rule, every shot: a main character is never hidden by anyone.
        - two main characters whose bodies overlap on screen: the one who is free to move (standing, not seated/lying,
          not the camera's focus) steps aside into the emptier side of the frame, same depth;
        - a background person who overlaps a main character (in front: hides them; behind: a second head sticks out
          of theirs) leaves the shot.
        - in a close shot the other main character never stands in front of the focus person's body."""
        chars = [dict(c) for c in sh.get("chars", [])]
        if len(chars) < 2:
            return sh
        def rect(c):
            s_ = c.get("s", .8); x_, by_ = c.get("x", W / 2), c.get("by", H * .84)
            if c.get("hold") == "lie": return (x_ - 380 * s_, by_ - 260 * s_, x_ + 380 * s_, by_)
            pdx = (c.get("path") or {}).get("dx", 0) or 0     # a walker sweeps the whole path, not just the first mark
            return (min(x_, x_ + pdx) - 105 * s_, by_ - 790 * s_, max(x_, x_ + pdx) + 105 * s_, by_)
        def ov(a, b):
            ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
            area = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])) or 1
            return ix * iy / area
        mains = [c for c in chars if not c.get("extra") and c.get("by", 0) < H * 1.02]
        fk = (sh.get("focus") or {}).get("k")
        def space(c): return 165 * c.get("s", .8)      # half of a person's talking distance (heads never touch)
        # a walk that would end ON someone stops beside them instead
        for c in mains:
            for a_ in c.get("acts", []):
                if a_[1] == "walkTo" and isinstance(a_[2], (int, float)):
                    end = c.get("x", 0) + a_[2]
                    for o in mains:
                        if o is c or abs(o.get("by", 0) - c.get("by", 0)) > H * .08: continue
                        if abs(end - o.get("x", 0)) < space(c) + space(o):
                            end = o.get("x", 0) + (1 if c.get("x", 0) > o.get("x", 0) else -1) * (space(c) + space(o))
                    a_[2] = round(end - c.get("x", 0), 1)
        def clash(a, b):
            if ov(rect(a), rect(b)) >= 0.08: return True
            return abs(a.get("by", 0) - b.get("by", 0)) < H * .06 and abs(a.get("x", 0) - b.get("x", 0)) < 0.9 * (space(a) + space(b))                 and not any(x_[1] == "walkTo" for x_ in a.get("acts", []) + b.get("acts", []))
        for i, a in enumerate(mains):
            for b in mains[i + 1:]:
                if not clash(a, b):
                    continue
                free = [c for c in (a, b) if not c.get("hold") and not c.get("path") and c["k"] != fk]
                if not free:
                    continue
                m = max(free, key=lambda c: c.get("by", 0)); o = b if m is a else a      # the nearer one moves
                need = space(m) + space(o)
                side = 1 if (m.get("x", 0) >= o.get("x", 0)) else -1
                nx = o.get("x", 0) + side * need
                if not (W * .07 < nx < W * .93): nx = o.get("x", 0) - side * need
                m["x"] = round(max(W * .07, min(W * .93, nx)), 1)
                if m.get("face") or m.get("flip") is not None:
                    m["face"] = 1 if o.get("x", 0) > m["x"] else -1 if m.get("face") else m.get("face")
        keep = []
        for c in chars:
            if c.get("extra") and any(ov(rect(c), rect(m)) > 0.12 for m in mains):
                continue
            keep.append(c)
        sh = dict(sh); sh["chars"] = keep
        return sh

    state = {"use": None}

    def resolve(sh, dur=4.0):
        """put characters and props ON the furniture the line talks about (anchors.py)."""
        A = anchors_of(sh.get("setting"))
        if not A:
            return sh
        sh = dict(sh); chars = []
        for ch in sh.get("chars", []):
            ch = dict(ch); an = ch.get("anchor"); cc = cast.get(ch["k"], {})
            if an:
                a = AN.find(A, an["to"], ch.get("x"))
                if an["pose"] == "sit" and an["to"] in ("chair", "seat") and any(a_[1] in ("type", "text", "drink") for a_ in ch.get("acts", [])):
                    # working or drinking: the chair at a desk/table, not a loose one in the middle of the room
                    works = [w for n_ in ("desk", "table") for w in A.get(n_, []) if w.get("on_screen")]
                    chairs = [c_ for c_ in A.get("chair", []) if c_.get("on_screen") and c_.get("seat")]
                    if works and chairs:
                        a = min(chairs, key=lambda c_: min(abs(c_["seat"][0] - (w.get("top") or w["floor"])[0]) / max(1, c_.get("seat_ppm") or c_["floor_ppm"])
                                                            + abs(c_["floor"][1] - w["floor"][1]) / max(1, c_["floor_ppm"]) for w in works))
                if a and an["pose"] == "lie" and "head" in a:
                    hx, hy = a["head"]; fx, fy = a["foot"]; ppm = a.get("top_ppm") or a["floor_ppm"]
                    sc_ = min(AN.scale_at(ppm), abs(fx - hx) * 0.95 / 706)
                    ch.update(x=round(fx - 0 * sc_, 1), by=round((hy + fy) / 2 + 40 * sc_, 1), s=round(sc_, 3), flip=hx > fx, hold="lie", awake=an.get("awake", True))
                    if a.get("n") in ("bed",):     # in bed: under the cover, chest to feet (the bed's own cover colour)
                        ch["blanket"] = a.get("c") or "#5b6f9a"
                    ch["acts"] = [a_ for a_ in ch.get("acts", []) if a_[1] in ("emote", "look", "talk", "phone", "surprise", "blink", "worry", "relief", "think")]
                elif a and an["pose"] == "use" and "behind" in a:
                    # an object used from behind (catalog stand="behind": podium, lectern): the person stands behind it,
                    # faces the room, and the object hides the legs (clip at its top edge)
                    ppm = a.get("behind_ppm") or a["floor_ppm"]
                    ch.update(x=round(a["behind"][0], 1), by=round(a["behind"][1], 1), s=AN.scale_at(ppm), flip=False,
                              clip_y=round(a["top"][1] + 0.02 * ppm, 1))
                    ch.pop("face", None)
                    keep = [a_ for a_ in ch.get("acts", []) if a_[1] in ("emote", "talk", "worry", "think", "surprise", "relief", "sad", "happy")]
                    act = an.get("act", "point"); act = "gesture" if act in ("stir", "reach", "type") else act
                    if act == "look":
                        keep.append([0.2, "look", 1, 0])
                    elif act == "gesture":
                        keep.append([0.3, "gesture", max(1.0, dur - 0.6)])
                    else:
                        k_ = 0
                        while 0.3 + k_ * 2.2 < dur - 0.4:      # point at the slides, talk to the room, point again
                            t_ = round(0.3 + k_ * 2.2, 2)
                            keep.append([t_, "gesture", 1.4] if k_ % 2 else [t_, act]); k_ += 1
                    ch["acts"] = keep
                elif a and an["pose"] == "use" and "approach" in a:
                    # standing at the object's front, a little to the side so the object stays visible, turned to it,
                    # the hands doing the job for the whole shot (any catalog object: oven, washer, shelf, podium, sink...)
                    ppm = a.get("approach_ppm") or a["floor_ppm"]; ox = a["floor"][0]
                    wob = CAT.C.get(a.get("n"), {}).get("w", .8)
                    side = -1 if ox > W / 2 else 1
                    sx_ = a["approach"][0] + side * (wob / 2 * 0.7 + 0.2) * ppm
                    ch.update(x=round(sx_, 1), by=round(a["approach"][1], 1), s=AN.scale_at(ppm), face=-side, flip=False)
                    keep = [a_ for a_ in ch.get("acts", []) if a_[1] in ("emote", "talk", "worry", "think", "surprise", "relief", "sad", "happy")]
                    act = an.get("act", "reach")
                    # a NEW object this shot (the previous shot of the scene was elsewhere): walk in from the side, then act
                    t_go = 0.3
                    key_ = (an.get("to"), round(a["floor"][0]))
                    if state["use"] != key_ and dur >= 3.2 and ch.get("enter") is None:
                        ch["enter"] = int(side * 300); t_go = max(1.8, 300 / 230) + 0.15
                    state["use"] = key_
                    if act == "look":
                        keep.append([t_go - 0.1, "look", -side, 0])
                    elif act in ("stir", "reach", "point", "type"):
                        k_ = 0
                        while t_go + k_ * 1.5 < dur - 0.4:
                            keep.append([round(t_go + k_ * 1.5, 2), act]); k_ += 1
                    ch["acts"] = keep
                elif a and an["pose"] == "stand":   # standing beside it (arrived there on an earlier line)
                    ppm = a["floor_ppm"]; side = 1 if a["floor"][0] >= ch.get("x", 960) else -1
                    ch.update(x=round(a["floor"][0] - side * 0.55 * ppm, 1), by=round(a["floor"][1] + 0.35 * ppm, 1), s=AN.scale_at(ppm))
                    ch["acts"] = [a_ for a_ in ch.get("acts", []) if not (a_[1] == "walkTo" and isinstance(a_[2], str))]
                elif a and an["pose"] == "sit" and "seat" in a:
                    sx_, sy_ = a["seat"]; sc_ = AN.scale_at(a.get("seat_ppm") or a["floor_ppm"])
                    hip, knee = CS.leg_geo(cc)
                    face_ = "b" if a.get("face_back") else a.get("face", 1)
                    for wk in ("desk", "table"):      # seated at a desk/table: face it (the screen, the laptop, the cup), never sit with the back to it
                        d_ = AN.find(A, wk, sx_)
                        if d_ and abs((d_.get("top") or d_["floor"])[0] - sx_) < 1.6 * (a.get("seat_ppm") or a["floor_ppm"]):
                            dx_ = (d_.get("top") or d_["floor"])[0] - sx_
                            if abs(dx_) > 4: face_ = 1 if dx_ > 0 else -1
                            # desk straight behind the chair (back-wall desk): seen from behind, not in profile
                            if abs(dx_) < 0.6 * (a.get("seat_ppm") or a["floor_ppm"]) and d_["floor"][1] < a["floor"][1] - 4: face_ = "b"
                            break
                    ch.update(x=round(sx_, 1), by=round(sy_ - knee * sc_ + 782 * sc_, 1), s=sc_, hold="sit", holdDir=face_, flip=False)
                    if face_ == "b" and (sh.get("focus") or {}).get("k") == ch["k"]:
                        # a close-up on them: the reverse angle, in profile (a close-up on the back of a head says nothing)
                        face_ = 1 if sx_ < W / 2 else -1
                        ch["holdDir"] = face_
                    if face_ == "b":
                        ch.update(back_sit(sy_, a["floor"][1], sc_, hip, knee))
                    if a.get("back_near") and a.get("backrest"):
                        ch["occl"] = {"pts": a["backrest"], "col": a["back_col"]}
                    ch["acts"] = [a_ for a_ in ch.get("acts", []) if a_[1] not in ("sit", "walkTo", "run", "walk", "jump", "crouch", "bend", "pickup")]
            if not an and A.get("_pave") and not ch.get("extra") and ch.get("by", 900) < H * 0.97:
                by_ = ch.get("by", 900)
                # only pavement that is ON screen (in 9:16 the pavement at the hero's depth can lie outside the frame:
                # then the hero walks back along it to where it is visible, instead of being snapped out of the picture)
                rows = [r for r in A["_pave"] if W * 0.1 < r[1] + (40 if r[2] < 0 else -40) < W * 0.9 and r[0] < H * 0.95]
                if rows:
                    best = min(rows, key=lambda r: 3 * abs(r[0] - by_) / H + abs(r[1] - ch.get("x", W / 2)) / W)
                    ch["x"] = round(best[1] + (40 if best[2] < 0 else -40), 1); ch["by"] = round(best[0], 1)
            if not an:   # standing on the floor: the set decides the size (feet lower on screen = nearer = bigger)
                pp = AN.ppm_at_y(A, ch.get("by", 900))
                if pp and ch.get("by", 900) < H * 0.97:
                    ch["s"] = AN.scale_at(pp)
            acts = []
            for a_ in ch.get("acts", []):
                if a_[1] == "walkTo" and isinstance(a_[2], str) and a_[2].startswith("@"):
                    a = AN.find(A, a_[2][1:], ch.get("x"))
                    if not a:
                        continue
                    ppm = a["floor_ppm"]; side = 1 if a["floor"][0] >= ch.get("x", 960) else -1
                    if not an:   # walk on the floor line of the target, at its depth and scale
                        ch["s"] = AN.scale_at(ppm); ch["by"] = round(a["floor"][1] + 0.35 * ppm, 1)
                    dest = a["floor"][0] - side * 0.55 * ppm
                    a_ = [a_[0], "walkTo", int(dest - ch.get("x", 960)), a_[3] if len(a_) > 3 else None]
                    ch["_end_x"] = dest
                acts.append(a_)
            ch["acts"] = acts
            chars.append(ch)
        sh["chars"] = chars
        props = []
        for pr in sh.get("props", []):
            pr = dict(pr)
            if pr.get("at"):
                hc0 = next((c for c in chars if c["k"] == pr.get("hand")), None)
                a = AN.find(A, pr["at"], hc0.get("_end_x", hc0["x"]) if hc0 else None)
                pt = a and (a.get("top") or a.get("seat") or a.get("front"))
                if pt:
                    ppm = a.get("top_ppm") or a.get("seat_ppm") or a["floor_ppm"]
                    w = max(28, int(ppm * {"phone": .2, "coffee": .2, "cup": .2, "document": .4, "book": .32, "keys": .14, "laptop": .45}.get(pr["id"], .3)))
                    pr.update(x=round(pt[0], 1), y=round(pt[1] - 0.3 * w, 1), w=w, sy=round(pt[1], 1))
                    hk = pr.get("hand"); hc = next((c for c in chars if c["k"] == hk), None)
                    if hc and pr.get("mode") in ("place", "take"):
                        hs = hc.get("s", 0.8); hx = hc.get("_end_x", hc["x"]) + (90 * hs if pt[0] >= hc.get("_end_x", hc["x"]) else -90 * hs)
                        hy = hc.get("by", 900) - 380 * hs
                        pr["fx"], pr["fy"] = round(hx - pr["x"], 1), round(hy - pr["y"], 1)
                else:
                    continue
            elif pr.get("hand"):   # an object in someone's hand follows that person after posing/scaling
                hc = next((c for c in chars if c["k"] == pr["hand"]), None)
                if hc:
                    hs = hc.get("s", 0.8); side = -1 if hc.get("flip") else 1
                    if hc.get("hold") == "sit": side = hc.get("holdDir", 1) if hc.get("holdDir") in (1, -1) else 1
                    drop = (CS.leg_geo(cast.get(hc["k"], {}))[1] - CS.leg_geo(cast.get(hc["k"], {}))[0]) if hc.get("hold") == "sit" else 0
                    w = int(hs * 400 * {"phone": .22, "coffee": .26, "cup": .26, "document": .42, "clock": .4, "book": .36, "keys": .16}.get(pr["id"], .3))
                    pr.update(x=round(hc["x"] + side * 105 * hs, 1), y=round(hc.get("by", 900) - (400 - drop) * hs, 1), w=max(24, w))
            props.append(pr)
        sh["props"] = props
        return add_extras(sh, A, dur)

    for sc in spec["scenes"]:
        n = sc["id"]; tsc = sc_by[n]; s0 = tsc["startMs"]; dur = tsc["sceneDurationMs"] / 1000; cid = f"scene-{n}"
        state["use"] = None
        shots_html, shots_data, caps_html, caps_data = [], [], [], []; prev = None; prev_ids = []; prev_full = (0, 1)
        for si, sh in enumerate(sc["shots"]):
            if sh.get("share"):      # reuse the previous shot's cues (cutaway/reaction inside the same line)
                cue_ids, (f0, f1) = prev_ids, prev_full
            else:
                cue_ids = list(range(next_cue, next_cue + len(sh["cues"]))); next_cue += len(sh["cues"])
                f0 = (cues[cue_ids[0]]["startMs"] - s0) / 1000; f1 = (cues[cue_ids[-1]]["endMs"] - s0) / 1000
                prev_ids, prev_full = cue_ids, (f0, f1)
            por = sh.get("portion", [0, 1]); t0 = f0 + (f1 - f0) * por[0]; t1 = f0 + (f1 - f0) * por[1]
            dom = f"s{n}{chr(65+si)}"; chars_html, chars_data = [], []
            sh = declutter(resolve(sh, t1 - t0))
            if sh.get("focus") and not sh.get("split"):      # close-ups: drop characters that end up outside the frame (fewer DOM nodes = faster render)
                _f = sh["focus"]; _z = min(_f.get("zoom", 2.4), _f.get("to", _f.get("zoom", 2.4) * 1.07)); _hx = next(x["x"] for x in sh["chars"] if x["k"] == _f["k"])
                sh = dict(sh, chars=[x for x in sh["chars"] if x["k"] == _f["k"] or x.get("enter") is not None or abs(_z * (x["x"] - _hx)) < W / 2 + _z * 200 * x.get("s", 0.8) + 60])
            pane_defs = ([dict(pn, idx=i) for i, pn in enumerate(sh["split"])] if sh.get("split") else [dict(idx=None, chars=sh["chars"])])
            pane_chars_html = {}; occ_list = []
            for pn in pane_defs:
              pane_chars_html[pn["idx"]] = []
              for ch in pn["chars"]:
                ccid = f"{dom}-{ch['k']}" if pn["idx"] is None else f"{dom}p{pn['idx']}-{ch['k']}"; s = ch.get("s", 0.8)
                w, h = 400 * s, 800 * s; left, top = ch["x"] - w / 2, ch.get("by", 900) - 782 * s
                flip = ("transform:scaleX(-1);" if ch.get("flip") else "") + ((f"filter:drop-shadow(-3px -2px 0 {_rim_col(sh.get('setting'))}) drop-shadow(0 0 5px rgba(255,190,130,.25));") if (ch.get("glow") or cast[ch["k"]].get("glow") or (spec.get("rim", True) and not ch.get("extra"))) else "")
                if not ch.get("extra") and (sh.get("focus") or {}).get("k") not in (None, ch["k"]) and float((sh.get("focus") or {}).get("zoom", 1) or 1) >= (1.6 if H > W else 2.2):
                    flip += "filter:blur(3px) brightness(.92);"   # the other person in a close-up is a soft foreground shape (reference framing)
                if ch.get("extra"):   # background people sit back; in a medium/close shot they fall out of focus (reference depth of field)
                    zf_ = float((sh.get("focus") or {}).get("zoom", 1) or 1)
                    flip += f"filter:saturate(.8) brightness(.96){' blur(%.1fpx)' % min(5, (zf_ - 1.3) * 4) if zf_ > 1.4 else ''};"
                acts_ = ch.get("acts", [])
                views_ = ["f"] + (["s"] if (ch.get("enter") is not None or ch.get("hold") == "sit" or ch.get("face") or (ch.get("path") or {}).get("view") == "s" or any(a_[1] in ("walkTo", "sit", "turn") or (a_[1] == "view" and a_[2] in ("side", "s")) for a_ in acts_)) else []) \
                                 + (["b"] if (ch.get("back") or ch.get("holdDir") == "b" or (ch.get("path") or {}).get("view") == "b" or any(a_[1] == "view" and a_[2] in ("back", "b") for a_ in acts_)) else [])
                ext_ = bool(cast[ch["k"]].get("external")) and (assets / f"{ch['k']}.svg").exists()
                svg = (f"<img id='{ccid}-ext' src='assets/{ch['k']}.svg' alt='' style='width:100%;height:100%;display:block'>" if ext_ else
                       CH.build_svg(ccid, cast[ch["k"]], tuple(views_)).replace("<svg xmlns", '<svg preserveAspectRatio="xMidYMax meet" xmlns', 1))
                if ch.get("item") and not ext_: svg = held_item(svg, ch["item"])
                # a label that floats over the head and follows the character (a stat, a level, a name, "100%"):
                # the reference films keep a number over every person for the whole story
                tag_ = ch.get("tag", cast[ch["k"]].get("tag"))
                tag_html = (f"<div class='ctag' style='position:absolute;left:50%;top:{4 - 2 * (cast[ch['k']].get('hat', 'none') != 'none')}%;transform:translate(-50%,-100%);"
                            f"background:rgba(24,20,32,.88);color:#ffd27a;font-weight:700;font-size:{max(18, 46 * s):.0f}px;line-height:1;padding:{6 * s + 3:.0f}px {14 * s + 6:.0f}px;"
                            f"border:2px solid #ffd27a;border-radius:999px;white-space:nowrap;font-variant-numeric:tabular-nums'>{html.escape(str(tag_))}</div>") if tag_ not in (None, "") else ""
                clip_ = ""
                if ch.get("clip_y") is not None:     # hidden below a counter top or the water line
                    cut = max(0.0, min(100.0, (top + h - ch["clip_y"]) / h * 100))
                    clip_ = f"clip-path:inset(0 0 {cut:.1f}% 0);"
                if ch.get("blanket") and ch.get("hold") == "lie":
                    # the bed is background and cannot cover the sleeper: a cover drawn over the body, chest to feet
                    bx0 = ch["x"] - 20 * s if ch.get("flip") else ch["x"] - 480 * s; bw = 500 * s; by0 = ch.get("by", 900) - 78 * s; bh = 130 * s
                    col = ch["blanket"]
                    pane_chars_html[pn["idx"]].append(
                        f"<svg class='blanket' style='position:absolute;left:{bx0:.1f}px;top:{by0:.1f}px;width:{bw:.1f}px;height:{bh:.1f}px;"
                        f"z-index:{int(ch.get('by', 900)) + 1 + (2000 if ch.get('by', 900) > H * 1.0 else 0)};overflow:visible' viewBox='0 0 100 26' preserveAspectRatio='none'>"
                        f"<path d='M2 9 Q20 3 40 7 T78 6 Q94 5 98 10 L99 24 Q50 27 1 24 Z' fill='{col}' stroke='#1e1a26' stroke-width='.8' vector-effect='non-scaling-stroke'/>"
                        f"<path d='M{'86' if not ch.get('flip') else '14'} 7 Q{'84' if not ch.get('flip') else '16'} 16 {'88' if not ch.get('flip') else '12'} 24' fill='none' stroke='rgba(0,0,0,.18)' stroke-width='1.2'/>"
                        f"<path d='M4 10 Q30 6 60 9 T96 11' fill='none' stroke='rgba(255,255,255,.28)' stroke-width='1.6'/></svg>")
                pane_chars_html[pn["idx"]].append(f"<div id='{ccid}-wrap' class='char' style='left:{left:.1f}px;top:{top:.1f}px;width:{w:.1f}px;height:{h:.1f}px;z-index:{int(ch.get('by', 900)) + (2000 if not ch.get('extra') and ch.get('by', 900) > H * 1.0 else 0)};{clip_}'><div class='flip' style='{flip}'>{svg}</div>{tag_html}</div>")
                if ch.get("occl"):   # LOGIC: the chair back is between the camera and the sitter, so it covers their back
                    # cut from the background picture itself (same pixels, light and outline as the chair; a drawn
                    # polygon never matched the render - owner, 2026-11-09); slightly grown so the ink edge comes too
                    pts0 = ch["occl"]["pts"]; mx_ = sum(q[0] for q in pts0) / 4; my_ = sum(q[1] for q in pts0) / 4
                    grow = [(mx_ + (q[0] - mx_) * 1.06 + (3 if q[0] > mx_ else -3), my_ + (q[1] - my_) * 1.04 + (3 if q[1] > my_ else -3)) for q in pts0]
                    occ_list.append(dict(poly=", ".join(f"{x_:.1f}px {y_:.1f}px" for x_, y_ in grow),
                                         z=int(ch.get('by', 900)) + (2000 if not ch.get('extra') and ch.get('by', 900) > H * 1.0 else 0) + 1))
                chars_data.append(dict(k=ch["k"], cid=ccid, acts=ch.get("acts", []), enter=ch.get("enter"), flip=bool(ch.get("flip")), ext=ext_,
                                       hold=ch.get("hold"), holdDir=ch.get("holdDir"), seatDrop=ch.get("seatDrop"), shinK=ch.get("shinK"), awake=ch.get("awake", True), face=ch.get("face"),
                                       path=ch.get("path"), back=ch.get("back"), extra=ch.get("extra")))
            chars_html = pane_chars_html[None] if None in pane_chars_html else []
            props_html, props_data = [], []
            for pi, p in enumerate(sh.get("props", [])):
                pid = f"{dom}-prop{pi}"; w = p.get("w", 170)
                FLAT = {"phone": 200 / 120, "document": 210 / 170, "book": 140 / 200, "wallet": 170 / 230, "card": 150 / 230}
                if p.get("sy") is not None and p["id"] in FLAT and p.get("mode") in ("place", "on"):
                    # put down on a surface it LIES on it: squashed flat, its bottom edge on the top of the counter / oven / table
                    # (standing upright it read as floating, or as still held in the hand - 2026-11-09 audit)
                    h_ = w * FLAT[p["id"]]
                    props_html.append(f"<img id='{pid}' class='prop' src='assets/props/{p['id']}.svg' style='left:{p['x']-w/2:.0f}px;top:{p['sy'] - h_ + 0.12 * h_ + 0.3 * w * FLAT[p['id']] * .3:.0f}px;width:{w}px;opacity:0;z-index:{int(p['sy']) + 30};transform-origin:50% 88%;scale:1 .3;filter:brightness(.9)'>")
                else:
                    props_html.append(f"<img id='{pid}' class='prop' src='assets/props/{p['id']}.svg' style='left:{p['x']-w/2:.0f}px;top:{p['y']-w*0.7:.0f}px;width:{w}px;opacity:0;z-index:5000'>")
                props_data.append(dict(dom=pid, mode=p.get("mode", "drop"), t=p.get("t", 0), lift=p.get("lift"), fx=p.get("fx"), fy=p.get("fy")))
            # crowd: seeded silhouettes in perspective rows
            veh_html, veh_data = [], []
            for vi, v in enumerate(sh.get("vehicles", []) or []):
                vid = f"{dom}-car{vi}"; vw = v["w"]; vh = vw * 0.65
                veh_html.append(f"<div id='{vid}' class='veh' style='position:absolute;left:{v['x'] - vw / 2:.1f}px;top:{v['y'] - vh:.1f}px;width:{vw:.1f}px;height:{vh:.1f}px;opacity:0;transform-origin:50% 100%;z-index:{int(v['y'] + v['dy'] * 0.6)}'>{EX.car_svg(v['color'], v.get('back'))}</div>")
                veh_data.append(dict(dom=vid, dx=round(v["dx"], 1), dy=round(v["dy"], 1), k=round(v["k"], 3), d=round(v["d"], 2), t=round(v["t"], 2), back=bool(v.get("back"))))
            crowd_html, crowd_data = [], []
            cr = sh.get("crowd")
            if cr:
                rs = [cr.get("seed", 7) * 9301 + 49297]
                def rnd():
                    rs[0] = (rs[0] * 9301 + 49297) % 233280; return rs[0] / 233280
                cols = cr.get("colors", ["#c0577a", "#e0b83a", "#3aa6a0", "#6a7ac8", "#d9884a", "#8a5ac8"])
                # `x` and `by` may be fractions of the frame (0-1, portable between 16:9 and 9:16)
                # or pixels in the real frame. Defaults are fractions so a crowd lands on the ground
                # in both aspects instead of floating in the sky of a portrait frame.
                def _span(v, size):
                    a_, b_ = v
                    return (a_ * size if a_ <= 1 else a_), (b_ * size if b_ <= 1 else b_)
                s0_, s1_ = cr.get("s", [0.18, 0.4])
                if H > W: s0_, s1_ = s0_ * 1.25, s1_ * 1.25    # portrait draws characters 1.25x: match them
                y0_, y1_ = _span(cr.get("by", [0.59, 0.83]), H); x0_, x1_ = _span(cr.get("x", [0.10, 0.90]), W)
                figs = sorted(((y0_ + (y1_ - y0_) * rnd(), rnd()) for _ in range(cr.get("n", 60))))
                for fi, (fy, rr) in enumerate(figs):
                    t_ = (fy - y0_) / max(1, (y1_ - y0_)); sc = s0_ + (s1_ - s0_) * t_; fx = x0_ + (x1_ - x0_) * rnd()
                    w_, h_ = 100 * sc * 1.6, 200 * sc * 1.6; fid = f"{dom}-cr{fi}"
                    crowd_html.append(f"<div id='{fid}' class='cfig' style='left:{fx - w_/2:.0f}px;top:{fy - h_:.0f}px;width:{w_:.0f}px;height:{h_:.0f}px;color:{cols[int(rnd()*len(cols))%len(cols)]}'><svg viewBox='0 0 100 200' width='100%' height='100%'><use href='#crowdfig'/></svg></div>")
                    crowd_data.append(dict(id=fid, a=round(rr, 3), d=round(rnd() * 0.5, 3)))
            # overlays (HUD language: chip / counter / burst / bubble / title)
            ov_html, ov_data = [], []
            POS = {"t": 5, "c": 40, "b": 70}; COL = {"l": "flex-start", "c": "center", "r": "flex-end"}
            if sh.get("trans") == "power":   # the reference films' power moment: white flash, action lines, a ring rippling out
                fc_ = next((c for c in sh.get("chars", []) if c["k"] == (sh.get("focus") or {}).get("k")), None) or next((c for c in sh.get("chars", []) if not c.get("extra")), None)
                cx_, cy_ = (fc_["x"], fc_.get("by", H * .8) - 640 * fc_.get("s", .8)) if fc_ else (W / 2, H / 2)
                sh = dict(sh, trans="cut", overlays=[{"type": "flash", "t": 0, "dur": 0.5}, {"type": "speedlines", "t": 0.02, "dur": 0.7},
                                                     {"type": "ripple", "t": 0.05, "dur": 1.3, "cx": round(cx_), "cy": round(cy_)}] + list(sh.get("overlays", [])))
            for oi, o in enumerate(sh.get("overlays", [])):
                oid = f"{dom}-ov{oi}"; ty = o["type"]; pos = o.get("pos", "tc")
                inner = ""; cls = f"ov {ty}"
                if ty == "chip": inner = html.escape(o["text"])
                elif ty == "counter": inner = f"<div class='num' id='{oid}-n'></div><div class='lbl'>{html.escape(o.get('label', ''))}</div>"
                elif ty == "burst": inner = html.escape(o["text"])
                elif ty == "word":   # the spoken keyword, big and hand-lettered, slammed over the picture (reference shorts)
                    col_ = o.get("color") or ["#e8402f", "#ffd23a", "#3fc46e", "#4fb3ff", "#ff7a3d"][oi % 5]
                    inner = f"<span style='color:{col_}'>{html.escape(str(o['text']).upper())}</span>"
                elif ty in ("bubble", "title"): inner = "".join(f"<span class='ch'>{html.escape(ch)}</span>" for ch in o["text"])
                elif ty == "chain":   # EYES -> BRAIN -> MUSCLES: a cause chain spelled out word by word
                    its = [html.escape(str(x)) for x in o.get("items", [])]
                    inner = "<span class='ch arrow'> &#8594; </span>".join(f"<span class='ch'>{x}</span>" for x in its)
                elif ty == "flash": inner = ""       # white frame: impact, a power switching on, a time jump
                elif ty == "graph":   # full-frame stat panel: "SUBJECT 11 - MAX  12.4x" with a rising line and labelled points
                    pts_ = [float(v) for v in o.get("points", [1, 2, 3])]; lo, hi = min(pts_), max(pts_); n_ = max(1, len(pts_) - 1)
                    gw, gh = (900, 420) if W > H else (820, 520)
                    xy = [(40 + i * (gw - 80) / n_, gh - 40 - (v - lo) / ((hi - lo) or 1) * (gh - 100)) for i, v in enumerate(pts_)]
                    col_ = {"up": "#ff6a6a", "down": "#3ccf9e"}.get(o.get("trend"), "#ffd27a")
                    inner = (f"<div class='g-h'><span>{html.escape(o.get('title', ''))}</span><b style='color:{col_}'>{html.escape(str(o.get('value', '')))} {'&#9650;' if o.get('trend') == 'up' else ('&#9660;' if o.get('trend') == 'down' else '')}</b></div>"
                             f"<div class='g-l'>{html.escape(o.get('label', ''))}</div><svg viewBox='0 0 {gw} {gh}' width='{gw}' height='{gh}'>"
                             f"<polyline points='{' '.join(f'{x:.0f},{y:.0f}' for x, y in xy)}' fill='none' stroke='{col_}' stroke-width='5' stroke-linecap='round' stroke-linejoin='round'/>"
                             + "".join(f"<text x='{x + 8:.0f}' y='{y - 12:.0f}' fill='#d9d2c0' font-size='26'>{html.escape(str(o.get('marks', pts_)[i]))}</text>" for i, (x, y) in enumerate(xy)) + "</svg>")
                elif ty == "clock":   # an analog clock that shows the time the line says
                    hh, mm = [int(x) for x in str(o.get("time", "6:00")).split(":")[:2]]
                    ah, am = (hh % 12 + mm / 60) * 30, mm * 6
                    inner = (f"<svg viewBox='0 0 300 300' width='{360 if W > H else 420}' height='{360 if W > H else 420}'><circle cx='150' cy='150' r='140' fill='#fbf8f1' stroke='#15121b' stroke-width='12'/>"
                             + "".join(f"<line x1='150' y1='22' x2='150' y2='{44 if k % 3 == 0 else 36}' stroke='#15121b' stroke-width='{9 if k % 3 == 0 else 5}' transform='rotate({k * 30} 150 150)'/>" for k in range(12))
                             + f"<line x1='150' y1='150' x2='150' y2='78' stroke='#15121b' stroke-width='12' stroke-linecap='round' transform='rotate({ah:.1f} 150 150)'/>"
                             f"<line x1='150' y1='150' x2='150' y2='46' stroke='#15121b' stroke-width='7' stroke-linecap='round' transform='rotate({am:.1f} 150 150)'/><circle cx='150' cy='150' r='10' fill='#e35d4f'/></svg>")
                elif ty == "ripple":                 # rings spreading from the person (a power switching on, a heartbeat, a realisation)
                    rx_, ry_ = o.get("cx", W / 2), o.get("cy", H / 2)
                    inner = (f"<svg viewBox='0 0 {W} {H}' width='{W}' height='{H}'>" + "".join(
                        f"<circle class='rp' cx='{rx_}' cy='{ry_}' r='{H * .32:.0f}' fill='none' stroke='#fffaf0' stroke-width='{6 - k * 1.5}' opacity='.9' style='transform-origin:{rx_}px {ry_}px'/>" for k in range(3)) + "</svg>")
                elif ty == "speedlines":             # comic action lines rushing to the centre: the moment the power fires
                    import math as _m
                    cxs, cys = W / 2, H / 2
                    ln = "".join(f"<line x1='{cxs + _m.cos(a_) * (W * .2 + (k % 3) * 40):.0f}' y1='{cys + _m.sin(a_) * (H * .2 + (k % 3) * 40):.0f}' "
                                 f"x2='{cxs + _m.cos(a_) * W:.0f}' y2='{cys + _m.sin(a_) * W:.0f}' stroke='#15121b' stroke-width='{4 + (k * 7) % 9}' stroke-linecap='round'/>"
                                 for k, a_ in enumerate([i * 2 * _m.pi / 56 + (i % 5) * .02 for i in range(56)]))
                    inner = f"<svg viewBox='0 0 {W} {H}' width='{W}' height='{H}'>{ln}</svg>"
                elif ty == "screen":
                    tr = o.get("trend")
                    pts = {"up": "0,90 60,82 120,86 180,70 240,74 300,40 360,8", "down": "0,10 60,22 120,16 180,44 240,40 300,70 360,92",
                           "flat": "0,50 60,48 120,52 180,49 240,51 300,50 360,49"}.get(tr, "")
                    colr = {"up": "#3ccf6e", "down": "#ff5a5a"}.get(tr, "#9aa3ad")
                    inner = (f"<div class='scr-h'><span class='dot'></span>{html.escape(o.get('app', ''))}</div>"
                             f"<div class='scr-l'>{html.escape(o.get('label', ''))}</div>"
                             f"<div class='scr-v' style='color:{colr if tr else '#f6f0e4'}'>{html.escape(str(o.get('value', '')))}</div>"
                             + (f"<svg class='scr-c' viewBox='0 0 360 100'><polyline points='{pts}' fill='none' stroke='{colr}' stroke-width='5' stroke-linecap='round' stroke-linejoin='round'/></svg>" if pts else ""))
                top_css = "160px" if (spec.get("letterbox") and pos[0] == "t") else "%s%%" % POS[pos[0]]
                if ty in ("flash", "speedlines", "ripple"):   # full frame
                    ov_html.append(f"<div id='{oid}' class='{cls}' style='opacity:0;position:absolute;left:0;top:0;width:{W}px;height:{H}px;pointer-events:none;"
                                   f"{'background:#fffaf0;' if ty == 'flash' else ''}'>{inner}</div>")
                elif "x" in o:   # absolute centre placement
                    ov_html.append(f"<div class='ovabs' style='left:{o['x']}px;top:{o['y']}px'><div id='{oid}' class='{cls}' style='opacity:0'>{inner}</div></div>")
                else:
                    ov_html.append(f"<div class='ovw' style='top:{top_css};justify-content:{COL[pos[1]]}'><div id='{oid}' class='{cls}' style='opacity:0'>{inner}</div></div>")
                extra = {"from": o.get("from", 0), "to": o.get("to", 0)} if ty == "counter" else {}
                ov_data.append(dict(id=oid, type=ty, t=o.get("t", 0), dur=o.get("dur", 3), abs=("x" in o), **extra))
            rain = "".join(f"<div class='rain' style='left:{(i*97)%{W+40}-20}px;height:{70+(i*13)%60}px;opacity:0'></div>" for i in range(70)) if sh.get("rain") else ""
            rays = "<div class='rays'></div>" if sh.get("rays") else ""
            GRADES = {"flashback": ("sepia(.5) saturate(.85) brightness(1.05) contrast(.94)", "radial-gradient(ellipse at 50% 45%, rgba(255,220,160,.10) 30%, rgba(70,38,12,.55) 100%)"),
                      "night": ("saturate(.78) brightness(.9) hue-rotate(-6deg)", "linear-gradient(rgba(30,50,130,.22), rgba(10,14,40,.35))"),
                      "tense": ("contrast(1.12) saturate(.8)", "radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 40%, rgba(0,0,0,.5) 100%)"),
                      "dream": ("saturate(1.1) brightness(1.08) blur(.6px)", "radial-gradient(ellipse at 50% 50%, rgba(255,255,255,.12) 30%, rgba(160,140,255,.3) 100%)")}
            grade = GRADES.get(sh.get("grade")); grade_css = f"filter:{grade[0]};" if grade else ""
            if grade: rays += f"<div style='position:absolute;inset:0;pointer-events:none;background:{grade[1]}'></div>"
            if sh.get("spot"):   # one cone of light on the person, darkness around (interrogation, a decision, a memory)
                mc = next((c for c in sh.get("chars", []) if not c.get("extra")), None)
                if mc:
                    sx_, sy_ = mc["x"], mc.get("by", 900) - 420 * mc.get("s", 0.8); r_ = 520 * mc.get("s", 0.8)
                    rays += (f"<div style='position:absolute;inset:0;pointer-events:none;background:radial-gradient(ellipse {r_:.0f}px {r_ * 1.25:.0f}px at {sx_:.0f}px {sy_:.0f}px,"
                             f" rgba(0,0,0,0) 0%, rgba(0,0,0,0) 55%, rgba(4,4,12,.78) 100%)'></div>"
                             f"<div style='position:absolute;left:{sx_ - r_ * .5:.0f}px;top:0;width:{r_:.0f}px;height:{sy_ + r_:.0f}px;pointer-events:none;"
                             f"background:linear-gradient(rgba(255,240,210,.18), rgba(255,240,210,0));clip-path:polygon(40% 0,60% 0,100% 100%,0 100%)'></div>")
            if sh.get("pov") and sh.get("props"):   # first-person insert: an arm from the corner holds the object
                pr0 = sh["props"][0]; hero = cast.get(sh["pov"]) or next((c for c in spec["cast"] if not c.get("narrator") and not c.get("extra")), {})
                sl = hero.get("top_color", "#3e7cb1"); px_, py_ = pr0["x"], pr0["y"] + pr0.get("w", 170) * 0.15
                ax, ay = W * 0.86, H * 1.12; aw = W * (0.06 if W > H else 0.1)   # forearm rising from the bottom edge, hand gripping the lower edge
                rays += (f"<svg style='position:absolute;left:0;top:0;z-index:4000;pointer-events:none' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>"
                         f"<path d='M{ax:.0f} {ay:.0f} L{px_ + aw * .4:.0f} {py_ + aw * .5:.0f}' stroke='#15121b' stroke-width='{aw + 8:.0f}' stroke-linecap='round'/>"
                         f"<path d='M{ax:.0f} {ay:.0f} L{px_ + aw * .4:.0f} {py_ + aw * .5:.0f}' stroke='{sl}' stroke-width='{aw:.0f}' stroke-linecap='round'/>"
                         f"</svg><svg style='position:absolute;left:0;top:0;z-index:6000;pointer-events:none' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>"
                         f"<ellipse cx='{px_ + aw * .1:.0f}' cy='{py_ + aw * .15:.0f}' rx='{aw * .42:.0f}' ry='{aw * .3:.0f}' fill='#15121b'/>"
                         f"<ellipse cx='{px_ - aw * .22:.0f}' cy='{py_ - aw * .02:.0f}' rx='{aw * .16:.0f}' ry='{aw * .1:.0f}' fill='#15121b' transform='rotate(-30 {px_ - aw * .22:.0f} {py_ - aw * .02:.0f})'/></svg>")
            cam = sh.get("cam", "push"); cam = CAMS[cam] if isinstance(cam, str) else cam
            foc = sh.get("focus")
            mains_ = [c for c in sh.get("chars", []) if not c.get("extra") and c.get("by", 0) < H * 1.02]
            if H > W and not foc and not sh.get("split") and mains_ and not isinstance(sh.get("cam"), list):
                # 9:16 wide: the tall frame was 40 % empty ceiling. Frame the people instead: a gentle zoom on the group,
                # their heads a little above the middle, the room still around them (reference shorts)
                lead = max(mains_, key=lambda c: c.get("s", .8))
                gx = sum(c["x"] for c in mains_) / len(mains_)
                foc = {"k": lead["k"], "zoom": 1.32, "to": 1.4, "dx": round(gx - lead["x"], 1), "target_y": int(H * 0.5)}
            if foc and not sh.get("split"):   # zoom on a character's head (medium close-up 1.8, close-up 2.6, extreme 3.6)
                chf = next(x for x in sh["chars"] if x["k"] == foc["k"]); sf = chf.get("s", 0.8)
                hx = chf["x"] + foc.get("dx", 0); hy = chf.get("by", 900) - 782 * sf + 176 * sf + foc.get("dy", 0)
                if chf.get("hold") == "lie":
                    hx = chf["x"] + (1 if chf.get("flip") else -1) * 600 * sf + foc.get("dx", 0); hy = chf.get("by", 900) - 40 * sf
                elif chf.get("hold") == "sit":
                    _hp, _kn = CS.leg_geo(cast.get(chf["k"], {})); hy += (_kn - _hp) * sf
                Z0 = foc.get("zoom", 2.4); Z1 = foc.get("to", round(Z0 * 1.07, 3))
                _zm = max(1.0, min(Z0, Z1)); hx = min(max(hx, W / (2 * _zm)), W - W / (2 * _zm))   # never pan past the picture's edge (black bar)
                tgt = foc.get("target_y", int(H * 0.44))
                kx = lambda Z: round(-Z * (hx - W / 2), 1); ky = lambda Z: round(tgt - 0.62 * H - Z * (hy - 0.62 * H), 1)
                cam = [Z0, kx(Z0), ky(Z0), Z1, kx(Z1), ky(Z1)]
            panes_data = None
            if sh.get("split"):
                parts = []; panes_data = []
                for pn in pane_defs:
                    i = pn["idx"]; pid = f"{dom}-pcam{i}"; panes_data.append(pid)
                    parts.append(f"<div class='pane' style='left:{i*960}px'><div id='{pid}' class='pcam'><img class='bgp' src='assets/bg_{pn['setting']}.png'>{''.join(pane_chars_html[i])}</div>"
                                 f"<div class='tint' style='background:{pn.get('tint', '#ffffff')}'></div></div>")
                sh = dict(sh, setting=sh["split"][0]["setting"], flat=True)
                scene_html = "".join(parts) + "<div class='pdiv'></div>" + "".join(crowd_html) + "".join(props_html)
            _ext = spec.get("external_bg", []); _ext = _ext is True or sh["setting"] in _ext
            layered = all((assets / f"bg_{sh['setting']}{suf}.png").exists() for suf in ("_far", "_mid", "_near")) and not sh.get("flat") and not _ext
            # depth of field only on a real close-up (zoom >= 2.2) or when a shot asks for it, and gently:
            # blurring the setting on every medium shot turned the story's places into colour blocks
            close = bool(foc) and float((foc or {}).get("zoom", 1)) >= 2.2
            dof_far = "filter:blur(2.5px);" if (sh.get("dof") or close) else ""; dof_mid = "filter:blur(1px);" if (sh.get("dof") or close) else ""
            # an insert (object / screen / clock with nobody in frame) is a CLOSE shot: the room behind it is a soft blur,
            # never a sharp wide of the set with the hero missing from their bed or desk (2026-11-09 audit)
            insert_ = not sh.get("chars") and bool(sh.get("props") or sh.get("overlays") or sh.get("pov"))
            if insert_:
                dof_far = dof_mid = "filter:blur(10px) brightness(.82);"
            if panes_data:
                layers_data = None
            elif layered:
                lid = lambda n: f"{dom}-{n}"
                scene_html = (f"<img id='{lid('L0')}' class='bg lay' style='{dof_far}' src='assets/bg_{sh['setting']}_far.png'><img id='{lid('L1')}' class='bg lay' style='{dof_mid}' src='assets/bg_{sh['setting']}_mid.png'>"
                              f"<div id='{lid('chars')}' class='lay'>{''.join(veh_html)}{''.join(crowd_html)}{''.join(props_html)}{''.join(chars_html)}</div>"
                              + (f"<div id='{lid('OC')}' class='lay' style='{dof_mid}'>" + "".join(
                                  f"<div style='position:absolute;left:0;top:0;width:{W}px;height:{H}px;background:url(assets/bg_{sh['setting']}_mid.png) 0 0/{W}px {H}px no-repeat;clip-path:polygon({o_['poly']})'></div>" for o_ in occ_list) + "</div>" if occ_list else "")
                              + f"<img id='{lid('L2')}' class='bg lay' style='filter:blur({spec.get('fg_blur', 5)}px);' src='assets/bg_{sh['setting']}_near.png'>")
                # the people stand on the floor and sit on the furniture of the MID layer: those two must move as one,
                # or under a push/pan the sitter slides off the chair and feet skate on the floor (2026-11-09 audit).
                # Parallax stays between the far wall/sky and the blurred near foreground only.
                k_on = 0.85 if not foc else 1.0
                layers_data = [dict(dom=lid("L0"), k=0.35 if not foc else 0.6), dict(dom=lid("L1"), k=k_on), dict(dom=lid("chars"), k=k_on), dict(dom=lid("L2"), k=1.2)]
                if occ_list: layers_data.insert(3, dict(dom=lid("OC"), k=k_on))
            else:
                scene_html = f"<img class='bg' style='{'filter:blur(10px) brightness(.82);transform:scale(1.15);' if insert_ else ('filter:blur(1.5px);' if (foc and float((foc or {}).get('zoom', 1)) >= 2.2) else '')}' src='assets/bg_{sh['setting']}.png'>{''.join(veh_html)}{''.join(crowd_html)}{''.join(props_html)}{''.join(chars_html)}" + "".join(
                    f"<div style='position:absolute;left:0;top:0;width:{W}px;height:{H}px;z-index:{o_['z']};background:url(assets/bg_{sh['setting']}.png) 0 0/{W}px {H}px no-repeat;clip-path:polygon({o_['poly']})'></div>" for o_ in occ_list)
                layers_data = None
            shots_html.append(f"<div id='{dom}' class='shot' style='z-index:{si+1}'><div id='{dom}-sway' class='cam'><div id='{dom}-cam' class='cam' style='{grade_css}'>{scene_html}</div></div>{rays}{rain}{''.join(ov_html)}</div>")
            d = dict(dom=dom, t0=round(t0, 3), t1=round(t1, 3), cam=cam, chars=chars_data, props=props_data, first=(si == 0), prev=prev,
                     cut=bool(sh.get("cut")), trans=sh.get("trans"), crowd=crowd_data, overlays=ov_data, vehicles=veh_data)
            lip = []
            for ci in cue_ids:
                who = cue_who.get(ci)
                if who and any(x["k"] == who for x in chars_data):
                    evs = LS.cue_events(cues[ci].get("words", []), t0, t1, s0 / 1000.0, env)
                    if evs: lip.append(dict(k=who, ev=evs, ci=ci))   # ci: ci/lipsync_audio.py swaps in mouth cues read from the real voice-over
            if lip: d["lip"] = lip
            if layers_data: d["layers"] = layers_data
            if panes_data: d["panes"] = panes_data
            for key in ("shake", "rain", "flash", "sway"):
                if key in sh: d[key] = sh[key]
            shots_data.append(d); prev = dom
        for idx in range(tsc["cueRange"][0], tsc["cueRange"][1] + 1):
            c = cues[idx]
            ct0 = (c["startMs"] - s0) / 1000; ct1 = (c["endMs"] - s0) / 1000; islast = idx == tsc["cueRange"][1]
            if islast: ct1 = dur                       # contract rule 17: the last caption of a scene is never faded early
            caps_html.append(f"<div id='cap-{n}-{idx}' class='caption clip' data-start='{ct0:.3f}' data-duration='{ct1 - ct0:.3f}'><span>{html.escape(c['text'])}</span></div>")
            caps_data.append(dict(id=f"cap-{n}-{idx}", t0=round(ct0, 3), t1=round(ct1, 3), last=islast))
        if a.no_captions: caps_html, caps_data = [], []
        data = json.dumps(dict(W=W, H=H, sceneId=cid, dur=dur, shots=shots_data, caps=caps_data, rigs=RIGS), ensure_ascii=False)
        sel = f"[data-composition-id='{cid}']"
        style = f"""
    {sel} {{ position:absolute; inset:0; width:{W}px; height:{H}px; overflow:hidden; background:#07060d; font-family:'Be Vietnam Pro','Nunito',Arial,sans-serif; }}
    {sel} .shot {{ position:absolute; inset:0; opacity:0; overflow:hidden; }}
    {sel} .cam {{ position:absolute; inset:0; }}
    {sel} .bg {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; display:block; }}
    {sel} .char {{ position:absolute; }}
    {sel} .flip, {sel} .flip svg {{ width:100%; height:100%; display:block; }}
    {sel} .prop {{ position:absolute; z-index:5; }}
    {sel} .rain {{ position:absolute; top:0; width:3px; background:linear-gradient(#cfe0ff00,#cfe0ffaa); z-index:8; }}
    {sel} .pane {{ position:absolute; top:0; width:960px; height:1080px; overflow:hidden; }}
    {sel} .pcam {{ position:absolute; inset:0; }}
    {sel} .bgp {{ position:absolute; left:-480px; top:0; width:1920px; height:1080px; display:block; }}
    {sel} .tint {{ position:absolute; inset:0; mix-blend-mode:soft-light; opacity:.6; pointer-events:none; z-index:7; }}
    {sel} .pdiv {{ position:absolute; left:958px; top:0; width:4px; height:1080px; background:#0b0a0c; z-index:9; }}
    {sel} .char, {sel} .flip, {sel} .shot {{ overflow:visible; }}
    {sel} .shot {{ overflow:hidden; }}
    {sel} .lb {{ position:absolute; left:0; width:{W}px; height:{int(H*0.128)}px; background:#000; z-index:25; }}
    {sel} .lay {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; }}
    {sel} .cfig {{ position:absolute; }}
    {sel} .rays {{ position:absolute; inset:0; z-index:12; pointer-events:none; background:conic-gradient(from 200deg at 78% -10%, rgba(255,214,150,0), rgba(255,214,150,.22) 8%, rgba(255,214,150,0) 16%, rgba(255,214,150,.16) 26%, rgba(255,214,150,0) 36%); }}
    {sel} .ovw {{ position:absolute; left:0; right:0; display:flex; padding:0 72px; z-index:22; pointer-events:none; box-sizing:border-box; }}
    {sel} .ovabs {{ position:absolute; width:0; height:0; z-index:22; pointer-events:none; }}
    {sel} .ov.chip {{ padding:10px 26px; border-radius:999px; background:rgba(8,10,24,.72); border:1.5px solid rgba(255,255,255,.35); color:#f6f0e4; font-size:28px; letter-spacing:.06em; text-transform:uppercase; font-weight:700; white-space:nowrap; }}
    {sel} .ov.screen {{ width:{560 if H > W else 760}px; padding:26px 34px 30px; border-radius:26px; background:#10141d; border:3px solid #2b3240; box-shadow:0 30px 80px rgba(0,0,0,.55); color:#f6f0e4; }}
    {sel} .ov.screen .scr-h {{ display:flex; align-items:center; gap:12px; font-size:24px; letter-spacing:.08em; color:#aeb6c2; text-transform:uppercase; }}
    {sel} .ov.screen .dot {{ width:18px; height:18px; border-radius:50%; background:#3ccf6e; display:inline-block; }}
    {sel} .ov.screen .scr-l {{ margin-top:18px; font-size:28px; color:#cfd6e0; }}
    {sel} .ov.screen .scr-v {{ font-size:{84 if H > W else 96}px; font-weight:700; line-height:1.05; font-variant-numeric:tabular-nums; }}
    {sel} .ov.screen .scr-c {{ width:100%; height:110px; margin-top:14px; }}
    {sel} .ov.counter {{ padding:12px 34px 14px; border-radius:18px; background:rgba(8,10,24,.74); border:1.5px solid rgba(232,184,74,.55); text-align:center; }}
    {sel} .ov.counter .num {{ font-size:78px; font-weight:700; color:#f0c75a; text-shadow:0 0 22px rgba(240,199,90,.55); font-variant-numeric:tabular-nums; line-height:1.05; }}
    {sel} .ov.counter .lbl {{ font-size:22px; letter-spacing:.14em; text-transform:uppercase; color:#d9d2c0; }}
    {sel} .ov.word {{ font-weight:900; font-size:{int(W * (0.105 if W > H else 0.14))}px; line-height:1; letter-spacing:.02em; font-style:italic;
      -webkit-text-stroke:{max(3, int(W * 0.004))}px #15121b; paint-order:stroke fill; text-shadow:{int(W*0.004)}px {int(W*0.004)}px 0 #15121b, 0 0 {int(W*0.012)}px rgba(0,0,0,.45); white-space:nowrap; }}
    {sel} .ov.burst {{ width:340px; height:300px; display:grid; place-items:center; text-align:center; background:#ffd23a; clip-path:polygon(100.0% 50.0%,82.3% 60.5%,90.5% 79.4%,70.0% 77.5%,65.5% 97.6%,50.0% 84.0%,34.5% 97.6%,30.0% 77.5%,9.5% 79.4%,17.7% 60.5%,0.0% 50.0%,17.7% 39.5%,9.5% 20.6%,30.0% 22.5%,34.5% 2.4%,50.0% 16.0%,65.5% 2.4%,70.0% 22.5%,90.5% 20.6%,82.3% 39.5%); color:#c2262e; font-size:52px; font-weight:700; line-height:1; padding:40px; box-sizing:border-box; }}
    {sel} .ov.bubble {{ width:560px; padding:20px 28px; border-radius:26px; background:#fff; color:#241726; font-size:34px; line-height:1.25; font-weight:700; box-sizing:border-box; box-shadow:0 6px 0 rgba(0,0,0,.25); }}
    {sel} .ov.chain {{ font-size:{64 if H > W else 72}px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:#f6f0e4; text-shadow:0 4px 18px rgba(0,0,0,.55); text-align:center; }}
    {sel} .ov.chain .arrow {{ color:#ffd27a; }}
    {sel} .ov.graph {{ padding:28px 36px; border-radius:22px; background:linear-gradient(#1c2a3e,#14202f); border:2px solid #2d4058; box-shadow:0 30px 80px rgba(0,0,0,.5); }}
    {sel} .ov.graph .g-h {{ display:flex; justify-content:space-between; align-items:baseline; gap:40px; font-size:30px; letter-spacing:.08em; color:#aeb9c8; text-transform:uppercase; }}
    {sel} .ov.graph .g-h b {{ font-size:56px; letter-spacing:0; }}
    {sel} .ov.graph .g-l {{ font-size:20px; letter-spacing:.14em; color:#7f8ca0; text-transform:uppercase; margin-bottom:8px; }}
    {sel} .ov.clock {{ filter:drop-shadow(0 20px 40px rgba(0,0,0,.45)); }}
    {sel} .ov.title {{ font-size:104px; letter-spacing:.06em; text-transform:uppercase; font-weight:700; color:#ff9ad0; text-shadow:0 0 24px rgba(255,120,190,.7); text-align:center; max-width:1500px; }}
    {sel} .vig {{ position:absolute; inset:0; z-index:20; pointer-events:none; background:radial-gradient(ellipse at 50% 46%, transparent 52%, rgba(3,2,10,.62) 100%); }}
    {sel} .flash {{ position:absolute; inset:0; z-index:30; background:#fff; opacity:0; }}
    {sel} .caption {{ position:absolute; left:{6 if H > W else 8}%; right:{6 if H > W else 8}%; bottom:{16 if H > W else 5.5}%; z-index:40; display:grid; place-items:center; text-align:center; opacity:0; }}
    {sel} .caption span {{ max-width:{980 if H > W else 1500}px; padding:14px 32px; border-radius:14px; background:rgba(8,6,16,.66); color:#f6f0e4; font-size:{62 if H > W else 44}px; line-height:1.25; font-weight:700; text-shadow:0 2px 6px #000; }}
    """
        lb_html = "<div class='lb' data-layout-allow-occlusion='true' style='top:0'></div><div class='lb' data-layout-allow-occlusion='true' style='bottom:0'></div>" if spec.get("letterbox") else ""
        script = engine.replace("__DATA__", data.replace("</", "<\\/"))
        doc = (f"<template id='{cid}-template'>\n  <div data-composition-id='{cid}' data-width='{W}' data-height='{H}' data-duration='{dur:.3f}'>\n"
               f"    <svg width='0' height='0' style='position:absolute'><defs><symbol id='crowdfig' viewBox='0 0 100 200'><circle cx='50' cy='36' r='22' fill='#0b0a0c'/><rect x='24' y='62' width='52' height='80' rx='20' fill='currentColor'/><path d='M38 140 L36 192 M62 140 L64 192' stroke='#241726' stroke-width='12' stroke-linecap='round'/></symbol></defs></svg>\n    {''.join(shots_html)}\n    {lb_html}<div class='vig' data-layout-allow-occlusion='true'></div><div id='flash-{cid}' class='flash'></div>\n    {''.join(caps_html)}\n"
               f"    <style>@font-face{{font-family:'Be Vietnam Pro';src:url('assets/fonts/BeVietnamPro-Bold.ttf');font-weight:700}}{style}</style>\n"
               f"    <script src='{GS}'></script>\n    <script>{script}</script>\n  </div>\n</template>\n")
        (out / "compositions" / f"scene_{n}.html").write_text(doc, encoding="utf-8")
        root_hosts.append(f"<div id='{cid}-host' class='clip scene-host' data-composition-id='{cid}' data-composition-src='compositions/scene_{n}.html' "
                          f"data-start='{sec(tsc['startMs'])}' data-duration='{sec(tsc['sceneDurationMs'])}' data-track-index='1' data-track-kind='graphics'></div>")

    total = sec(TL["durationMs"]); td = TL["durationMs"] / 1000
    fps = spec.get("fps", 60 if td <= 180 else 30)      # long films default to 30 fps: render time is ~7 s per second of video at 30 fps on a laptop
    mb_attr = (' data-motion-blur="on" data-motion-blur-shutter="%s"' % spec.get("motion_blur_shutter", 180)) if spec.get("motion_blur") else ""
    audio = "" if a.no_audio_tag else f"<audio id=\"voice\" src=\"assets/audio/voiceover.wav\" data-start=\"0\" data-duration=\"{total}\" data-track-index=\"0\"></audio>"
    index = f"""<!doctype html>
<html lang="{spec.get('lang', 'vi')}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width={W}, height={H}">
  <title>{html.escape(spec.get('title', 'Code2Video'))}</title>
  <script src="{GS}"></script>
  <style>
    html, body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:#07060d; }}
    #root {{ position:relative; width:{W}px; height:{H}px; overflow:hidden; }}
    .scene-host {{ position:absolute; inset:0; z-index:2; }}
    .stage {{ position:absolute; inset:0; z-index:1; background:#07060d; }}
    #voice {{ position:absolute; width:1px; height:1px; opacity:0; }}
    #endfade {{ position:absolute; inset:0; background:#000; opacity:0; z-index:100; pointer-events:none; }}
  </style>
</head>
<body>
  <div id="root" data-composition-id="story" data-width="{W}" data-height="{H}" data-start="0" data-duration="{total}" data-fps="{fps}"{mb_attr}>
    <div id="stage" class="clip stage" data-start="0" data-duration="{total}" data-track-index="0"></div>
    {audio}
    {chr(10).join('    ' + h for h in root_hosts)}
    <div id="endfade"></div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      tl.to("#endfade", {{ opacity: 1, duration: 1.2, ease: "power1.in" }}, {max(0, td - 1.2):.3f});
      window.__timelines = window.__timelines || {{}};
      window.__timelines["story"] = tl;
    </script>
  </div>
</body>
</html>
"""
    (out / "index.html").write_text(index, encoding="utf-8")
    print(f"built {len(spec['scenes'])} scenes -> {out}")

if __name__ == "__main__":
    main()
