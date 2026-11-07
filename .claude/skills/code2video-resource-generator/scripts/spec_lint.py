"""Structural lint of spec.json, run by generate.py before anything is built.

It catches the things that make a finished video dull or wrong but that the contract check cannot see:
too few settings for the story, stock `lib:` backgrounds used for a story that needs its own places,
a cast of one, nobody but the hero ever on screen, long single-shot scenes, and wardrobe rule breaks.

Every line it returns starts with WARNING or NOTE. Fix every WARNING in the spec and run generate again.
"""
import re

# Words that mean the story has other people in it. If the script says so, the picture must show it.
GROUP_WORDS = re.compile(
    r"\b(crowd|crowds|people|everyone|everybody|they|them|hundreds|thousands|horde|hordes|mob|swarm|"
    r"zombie|zombies|survivor|survivors|soldier|soldiers|neighbou?rs?|strangers?|figures?|bodies|"
    r"đám đông|mọi người|họ|bọn họ|hàng trăm|hàng nghìn|xác sống|người lạ|hàng xóm|binh lính)\b", re.I)


def _cast(spec):
    return [c for c in spec.get("cast", []) if not c.get("narrator")]


def _walk(spec):
    """-> (settings per scene id, actor ids per scene id, shot count per scene id, crowd scene ids)"""
    sets, actors, shots, crowds = {}, {}, {}, set()
    for sc in spec.get("scenes", []):
        sid = sc.get("id")
        sets[sid], actors[sid], shots[sid] = [], set(), 0
        for item in sc.get("shots", []):
            seq = item.get("sequence")
            panes = item.get("split") or []
            if seq:
                # narration: settings[] / actors[] / cues[]   dialogue: setting / a + b / lines[]
                sets[sid] += [s for s in list(seq.get("settings", [])) + [seq.get("setting")] if s]
                actors[sid] |= {a.get("k") for a in seq.get("actors", []) if a.get("k")}
                actors[sid] |= {seq[k]["k"] for k in ("a", "b") if isinstance(seq.get(k), dict) and seq[k].get("k")}
                shots[sid] += max(1, len(seq.get("cues", [])) + len(seq.get("lines", [])))
                if seq.get("crowd"):
                    crowds.add(sid)
            elif panes:
                for pn in panes:
                    if pn.get("setting"):
                        sets[sid].append(pn["setting"])
                    actors[sid] |= {a.get("k") for a in pn.get("actors", []) if a.get("k")}
                    if pn.get("crowd"):
                        crowds.add(sid)
                shots[sid] += 1
            else:
                if item.get("setting"):
                    sets[sid].append(item["setting"])
                actors[sid] |= {a.get("k") for a in item.get("actors", []) if a.get("k")}
                if item.get("crowd"):
                    crowds.add(sid)
                shots[sid] += 1
    return sets, actors, shots, crowds


def _script_text(spec):
    out = []
    for sc in spec.get("scenes", []):
        for item in sc.get("shots", []):
            seq = item.get("sequence") or {}
            for c in list(seq.get("cues", [])) + list(seq.get("lines", [])) + list(item.get("cues") or []):
                out.append(c if isinstance(c, str) else c.get("t", ""))
    return " ".join(out)


def lint(spec):
    notes = []
    scenes = spec.get("scenes", [])
    n_scenes = len(scenes)
    if not n_scenes:
        return ["WARNING: the spec has no scenes."]
    sets, actors, shots, crowds = _walk(spec)
    cast = _cast(spec)
    flat = [s for v in sets.values() for s in v]
    distinct = sorted(set(flat))

    # ---- settings: enough of them, and made for this story -------------------------------------
    want = max(3, round(n_scenes * 0.6))
    if len(distinct) < want:
        notes.append(f"WARNING: only {len(distinct)} distinct setting(s) for {n_scenes} scenes "
                     f"(aim for at least {want}): the video repeats the same picture. Add settings that the story needs.")
    for s in distinct:
        used = sum(1 for sid, v in sets.items() if s in v)
        if n_scenes >= 5 and used > max(2, round(n_scenes * 0.35)):
            notes.append(f"WARNING: setting '{s}' is used in {used} of {n_scenes} scenes: "
                         f"give those scenes their own place, or at least a different camera and time of day.")
    lib = [s for s in distinct if str(s).startswith("lib:")]
    if distinct and len(lib) == len(distinct) and n_scenes >= 5:
        notes.append(f"WARNING: every setting is a stock `lib:` background ({', '.join(lib)}) but this story is "
                     f"'{str(spec.get('idea', ''))[:60]}'. The library only has ordinary places (cafe, office, bedroom, "
                     f"street, park, rooftop). Write the places the story actually needs in spec.settings "
                     f"(references/scene-dsl.md); keep `lib:` only where it really fits.")
    empty = [sid for sid, v in sets.items() if not v]
    if empty:
        notes.append(f"WARNING: scene(s) {empty} have no setting.")

    # ---- cast: more than the hero, and other people on screen ----------------------------------
    if n_scenes >= 6 and len(cast) < 2:
        notes.append(f"WARNING: the cast is {len(cast)} character(s) besides the narrator. A {n_scenes}-scene story "
                     f"needs supporting characters (the people the script talks about) so the screen is not one "
                     f"figure for the whole film.")
    multi = [sid for sid, a in actors.items() if len(a) >= 2]
    if n_scenes >= 6 and not multi and not crowds:
        notes.append("WARNING: no scene has two characters or a `crowd`: nobody ever meets anyone. "
                     "Put the other characters on screen, or add a `crowd` block (spec-schema.md) for groups.")
    text = _script_text(spec)
    if GROUP_WORDS.search(text) and not crowds:
        hit = sorted({m.group(0).lower() for m in GROUP_WORDS.finditer(text)})[:6]
        notes.append(f"WARNING: the script talks about other people ({', '.join(hit)}) but no scene has a `crowd` "
                     f"block or a second character: the viewer never sees them. Add them.")
    never_seen = [c["id"] for c in cast if not any(c["id"] in a for a in actors.values())]
    if never_seen:
        notes.append(f"WARNING: cast {never_seen} never appear in any shot's `actors`.")

    # ---- shots: no long static scene ------------------------------------------------------------
    for sc in scenes:
        sid, t = sc.get("id"), float(sc.get("target_s") or 0)
        if shots.get(sid, 0) <= 1 and t > 15:
            notes.append(f"WARNING: scene {sid} is one shot for {t:.0f}s: split it into 2-3 shots "
                         f"(different framing, or a cut to another setting).")

    # ---- wardrobe: male characters wear no long trousers ----------------------------------------
    for c in cast:
        if str(c.get("gender", "")).lower() in ("male", "m", "nam") and c.get("bottom") == "pants":
            notes.append(f"WARNING: male character '{c['id']}' has bottom \"pants\". Male characters keep bare stick "
                         f"legs (bottom \"none\") or wear \"shorts\"; give the outfit character with a top, shoes, "
                         f"hat, bag or other accessory instead (references/wardrobe.md).")
    return notes


if __name__ == "__main__":
    import json
    import sys
    for line in lint(json.load(open(sys.argv[1], encoding="utf-8"))):
        print(line)
