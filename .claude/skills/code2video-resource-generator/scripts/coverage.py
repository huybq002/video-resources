"""Shot-coverage generator: expands `sequence` blocks in spec.json into many cinematic shots (master / medium / close-up / reaction / insert ...),
so a 10-minute film does not have to be authored shot by shot.

In spec.json a scene's `shots` list may contain items like
  {"sequence": {"type": "dialogue", "setting": "lib:cafe", "a": {"k": "an", "x": 620}, "b": {"k": "binh", "x": 1300, "flip": true},
                "lines": [{"who": "an", "t": "..."}, {"who": "binh", "t": "..."}], "mood": "warm|tense|sad|funny", "seed": 1}}
  {"sequence": {"type": "narration", "settings": ["lib:street_day", "lib:cafe"], "cues": ["...", "..."], "actors": [{"k": "an", "x": 700}], "mood": "warm"}}
`expand(spec, spec_dir)` returns a new spec with plain shots (cues may be {"t","who"}), resolves `lib:<name>` settings and relative setting paths.
"""
import copy, json, pathlib, random

SKILL = pathlib.Path(__file__).resolve().parent.parent
LIB = SKILL / "assets" / "settings-library"

def _sid(name):
    return "lib_" + name[4:] if isinstance(name, str) and name.startswith("lib:") else name

PORTRAIT = [False]
_base = lambda s: (s or "").split("__")[0]          # "bedroom__high" is the bedroom seen from another camera
HANDHELD = {"phone", "photo", "ticket", "card", "cash", "document", "envelope", "key", "wallet", "receipt", "newspaper",
            "calendar", "camera", "coins", "gift", "book", "letter", "laptop"}
NUM_WORDS = {w: i + 1 for i, w in enumerate("one two three four five six seven eight nine ten eleven twelve".split())}


def _time_in(text):
    """'set for six' / 'at 6:30' / 'two in the morning' -> '6:00' / '6:30' / '2:00' (for the clock face)"""
    import re as _re
    m = _re.search(r"\b(\d{1,2})(?::(\d{2}))\b", text) or _re.search(r"\b(\d{1,2})\s*(?:a\.?m|p\.?m|o'clock)", text, _re.I)
    if m:
        return f"{int(m.group(1))}:{(m.group(2) if m.lastindex and m.lastindex >= 2 and m.group(2) else '00')}"
    m = _re.search(r"\b(?:for|at|to|past|until|by)\s+(" + "|".join(NUM_WORDS) + r")\b", text, _re.I) or \
        _re.search(r"\b(" + "|".join(NUM_WORDS) + r")\s+(?:o'clock|in the morning|at night|a\.?m|p\.?m)", text, _re.I)
    return f"{NUM_WORDS[m.group(1).lower()]}:00" if m else None

def _actor(a, default_flip=False):
    x, by, s = a.get("x", 960), a.get("by", 905), a.get("s", 0.82)
    if PORTRAIT[0]: x, by, s = int(540 + (x - 960) * 0.62), a.get("by", 1560), round(s * 1.25, 2)   # sequences are authored in landscape coordinates
    d = {"k": a["k"], "x": x, "by": by, "s": s, "flip": a.get("flip", default_flip)}
    for k in ("glow", "enter", "tag"):
        if k in a: d[k] = a[k]
    return d

def _emote_for(text, mood, role):
    t = text.strip()
    if role == "listener":
        if t.endswith("?"): return "doubt"
        if t.endswith("!"): return {"warm": "joy", "tense": "fear", "sad": "sad", "funny": "surprise"}.get(mood, "surprise")
        return {"warm": "joy", "tense": "doubt", "sad": "sad", "funny": "smirk"}.get(mood, "neutral")
    if t.endswith("!"): return {"warm": "joy", "tense": "anger", "sad": "cry", "funny": "joy"}.get(mood, "joy")
    if t.endswith("?"): return "doubt" if mood in ("tense", "funny") else "neutral"
    return {"warm": "joy", "tense": "neutral", "sad": "sad", "funny": "smirk"}.get(mood, "neutral")

def _shot(setting, chars, **kw):
    s = {"setting": setting, "chars": copy.deepcopy(chars)}; s.update(kw)
    # Portrait frames are half as wide, and _actor already draws characters 1.25x bigger there.
    # Applying the landscape zoom on top fills the screen with a head and throws the setting away,
    # so ease every focus zoom back towards 1 in 9:16.
    if PORTRAIT[0] and isinstance(s.get("focus"), dict) and not s["focus"].get("face"):
        f = dict(s["focus"])
        for key in ("zoom", "to"):
            if isinstance(f.get(key), (int, float)): f[key] = round(1 + (f[key] - 1) * 0.55, 2)
        s["focus"] = f
    return s

def _face(k, kind="cu", push=False):
    """camera on the FACE (reference films: whoever speaks or feels something is seen big, head and shoulders):
    cu  - face close-up while speaking      ecu - eyes only, the shock / realisation beat
    mcu - head and chest                     push - a slow dolly in across the line (emotional lines)"""
    if PORTRAIT[0]: z = {"mcu": 1.8, "cu": 2.35, "ecu": 3.6}[kind]   # 9:16 people are drawn 1.25x already: these fill the tall frame
    else: z = {"mcu": 2.2, "cu": 3.2, "ecu": 5.0}[kind]
    f = {"k": k, "zoom": round(z * (0.82 if push else 1), 2), "to": round(z * (1.08 if push else 1.04), 2), "face": True}
    if kind == "ecu": f["dy"] = -8
    return f


def _set_acts(shot, k, acts):
    for c in shot["chars"]:
        if c["k"] == k: c.setdefault("acts", []).extend(acts)

def _face_each_other(sh, A, B):
    """two-shot staging from the reference films: both people in profile, turned toward each other."""
    for ch in sh["chars"]:
        other = B if ch["k"] == A["k"] else A
        if ch["k"] in (A["k"], B["k"]):
            ch["face"] = 1 if other["x"] > ch["x"] else -1


def dialogue(seq, rnd):
    A, B = _actor(seq["a"]), _actor(seq["b"], True)
    if "flip" not in seq["b"]: B["flip"] = True
    who = {A["k"]: (A, B, 1), B["k"]: (B, A, -1)}
    st = _sid(seq["setting"]); mood = seq.get("mood", "warm"); out = []
    for i, ln in enumerate(seq["lines"]):
        S, L, d = who[ln["who"]]; txt = ln["t"]; cue = {"t": txt, "who": ln["who"]}; n = len(txt.split())
        st = _sid(ln["at"]) if ln.get("at") else _sid(seq["setting"]); _mark = len(out)
        if i == 0 or seq.get("master_every") and i % seq["master_every"] == 0:
            sh = _shot(st, [A, B], cues=[cue], cam="push_slow", trans="fade" if i == 0 else "cut")
            _face_each_other(sh, A, B)
            if n > 10: _set_acts(sh, S["k"], [[0.8, "gesture", 1.4]])
            _set_acts(sh, L["k"], [[1.6, "nod"]])
            out.append(sh); _apply_beat(out[_mark:], ln, S["k"]); continue
        p = (i - 1 + seq.get("seed", 0)) % 4
        if p == 0:    # close-up of the speaker, then the listener's reaction
            cut = 0.58 if n > 5 else 0.7
            sh = _shot(st, [A, B], cues=[cue], focus=_face(S["k"], "cu", push=txt.rstrip().endswith(("!", "?"))), portion=[0, cut], trans="cut")
            _set_acts(sh, S["k"], [[0.0, "turn", 0.5 * d, 0.45], [0.2, "emote", _emote_for(txt, mood, "speaker")]])
            sh2 = _shot(st, [A, B], share=True, focus=_face(L["k"], "mcu"), portion=[cut, 1], trans="cut")
            _set_acts(sh2, L["k"], [[0.0, "turn", -0.45 * d, 0.45], [0.1, "emote", _emote_for(txt, mood, "listener")]])
            out += [sh, sh2]
        elif p == 1:  # over the listener's shoulder onto the speaker (the reference films' main dialogue framing)
            W_, H_ = (1080, 1920) if PORTRAIT[0] else (1920, 1080)
            fg = dict(L); left = L["x"] < S["x"]
            fg["x"] = int(W_ * (0.13 if left else 0.87)); fg["by"] = int(H_ * 1.1); fg["s"] = round(L.get("s", 0.82) * 2.0, 2)
            sh = _shot(st, [fg, S], cues=[cue], cam="push_slow", trans="cut")
            _set_acts(sh, L["k"], [[0.0, "view", "back", 1]])
            _set_acts(sh, S["k"], [[0.0, "turn", 0.3 * d, 0.4]] + ([[0.6, "gesture", 1.4]] if n > 12 else []))
            out.append(sh)
        elif p == 2:  # listener first (reaction), then speaker close-up
            sh = _shot(st, [A, B], cues=[cue], focus={"k": L["k"], "zoom": 2.4}, portion=[0, 0.3], trans="cut")
            _set_acts(sh, L["k"], [[0.0, "turn", -0.4 * d, 0.4], [0.0, "look", d, 0]])
            sh2 = _shot(st, [A, B], share=True, focus=_face(S["k"], "cu", push=True), portion=[0.3, 1], trans="cut")
            _set_acts(sh2, S["k"], [[0.0, "turn", 0.55 * d, 0.4], [0.2, "emote", _emote_for(txt, mood, "speaker")]])
            out += [sh, sh2]
        else:         # wide two-shot, camera drifts
            sh = _shot(st, [A, B], cues=[cue], cam=rnd.choice(["push_slow", "pan_left", "pan_right"]), trans="cut")
            _face_each_other(sh, A, B)
            _set_acts(sh, L["k"], [[1.4, "emote", _emote_for(txt, mood, "listener")]])
            out.append(sh)
        if n >= 7 and out and not out[-1].get("focus") and not out[-1].get("share"):
            # a master / two-shot / over-the-shoulder held for a whole line: cut in to the SPEAKER'S FACE for its second half
            first = out[-1]; first["portion"] = [0, 0.45]
            sh3 = _shot(st, [A, B], share=True, focus=_face(S["k"], "ecu" if ln.get("emote") in ("fear", "surprise", "shock", "anger") and n <= 9 else "cu",
                                                                push=txt.rstrip().endswith(("!", "?"))), portion=[0.45, 1], trans="cut")
            _set_acts(sh3, S["k"], [[0.0, "emote", ln.get("emote") or _emote_for(txt, mood, "speaker")]])
            out.append(sh3)
        if n > 16 and out:   # long line: add an insert/reaction cut in its second half
            last = out[-1]; last["portion"] = [last.get("portion", [0, 1])[0], 0.5] if not last.get("share") else last.get("portion", [0, 1])
        for sh_ in out[_mark:]:      # in every framing of a conversation the two turn toward each other (3/4), never to the lens
            if not sh_.get("chars"): continue
            _face_each_other(sh_, A, B)
        _apply_beat(out[_mark:], ln, S["k"])                                     # what the line says is happening
    return out

MOOD_ACTS = {"warm": ["nod", "wave", "gesture", "happy"], "tense": ["look", "worry", "think", "shake"], "sad": ["sad", "look", "think", "shrug"], "funny": ["shrug", "happy", "reach", "surprise"]}

BEAT_KEYS = ("at", "on", "shot", "focus", "do", "emote", "props", "crowd", "hud", "tag", "look", "spot", "angle", "plant", "payoff", "trans")

# actions the rig can play (scripts/engine.js ACT) and the words people actually write for them
KNOWN_ACTS = {"use", "breathe", "bend", "nod", "shake", "think", "worry", "relief", "lean", "sad", "surprise", "wave", "stir",
              "receive", "stamp", "point", "cheer", "laugh", "angry", "cry", "walk", "walkTo", "look", "reach", "shrug",
              "talk", "turn", "gesture", "happy", "heart", "glare", "normal", "offer",
              "sit", "stand", "run", "jump", "fall", "lie", "sleep", "pickup", "type", "text", "drink", "phone", "throw", "crouch", "panic"}
ACT_ALIASES = {"sits": "sit", "sitdown": "sit", "sit_down": "sit", "stands": "stand", "getup": "stand", "get_up": "stand",
               "runs": "run", "rush": "run", "sprint": "run", "jumps": "jump", "leap": "jump", "falls": "fall", "trip": "fall",
               "faint": "fall", "collapse": "fall", "liedown": "lie", "lie_down": "lie", "sleeps": "sleep", "nap": "sleep",
               "pick": "pickup", "pick_up": "pickup", "grab": "pickup", "types": "type", "typing": "type", "texts": "text", "texting": "text", "drinks": "drink",
               "sip": "drink", "call": "phone", "calls": "phone", "throws": "throw", "toss": "throw", "hide": "crouch",
              "duck": "crouch", "scream": "panic", "panics": "panic", "walks": "walkTo", "walkto": "walkTo", "walk_to": "walkTo",
               "nods": "nod", "waves": "wave", "points": "point", "laughs": "laugh", "cries": "cry", "shrugs": "shrug",
               "celebrate": "cheer", "cheers": "cheer", "thinks": "think", "worries": "worry", "reaches": "reach"}


PROP_SIZE = {"phone": .45, "coffee": .62, "cup": .62, "clock": .7, "document": .85, "letter": .7, "key": .35, "keys": .35,
             "wallet": .45, "money": .6, "book": .75, "laptop": 1.1, "bag": 1.0, "ticket": .55, "card": .4}

# pose held across cuts inside one scene: {char_key: {"pose": "lie"|"sit", "to": "bed", "setting": sid, "awake": bool}}
# and props left on furniture: {setting: [{"id", "at"}]}. Reset at every scene (expand()).
STATE = {"pose": {}, "left": {}}
SETTINGS = [{}, pathlib.Path(".")]
CAST_NAMES = {}     # key -> display name (expand() fills it): a line that names someone puts them in the shot


def _stage_line(beat, by_key, actors, W_):
    """Blocking for one narration line, BEFORE the shots are made (the same person, the same place, line after line):
    - "walkTo@ana" walks to stand beside Ana and face her (a person target, not only furniture);
    - "walkTo:600" never leaves the frame (clamped to 8-92 % of the width);
    - where someone ends a walk is where they stand on the next line (no snapping back to the start mark);
    - a person the line names ("...back to Ana") is in the shot even when "on" forgot them."""
    import re as _re
    beat = dict(beat)
    text = beat.get("t", "")
    on = list(beat["on"]) if beat.get("on") is not None else None
    named = [k for k, nm in CAST_NAMES.items() if k in by_key and nm and _re.search(r"\b%s\b" % _re.escape(nm), text)]
    if on is not None and _re.search(r"BSb(they|together|both|each other|the two)BSb".replace("BS", chr(92)), text, _re.I):
        on += [a_["k"] for a_ in actors if a_["k"] not in on]      # "they talk": everyone of the sequence is in the shot
    walker = beat.get("focus") or (on[0] if on else (actors[0]["k"] if actors else None))
    dos = [beat["do"]] if isinstance(beat.get("do"), str) else list(beat.get("do") or [])
    moved = {}
    lo, hi = 0.08 * W_, 0.92 * W_
    for j, d in enumerate(dos):
        d_, _, target = str(d).strip().partition("@")
        name, _, arg = d_.partition(":")
        if ACT_ALIASES.get(name.lower(), name) != "walkTo" or walker not in by_key:
            continue
        me = by_key[walker]
        if not target:      # "walks (back) to Ana" with a bare walkTo: the person named after "to" is where they go
            toward = [k for k in named if k != walker and _re.search(r"\b(to|toward|towards|over to|up to)\s+(\w+\s+)?%s\b" % _re.escape(CAST_NAMES[k]), text, _re.I)]
            if toward: target = toward[0]
        if target in by_key or target in {nm: k for k, nm in CAST_NAMES.items()}:
            tk = target if target in by_key else {nm: k for k, nm in CAST_NAMES.items()}[target]
            if tk not in by_key: continue
            tx = by_key[tk]["x"]; side = 1 if tx >= me["x"] else -1
            dest = tx - side * 250 * (me.get("s", 0.82) / 0.82)
            dest = max(lo, min(hi, dest)); dx = int(dest - me["x"])
            dos[j] = f"walkTo:{dx}"
            moved[walker] = dict(me, x=int(dest), flip=side < 0)
            moved[tk] = dict(by_key[tk], flip=side > 0)        # the one waiting turns to face the one arriving
            if on is not None and tk not in on: on.append(tk)
        elif not target:
            try: dx = float(arg or 300)
            except ValueError: continue
            dest = max(lo, min(hi, me["x"] + dx))
            for o_ in by_key.values():      # never walk into (through) someone standing there: stop beside them
                if o_["k"] != walker and (on is None or o_["k"] in on) and abs(dest - o_["x"]) < 230 * me.get("s", 0.82) / 0.82:
                    dest = o_["x"] + (230 if me["x"] > o_["x"] else -230) * me.get("s", 0.82) / 0.82
            dos[j] = f"walkTo:{int(dest - me['x'])}"
            moved[walker] = dict(me, x=int(dest), flip=dest < me["x"])
    if dos: beat["do"] = dos
    if walker in moved and not beat.get("focus"):
        beat["focus"] = walker          # the actions of the line belong to the one who walks, not to whoever the shot cycle picks
    if on is not None:
        for k in named:
            if k not in on: on.append(k)
        beat["on"] = on
    return beat, moved      # the spec's settings (expand() fills it) so a line can ask what furniture a place has


def _furniture(sid):
    """names of the furniture a setting has: {"desk", "computer", "chair", ...}"""
    v = SETTINGS[0].get(_base(sid or ""))
    if isinstance(v, str):
        try:
            p = pathlib.Path(v); v = json.load(open(p if p.is_absolute() else SETTINGS[1] / p, encoding="utf-8"))
        except Exception:
            return set()
    if not isinstance(v, dict):
        return set()
    names = {o.get("n") for o in v.get("objects", []) if isinstance(o, dict) and o.get("t") == "furn"}
    if isinstance(v.get("set"), dict):
        try:
            import sets as _sets
            names |= _sets.contents(v)
        except Exception:
            pass
    return names


# an action needs its object on screen: nobody types on air, drinks from nothing or talks into an empty hand.
#   type  -> sits at the desk/table of the place (laptop put on it when the place has no computer),
#            or types on a phone when there is nowhere to sit
#   drink -> a cup in the hand        phone -> a phone in the hand
# held items are drawn INSIDE the hand (build_project, "item"), so they follow the arm to the ear or the mouth.
ACT_ITEM = {"drink": "cup", "phone": "phone"}
HOLD_POSES = {"lie": ("lie", True), "sleep": ("lie", False), "sit": ("sit", True)}
BREAKS_HOLD = {"stand", "walkTo", "run", "walk", "jump", "fall"}


def _line_props(props, a):
    """props on a line: ids ("phone") or full dicts; ids are placed by the focus character's hand."""
    out = []
    W, H = (1080, 1920) if PORTRAIT[0] else (1920, 1080)
    for j, p in enumerate(props or []):
        if isinstance(p, dict):
            out.append(dict(p)); continue
        side = 1 if not a.get("flip") else -1
        x = (a["x"] if a else W / 2) + side * (95 + 130 * j) * (0.8 if PORTRAIT[0] else 1)
        y = (a["by"] if a else H * 0.8) - (330 if PORTRAIT[0] else 250)      # about hand height
        sc = (a.get("s", 0.82) if a else 0.82) / 0.82
        out.append({"id": p, "x": int(max(90, min(W - 90, x))), "y": int(y), "w": int((140 if PORTRAIT[0] else 115) * sc * PROP_SIZE.get(p, .7) * 1.5),
                    "t": 0.15 + 0.25 * j, "mode": "pop", "hand": a["k"] if a else None})
    return out


def _apply_beat(shots, cue, focus_key):
    """What the LINE says is happening goes on screen: actions, face, the objects it mentions, the crowd."""
    if not isinstance(cue, dict) or not shots:
        return
    acts = []
    t_at = 0.25
    anchor_set, placed = None, []
    for d in ([cue["do"]] if isinstance(cue.get("do"), str) else cue.get("do", [])):
        d, _, target = str(d).strip().partition("@")
        name, _, arg = d.partition(":")
        name = ACT_ALIASES.get(name.lower(), name)
        if target:      # the action uses a piece of furniture (anchors.py resolves where it is on screen)
            if name == "use":       # stand at its front, turned to it, hands busy: "use:stir@oven", "use:reach@washer"
                anchor_set = {"pose": "use", "to": target, "awake": True, "act": arg or "reach"}; continue
            if name in HOLD_POSES:
                pose, awake = HOLD_POSES[name]; anchor_set = {"pose": pose, "to": target, "awake": awake}; continue
            if name in ("place", "put", "leave", "pickup", "take"):
                mode = "place" if name in ("place", "put", "leave") else "take"
                acts.append([t_at, "reach", "r"]); placed.append({"id": arg or "phone", "at": target, "mode": mode, "t": round(t_at + 0.35, 2)})
                t_at += 1.1; continue
            if name == "walkTo":
                acts.append([t_at, "walkTo", "@" + target, None]); t_at += 1.6; continue
        if name not in KNOWN_ACTS:
            print(f"coverage: unknown action '{d}' skipped (known: {', '.join(sorted(KNOWN_ACTS))})"); continue
        if name == "walkTo": acts.append([t_at, "walkTo", int(float(arg or 300)), None])
        elif name == "run": acts.append([t_at, "run", int(float(arg or 520)), None])
        elif name == "look": acts.append([t_at, "look", float(arg or 1), 0])
        elif name == "turn": acts.append([t_at, "turn", float(arg or 0.5), 0.45])
        elif arg: acts.append([t_at, name, float(arg)])
        else: acts.append([t_at, name])
        t_at += 1.1          # several actions on one line play one after another, not on top of each other
    if cue.get("emote"): acts.append([0.15, "emote", cue["emote"]])
    fk = focus_key
    item = None
    names_ = {a_[1] for a_ in acts}
    if fk and names_ & {"type", "drink", "phone"}:
        furn = _furniture(shots[0].get("setting"))
        cue_props = {p if isinstance(p, str) else (p or {}).get("id") for p in (cue.get("props") or [])}
        held_ = anchor_set or (None if names_ & BREAKS_HOLD else STATE["pose"].get(fk))
        sitting = bool(held_ and held_.get("pose") == "sit")
        walking = any(a_[1] == "walkTo" for a_ in acts)
        if "drink" in names_ and not sitting and not walking and "chair" in furn and furn & {"table", "desk"}:
            anchor_set = {"pose": "sit", "to": "chair", "awake": True}; sitting = True     # a coffee at a cafe/kitchen is drunk sitting down
        if "type" in names_ and not cue_props & {"laptop", "phone", "computer", "tablet"}:
            work = sorted(furn & {"desk", "table"})
            if not sitting and not walking and "chair" in furn and work:
                anchor_set = {"pose": "sit", "to": "chair", "awake": True}; sitting = True
            if sitting and work and "computer" not in furn:
                left = STATE["left"].setdefault(_base(shots[0].get("setting")), [])
                if not any(l_["id"] == "laptop" for l_ in left):
                    left.append({"id": "laptop", "at": work[0], "hand": fk})
            elif not sitting or not work:
                item = "phone"      # nowhere to sit: texting on a phone held in front of the chest
                for a_ in acts:
                    if a_[1] == "type": a_[1] = "text"
        if "text" in {a_[1] for a_ in acts}:
            item = item or "phone"
        for nm, it in ACT_ITEM.items():
            if nm in names_ and not cue_props & ({"cup", "coffee", "mug"} if it == "cup" else {"phone"}):
                item = item or it
    if fk and not item and not placed:    # the line is about her phone / cup: whenever she is on screen she holds it
        lp_ = [p if isinstance(p, str) else (p or {}).get("id") for p in (cue.get("props") or [])]
        if "phone" in lp_: item = "phone"
        elif set(lp_) & {"coffee", "cup", "mug"}: item = "cup"
    if fk and any(a_[1] in BREAKS_HOLD for a_ in acts):
        STATE["pose"].pop(fk, None)
    walked = next((a_[2][1:] for a_ in acts if a_[1] == "walkTo" and isinstance(a_[2], str) and a_[2].startswith("@")), None)
    for sh in shots:      # continuity: a pose held from an earlier line, props left on furniture earlier in the scene
        for ch in sh.get("chars", []):
            held = STATE["pose"].get(ch["k"])
            if held and _base(held["setting"]) == _base(sh.get("setting")) and not ch.get("anchor") and ch.get("by", 0) < (1900 if PORTRAIT[0] else 1060):
                ch["anchor"] = dict(held)
        for lp in STATE["left"].get(_base(sh.get("setting")), []):
            sh.setdefault("props", []).append(dict(lp, mode="on"))
    if walked and fk:
        STATE["pose"][fk] = {"pose": "stand", "to": walked, "setting": shots[0].get("setting")}
        for sh in shots[1:]:      # later shots of the same line: already there
            for ch in sh.get("chars", []):
                if ch["k"] == fk: ch["anchor"] = {"pose": "stand", "to": walked}
    if anchor_set and fk:
        for sh in shots:
            for ch in sh.get("chars", []):
                if ch["k"] == fk: ch["anchor"] = dict(anchor_set)
        STATE["pose"][fk] = dict(anchor_set, setting=shots[0].get("setting"))
    for pl in placed:
        shots[0].setdefault("props", []).append(dict(pl, hand=fk))
        for sh_ in shots[1:]:     # the next angle of the same line: it is already where she put it (or already gone)
            if pl["mode"] == "place": sh_.setdefault("props", []).append({"id": pl["id"], "at": pl["at"], "mode": "on", "hand": fk})
        if pl["mode"] == "place":
            STATE["left"].setdefault(_base(shots[0].get("setting")), []).append({"id": pl["id"], "at": pl["at"]})
    for sh in shots:
        if item:
            for ch in sh.get("chars", []):
                if ch["k"] == fk: ch["item"] = item
        if acts and focus_key: _set_acts(sh, focus_key, copy.deepcopy(acts))
        if cue.get("crowd") is False: sh["crowd"] = None
        elif isinstance(cue.get("crowd"), dict): sh["crowd"] = copy.deepcopy(cue["crowd"])
    if cue.get("props") and not shots[0].get("props"):
        a = next((c for c in shots[0]["chars"] if c["k"] == focus_key), shots[0]["chars"][0] if shots[0]["chars"] else None)
        held_ids = {"phone"} if item == "phone" else ({"coffee", "cup", "mug"} if item == "cup" else set())
        lp_ = [p for p in cue["props"] if not (a and a["k"] == fk and (p if isinstance(p, str) else p.get("id")) in held_ids)]
        # only things a person can hold go in the hand: a calendar, a clock, a lightbulb, a chart is shown as an insert or
        # a HUD, never floating beside someone's hand (2026-11-09 audit: a calendar held on the sofa)
        lp_ = [p for p in lp_ if isinstance(p, dict) or (p in HANDHELD and p not in ("calendar", "laptop")) or p in ("coffee", "cup", "mug", "money", "cash", "coins", "book", "gift", "laptop")]
        shots[0]["props"] = _line_props(lp_, a)      # (an object already drawn in the hand is not floated beside it again)
    if isinstance(cue.get("tag"), dict):   # {"tag": {"lena": "LEVEL 2"}}: the label over a head changes on this line
        for sh in shots:
            for ch in sh.get("chars", []):
                if ch["k"] in cue["tag"]: ch["tag"] = cue["tag"][ch["k"]]
    if cue.get("hud") and any(isinstance(h, dict) and h.get("type") == "screen" for h in (cue["hud"] if isinstance(cue["hud"], list) else [cue["hud"]])):
        for sh in shots:
            if not sh.get("chars"): sh["props"] = [p_ for p_ in sh.get("props", []) if p_.get("id") not in ("phone", "laptop", "computer")]
    if cue.get("trans"): shots[0]["trans"] = cue["trans"]     # "power": flash + action lines + ripple on the moment a power fires
    # film looks (reference: flashbacks in warm sepia haze, night in cool blue, a single spotlight in the dark)
    for sh in shots:
        if cue.get("look"): sh["grade"] = cue["look"]
        if cue.get("spot"): sh["spot"] = True
        if cue.get("angle") in ("high", "low") and sh.get("chars"):
            sh["setting"] = f"{_base(sh['setting'])}__{cue['angle']}"
        if not sh.get("chars") and any(p_.get("id") in HANDHELD for p_ in sh.get("props", [])):
            sh["pov"] = focus_key      # first-person insert: the hand that holds it comes in from the frame edge
        if not sh.get("chars") and any(p_.get("id") == "clock" for p_ in sh.get("props", [])):
            tm = _time_in(cue.get("t", ""))
            if tm:                     # a clock face that shows the time the line says
                sh["props"] = [p_ for p_ in sh["props"] if p_.get("id") != "clock"]
                sh.setdefault("overlays", []).append({"type": "clock", "time": tm, "pos": "cc", "t": 0.1, "dur": 30})
    if cue.get("hud"):          # on-screen numbers, labels, title cards (chip / counter / burst / bubble / title)
        huds = cue["hud"] if isinstance(cue["hud"], list) else [cue["hud"]]
        shots[0].setdefault("overlays", []).extend(copy.deepcopy(h) for h in huds if isinstance(h, dict))


def narration(seq, rnd):
    settings = [_sid(s) for s in seq["settings"]]; mood = seq.get("mood", "warm")
    actors = [_actor(a, i % 2 == 1) for i, a in enumerate(seq.get("actors", []))]
    by_key = {a["k"]: a for a in actors}
    out = []; cycle = ["wide", "medium", "wide2", "cu", "wide", "medium"]   # 3 wide, 2 medium, 1 close-up: the setting stays on screen
    for i, text in enumerate(seq["cues"]):
        cue = text
        moved = {}
        if isinstance(cue, dict):
            cue, moved = _stage_line(cue, by_key, actors, (1080 if PORTRAIT[0] else 1920))
        beat = cue if isinstance(cue, dict) else {}
        st = settings[(i // len(cycle)) % len(settings)] if len(settings) > 1 else settings[0]
        if len(settings) > 1 and i % 3 == 0: st = settings[(i // 3) % len(settings)]
        if beat.get("at"): st = _sid(beat["at"])                                  # the line says where we are
        kind = cycle[(i + seq.get("seed", 0)) % len(cycle)]
        if i == 0 and not beat.get("shot"): kind = "establish"                   # every scene opens on the place
        kind = {"wide": "wide", "medium": "medium", "cu": "cu", "close": "cu", "establish": "establish",
                "insert": "insert", "ots": "ots"}.get(beat.get("shot"), kind)
        line_props = [x if isinstance(x, str) else x.get("id") for x in beat.get("props", []) or []]
        if kind == "insert" and not line_props: kind = "cu"
        pool = MOOD_ACTS.get(mood, MOOD_ACTS["warm"]); n = len((text if isinstance(text, str) else text["t"]).split())
        cast = actors
        if beat.get("on") is not None:                                            # the line says who is there
            cast = []
            for j, k in enumerate(beat["on"]):
                cast.append(by_key.get(k) or _actor({"k": k, "x": 700 + 520 * j}, j % 2 == 1))
        if not cast:
            sh = {"setting": st, "chars": [], "cues": [cue], "cam": rnd.choice(["push_slow", "pan_left", "pan_right", "pull"])}
            _apply_beat([sh], cue, None); out.append(sh); continue
        fk = beat.get("focus") or (beat.get("who") if beat.get("who") in [c["k"] for c in cast] else None) or cast[i % len(cast)]["k"]
        a = next(c for c in cast if c["k"] == fk) if fk in [c["k"] for c in cast] else cast[0]
        chars = cast
        W_, H_ = (1080, 1920) if PORTRAIT[0] else (1920, 1080)
        if kind == "establish":   # the place first: people small and further back, the set fills the frame (reference wides)
            small = [dict(c, s=round(c.get("s", 0.82) * 0.62, 2), by=int(H_ * (0.80 if PORTRAIT[0] else 0.78)),
                          x=int(W_ / 2 + (c.get("x", W_ / 2) - W_ / 2) * 0.6)) for c in chars]
            sh = _shot(st, small, cues=[cue], cam="push_slow", trans="fade" if i == 0 else "cut")
        elif kind == "insert":                                                   # the object fills the frame
            sh = {"setting": st, "chars": [], "cues": [cue], "cam": "push_slow", "dof": True, "trans": "cut",
                  "props": [{"id": line_props[0], "x": W_ // 2, "y": int(H_ * 0.58), "w": int(W_ * (0.5 if PORTRAIT[0] else 0.3)),
                             "t": 0.0, "mode": "static"}]}
        elif kind == "ots" and len(chars) >= 2:                                  # over the shoulder of the first, onto the second
            fg = dict(chars[0]); fg["x"] = int(W_ * 0.14); fg["by"] = int(H_ * 1.08); fg["s"] = round(fg.get("s", 0.82) * 1.9, 2)
            sh = _shot(st, [fg] + list(chars[1:]), cues=[cue], cam="push_slow", trans="cut")
        elif kind == "wide":
            sh = _shot(st, chars, cues=[cue], cam="pull", trans="cut" if i else "fade")
        elif kind == "medium":
            sh = _shot(st, chars, cues=[cue], focus={"k": a["k"], "zoom": 1.8, "dy": 40}, trans="cut")
        elif kind == "cu":
            sh = _shot(st, chars, cues=[cue], focus=_face(a["k"], "cu", push=True), trans="cut")
            if not beat.get("emote"):
                _set_acts(sh, a["k"], [[0.0, "turn", rnd.choice([-0.5, 0.5]), 0.45], [0.2, "emote", {"warm": "joy", "tense": "doubt", "sad": "sad", "funny": "smirk"}.get(mood, "neutral")]])
        else:
            sh = _shot(st, chars, cues=[cue], cam=rnd.choice(["pan_left", "pan_right"]), trans="cut", sway=True)
        if not beat.get("do") and kind not in ("insert",) and rnd.random() < 0.35:
            # Act small, like the reference films: a look, a nod, a thought - never a random walk across the room
            # (an unmotivated walkTo made people wander off mid-sentence). Most shots just breathe and blink.
            _set_acts(sh, a["k"], [[rnd.choice([0.4, 0.8]), rnd.choice(["look", "nod", "think"] if mood != "warm" else ["look", "nod", "happy"])]])
        made = [sh]
        out.append(sh)
        if line_props and kind not in ("insert",) and not beat.get("shot") and n >= 8:
            # the line names an object: cut to it in the second half (insert), like the reference films do
            first = out[-1]; first["portion"] = [0, 0.55]
            ins = {"setting": st, "chars": [], "share": True, "portion": [0.55, 1], "cam": "push_slow", "dof": True, "trans": "cut",
                   "props": [{"id": line_props[0], "x": W_ // 2, "y": int(H_ * 0.58), "w": int(W_ * (0.5 if PORTRAIT[0] else 0.3)),
                              "t": 0.0, "mode": "static"}]}
            out.append(ins)
        elif (n > 9 or (n >= 6 and kind in ("wide", "establish", "wide2"))) and not ({str(d).split(':')[0] for d in ([beat.get('do')] if isinstance(beat.get('do'), str) else beat.get('do') or [])}
                            & {'sleep', 'lie', 'fall'}):   # long cue: cut to a second angle halfway (not while lying: the close-up would miss her) (was 13 words: shots ran 7.9 s on average)
            first = out[-1]; first["portion"] = [0, 0.5]
            t_ = text if isinstance(text, str) else text.get("t", "")
            feels = beat.get("emote") or t_.rstrip().endswith(("!", "?")) or '"' in t_ or "“" in t_
            big = beat.get("emote") in ("fear", "surprise", "shock", "anger") and n <= 10
            fz = _face(a["k"], "ecu" if big else ("cu" if feels else "mcu"), push=bool(feels))
            sh2 = _shot(st, chars, share=True, portion=[0.5, 1], focus=fz, trans="cut"); _set_acts(sh2, a["k"], [[0.0, "look", rnd.choice([-1, 1]), 0]])
            out.append(sh2); made.append(sh2)
        _apply_beat(made, cue, a["k"])
        for sh_ in made[1:]:                # the second angle of the same line: already arrived, not walking it again
            for ch in sh_.get("chars", []):
                if ch["k"] in moved and any(a_[1] == "walkTo" and not isinstance(a_[2], str) for a_ in ch.get("acts", [])):
                    ch["x"] = moved[ch["k"]]["x"]; ch["flip"] = moved[ch["k"]].get("flip", ch.get("flip"))
                    ch["acts"] = [a_ for a_ in ch["acts"] if a_[1] != "walkTo"]
        for k, v in moved.items():          # where the walk ended is where they stand on the next line
            by_key[k] = v
            actors[:] = [v if x_["k"] == k else x_ for x_ in actors]
    return out


def _cinematic_pass(shots):
    """Editing grammar on the finished shot list of ONE scene (short-film-craft.md):
    - 30-degree rule: two cuts in a row on the same person at (nearly) the same size read as a jump cut. The second
      one is pushed to a clearly different size (wider or tighter by >= 0.7 zoom) or turned to the other side.
    - eyeline match: an insert of an object is preceded by the person LOOKING at it (a look act in the shot before),
      so the cut shows what they see instead of an object that appears from nowhere.
    - the last shot of a scene is a slow push (a held beat) unless the author chose a camera move."""
    W_ = 1080 if PORTRAIT[0] else 1920
    for i, sh in enumerate(shots):
        f = sh.get("focus") if isinstance(sh.get("focus"), dict) else None
        if i and f and not sh.get("share"):
            pf = shots[i - 1].get("focus") if isinstance(shots[i - 1].get("focus"), dict) else None
            if pf and pf.get("k") == f.get("k") and abs(float(pf.get("zoom", 1)) - float(f.get("zoom", 1))) < 0.7 and not f.get("fixed"):
                z = float(f.get("zoom", 1)); f["zoom"] = round(z - 0.9 if z > 2.0 else z + 0.9, 2)
                if isinstance(f.get("to"), (int, float)): f["to"] = round(f["zoom"] * 1.07, 2)
        if sh.get("props") and not sh.get("chars") and i:
            prev = shots[i - 1]
            for c in prev.get("chars", []):
                if prev.get("share") or c.get("acts") and any(a[1] == "look" for a in c["acts"]):
                    continue
                if not (sh.get("props") or [{}])[0].get("pov") and c is prev["chars"][0]:
                    c.setdefault("acts", []).append([0.1, "look", 1 if c.get("x", W_ / 2) < W_ / 2 else -1, 0])
    if shots and not shots[-1].get("cam") and not shots[-1].get("focus"):
        shots[-1]["cam"] = "push_slow"
    return shots

EXPAND = {"dialogue": dialogue, "narration": narration}

def expand(spec, spec_dir):
    spec = copy.deepcopy(spec); spec_dir = pathlib.Path(spec_dir); PORTRAIT[0] = spec.get("aspect", "16:9") == "9:16"
    settings = dict(spec.get("settings", {})); SETTINGS[0] = settings; SETTINGS[1] = spec_dir
    CAST_NAMES.clear(); CAST_NAMES.update({c["id"]: c.get("name") for c in spec.get("cast", []) if not c.get("narrator")})
    def reg(name):
        sid = _sid(name)
        if name.startswith("lib:"): settings[sid] = str(LIB / (name[4:] + ".json"))
        return sid
    for sc in spec["scenes"]:
        STATE["pose"].clear(); STATE["left"].clear()
        shots = []
        for item in sc["shots"]:
            if "sequence" in item:
                seq = item["sequence"]; rnd = random.Random(seq.get("seed", 1))
                for key in ("setting",):
                    if key in seq: reg(seq[key])
                for s in seq.get("settings", []): reg(s)
                for ln in list(seq.get("cues", [])) + list(seq.get("lines", [])):      # per-line "at"
                    if isinstance(ln, dict) and isinstance(ln.get("at"), str): reg(ln["at"])
                made = EXPAND[seq["type"]](seq, rnd)
                # a `crowd` / `props` / `overlays` block on the sequence applies to every shot it makes
                # (build_project reads them per shot; without this they would be silently dropped)
                for key in ("crowd", "props", "overlays"):
                    if seq.get(key) is not None:
                        for sh in made: sh.setdefault(key, copy.deepcopy(seq[key]))
                shots += made
            else:
                if "setting" in item and isinstance(item["setting"], str) and item["setting"].startswith("lib:"): item["setting"] = reg(item["setting"])
                for pn in item.get("split", []):
                    if pn["setting"].startswith("lib:"): pn["setting"] = reg(pn["setting"])
                shots.append(item)
        sc["shots"] = _cinematic_pass(shots)
    for sc in spec["scenes"]:     # camera-angle variants share the base setting, with another camera (generate.py)
        for sh in sc["shots"]:
            sid = sh.get("setting") or ""
            if "__" in sid and sid not in settings and _base(sid) in settings:
                b = settings[_base(sid)]
                settings[sid] = dict(b, _angle=sid.split("__")[1]) if isinstance(b, dict) else {"_lib": b, "_angle": sid.split("__")[1]}
    for k, v in list(settings.items()):
        if isinstance(v, str) and not pathlib.Path(v).is_absolute(): settings[k] = str((spec_dir / v).resolve())
    spec["settings"] = settings
    return spec

if __name__ == "__main__":
    import sys
    sp = json.load(open(sys.argv[1], encoding="utf-8")); ex = expand(sp, pathlib.Path(sys.argv[1]).parent)
    n = sum(len(s["shots"]) for s in ex["scenes"]); print("shots after expansion:", n)
