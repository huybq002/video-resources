"""Does the script sound like a person talking? Lint for stiff, machine-written narration and dialogue.

The other lints check structure (length, shots, visuals). This one checks the *voice*, which is what makes a
viewer feel the film was written by someone. Everything is a WARNING with the exact line and a suggested fix.
See references/spoken-voice.md for the rules and the reasons.

    python voice_lint.py spec.json
"""
import re
import statistics

# ---- English ---------------------------------------------------------------------------------------
CONTRACT = [
    (r"\bI am\b", "I'm"), (r"\bI will\b", "I'll"), (r"\bI have\b(?! to)", "I've"), (r"\bI would\b", "I'd"),
    (r"\b(you|we|they) are\b", r"\1're"), (r"\b(you|we|they) will\b", r"\1'll"), (r"\b(you|we|they) have\b(?! to)", r"\1've"),
    (r"\b(he|she|it|that|there|what|who) is\b", r"\1's"), (r"\blet us\b", "let's"),
    (r"\b(do|does|did|is|are|was|were|has|have|had|would|could|should) not\b", r"\1n't"),
    (r"\bcannot\b", "can't"), (r"\bwill not\b", "won't"),
]
# phrases that mark text written by a model, not spoken by a person
CLICHES = [
    r"\bin today'?s (fast[- ]paced )?world\b", r"\blet'?s dive in\b", r"\bdelve\b", r"\btapestry\b", r"\btestament to\b",
    r"\bit'?s not (just|only|about) [^.?!]{3,40}[,;] (it'?s|but)\b", r"\bnot (just|only) [^.?!]{3,40}, but\b",
    r"\bimagine (this|a world|if)\b", r"\blittle did (he|she|they|we) know\b", r"\bhere'?s the thing\b",
    r"\bat the end of the day\b", r"\bgame[- ]?changer\b", r"\bunlock(ing)? (the|your)\b", r"\bnavigat(e|ing) the\b",
    r"\bsilent (killer|thief)\b", r"\bheart (was )?pounding\b", r"\bshiver(ed)? down\b", r"\ba stark reminder\b",
    r"\bthe truth (is|was)\b", r"\bin a world where\b", r"\bsomething (shifted|changed) (in|inside)\b",
    r"\bevery (single )?(decision|choice) (matters|counts)\b", r"\bjourney\b", r"\bwhisper(s|ed)? of\b",
]
TELL = re.compile(r"\b(felt|feels|was feeling|is feeling|was|is|seemed|looked) (so |very |really |extremely |deeply )?"
                  r"(anxious|nervous|sad|happy|angry|afraid|scared|terrified|overwhelmed|guilty|ashamed|lonely|"
                  r"exhausted|frustrated|hopeless|excited|worried|stressed|depressed|relieved|proud)\b", re.I)
# the narrator explaining the lesson instead of the story showing it
MORAL = re.compile(r"\b(the lesson (is|here)|the moral|what this (teaches|shows) us|this (teaches|shows) us|remember[,:] )", re.I)
# dialogue that explains things to the viewer through the characters' mouths
EXPO = re.compile(r"\b(as you know|as we both know|you remember (that|how)|like i (said|told you) (before|earlier))\b", re.I)
FILLER_OPEN = re.compile(r"^(so|well|and|but|now|okay|ok|look|listen|right|honestly|yeah|oh|hm+|uh|um)\b[ ,.]", re.I)

# ---- Vietnamese ------------------------------------------------------------------------------------
VI_STIFF = [
    r"h[ãa]y t[ưu]ởng t[ưu]ợng", r"trong th[ếe] gi[ớo]i ng[àa]y nay", r"ch[úu]ng ta h[ãa]y c[ùu]ng", r"m[ộo]t c[áa]ch (r[ấa]t |h[ếe]t s[ứư]c )?\w+",
    r"kh[ôo]ng ch[ỉi] \w+( \w+)? m[àa] c[òo]n", r"h[àa]nh tr[ìi]nh", r"v[ôo] c[ùu]ng quan tr[ọo]ng", r"[đd][ềe] c[ậa]p [đd][ếe]n",
    r"th[ôo]ng qua vi[ệe]c", r"[đd][ốo]i v[ớo]i ch[úu]ng ta",
]


def _cues(spec):
    """-> [(scene_id, cue_dict, is_dialogue)] in film order."""
    out = []
    for sc in spec.get("scenes", []):
        for it in sc.get("shots", []):
            seq = it.get("sequence") or {}
            for c in list(seq.get("cues", [])) + list(seq.get("lines", [])) + list(it.get("cues") or []):
                c = c if isinstance(c, dict) else {"t": c}
                out.append((sc.get("id"), c, bool(c.get("who")) and c.get("who") != spec.get("narrator", "narrator")))
    return out


def _sents(t):
    return [x.strip() for x in re.split(r"(?<=[.?!])\s+", t) if x.strip()]


def voice(spec):
    notes = []
    rows = _cues(spec)
    if not rows or spec.get("format") == "wordless":
        return notes
    lang = str(spec.get("lang", "vi")).lower()
    texts = [(sid, c.get("t", ""), d) for sid, c, d in rows if c.get("t")]
    allt = " ".join(t for _s, t, _d in texts)

    def q(t):
        return f"'{t[:48]}{'...' if len(t) > 48 else ''}'"

    if lang.startswith("en"):
        # 1. contractions: people say "I'm", "don't". The voice-over reads the text exactly as written.
        stiff = []
        for sid, t, d in texts:
            for pat, fix in CONTRACT:
                m = re.search(pat, t, re.I)
                if not m:
                    continue
                if re.search(r"not (only|just|even)\b", t[m.start():m.start() + 20], re.I):
                    continue      # "not only" is a rhythm choice, not stiffness
                if m.end() >= len(t.rstrip(" .!?\"'")):
                    continue      # "Yes, I am." / "It is." : a full form at the end of a line is stress, not stiffness
                stiff.append((sid, t, d, m.group(0), re.sub(pat, fix, m.group(0), flags=re.I)))
                break
        dial = [x for x in stiff if x[2]]
        if dial:
            for sid, t, _d, got, fix in dial[:4]:
                notes.append(f"WARNING: voice: scene {sid} dialogue {q(t)} says \"{got}\": people say \"{fix}\". Contract it (the voice-over reads the text literally).")
        if len(stiff) >= max(3, len(texts) // 5):
            notes.append(f"WARNING: voice: {len(stiff)} of {len(texts)} lines have no contractions (\"{stiff[0][3]}\" -> \"{stiff[0][4]}\"). "
                         f"Spoken English contracts; only stress a full form on purpose (\"I do not know.\" as a flat refusal).")
        # 2. model-isms
        hit = []
        for pat in CLICHES:
            for m in re.finditer(pat, allt, re.I):
                hit.append(m.group(0))
        if hit:
            notes.append(f"WARNING: voice: stock phrases that read as machine-written: {', '.join(sorted(set(h.lower() for h in hit))[:6])}. "
                         f"Say the concrete thing instead (what exactly happened, to whom, with what object).")
        # 3. tell, don't show
        told = [t for _s, t, d in texts if not d and TELL.search(t)]
        if len(told) >= 2:
            notes.append(f"WARNING: voice: the narrator names feelings {len(told)} times ({q(told[0])}). Show it with an action, a prop, or a "
                         f"line of dialogue, then cut the label: \"She read it twice\" beats \"She felt anxious\".")
        # 4. narrator explaining the moral
        for sid, t, d in texts:
            if not d and MORAL.search(t):
                notes.append(f"WARNING: voice: scene {sid} {q(t)} lectures. Let an event carry the lesson, or hand it to a character who is wrong about it.")
                break
        # 5. exposition in dialogue
        for sid, t, d in texts:
            if d and EXPO.search(t):
                notes.append(f"WARNING: voice: scene {sid} dialogue {q(t)} tells the audience what both characters already know. "
                             f"Cut it, or turn it into something one of them wants.")
        # 6. dialogue that is all full sentences: no interruptions, no fragments, nobody dodges a question
        dl = [t for _s, t, d in texts if d]
        if len(dl) >= 6:
            frag = sum(1 for t in dl if len(t.split()) <= 4 or t.rstrip().endswith(("...", "-", "--")) or FILLER_OPEN.match(t))
            if frag / len(dl) < 0.25:
                notes.append(f"WARNING: voice: only {frag} of {len(dl)} dialogue lines are short, broken or start with a filler (\"Well,\" \"Look,\"). "
                             f"Real people answer with one word, trail off, change the subject. Give at least a quarter of the lines that shape.")
            ans = sum(1 for i in range(1, len(dl)) if dl[i - 1].rstrip().endswith("?") and len(dl[i].split()) > 12)
            if ans >= 2:
                notes.append("WARNING: voice: characters answer questions with speeches (12+ words) in several places. Answer short, let the picture or the next line say the rest.")
    elif lang.startswith("vi"):
        hit = []
        for pat in VI_STIFF:
            hit += [m.group(0) for m in re.finditer(pat, allt, re.I)]
        if hit:
            notes.append(f"WARNING: voice: văn dịch / văn mẫu: {', '.join(sorted(set(h.lower() for h in hit))[:6])}. Nói như người Việt kể chuyện: câu ngắn, từ cụ thể, "
                         f"bỏ \"một cách\", \"thông qua việc\", \"hãy tưởng tượng\".")
        dl = [t for _s, t, d in texts if d]
        if len(dl) >= 6 and not any(re.search(r"\b(à|ơi|nhỉ|nhé|đấy|thôi|hả|chứ|mà|vậy)\b[.?!]*$", t, re.I) for t in dl):
            notes.append("WARNING: voice: lời thoại không có từ đệm cuối câu (à, nhé, đấy, thôi, hả, chứ...): nghe như đọc văn bản. Thêm theo tính cách từng người.")

    # ---- language-independent ----------------------------------------------------------------------
    # repeated openers: three-in-a-row is a device, five is a tic
    firsts = [re.sub(r"\W", "", t.split()[0].lower()) for _s, t, _d in texts if t.split()]
    run = 1
    for i in range(1, len(firsts)):
        run = run + 1 if firsts[i] == firsts[i - 1] else 1
        if run == 5:
            notes.append(f"WARNING: voice: five lines in a row start with \"{firsts[i]}\". Break the pattern (a three-line anaphora is a device; five is a tic).")
            break
    sl = [len(s.split()) for _s, t, d in texts if not d for s in _sents(t)]
    if len(sl) >= 14 and statistics.pstdev(sl) < 1.4:
        notes.append(f"WARNING: voice: narration sentences are all about {statistics.mean(sl):.0f} words (spread {statistics.pstdev(sl):.1f}): it drones. "
                     f"Mix a one-word line, a medium line and now and then a long one that runs on.")
    qn = sum(1 for _s, t, d in texts if not d and t.rstrip().endswith("?"))
    nn = sum(1 for _s, t, d in texts if not d) or 1
    if nn >= 8 and qn / nn > 0.25:
        notes.append(f"WARNING: voice: {qn} of {nn} narration lines are questions. Rhetorical questions are a hook, not a rhythm: answer most of them with a fact.")
    # every cue that names a thing says it with the same word: repetition of a long content word
    words = [w for w in re.findall(r"[a-zà-ỹ']{7,}", allt.lower())]
    if len(words) > 40:
        top = max(set(words), key=words.count)
        if words.count(top) >= max(6, len(words) // 12):
            notes.append(f"WARNING: voice: the word \"{top}\" appears {words.count(top)} times. Use the thing's own name, a pronoun, or cut the line.")
    return notes


if __name__ == "__main__":
    import json
    import sys
    for line in voice(json.load(open(sys.argv[1], encoding="utf-8"))):
        print(line)
