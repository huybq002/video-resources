"""Does the film have a story, not just a sequence of pictures? Dramaturgy lint for short films.

Checks the `spine` block and the per-scene `turn` that references/short-film-craft.md asks for, plus shot-grammar
mistakes that can be seen in the spec (180-degree line, place changes with no establishing shot). All WARNINGs.

    python craft_lint.py spec.json
"""
import re

SPINE_KEYS = ("want", "obstacle", "turn", "choice", "opening_image", "ending_image", "motif")
GENERIC_WANT = re.compile(r"^(to )?(be happy|succeed|learn|understand|find (the )?(truth|meaning)|change|grow|survive)\.?$", re.I)


def _cues(sc):
    out = []
    for it in sc.get("shots", []):
        seq = it.get("sequence") or {}
        for c in list(seq.get("cues", [])) + list(seq.get("lines", [])) + list(it.get("cues") or []):
            out.append(c if isinstance(c, dict) else {"t": c})
    return out


def craft(spec):
    notes = []
    scenes = spec.get("scenes", [])
    if len(scenes) < 3 or spec.get("format") == "wordless" and len(scenes) < 2:
        return notes
    total = sum(float(s.get("target_s") or 0) for s in scenes)
    # ---- the spine: one person wants one thing, something stops them, something turns, they choose ----------
    sp = spec.get("spine")
    if not isinstance(sp, dict):
        notes.append("WARNING: craft: no `spine` block. A short film is one person who WANTS something, an OBSTACLE, a TURN and a CHOICE "
                     "that costs something, plus an opening and an ending image that rhyme and a motif object that returns "
                     "(references/short-film-craft.md, \"The spine\"). Add spine: {want, obstacle, turn, choice, opening_image, ending_image, motif}.")
    else:
        miss = [k for k in SPINE_KEYS if not str(sp.get(k, "")).strip()]
        if miss:
            notes.append(f"WARNING: craft: spine is missing {', '.join(miss)} (short-film-craft.md).")
        if GENERIC_WANT.match(str(sp.get("want", "")).strip()):
            notes.append(f"WARNING: craft: the want \"{sp['want']}\" is a theme, not a want. A want is something you can film someone doing: "
                         f"\"get the 6:15 train\", \"make her mother say sorry\", \"be the first one to open the box\".")
        o, e = str(sp.get("opening_image", "")).strip().lower(), str(sp.get("ending_image", "")).strip().lower()
        if o and e and o == e:
            notes.append("WARNING: craft: opening_image and ending_image are the same. The ending must be the opening image CHANGED "
                         "(same place and object, different meaning: the empty chair is now occupied, the lit phone is now face down).")
        motif = str(sp.get("motif", "")).strip().lower()
        if motif:
            first = " ".join(c.get("t", "") + " " + " ".join(map(str, c.get("props", []) or [])) for c in _cues(scenes[0])).lower()
            last = " ".join(c.get("t", "") + " " + " ".join(map(str, c.get("props", []) or [])) for c in _cues(scenes[-1])).lower()
            mid = " ".join(c.get("t", "") + " " + " ".join(map(str, c.get("props", []) or [])) for s in scenes[1:-1] for c in _cues(s)).lower()
            word = motif.split()[-1]
            if not (word in first or any(word in str(p) for p in _props(scenes[0]))):
                notes.append(f"WARNING: craft: the motif '{motif}' is not in the first scene: plant it in the opening so the ending can return to it.")
            if not (word in last or any(word in str(p) for p in _props(scenes[-1]))):
                notes.append(f"WARNING: craft: the motif '{motif}' does not come back in the last scene: a film that ends on an object it never showed feels random.")
            if len(scenes) >= 5 and word not in mid and not any(word in str(p) for s in scenes[1:-1] for p in _props(s)):
                notes.append(f"WARNING: craft: the motif '{motif}' appears at the start and the end but never between: show it changing in the middle.")
    # ---- each scene is a small story: goal, conflict, and the situation is different when it ends ------------
    pol = []
    for sc in scenes:
        sid = sc.get("id")
        if not str(sc.get("goal", "")).strip():
            notes.append(f"WARNING: craft: scene {sid} has no `goal` (what the hero wants in THIS scene).")
        if not str(sc.get("turn", "")).strip():
            notes.append(f"WARNING: craft: scene {sid} has no `turn`: one sentence saying what is different at the end (\"she now knows he lied\"). "
                         f"A scene that ends where it began is cut, or merged.")
        v = str(sc.get("value", "")).strip()
        if v and v not in ("+", "-", "0"):
            notes.append(f"WARNING: craft: scene {sid} `value` must be \"+\", \"-\" or \"0\" (does it end better or worse for the hero?).")
        pol.append(v)
    for i in range(len(pol) - 3):
        if pol[i] and pol[i] == pol[i + 1] == pol[i + 2] == pol[i + 3] and pol[i] != "0":
            notes.append(f"WARNING: craft: scenes {i + 1}-{i + 4} all end '{pol[i]}'. Alternate (win, then a price; loss, then a spark of hope): "
                         f"four in a row is a straight line, and straight lines are boring.")
            break
    if any(pol) and total >= 60:
        low = [i for i, v in enumerate(pol) if v == "-"]
        if not low:
            notes.append("WARNING: craft: no scene ends worse for the hero. Without a low point there is nothing to climb out of.")
        elif low and low[-1] < len(scenes) * 0.55:
            notes.append("WARNING: craft: the lowest moment comes before the middle of the film; the darkest point belongs at 70-85 % so the choice is hard.")
    # ---- grammar visible in the spec ------------------------------------------------------------------------
    last_place = None
    for sc in scenes:
        places = []
        for it in sc.get("shots", []):
            seq = it.get("sequence") or {}
            ss = seq.get("settings") or ([seq["setting"]] if seq.get("setting") else []) or ([it["setting"]] if it.get("setting") else [])
            places += [str(x) for x in ss]
        first = _cues(sc)[0] if _cues(sc) else {}
        place = (first.get("at") or (places[0] if places else None))
        if last_place and place and place != last_place and first.get("shot") not in (None, "establish", "wide") and sc is not scenes[0]:
            notes.append(f"WARNING: craft: scene {sc.get('id')} changes place ({last_place} -> {place}) but opens on a '{first.get('shot')}' shot. "
                         f"Open a new place on a wide or establishing shot (the viewer must learn where we are before who is in it).")
        last_place = place or last_place
    # 180-degree line: a pair that is left/right in one scene stays left/right while they talk in the same place
    sides = {}
    for sc in scenes:
        for it in sc.get("shots", []):
            seq = it.get("sequence") or {}
            if seq.get("type") == "dialogue" and "a" in seq and "b" in seq:
                key = (seq["a"]["k"], seq["b"]["k"]); xa, xb = seq["a"].get("x", 600), seq["b"].get("x", 1300)
                side = xa < xb
                if key in sides and sides[key][0] != side and sides[key][1] == sc.get("id"):
                    notes.append(f"WARNING: craft: in scene {sc.get('id')} {key[0]} and {key[1]} swap sides between two dialogue blocks: the camera crosses the "
                                 f"180-degree line and the viewer loses who is where. Keep {key[0]} on the {'left' if sides[key][0] else 'right'}.")
                sides[key] = (side, sc.get("id"))
    return notes


def _props(sc):
    out = []
    for c in _cues(sc):
        out += [x if isinstance(x, str) else x.get("id", "") for x in (c.get("props") or [])]
        for d in ([c["do"]] if isinstance(c.get("do"), str) else c.get("do") or []):
            m = re.match(r"(?:place|pickup):(\w+)", str(d))
            if m:
                out.append(m.group(1))
    return out


if __name__ == "__main__":
    import json
    import sys
    for line in craft(json.load(open(sys.argv[1], encoding="utf-8"))):
        print(line)
