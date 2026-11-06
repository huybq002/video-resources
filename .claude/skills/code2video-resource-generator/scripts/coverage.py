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

def _actor(a, default_flip=False):
    x, by, s = a.get("x", 960), a.get("by", 905), a.get("s", 0.82)
    if PORTRAIT[0]: x, by, s = int(540 + (x - 960) * 0.62), a.get("by", 1560), round(s * 1.25, 2)   # sequences are authored in landscape coordinates
    d = {"k": a["k"], "x": x, "by": by, "s": s, "flip": a.get("flip", default_flip)}
    for k in ("glow", "enter"):
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
    s = {"setting": setting, "chars": copy.deepcopy(chars)}; s.update(kw); return s

def _set_acts(shot, k, acts):
    for c in shot["chars"]:
        if c["k"] == k: c.setdefault("acts", []).extend(acts)

def dialogue(seq, rnd):
    A, B = _actor(seq["a"]), _actor(seq["b"], True)
    if "flip" not in seq["b"]: B["flip"] = True
    who = {A["k"]: (A, B, 1), B["k"]: (B, A, -1)}
    st = _sid(seq["setting"]); mood = seq.get("mood", "warm"); out = []
    for i, ln in enumerate(seq["lines"]):
        S, L, d = who[ln["who"]]; txt = ln["t"]; cue = {"t": txt, "who": ln["who"]}; n = len(txt.split())
        if i == 0 or seq.get("master_every") and i % seq["master_every"] == 0:
            sh = _shot(st, [A, B], cues=[cue], cam="push_slow", trans="fade" if i == 0 else "cut")
            _set_acts(sh, S["k"], [[0.5, "turn", 0.2 * d, 0.5], [0.8, "gesture", 3]]); _set_acts(sh, L["k"], [[0.3, "look", d, 0], [1.6, "nod"]])
            out.append(sh); continue
        p = (i - 1 + seq.get("seed", 0)) % 4
        if p == 0:    # close-up of the speaker, then the listener's reaction
            cut = 0.58 if n > 5 else 0.7
            sh = _shot(st, [A, B], cues=[cue], focus={"k": S["k"], "zoom": 2.7}, portion=[0, cut], trans="cut")
            _set_acts(sh, S["k"], [[0.0, "turn", 0.5 * d, 0.45], [0.2, "emote", _emote_for(txt, mood, "speaker")]])
            sh2 = _shot(st, [A, B], share=True, focus={"k": L["k"], "zoom": 2.5}, portion=[cut, 1], trans="cut")
            _set_acts(sh2, L["k"], [[0.0, "turn", -0.45 * d, 0.45], [0.1, "emote", _emote_for(txt, mood, "listener")]])
            out += [sh, sh2]
        elif p == 1:  # medium close-up on the speaker with hands
            sh = _shot(st, [A, B], cues=[cue], focus={"k": S["k"], "zoom": 1.85, "dy": 40}, trans="cut")
            _set_acts(sh, S["k"], [[0.0, "turn", 0.3 * d, 0.4], [0.5, "gesture", 3]]); _set_acts(sh, L["k"], [[0.3, "look", d, 0]])
            out.append(sh)
        elif p == 2:  # listener first (reaction), then speaker close-up
            sh = _shot(st, [A, B], cues=[cue], focus={"k": L["k"], "zoom": 2.4}, portion=[0, 0.3], trans="cut")
            _set_acts(sh, L["k"], [[0.0, "turn", -0.4 * d, 0.4], [0.0, "look", d, 0]])
            sh2 = _shot(st, [A, B], share=True, focus={"k": S["k"], "zoom": 2.9, "to": 3.1}, portion=[0.3, 1], trans="cut")
            _set_acts(sh2, S["k"], [[0.0, "turn", 0.55 * d, 0.4], [0.2, "emote", _emote_for(txt, mood, "speaker")]])
            out += [sh, sh2]
        else:         # wide two-shot, camera drifts
            sh = _shot(st, [A, B], cues=[cue], cam=rnd.choice(["pan_left", "pan_right", "push"]), trans="cut", sway=True)
            _set_acts(sh, S["k"], [[0.4, "gesture", 3]]); _set_acts(sh, L["k"], [[0.2, "look", d, 0], [1.4, "emote", _emote_for(txt, mood, "listener")]])
            out.append(sh)
        if n > 16 and out:   # long line: add an insert/reaction cut in its second half
            last = out[-1]; last["portion"] = [last.get("portion", [0, 1])[0], 0.5] if not last.get("share") else last.get("portion", [0, 1])
    return out

MOOD_ACTS = {"warm": ["nod", "wave", "gesture", "happy"], "tense": ["look", "worry", "think", "shake"], "sad": ["sad", "look", "think", "shrug"], "funny": ["shrug", "happy", "reach", "surprise"]}

def narration(seq, rnd):
    settings = [_sid(s) for s in seq["settings"]]; mood = seq.get("mood", "warm")
    actors = [_actor(a, i % 2 == 1) for i, a in enumerate(seq.get("actors", []))]
    out = []; cycle = ["wide", "medium", "cu", "wide2", "medium", "cu"]
    for i, text in enumerate(seq["cues"]):
        st = settings[(i // len(cycle)) % len(settings)] if len(settings) > 1 else settings[0]
        if len(settings) > 1 and i % 3 == 0: st = settings[(i // 3) % len(settings)]
        kind = cycle[(i + seq.get("seed", 0)) % len(cycle)]; cue = text if not isinstance(text, dict) else text
        pool = MOOD_ACTS.get(mood, MOOD_ACTS["warm"]); n = len((text if isinstance(text, str) else text["t"]).split())
        if not actors:
            out.append({"setting": st, "chars": [], "cues": [cue], "cam": rnd.choice(["push_slow", "pan_left", "pan_right", "pull"])}); continue
        a = actors[i % len(actors)]
        chars = actors if kind in ("wide", "wide2") or len(actors) == 1 else actors
        if kind == "wide":
            sh = _shot(st, chars, cues=[cue], cam="pull", trans="cut" if i else "fade")
        elif kind == "medium":
            sh = _shot(st, chars, cues=[cue], focus={"k": a["k"], "zoom": 1.8, "dy": 40}, trans="cut")
        elif kind == "cu":
            sh = _shot(st, chars, cues=[cue], focus={"k": a["k"], "zoom": 2.6}, trans="cut")
            _set_acts(sh, a["k"], [[0.0, "turn", rnd.choice([-0.5, 0.5]), 0.45], [0.2, "emote", {"warm": "joy", "tense": "doubt", "sad": "sad", "funny": "smirk"}.get(mood, "neutral")]])
        else:
            sh = _shot(st, chars, cues=[cue], cam=rnd.choice(["pan_left", "pan_right"]), trans="cut", sway=True)
        if kind in ("wide", "wide2") and rnd.random() < 0.5:
            _set_acts(sh, a["k"], [[0.3, "walkTo", rnd.choice([-1, 1]) * rnd.choice([220, 300, 380]), None]])
        elif kind != "cu": _set_acts(sh, a["k"], [[rnd.choice([0.3, 0.6, 1.0]), rnd.choice(pool)]])
        out.append(sh)
        if n > 13:   # long cue: cut to a second angle halfway
            first = out[-1]; first["portion"] = [0, 0.5]
            sh2 = _shot(st, chars, share=True, portion=[0.5, 1], focus={"k": a["k"], "zoom": 2.3}, trans="cut"); _set_acts(sh2, a["k"], [[0.0, "emote", {"warm": "joy", "tense": "worry", "sad": "sad", "funny": "surprise"}.get(mood, "neutral")] if False else [0.0, "look", rnd.choice([-1, 1]), 0]])
            out.append(sh2)
    return out

EXPAND = {"dialogue": dialogue, "narration": narration}

def expand(spec, spec_dir):
    spec = copy.deepcopy(spec); spec_dir = pathlib.Path(spec_dir); PORTRAIT[0] = spec.get("aspect", "16:9") == "9:16"
    settings = dict(spec.get("settings", {}))
    def reg(name):
        sid = _sid(name)
        if name.startswith("lib:"): settings[sid] = str(LIB / (name[4:] + ".json"))
        return sid
    for sc in spec["scenes"]:
        shots = []
        for item in sc["shots"]:
            if "sequence" in item:
                seq = item["sequence"]; rnd = random.Random(seq.get("seed", 1))
                for key in ("setting",):
                    if key in seq: reg(seq[key])
                for s in seq.get("settings", []): reg(s)
                shots += EXPAND[seq["type"]](seq, rnd)
            else:
                if "setting" in item and isinstance(item["setting"], str) and item["setting"].startswith("lib:"): item["setting"] = reg(item["setting"])
                for pn in item.get("split", []):
                    if pn["setting"].startswith("lib:"): pn["setting"] = reg(pn["setting"])
                shots.append(item)
        sc["shots"] = shots
    for k, v in list(settings.items()):
        if isinstance(v, str) and not pathlib.Path(v).is_absolute(): settings[k] = str((spec_dir / v).resolve())
    spec["settings"] = settings
    return spec

if __name__ == "__main__":
    import sys
    sp = json.load(open(sys.argv[1], encoding="utf-8")); ex = expand(sp, pathlib.Path(sys.argv[1]).parent)
    n = sum(len(s["shots"]) for s in ex["scenes"]); print("shots after expansion:", n)
