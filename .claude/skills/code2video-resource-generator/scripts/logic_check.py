"""Character-logic audit of a BUILT project (reads assets/shots_debug.json + assets/anchors_<setting>.json).

python logic_check.py <project_dir> [--spec spec.json]

Looks at every shot the way the camera frames it and reports what a viewer would call a mistake:
  focus-off      the camera zooms on someone whose face is outside the frame
  cut-off        a main character half outside a wide shot
  overlap        two main characters drawn on top of each other
  extra-over     a background person on top of a main character
  floating       feet above the floor (standing on the wall / in the air)
  in-furniture   standing inside a bed / table / sofa / counter
  facing-away    two people in a conversation framing turned away from each other
  named-missing  the line names someone who is not in the shot
  jump           someone teleports between two wide shots of the same place (no walk in between)
  scale-jump     the same person at the same depth drawn at a clearly different size
  double-item    the same object both in the hand and floating beside it
Each problem prints one "WARNING: logic: ..." line (the pipeline's lint gate counts them). Exit 0 always.
"""
import argparse, json, pathlib, re, sys

STAND_IN = {"bed": .9, "table": .55, "desk": .6, "sofa": .8, "kitchen_counter": .5, "shop_counter": .55, "bench": .7}


def cam_map(cam, W, H, k):
    """screen position of a stage point under the shot's camera at its start and end (transform origin 50% 62%)"""
    ox, oy = W * .5, H * .62
    out = []
    for Z, tx, ty in ((cam[0], cam[1], cam[2]), (cam[3], cam[4], cam[5])):
        z = 1 + (Z - 1) * k
        out.append(lambda x, y, z=z, tx=tx, ty=ty: (ox + z * (x - ox) + tx * k, oy + z * (y - oy) + ty * k))
    return out


def body(c):
    s = c.get("s") or .8; x = c.get("x") or 0; by = c.get("by") or 0
    if c.get("hold") == "lie": return (x - 380 * s, by - 260 * s, x + 380 * s, by)
    top = by - (560 if c.get("hold") == "sit" else 790) * s
    return (x - 105 * s, top, x + 105 * s, by)


def head(c):
    s = c.get("s") or .8; x = c.get("x") or 0; by = c.get("by") or 0
    if c.get("hold") == "lie": return (x + (1 if c.get("flip") else -1) * 600 * s, by - 40 * s)
    return (x, by - (560 if c.get("hold") == "sit" else 782) * s + 176 * s)


def ov(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / (min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])) or 1)


def acting(nm, txt):
    """the line makes this person DO something here: they are the subject of a sentence ("Zoe walks..."), or the
    one someone goes to / talks to ("walks over to Rex", "tells Sam"). A name only mentioned ("Sam is doing it alone"
    said by someone else, "sends a copy to Zoe") does not put them in the shot."""
    n = re.escape(nm)
    if re.search(r"(^|[.!?]\s+)" + n + r"\b(?!'s)\s+(?!is doing|was|has|had)\w+", txt): return True
    if re.search(r"\b" + n + r"\s+(?!is \b|was \b|has \b|does \b)[a-z]+s\b", txt): return True   # "On Friday Zoe finds..."
    return bool(re.search(r"\b(walks?|runs?|goes|comes|turns?|looks?|smiles?|talks?|tells?|asks?|hugs?|finds?|meets?|joins?)\b[^.!?]{0,20}\b(to|at|with)?\s*" + n + r"\b", txt, re.I))

def walks(c): return any(a[1] in ("walkTo", "run", "walk", "enter") for a in (c.get("acts") or [])) or c.get("enter") is not None


def check(proj, spec=None):
    proj = pathlib.Path(proj); dbg = json.loads((proj / "assets" / "shots_debug.json").read_text(encoding="utf-8"))
    W, H, shots = dbg["W"], dbg["H"], dbg["shots"]
    names = {c["id"]: c.get("name", c["id"]) for c in (spec or {}).get("cast", []) if not c.get("narrator")}
    anch = {}
    def A(sid):
        sid = (sid or "").split("__")[0]
        if sid not in anch:
            f = proj / "assets" / f"anchors_{sid}.json"; anch[sid] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        return anch[sid]
    out = []; prev = None; seen_scale = {}
    for i, sh in enumerate(shots):
        tag = f"scene {sh['scene']} shot {sh['dom']} ({sh['t0']:.1f}s)"
        chars = sh["chars"]; mains = [c for c in chars if not c.get("extra") and (c.get("by") or 0) < H * 1.02]
        foc = sh.get("focus") or {}; k = 1.0 if foc else 0.85
        maps = cam_map(sh["cam"], W, H, k) if sh.get("cam") else [lambda x, y: (x, y)] * 2
        inside = lambda p: -0.02 * W <= p[0] <= 1.02 * W and -0.02 * H <= p[1] <= 1.02 * H
        if foc.get("k"):
            fc = next((c for c in chars if c["k"] == foc["k"]), None)
            if fc and not all(inside(m(*head(fc))) for m in maps):
                out.append(f"{tag}: focus-off: the camera frames {fc['k']} but the face is outside the picture")
        elif mains:
            for c in mains:
                b = body(c); cx = (b[0] + b[2]) / 2
                if not any(inside(m(cx, (b[1] + b[3]) / 2)) and inside(m(*head(c))) for m in maps):
                    out.append(f"{tag}: cut-off: {c['k']} is outside the frame of a wide shot")
        for a_i, a in enumerate(mains):
            for b in mains[a_i + 1:]:
                if ov(body(a), body(b)) > 0.15 and not (foc and foc.get("zoom", 1) >= 2.2):
                    out.append(f"{tag}: overlap: {a['k']} and {b['k']} are drawn on top of each other")
        for e in (c for c in chars if c.get("extra")):
            for m in mains:
                if ov(body(e), body(m)) > 0.12 and not e.get("path"):
                    out.append(f"{tag}: extra-over: background person {e['k']} overlaps {m['k']}")
        an = A(sh.get("setting")); floor = an.get("_floor") or []
        for c in mains:
            if c.get("hold") or c.get("path"): continue
            by = c.get("by") or 0
            if floor and by < min(r[0] for r in floor) - 0.02 * H and by < H * 0.98:
                out.append(f"{tag}: floating: {c['k']}'s feet are above the floor line")
            for nm, rad in STAND_IN.items():
                for p in an.get(nm, []):
                    fl = p.get("floor"); ppm = p.get("floor_ppm") or 100
                    if fl and abs(fl[0] - c["x"]) < rad * ppm * 0.6 and abs(fl[1] - by) < 0.25 * ppm and not walks(c):
                        out.append(f"{tag}: in-furniture: {c['k']} stands inside the {nm}"); break
        faced = [c for c in mains if c.get("face") in (1, -1) and not c.get("back")]
        if len(faced) == 2:
            a, b = sorted(faced, key=lambda c: c["x"])
            if a["face"] == -1 and b["face"] == 1:
                out.append(f"{tag}: facing-away: {a['k']} and {b['k']} turn away from each other")
        if chars and names and not foc:      # a close-up shows one face on purpose
            txt = " ".join(sh.get("cues") or [])
            for k_, nm in names.items():
                if nm and acting(nm, txt) and not any(c["k"] == k_ for c in chars) and not sh.get("share"):
                    out.append(f"{tag}: named-missing: the line has {nm} act, but {k_} is not in the shot")
        if len(mains) == 2 and not foc and not any(c.get("hold") for c in mains) and not any(walks(c) for c in mains):
            a, b = sorted(mains, key=lambda c: c["x"]); ppm = ((a["s"] + b["s"]) / 2) * 720 / 1.65   # pixels per metre at their depth
            if abs(a["by"] - b["by"]) < 0.06 * H and (a.get("face") or b.get("face")) and (b["x"] - a["x"]) / ppm > 2.4:
                out.append(f"{tag}: too-far: {a['k']} and {b['k']} talk from {(b['x'] - a['x']) / ppm:.1f} m apart (shouting across the room)")
        if len(mains) >= 2 and an.get("_pave") and not any(c.get("hold") for c in mains):
            sides = set()
            for c in mains:
                rows = [r for r in an["_pave"] if abs(r[0] - c["by"]) < 0.04 * H]
                if rows: sides.add(min(rows, key=lambda r: abs(r[1] - c["x"]))[2] > 0)
            if len(sides) == 2:
                out.append(f"{tag}: across-road: {' and '.join(c['k'] for c in mains)} stand on opposite pavements")
        if prev and prev["scene"] == sh["scene"] and prev.get("setting") == sh.get("setting") and not prev.get("focus") and not foc:
            for c in mains:
                p_ = next((x for x in prev["chars"] if x["k"] == c["k"] and not x.get("extra")), None)
                if p_ and not walks(p_) and not walks(c) and not c.get("hold") and not p_.get("hold"):
                    if abs(p_["x"] - c["x"]) > 0.15 * W or abs(p_["by"] - c["by"]) > 0.1 * H:
                        out.append(f"{tag}: jump: {c['k']} moves from x={p_['x']:.0f} to x={c['x']:.0f} between two wide shots without walking")
        for c in mains:
            if c.get("hold") or (c.get("by") or 0) >= H * 0.98: continue
            key = (c["k"], (sh.get("setting") or "").split("__")[0], round((c.get("by") or 0) / (0.03 * H)))
            if key in seen_scale and max(seen_scale[key], c["s"]) / max(1e-3, min(seen_scale[key], c["s"])) > 1.2:
                out.append(f"{tag}: scale-jump: {c['k']} at the same depth is drawn {c['s']:.2f} here vs {seen_scale[key]:.2f} before")
            seen_scale.setdefault(key, c["s"])
        for c in mains:
            if c.get("item") and any(p.get("id") in (c["item"], "coffee" if c["item"] == "cup" else c["item"]) and p.get("hand") == c["k"] and p.get("mode") == "pop" for p in sh.get("props", [])):
                out.append(f"{tag}: double-item: {c['k']} holds the {c['item']} and the same object floats beside the hand")
        for pr in sh.get("props", []):        # an object popped beside a hand while that person runs/walks away
            hc = next((c for c in mains if c["k"] == pr.get("hand")), None)
            if hc and pr.get("mode") == "pop" and any(a[1] in ("run", "walkTo") for a in (hc.get("acts") or [])):
                out.append(f"{tag}: left-behind: {hc['k']} moves away but the {pr.get('id')} stays floating where they were")
        txt_ = " ".join(sh.get("cues") or [])
        if len(mains) == 2 and not foc and re.search(r"(you|your|sorry|thanks?)", txt_, re.I) and not any(c.get("face") for c in mains)                 and not any(c.get("hold") for c in mains):
            out.append(f"{tag}: not-facing: someone speaks to the other ('you') but both face the camera")
        if not sh.get("share"): prev = sh
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--spec")
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8")) if a.spec else None
    probs = check(a.project, spec)
    for p in probs: print("WARNING: logic: " + p)
    print(f"logic: {len(probs)} problem(s)")
