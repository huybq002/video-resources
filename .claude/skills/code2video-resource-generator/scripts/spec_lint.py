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


# Openings that throw the first seconds away. 20 % of viewers leave in the first 10 s.
GREETING = re.compile(
    r"^\s*(hi|hey|hello|yo)\b|welcome (back|to)\b|in (this|today'?s) video\b|today (i|we|i'?m|we'?re)\b|"
    r"before we (start|begin)\b|don'?t forget to subscribe|like and subscribe|"
    r"xin chào|chào (các bạn|mọi người|mừng)|hôm nay (mình|chúng ta|chúng mình)|trong video (này|hôm nay)|"
    r"đừng quên (đăng ký|like)", re.I)

# A hook works by leaving something open. A question mark is the cheapest proof; these phrases count too.
OPEN_LOOP = re.compile(
    r"\?|what if\b|but first\b|by the end\b|you'?ll (see|understand|know|find)\b|find out\b|until\b|"
    r"nobody\b|no one\b|the reason\b|here'?s why\b|except\b|"
    r"điều gì (xảy ra|sẽ)|nhưng trước (hết|tiên)|cuối (video|phim)|bạn sẽ (hiểu|biết|thấy)|lý do\b|"
    r"cho đến khi\b|không ai\b|trừ\b", re.I)


def _cast(spec):
    return [c for c in spec.get("cast", []) if not c.get("narrator")]


def _timeline(spec):
    """-> [(scene, start_s, end_s, [cue text], shot count, [settings])] using scenes[].target_s."""
    rows, t = [], 0.0
    for sc in spec.get("scenes", []):
        d = float(sc.get("target_s") or 0)
        texts, shots, sets = [], 0, []
        for item in sc.get("shots", []):
            seq = item.get("sequence") or {}
            cues = list(seq.get("cues", [])) + list(seq.get("lines", [])) + list(item.get("cues") or [])
            texts += [c if isinstance(c, str) else c.get("t", "") for c in cues]
            shots += max(1, len(cues)) if seq else 1
            sets += [s for s in list(seq.get("settings", [])) + [seq.get("setting"), item.get("setting")] if s]
        rows.append((sc, t, t + d, texts, shots, sets))
        t += d
    return rows


def hook_and_ending(spec):
    """The first 30 s decide whether anyone sees the rest; the last scene decides the comments."""
    notes, rows = [], _timeline(spec)
    if not rows:
        return notes
    portrait = spec.get("aspect") == "9:16"
    first = rows[0][3]
    opening = next((t for t in first if t.strip()), "")
    cap = 10 if portrait else 14

    if float(rows[0][0].get("target_s") or 0) > 30:
        notes.append(f"WARNING: scene 1 lasts {rows[0][0].get('target_s')}s. The hook has to land inside 30 s: "
                     f"make scene 1 shorter (15-30 s) and move the rest into scene 2.")
    if GREETING.search(opening):
        notes.append(f"WARNING: the film opens with a greeting/filler ({opening[:46]!r}). Open on the strongest "
                     f"image, line or claim of the whole story instead; never 'welcome back' / 'xin chào'.")
    if opening and len(opening.split()) > cap:
        notes.append(f"WARNING: the first line is {len(opening.split())} words (max {cap} "
                     f"{'for 9:16: the hook must land in 1-3 s' if portrait else 'for the 0-5 s attention grab'}).")

    head = [t for sc, s0, s1, texts, _, _ in rows if s0 < 30 for t in texts]
    if head and not OPEN_LOOP.search(" ".join(head)):
        notes.append("WARNING: nothing is left open in the first 30 s: no question and no open loop. "
                     "Ask the question the film answers, or promise what the viewer will understand by the end "
                     "(references/youtube-craft.md).")
    shots30 = sum(n for sc, s0, s1, _, n, _ in rows if s0 < 30)
    want30 = 8 if portrait else 4
    if shots30 < want30:
        notes.append(f"WARNING: only {shots30} shot(s) in the first 30 s (want {want30}+): the picture has to change "
                     f"every {'2-3' if portrait else '5-8'} s or the viewer leaves. Add shots or cut to another place.")
    sets30 = {s for sc, s0, s1, _, _, ss in rows if s0 < 30 for s in ss}
    if len(sets30) < 2 and len(rows) > 2:
        notes.append("WARNING: the first 30 s never leave one place. Cut to a second setting inside the hook.")

    last = rows[-1][3]
    if last and "?" not in " ".join(last):
        notes.append("WARNING: the last scene asks the viewer nothing. End on a question they can answer in the "
                     "comments (it is the cheapest engagement there is).")
    return notes


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

    notes += hook_and_ending(spec)
    return notes


if __name__ == "__main__":
    import json
    import sys
    for line in lint(json.load(open(sys.argv[1], encoding="utf-8"))):
        print(line)
