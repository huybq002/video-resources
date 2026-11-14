"""Make the picture follow the words for ANY script, from data (catalog.py), not per-case code.

Night video 003 ("procrastination oven", 2026-11-07): "Maya is scrubbing a spotless oven" over a woman standing still in
front of five coloured boxes; "folds every shirt", "presents to a room of tired colleagues" - nothing on screen. This
pass runs before the lint and fills what the spec left out. It never overwrites what the author wrote.

1. places   a setting without a dressed set becomes one: a known style (laundry, kitchen, meeting...), or a place from
            catalog.PLACES (hospital, library, bar, police station, garage...) built as a generic room furnished by
            layout.py, or - for any other place - a generic room holding the objects its lines name.
2. objects  every object a line names that the catalog knows ("the washing machines", "the kettle", "a podium") and that
            belongs in that place is ADDED to the setting by layout.py (zone + footprint + free space).
3. at       a line that says it happens somewhere else ("down to the laundry") moves to the setting of that kind.
4. do       the verb decides the affordance (catalog.VERBS: sleep, lie, sit, work, use:stir, use:reach, use:point,
            use:look, stand); the object in the setting that offers it is used, or the first plausible one is added:
            "collapses onto the sofa" -> lie@sofa, "loads the washer" -> use:reach@washer, "lectures" -> use:point@podium.
            Hand/face actions from spec_lint.ACTION_NEEDS (drink, phone, wave, laugh...) are added on top.
5. props / emote from the words.
generate.py prints one summary line.
"""
import pathlib
import re

try:
    import sets as SETS, catalog as CAT, layout as LAY
    from spec_lint import ACTION_NEEDS, PROP_NEEDS
except ImportError:      # imported as scripts.autofill
    from scripts import sets as SETS, catalog as CAT, layout as LAY
    from scripts.spec_lint import ACTION_NEEDS, PROP_NEEDS

PROPS = {p.stem for p in (pathlib.Path(__file__).resolve().parent.parent / "assets" / "props").glob("*.svg")}

# words -> a dressed style of sets.py (anything else goes through catalog.PLACES or the generic room)
STYLE_WORDS = [
    (r"laundr|washing machine|laundromat|basement", {"type": "room", "style": "laundry"}),
    (r"grocer|supermarket|all[- ]night shop|corner shop|convenience|aisle|store\b", {"type": "room", "style": "grocery"}),
    (r"meeting|conference|presentation|boardroom|auditorium|seminar", {"type": "room", "style": "meeting"}),
    (r"bathroom|toilet|shower|washroom", {"type": "room", "style": "bathroom"}),
    (r"kitchen", {"type": "room", "style": "kitchen"}),
    (r"bedroom|desk[ _]room|study\b|home office", {"type": "room", "style": "bedroom"}),
    (r"living ?room|lounge", {"type": "room", "style": "living"}),
    (r"office|workplace|cubicle", {"type": "room", "style": "office"}),
    (r"classroom|school|lecture hall", {"type": "room", "style": "classroom"}),
    (r"\blab\b|laboratory", {"type": "room", "style": "lab"}),
    (r"cafe|café|coffee ?shop", {"type": "room", "style": "cafe"}),
    (r"shopfront|storefront", {"type": "shopfront", "style": "cafe"}),
    (r"street|commute|road|sidewalk|crosswalk|city", {"type": "street"}),
    (r"beach|seaside", {"type": "beach"}),
]
# a place in a special state is the author's design, never swapped for a clean stock room
STATE = re.compile(r"\b(ruin|abandon|flood|burn|destroy|wreck|barricad|haunt|alien|underwater|cave|forest|desert|outer space|space ?(ship|station)|"
                   r"post[- ]?apocalyp|apocalyp|war\b|wartime|battle|zombie|collaps|derelict|dream|mind\b|memory|void\b|fantasy|castle|"
                   r"dungeon|ship\b|island|jungle|mountain|snow)", re.I)
# an abstract place: a black-box stage (sets.py style "void") holding the objects its lines name
ABSTRACT = [(r"dream|nightmare", "dream"), (r"\bmemor|flashback|remember", "memory"),
            (r"\bmind\b|in(side)? (her|his|their|my|your) head|thoughts?\b|imagin|subconscious|\bbrain\b", "mind"),
            (r"\bvoid\b|limbo|nowhere|abstract|black ?box|empty space", "void")]
TIME_WORDS = [(r"night|midnight|late|dark|\b(1[0-2]|[1-4]) ?(am|a\.m)", "night"), (r"dusk|evening|sunset", "dusk"),
              (r"morning|dawn|day|noon|lunch|afternoon", "day")]
EMOTE = [(r"\b(panic\w*|terrified|afraid|scared|dread\w*)\b", "fear"), (r"\b(worr\w*|anxious|nervous|tight\w*|stomach)\b", "worry"),
         (r"\b(tired|exhausted|yawn\w*|sleepy|slept (two|three) hours)\b", "sleepy"), (r"\b(sad|cr(y|ies|ied)|tears)\b", "sad"),
         (r"\b(angry|furious|snaps?)\b", "anger"), (r"\b(relie\w*|smiles?|laughs?|happy|better)\b", "joy"),
         (r"\b(surprised?|shocked|odd thing)\b", "surprise"), (r"\b(doubt\w*|unsure|not (yet )?knowing)\b", "doubt")]
HAND_ACTS = {"drink", "phone", "wave", "point", "laugh", "cry", "shrug", "nod", "cheer", "panic", "throw", "run", "jump", "fall", "crouch", "stand"}


def _negated(t, m, noun=False):
    """Words that are not an action happening now, in any script:
    "She never cooks" (negation), "like closing a door on a sleeping dog" (a simile), "an hour of sleep" / "some
    studies" (the verb used as a noun), "she used to cook" / "she could sleep" (not now)."""
    if not m:
        return False
    pre = t[:m.start()]
    if re.search(r"\b(never|not|no|don't|doesn't|didn't|won't|can't|cannot|without)\b(\W+\w+){0,2}\W*$", pre, re.I):
        return True
    if re.search(r"\b(like|as if|as though|as when)\b[^.,;:!?]*$", pre, re.I):
        return True
    if noun:              # an object named in a line: only negation and simile take it off screen
        return False
    if re.search(r"\b(of|some|enough|more|less|any|an|a)\W*$", pre, re.I):
        return True
    if re.search(r"\b(used to|could|would|should|might|wants? to|tries to|plans? to|dreams? of)\W*$", pre, re.I):
        return True
    # the viewer is the subject ("Would you run it back?", "Could you sleep?"): a question to the audience, not an action
    if re.search(r"\b(you|we)\s+(\w+\s+)?$", pre, re.I):
        return True
    # the subject is a THING, not a person: "the sun goes down", "the price rises", "time runs out", "the bus leaves"
    m2 = re.search(r"\b(the|a|an|his|her|their|its|my|your)\s+([a-z]+)\s*$", pre, re.I)
    if m2 and m2.group(2).lower() not in PEOPLE:
        return True
    if re.search(r"\b(time|money|sun|moon|night|day|rain|snow|wind|price|clock|car|bus|train|music|light|water|news)\s*$", pre, re.I):
        return True
    return False


PEOPLE = {"man", "woman", "boy", "girl", "kid", "child", "boss", "mom", "mum", "dad", "mother", "father", "friend", "teacher",
          "student", "doctor", "nurse", "cashier", "waiter", "driver", "neighbour", "neighbor", "stranger", "guard", "officer",
          "sister", "brother", "wife", "husband", "baby", "colleague", "coworker", "owner", "customer", "people", "crowd", "team"}


def _first(pats, text):
    for pat, val in pats:
        if re.search(pat, text, re.I):
            return val
    return None


def _style_of(st):
    k = (st.get("set") or {}) if isinstance(st, dict) else {}
    return k.get("style") if k.get("type", "room") == "room" else k.get("type")


def _is_room(st):
    return isinstance(st, dict) and isinstance(st.get("set"), dict) and st["set"].get("type", "room") == "room"


def _contents(st):
    if not isinstance(st, dict):
        return set()
    return {o.get("n") for o in st.get("objects", []) if o.get("t") == "furn"} | SETS.contents(st)


def _seq_items(spec):
    """-> [(scene, seq, list_key, index, cue_dict, setting_ids)]"""
    for sc in spec.get("scenes", []):
        for it in sc.get("shots", []):
            seq = it.get("sequence")
            if seq:
                sts = list(seq.get("settings") or ([seq["setting"]] if seq.get("setting") else []))
                for key in ("cues", "lines"):
                    for i, c in enumerate(seq.get(key, []) or []):
                        if isinstance(c, str):
                            c = seq[key][i] = {"t": c}
                        yield sc, seq, key, i, c, sts


def _lines_by_setting(spec):
    out = {}
    for sc, seq, key, i, c, sts in _seq_items(spec):
        sid = c.get("at") or (sts[i % len(sts)] if sts else None)
        if sid:
            out.setdefault(sid, []).append(c.get("t", ""))
    return out


def places(spec, log):
    desc = spec.get("setting_desc") or {}
    lines = _lines_by_setting(spec)
    for sid, st in list((spec.get("settings") or {}).items()):
        objs = st.get("objects", []) if isinstance(st, dict) else []
        if not isinstance(st, dict) or isinstance(st.get("set"), dict):
            continue
        name = f"{sid.replace('_', ' ')} {desc.get(sid, '')}"
        built = len(objs) >= 12 and (any(o.get("t") == "furn" for o in objs) or "sky" in st or "ground" in st)
        text = name + " " + " ".join(lines.get(sid, []))
        mood = _first(ABSTRACT, name)
        if mood and not built:
            # inside a mind / a dream / a memory: a dark stage with one pool of light and the objects the lines name
            named = [x for x in CAT.syn_find(text) if CAT.C[x]["zone"] != "surface" and x not in ("window", "door_frame")]
            new = {"set": {"type": "room", "style": "void", "mood": mood, "window": "none", "fg": False, "time": "night"},
                   "objects": [o for o in objs if o.get("t") == "furn"]}
            LAY.add(new, named[:5])
            for k in ("extras",):
                if k in st:
                    new[k] = st[k]
            new["look"] = st.get("look") or {"dream": "dream", "memory": "flashback"}.get(mood)
            if not new["look"]:
                new.pop("look")
            spec["settings"][sid] = new
            log.append(f"{sid}->void:{mood}" + (f"({','.join(named[:5])})" if named else ""))
            continue
        if STATE.search(name) or built:
            continue          # a place the author built on purpose (a ruined street, a barricaded flat): it stays
        time = _first(TIME_WORDS, name) or ("night" if "night" in sid else "day")
        keep = [o for o in objs if o.get("t") == "furn"]
        kind = _first(STYLE_WORDS, name)
        place = next((k for k, pat in CAT.PLACE_WORDS.items() if re.search(pat, name, re.I)), None)
        if kind:
            new = {"set": dict(kind, time=time), "objects": keep}; how = kind.get("style") or kind["type"]
        elif place and CAT.PLACES.get(place):
            new = {"set": {"type": "room", "style": "generic", "time": time, "place": place}, "objects": keep}
            LAY.add(new, CAT.PLACES[place]); how = place
        else:
            named = [x for x in CAT.syn_find(text) if CAT.C[x]["zone"] != "surface" and x not in ("window", "door_frame")]
            if not named:
                continue      # a place no word describes and no line furnishes: leave it, the lint says so
            new = {"set": {"type": "room", "style": "generic", "time": time}, "objects": keep}
            LAY.add(new, named); how = "generic(" + ",".join(named[:4]) + ")"
        for k in ("extras", "look"):
            if k in st:
                new[k] = st[k]
        spec["settings"][sid] = new
        log.append(f"{sid}->{how}")


def _ensure(spec, sid, names, n, explicit=False):
    """add catalog objects the setting lacks (only to dressed rooms; only what belongs there unless the line names it)."""
    st = (spec.get("settings") or {}).get(sid)
    if not _is_room(st):
        return []
    style = _style_of(st); have = _contents(st)
    want = [x for x in names if x not in have and (style == "generic" or CAT.plausible(x, style) or explicit)]
    if want:
        got = LAY.add(st, want); n["objects"] += len(got); return got
    return []


def beats(spec, log):
    settings = spec.get("settings") or {}
    kinds = {}
    for sid, st in settings.items():
        kinds.setdefault(_style_of(st) or sid, sid)
    n = {"at": 0, "do": 0, "objects": 0, "props": 0, "emote": 0}
    for sc, seq, key, i, c, sts in _seq_items(spec):
        t = c.get("t", "")
        if not t:
            continue
        # where: a line that says it happens in another kind of place goes there
        if not c.get("at"):
            cur = sts[i % len(sts)] if sts else None
            for pat, kind in STYLE_WORDS:
                m = re.search(pat, t, re.I)
                want = kind.get("style") or kind.get("type")
                if m and want in kinds and kinds[want] != cur and re.search(r"\b(in|at|to|into|inside|through)\b(\W+\w+){0,3}\W*$", t[:m.start()], re.I):
                    c["at"] = kinds[want]; n["at"] += 1
                    break
        sid = c.get("at") or (sts[i % len(sts)] if sts else None)
        st = settings.get(sid)
        style = _style_of(st)
        if isinstance(st, dict) and isinstance(st.get("look"), str) and not c.get("look"):
            c["look"] = st["look"]                                   # a dream/memory place carries its colour grade
        # objects the line names are on screen (if they belong in this place)
        named = [x for x in CAT.syn_find(t) if x not in ("window", "door_frame")]
        named = [x for x in named if not _negated(t, re.search(r"\b(" + CAT.C[x]["syn"] + r")\b", t, re.I), noun=True)]
        _ensure(spec, sid, named, n)
        have = _contents(st)
        # what the body does: verb -> affordance -> an object that offers it (present, else added)
        if not c.get("do"):
            acts = []
            for pat, aff, providers in CAT.VERBS:
                m = re.search(pat, t, re.I)
                if not m or _negated(t, m):
                    continue
                named_prov = [p for p in providers if p in named]
                prov = next((p for p in named_prov + providers if p in have), None)
                if prov and CAT.C.get(prov, {}).get("via") in have:
                    prov = CAT.C[prov]["via"]                    # the slides are pointed at from the podium
                if not prov and _is_room(st):
                    cand = named_prov or [p for p in providers if style == "generic" or CAT.plausible(p, style)]
                    if cand and _ensure(spec, sid, cand[:1], n, explicit=bool(named_prov)):
                        prov = cand[0]; have = _contents(st)
                if aff == "work":
                    acts.append("type")                          # coverage seats them at the desk/table (laptop if no screen)
                elif not prov:
                    if aff.startswith("use:") and aff.split(":")[1] in ("look", "point", "reach"):
                        acts.append(aff.split(":")[1])           # nowhere to do it: the gesture alone
                elif aff in ("sleep", "lie", "sit"):
                    acts.append(f"{aff}@{prov}")
                elif aff.startswith("use:"):
                    acts.append(f"use:{aff.split(':')[1]}@{prov}")
                elif aff == "stand":
                    acts.append(f"walkTo@{prov}")
                if aff == "sit" and any(re.search(p2, t, re.I) for p2, a2, _ in CAT.VERBS if a2 == "work"):
                    acts.append("type")                          # "sits down at her desk, opens the file"
                break
            if not acts:
                # no verb group matched, but the line names an object that is used by hand/eye ("reaches inside the fridge",
                # "stands at the washer"): use it by what the object's own data says (catalog aff "use")
                for x in named:
                    u = CAT.C[x].get("aff", {}).get("use")
                    if u and x in have and not re.search(r"\b(no|not|never|without)\b[^.,;]{0,12}\b" + CAT.C[x]["syn"] + r"\b", t, re.I):
                        acts.append(f"use:{u}@{x}"); break
            for pat, need in ACTION_NEEDS:                       # hands and face on top of the body action
                m = re.search(pat, t, re.I)
                if m and not _negated(t, m):
                    a = sorted(need)[0]
                    if "walkTo" in need:
                        if not acts:
                            acts.append("walk")
                    elif a in HAND_ACTS and a not in acts and not (a in ("stand", "fall") and acts):
                        acts.append(a)
            if not acts and re.search(r"\b(thinks?|wonders?|realis\w*|realiz\w*|remembers?)\b", t, re.I):
                acts.append("think")
            if acts:
                c["do"] = acts if len(acts) > 1 else acts[0]; n["do"] += 1
        if not c.get("props") and c.get("shot") != "insert":
            for pat, need in PROP_NEEDS:
                m = re.search(pat, t, re.I)
                if m and not _negated(t, m, noun=True):        # a prop is a noun: "a message" is on screen
                    pref = ["clock", "phone", "cash", "wallet", "document", "envelope", "key", "photo", "coffee"]
                    p = next((x for x in pref + sorted(need) if x in need and x in PROPS), None)
                    if p:
                        c["props"] = [p]; n["props"] += 1
                    break
        if not c.get("emote"):
            em = _first(EMOTE, t)
            if em:
                c["emote"] = em; n["emote"] += 1
    log.append(", ".join(f"{k} on {v} lines" if k != "objects" else f"{v} objects added" for k, v in n.items() if v))


def run(spec):
    log_p, log_b = [], []
    places(spec, log_p)
    beats(spec, log_b)
    msg = []
    if log_p:
        msg.append("places: " + ", ".join(log_p))
    if log_b and log_b[0]:
        msg.append("beats: " + log_b[0])
    if msg:
        print("autofill: " + "; ".join(msg))
    return spec


if __name__ == "__main__":
    import json
    import sys
    sp = run(json.load(open(sys.argv[1], encoding="utf-8")))
    if len(sys.argv) > 2:
        json.dump(sp, open(sys.argv[2], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
