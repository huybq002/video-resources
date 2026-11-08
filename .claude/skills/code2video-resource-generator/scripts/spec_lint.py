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


# ---- lines must match what is on screen --------------------------------------------------------------
# A word in the line -> what must be visible for that line: furniture in its setting, or a prop.
PLACE_NEEDS = [
    (r"\b(sleeps|slept|sleeping|asleep|in bed|to bed|bed|bedroom|naps?|napping|insomnia|pillow|lies? awake|lay awake|wakes? up|woke( up)?)\b|đang ngủ|đi ngủ|giường|phòng ngủ", {"bed"}, "a bed"),
    (r"\b(kitchen|cook\w*|oven|bak(e|ed|ing)|fridge|stove)\b|nhà bếp|nấu|lò nướng|tủ lạnh", {"oven", "kitchen_counter", "fridge"}, "a kitchen (oven / counter / fridge)"),
    (r"\b(office|desk|boss|meeting|spreadsheet|inbox|work(ed|ing)? late)\b|văn phòng|bàn làm việc|sếp|cuộc họp", {"desk", "computer"}, "a desk or a computer"),
    (r"\b(shop|store|supermarket|cashier|checkout|aisle)\b|cửa hàng|siêu thị|thu ngân", {"shop_counter", "shelf_goods"}, "a shop counter or shelves"),
    (r"\b(sofa|couch|television|tv)\b|ghế sofa|ti vi|tivi", {"sofa", "tv"}, "a sofa or a TV"),
    (r"\b(classroom|whiteboard|lecture)\b|lớp học|bảng trắng", {"whiteboard"}, "a whiteboard"),
    (r"\b(library|bookshelf|bookshelves)\b|thư viện|giá sách", {"bookshelf"}, "a bookshelf"),
    (r"\b(drive|drove|driving|car|traffic)\b|lái xe|ô tô|xe hơi", {"car"}, "a car"),
    (r"\b(window|stares? out|looks? out)\b|cửa sổ", {"window", "night_window"}, "a window"),
]
PROP_NEEDS = [
    (r"\b(phone|texts?|texted|messaged?|notifications?|rang|buzz\w*)\b|điện thoại|tin nhắn", {"phone"}),
    (r"\b(laptop)\b|máy tính xách tay", {"laptop"}),
    (r"\b(coffee|latte|espresso)\b|cà phê", {"coffee"}),
    (r"\b(cash|banknotes?|dollars?|bucks|salary|paycheck|paid)\b|tiền mặt|lương", {"cash", "coins", "moneybag", "wallet", "card"}),
    (r"\b(credit card|debit card|card declined)\b|thẻ tín dụng", {"card"}),
    (r"\b(coins?|small change)\b|đồng xu", {"coins"}),
    (r"\b(savings?|piggy bank|saved up)\b|tiết kiệm|heo đất", {"piggybank", "coins", "moneybag"}),
    (r"\b(receipts?|invoices?|bills?)\b|hóa đơn", {"receipt", "document"}),
    (r"\b(stock|shares?|price) (rose|soared|went up|doubled)\b|tăng giá", {"chart_up"}),
    (r"\b(crash\w*|plunged|plummet\w*|lost (half|everything)|went down)\b|sụp đổ|mất trắng", {"chart_down"}),
    (r"\b(clock|o'clock|midnight|deadline)\b|đồng hồ|nửa đêm|hạn chót", {"clock", "calendar", "wall_clock"}),
    (r"\b(calendar|monday|tuesday|wednesday|thursday|friday|weekend)\b|lịch|thứ hai", {"calendar"}),
    (r"\b(idea|realis(e|ed|es)|realiz(e|ed|es)|figured (it )?out|it clicked)\b|ý tưởng|nhận ra", {"lightbulb"}),
    (r"\b(letter|envelope|mail)\b|lá thư|phong bì", {"envelope"}),
    (r"\b(keys?|unlock\w*)\b|chìa khóa", {"key", "lock"}),
    (r"\b(photo(graph)?s?|picture of)\b|bức ảnh|tấm ảnh", {"photo", "camera", "picture"}),
    (r"\b(document|contract|report|form|paperwork)\b|tài liệu|hợp đồng|báo cáo", {"document"}),
    (r"\b(newspaper|headline)\b|tờ báo", {"newspaper"}),
    (r"\b(gift|present for)\b|món quà", {"gift"}),
    (r"\b(wallet)\b|ví tiền|cái ví", {"wallet"}),
    (r"\b(shopping|shopping bags?)\b|mua sắm", {"shopping_bag"}),
    (r"\b(pizza)\b", {"pizza"}),
    (r"\b(book|novel)\b|cuốn sách|quyển sách", {"book", "bookshelf"}),
]
# verbs in the line -> the action the character must perform on that line (beat "do")
ACTION_NEEDS = [
    (r"\b(sits?|sat|sitting|takes a seat)\b|ngồi", {"sit"}),
    (r"\b(stands? up|gets? up|got up|rises)\b|đứng dậy", {"stand"}),
    (r"\b(runs?|ran|running|rushes|rushed|sprints?|races? (to|out|home))\b|chạy", {"run"}),
    (r"\b(jumps?|jumped|leaps?|leapt)\b|nhảy", {"jump"}),
    (r"\b(falls? (down|over|asleep)?|fell|trips?|tripped|collapses?|collapsed|faints?|fainted)\b|ngã|té|ngất", {"fall", "lie", "sleep"}),
    (r"\b(lies? down|lay down|goes to bed|went to bed|falls asleep|fell asleep|asleep|sleeping)\b|nằm|đi ngủ|ngủ thiếp", {"lie", "sleep"}),
    (r"\b(walks?|walked|walking|steps? (in|out|into|over)|heads? (to|for|home)|crosses)\b|đi bộ|bước", {"walkTo", "walk", "run"}),
    (r"\b(picks? up|picked up|grabs?|grabbed)\b|nhặt|chộp", {"pickup", "reach"}),
    (r"\b(types?|typed|typing)\b|gõ phím", {"type"}),
    (r"\b(drinks?|drank|sips?|sipped)\b|uống|nhấp", {"drink"}),
    (r"\b(calls? (him|her|them|back|home)|on the phone|answers? the phone|picks up the phone)\b|gọi điện|nghe máy", {"phone"}),
    (r"\b(throws?|threw|tosses|tossed|hurls?)\b|ném|quăng", {"throw"}),
    (r"\b(hides?|hid|hiding|ducks?|ducked|crouch\w*)\b|trốn|nấp", {"crouch"}),
    (r"\b(panics?|panicked|screams?|screamed)\b|hoảng|la hét", {"panic"}),
    (r"\b(waves?|waved)\b|vẫy tay", {"wave"}),
    (r"\b(points? at|pointed at)\b|chỉ tay", {"point"}),
    (r"\b(laughs?|laughed)\b|cười lớn", {"laugh"}),
    (r"\b(cries|cried|crying|sobs?|in tears)\b|khóc", {"cry"}),
    (r"\b(shrugs?|shrugged)\b|nhún vai", {"shrug"}),
    (r"\b(nods?|nodded)\b|gật đầu", {"nod"}),
    (r"\b(cheers?|celebrates?|celebrated)\b|ăn mừng|reo hò", {"cheer"}),
]
ACT_WORDS = {"sits": "sit", "sitdown": "sit", "stands": "stand", "getup": "stand", "runs": "run", "rush": "run", "sprint": "run",
             "jumps": "jump", "leap": "jump", "falls": "fall", "trip": "fall", "faint": "fall", "collapse": "fall",
             "liedown": "lie", "sleeps": "sleep", "nap": "sleep", "pick": "pickup", "grab": "pickup", "types": "type",
             "typing": "type", "drinks": "drink", "sip": "drink", "call": "phone", "calls": "phone", "throws": "throw",
             "toss": "throw", "hide": "crouch", "duck": "crouch", "scream": "panic", "walks": "walkTo", "walkto": "walkTo"}


def _beat_acts(beat):
    out = set()
    for d in ([beat["do"]] if isinstance(beat.get("do"), str) else beat.get("do", []) or []):
        n = str(d).split(":")[0].strip()
        out.add(ACT_WORDS.get(n.lower(), n))
    return out


# library settings and what they contain
LIB_HAS = {"bedroom_night": {"bed", "window", "night_window"}, "office": {"desk", "computer"},
           "cafe": {"table", "coffee"}, "street_day": {"car", "building"}, "park_dusk": {"bench"},
           "rooftop_night": {"building"}}


def _setting_has(spec, sid):
    if not sid:
        return set()
    if str(sid).startswith("lib:"):
        return LIB_HAS.get(str(sid)[4:], set())
    st = spec.get("settings", {}).get(sid)
    if isinstance(st, dict):
        import sets
        return {o.get("n") for o in st.get("objects", []) if o.get("t") == "furn"} | sets.contents(st)
    return set()


def script_visual_match(spec):
    """Every line that names a place or an object must be shot where that place or object is visible."""
    notes, misses = [], []
    for sc in spec.get("scenes", []):
        for item in sc.get("shots", []):
            seq = item.get("sequence")
            if not seq:
                continue
            seq_sets = [x for x in list(seq.get("settings", [])) + [seq.get("setting")] if x]
            seq_props = {p if isinstance(p, str) else p.get("id") for p in seq.get("props", []) or []}
            lines = list(seq.get("cues", [])) + list(seq.get("lines", []))
            bare_run, last_state, beats = 0, None, 0
            for li, ln in enumerate(lines, 1):
                text = ln if isinstance(ln, str) else ln.get("t", "")
                beat = ln if isinstance(ln, dict) else {}
                has_beat = any(k in beat for k in ("at", "on", "do", "emote", "props", "shot"))
                beats += 1 if has_beat else 0
                sets = [beat["at"]] if beat.get("at") else seq_sets
                have = set().union(*[_setting_has(spec, x) for x in sets]) if sets else set()
                props = seq_props | {p if isinstance(p, str) else p.get("id") for p in beat.get("props", []) or []}
                where = f"scene {sc.get('id')} line {li} ({text[:42]!r})"
                for rx, need, what in PLACE_NEEDS:
                    m = re.search(rx, text, re.I)
                    if m and not (have & need):
                        misses.append(f"{where} says '{m.group(0)}' but its setting {sets or '?'} does not show {what}: "
                                      f"shoot that line in a setting that has one (line \"at\", furniture in scene-dsl.md)")
                acts = _beat_acts(beat)
                for rx, need in ACTION_NEEDS:
                    m = re.search(rx, text, re.I)
                    if m and not (acts & need):
                        misses.append(f"{where} says '{m.group(0)}' but nobody does it on screen: "
                                      f"add \"do\": \"{sorted(need)[0]}\" to that line (actions: spec-schema.md)")
                for rx, need in PROP_NEEDS:
                    m = re.search(rx, text, re.I)
                    if m and not (props & need) and not (have & need):
                        misses.append(f"{where} says '{m.group(0)}' but nothing on screen shows it: "
                                      f"add \"props\": [\"{sorted(need)[0]}\"] to that line")
                state = (beat.get("at") or tuple(seq_sets), tuple(beat.get("on") or ()))
                bare_run = bare_run + 1 if (state == last_state and not has_beat) else 1
                last_state = state
                if bare_run == 3:
                    notes.append(f"WARNING: {where}: three lines in a row with the same place, the same people and no "
                                 f"action or object while the words move on. Give each line its own beat "
                                 f"(\"at\", \"on\", \"do\", \"props\", \"shot\").")
            if len(lines) >= 4 and beats < len(lines) / 2:
                notes.append(f"WARNING: scene {sc.get('id')}: only {beats} of {len(lines)} lines say what is on screen. "
                             f"Write a visual beat for at least every other line, so the picture follows the words.")
    if misses:
        shown = misses[:12]
        notes += [f"WARNING: {m}" for m in shown]
        if len(misses) > len(shown):
            notes.append(f"WARNING: ... and {len(misses) - len(shown)} more lines whose words are not on screen.")
    return notes



NUMBER = re.compile(r"\b(\d[\d,.]*\s*(%|percent|dollars?|hours?|minutes?|seconds?|days?|years?|x|times)?|"
                    r"(one|two|three|four|five|six|seven|eight|nine|ten|twelve|twenty|thirty|forty|fifty|hundred|thousand|million)"
                    r"\s+(percent|dollars|hours|minutes|seconds|days|years|times))\b", re.I)


def film_pace(spec):
    """Pace like the reference films: IfverseTales cuts every 2.8 s (top video) to 5.2 s; ours ran 7.9 s.
    A number the narrator says is shown on screen (counter / chip), the way they show '0.25 s' or 'LEVEL 1'."""
    notes, no_hud = [], []
    for sc in spec.get("scenes", []):
        t = float(sc.get("target_s") or 0)
        shots = 0
        for item in sc.get("shots", []):
            seq = item.get("sequence")
            if not seq:
                shots += 1
                continue
            for ln in list(seq.get("cues", [])) + list(seq.get("lines", [])):
                text = ln if isinstance(ln, str) else ln.get("t", "")
                beat = ln if isinstance(ln, dict) else {}
                n = len(text.split())
                shots += 1 + (1 if (n > 9 or (beat.get("props") and n >= 8 and not beat.get("shot"))) else 0)
                if NUMBER.search(text) and not beat.get("hud"):
                    no_hud.append(f"scene {sc.get('id')} ({text[:40]!r})")
        if t and shots and t / shots > 4.5:
            notes.append(f"WARNING: scene {sc.get('id')}: about {t / shots:.1f} s per shot (aim <= 3.5 s; the reference "
                         f"films cut every 2.8-5 s). Split lines, add an insert on an object, or a reaction shot.")
    if no_hud:
        notes.append(f"WARNING: {len(no_hud)} line(s) say a number with nothing on screen showing it, e.g. {no_hud[0]}: "
                     f"add \"hud\": {{\"type\": \"counter\" | \"chip\", ...}} so the viewer SEES it (spec-schema.md).")
    return notes


# ---- script craft (references/story-formats.md, measured on the reference channel) ----------------------------
FORMATS = ("what_if", "character", "episode", "days", "dilemma", "explainer", "wordless")
TURN_WORDS = re.compile(r"\b(but|until|except|cost|price|then one day|that's when|the problem|unless|instead)\b", re.I)


def _lines_timed(spec):
    """-> [(t_mid_fraction, text, beat_dict)] across the film, spread evenly inside each scene."""
    rows = _timeline(spec)
    total = sum(r[2] - r[1] for r in rows) or 1
    out = []
    for sc, t0, t1, texts, _n, _s in rows:
        beats = []
        for item in sc.get("shots", []):
            seq = item.get("sequence") or {}
            beats += [c if isinstance(c, dict) else {"t": c} for c in list(seq.get("cues", [])) + list(seq.get("lines", [])) + list(item.get("cues") or [])]
        for i, b in enumerate(beats):
            out.append(((t0 + (i + 0.5) * (t1 - t0) / max(1, len(beats))) / total, b.get("t", ""), b))
    return out


def script_craft(spec):
    notes = []
    fmt = spec.get("format")
    lines = _lines_timed(spec)
    if not lines:
        return notes
    if fmt not in FORMATS:
        notes.append(f"WARNING: set \"format\" to one of {', '.join(FORMATS)} (references/story-formats.md): the format decides "
                     f"the voice, the shape of the story and the cast.")
    if fmt == "wordless":
        return notes
    sents = [x for _f, t, _b in lines for x in re.split(r"[.?!]+", t) if x.strip()]
    words = sum(len(x.split()) for x in sents)
    if sents and words / len(sents) > 9:
        notes.append(f"WARNING: sentences average {words / len(sents):.1f} words (the reference films: 5-7). Cut them: short lines, "
                     f"one-word payoffs (\"Caught.\"), and let actions carry the rest.")
    total_s = sum(r[2] - r[1] for r in _timeline(spec))
    if fmt in ("what_if", "days", "dilemma", "episode"):
        you = sum(1 for _f, t, b in lines if re.search(r"\byou(r|'re|'ve|'ll)?\b", t, re.I) and not b.get("who"))
        narr = sum(1 for _f, _t, b in lines if not b.get("who")) or 1
        if you / narr < 0.4:
            notes.append(f"WARNING: format '{fmt}' is told to the viewer as \"you\", but only {you} of {narr} narration lines say you/your.")
    if fmt == "what_if" and total_s > 90:
        early = [t for f, t, _b in lines if f * total_s <= 45]
        if not any("?" in t for t in early):
            notes.append("WARNING: 'what_if' needs its title question (\"So what if...?\") in the first 45 s, after 2-3 demonstrations, with a title card.")
    if fmt == "character":
        cast_names = [str(c.get("name") or c.get("id", "")).split()[0].lower() for c in spec.get("cast", []) if c.get("name") or c.get("id")]
        first = " ".join(t for f, t, _b in lines[:3]).lower()
        if not any(n and n in first for n in cast_names):
            notes.append("WARNING: 'character' format introduces the hero by name in the first lines (\"This is Jonah Pike.\").")
    if total_s >= 60:
        mid = [t for f, t, _b in lines if 0.45 <= f <= 0.8]
        if mid and not any(TURN_WORDS.search(t) for t in mid):
            notes.append("WARNING: no turn between 45 % and 80 % of the film (no 'but', 'until', 'the cost'...). The power/plan must show "
                         "its price there; without it the second half is a list.")
    plants = {b["plant"] for _f, _t, b in lines if b.get("plant")}
    payoffs = {b["payoff"] for _f, _t, b in lines if b.get("payoff")}
    for pl in sorted(plants - payoffs):
        notes.append(f"WARNING: plant '{pl}' is never paid off: add a line with \"payoff\": \"{pl}\" in the last third.")
    nums = sum(1 for _f, t, b in lines if re.search(r"\d|\b(one|two|three|ten|hundred|thousand|million|percent|half)\b", t, re.I))
    if total_s >= 60 and nums < max(2, len(lines) // 8):
        notes.append("WARNING: almost no numbers in the script. Make the idea measurable (a test, a score, a price, a count) and put the numbers on screen.")
    return notes


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
    # ---- places that look like places: a dressed set, not a floor box and a wall box ------------
    for sid, st in (spec.get("settings") or {}).items():
        if not isinstance(st, dict) or isinstance(st.get("set"), dict):
            continue
        objs = st.get("objects", [])
        if len(objs) < 12:
            notes.append(f"WARNING: setting '{sid}' has only {len(objs)} objects: close-ups will show an empty wall. "
                         f"Start it from a set (\"set\": {{\"type\": \"room\", \"style\": \"bedroom\", \"time\": \"dusk\"}}, "
                         f"or street / shopfront, references/set-design.md) and add the story's own objects on top.")
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
        if c.get("bottom") == "pants":
            notes.append(f"WARNING: character '{c['id']}' has bottom \"pants\". No character wears long trousers: "
                         f"everyone is a full stick figure (bottom \"none\"), \"shorts\" or a \"skirt\" at most. "
                         f"It is drawn as bare legs anyway; fix the spec so the Gemini prompt matches (references/wardrobe.md).")

    notes += hook_and_ending(spec)
    notes += script_visual_match(spec)
    notes += film_pace(spec)
    notes += script_craft(spec)
    return notes


if __name__ == "__main__":
    import json
    import sys
    for line in lint(json.load(open(sys.argv[1], encoding="utf-8"))):
        print(line)
