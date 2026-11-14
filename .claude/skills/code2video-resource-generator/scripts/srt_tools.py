"""script.srt planner / parser for the Code2Video contract.
Format (multi-speaker):   [An][00:00:00,000 --> 00:00:03,500][nữ]: Lời thoại.   (gender tag only with several speakers)
 - cue windows are contiguous, the last cue ends exactly at spec.duration_s
 - every cue lasts >= 0.5 s + 0.3 s x words (the contract's reading-time rule), the last cue of a scene >= 2.2 s
 - the app time-stretches the real voice into each window, so these windows ARE the timeline
"""
import json, re, pathlib

GAP = 0.2

def ts(ms):
    h, r = divmod(int(round(ms)), 3600000); m, r = divmod(r, 60000); s, r = divmod(r, 1000)
    return f"{h:02}:{m:02}:{s:02},{r:03}"

def parse_ts(t):
    h, m, rest = t.strip().split(":"); s, ms = rest.split(",")
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(ms)

def cue_items(spec):
    """flatten spec -> [{text, who, scene}] in order (shots with share:true consume no cues)"""
    out = []
    narr = spec.get("narrator", "narrator")
    for sc in spec["scenes"]:
        for sh in sc["shots"]:
            for cu in sh.get("cues", []):
                if isinstance(cu, dict): out.append(dict(text=cu["t"].strip(), who=cu.get("who") or narr, scene=sc["id"],
                                                         emote=cu.get("emote") or cu.get("say") or "", mood=sh.get("mood") or ""))
                else: out.append(dict(text=cu.strip(), who=narr, scene=sc["id"], emote="", mood=sh.get("mood") or ""))
    return out

def display_name(spec, cid):
    for c in spec.get("cast", []):
        if c["id"] == cid: return c.get("name", cid)
    return {"narrator": spec.get("narrator_name", "Người kể")}.get(cid, cid)

def min_len(text):
    return 0.5 + 0.3 * len(text.split())

# Words per second the voice-over ACTUALLY speaks, by language. Measured, not guessed:
#   en 3.79 w/s on the 2026-11-07 night job (edge-tts English voice), which left 37% of the film silent
#   while the planner still assumed 2.55. Override per spec with "speech_rate". vi is an estimate until measured.
# Capped at 3.3 by the contract's caption reading rule (>= 0.5 s + 0.3 s per word, i.e. at most ~3.33 w/s):
# planning faster than that makes validate.py reject the cues. The voice is a little faster still, so expect
# ~10-13 % natural pauses, not the 37 % we had at 2.55.
SPEECH_RATE = {"en": 3.3, "vi": 3.0}


def plan(spec, rate=None):
    rate = float(spec.get("speech_rate") or rate or SPEECH_RATE.get(spec.get("lang", "vi"), 3.0))
    """returns dict(cues=[{index,text,who,speaker,scene,startMs,endMs,words}], scenes=[{id,startMs,endMs}], notes=[...])"""
    items = cue_items(spec); n = len(items); notes = []
    if not n:
        raise SystemExit("no cues in the spec: plan() needs the expanded spec (coverage.expand), "
                         "and every scene needs cues in its shots.")
    total = int(round(float(spec.get("duration_s", 0)) * 1000)) if spec.get("duration_s") else 0
    base = []
    for i, it in enumerate(items):
        w = len(it["text"].split()); pauses = len(re.findall(r"[.,;:!?…]", it["text"])) * 0.12
        d = max(w / rate + pauses + GAP, min_len(it["text"]) + 0.05)
        base.append(d)
    # last cue of each scene stays on screen >= 2.2 s
    for i, it in enumerate(items):
        if i == n - 1 or items[i + 1]["scene"] != it["scene"]: base[i] = max(base[i], 2.3)
    # ---- scene budgets: scene.target_s (seconds) are authoritative; they must add up to duration_s
    scene_ids = [sc["id"] for sc in spec["scenes"] if any(it["scene"] == sc["id"] for it in items)]
    targets = {sc["id"]: float(sc["target_s"]) for sc in spec["scenes"] if sc.get("target_s")}
    if total and len(targets) == len(scene_ids):
        tsum = sum(targets.values())
        if abs(tsum - total / 1000.0) > 0.5:
            notes.append(f"NOTE: scene target_s add up to {tsum:.1f}s but duration_s is {total/1000:.1f}s: scaled proportionally.")
            targets = {k: v * total / 1000.0 / tsum for k, v in targets.items()}
    else:
        if total:
            notes.append("NOTE: scenes have no target_s; durations are spread by word count (set scenes[].target_s to control each scene).")
        raw = sum(base); f = (total / 1000.0 / raw) if total else 1.0
        targets = {}
        for sid in scene_ids:
            targets[sid] = sum(d for d, it in zip(base, items) if it["scene"] == sid) * f
    durs = list(base)
    for sid in scene_ids:
        idx = [i for i, it in enumerate(items) if it["scene"] == sid]; bs = sum(base[i] for i in idx); f = targets[sid] / bs
        # f > 1 means the scene is longer than its text needs: the voice-over stops and the scene keeps
        # running in silence. Keep this tight (1.12 = at most ~12% breathing room), it is the single
        # biggest cause of dead air in the rendered video.
        if f < 0.88 or f > 1.12:
            words = sum(len(items[i]["text"].split()) for i in idx)
            notes.append(f"WARNING: scene {sid} target {targets[sid]:.0f}s but its text naturally takes {bs:.0f}s "
                         + (f"({(1 - f) * 100:.0f}% too much text): cut about {int(words * (1 - f))} words" if f < 1
                            else f"({(f - 1) * 100:.0f}% of the scene would be silent): add about {int(words * (f - 1))} words")
                         + " (or change target_s).")
        for i in idx: durs[i] = base[i] * f
        for _ in range(4):                      # keep every cue above the reading minimum (0.5s + 0.3s/word)
            short = sum(max(0, min_len(items[i]["text"]) - durs[i]) for i in idx)
            if short <= 0: break
            slack = {i: max(0, durs[i] - min_len(items[i]["text"]) - 0.05) for i in idx}; ts_ = sum(slack.values()) or 1
            for i in idx: durs[i] = max(min_len(items[i]["text"]), durs[i] - short * slack[i] / ts_)
        # re-fit the scene to its target exactly (change the longest cue)
        diff = targets[sid] - sum(durs[i] for i in idx)
        j = max(idx, key=lambda i: durs[i]); durs[j] += diff
    ms = [int(round(d * 1000)) for d in durs]
    if total: ms[-1] += total - sum(ms)          # exact total (rounding remainder goes to the last cue)
    cues, t = [], 0
    for i, it in enumerate(items):
        st, en = t, t + ms[i]; t = en
        speech = max(0.3, (en - st) / 1000.0 - GAP)
        ws = it["text"].split(); wl = [len(re.sub(r"\W", "", x)) + 1 for x in ws]; tw = sum(wl); a = st; words = []
        for x, k in zip(ws, wl):
            b = a + int(round(speech * 1000 * k / tw)); words.append({"text": x, "startMs": a, "endMs": b}); a = b
        cues.append(dict(index=i + 1, text=it["text"], who=it["who"], speaker=display_name(spec, it["who"]), scene=it["scene"], startMs=st, endMs=en, words=words,
                         emote=it.get("emote", ""), mood=it.get("mood", "")))
    scenes = []
    for sc in spec["scenes"]:
        cs = [c for c in cues if c["scene"] == sc["id"]]
        if not cs: continue
        scenes.append(dict(id=sc["id"], startMs=cs[0]["startMs"], endMs=cs[-1]["endMs"]))
        L = (cs[-1]["endMs"] - cs[0]["startMs"]) / 1000.0
        if L < 12 or L > 50: notes.append(f"WARNING: scene {sc['id']} lasts {L:.0f}s (aim 20-40 s per scene): split or merge scenes.")
    # whole-film dead air: how much of the running time no one is speaking
    if cues:
        spoken = sum(min(c["endMs"] - c["startMs"], 1000 * (len(c["text"].split()) / rate
                     + len(re.findall(r"[.,;:!?…]", c["text"])) * 0.12)) for c in cues)
        silent_pct = 100.0 * (1 - spoken / cues[-1]["endMs"])
        line = f"silence: about {silent_pct:.0f}% of the film has no voice ({len(items)} cues, " \
               f"{sum(len(c['text'].split()) for c in cues)} words, " \
               f"{sum(len(c['text'].split()) for c in cues) / (cues[-1]['endMs'] / 1000):.2f} words/s)"
        notes.append(("WARNING: " + line + ": the script is too thin for this duration, add words or cut scene targets."
                      if silent_pct > 12 else "NOTE: " + line))
    return dict(cues=cues, scenes=scenes, notes=notes, totalMs=cues[-1]["endMs"] if cues else 0)

LABELS = {"vi": ("nam", "nữ"), "en": ("male", "female"), "es": ("hombre", "mujer"), "fr": ("homme", "femme"), "de": ("männlich", "weiblich"),
          "pt": ("masculino", "feminino"), "it": ("maschio", "femmina"), "id": ("pria", "wanita"), "ja": ("男性", "女性"), "ko": ("남성", "여성"),
          "zh": ("男", "女"), "th": ("ชาย", "หญิง"), "ru": ("муж", "жен"), "hi": ("पुरुष", "महिला")}
_FEM = {"f", "female", "woman", "girl", "nu", "nữ", "mujer", "femme", "weiblich", "feminino", "femmina", "wanita", "女性", "女", "여성", "หญิง", "жен", "महिला"}
_MAL = {"m", "male", "man", "boy", "nam", "hombre", "homme", "männlich", "masculino", "maschio", "pria", "男性", "男", "남성", "ชาย", "муж", "पुरुष"}

def norm_gender(g):
    g = (g or "").strip().lower()
    return "f" if g in _FEM else "m" if g in _MAL else None

def gender_of(spec, cid):
    """'f' | 'm' | None from cast[].gender (or spec.narrator_gender / legacy spec.female list)"""
    for c in spec.get("cast", []):
        if c["id"] == cid and c.get("gender"): return norm_gender(c["gender"])
    if cid == spec.get("narrator", "narrator") and spec.get("narrator_gender"): return norm_gender(spec["narrator_gender"])
    return "f" if display_name(spec, cid) in spec.get("female", []) else None

def write_srt(p, cues, spec=None):
    """multi-speaker format: [Name][00:00:00,000 --> 00:00:03,500][gender]: text  (gender tag only when more than one speaker; label in the script language)"""
    multi = len({c["speaker"] for c in cues}) > 1 and spec is not None
    lab = (spec or {}).get("gender_labels") or LABELS.get((spec or {}).get("lang", "vi"), LABELS["en"])
    def tag(c):
        g = gender_of(spec, c["who"]) if multi else None
        return f"[{lab[1] if g == 'f' else lab[0]}]" if g else ""
    blocks = [f"[{c['speaker']}][{ts(c['startMs'])} --> {ts(c['endMs'])}]{tag(c)}: {c['text']}" for c in cues]
    pathlib.Path(p).write_text("\n\n".join(blocks) + "\n", encoding="utf-8")

SRT_RE = re.compile(r"^\[(?P<who>[^\]]+)\]\[(?P<a>[\d:,]+)\s*-->\s*(?P<b>[\d:,]+)\](?:\[(?P<g>[^\]]*)\])?:\s*(?P<text>.+)$")

def parse_srt(p):
    """parse contract SRT (multi-speaker) -> list of dict(speaker,startMs,endMs,text,gender 'f'|'m'|None)"""
    cues = []
    for block in re.split(r"\n\s*\n", pathlib.Path(p).read_text(encoding="utf-8").strip()):
        line = " ".join(block.strip().splitlines())
        m = SRT_RE.match(line)
        if m: cues.append(dict(speaker=m["who"], startMs=parse_ts(m["a"]), endMs=parse_ts(m["b"]), text=m["text"].strip(), gender=norm_gender(m["g"])))
    return cues
