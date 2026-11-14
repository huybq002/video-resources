"""Places are DESIGNED for each film, and every line happens where it says it happens (spec lint).

Owner, 2026-11-14 (video 007): every story used the same 3D rooms, and "Then she went to work and held patients' hands"
was shot at a shop counter because nobody built a ward. The owner's rule: no menu of predefined places; the AI that writes
the spec thinks about each place the story needs and designs it, and says so when it cannot.

Each setting in spec.settings carries:
  "place":      free text, what this place is in THIS story ("night ward of a small city hospital, nurse station lit")
  "signature":  2+ objects that make it recognisable in a close-up (["drip stand", "heart monitor", "bed curtains"])
  "set":        a SHELL only: {"type": "room", "style": "generic"} (or street / shopfront / beach), with optional
                wall / floor / ceil colours, window, ceiling, finish; the film seed varies the rest
  "objects":    the designer's own pieces that build the place: primitives (box, cylinder, sphere, cone, glow, disc,
                lamp, lamp_hang, light, grad), furniture macros {"t":"furn"} and Kenney models {"t":"prop"}
  "needs_owner": optional, what could not be built and why (a car interior, a bus, an animal ...): the night job puts it
                in data/asset-requests.md and the report, and the owner makes it by hand

place_match(spec) -> WARNING lines (and NOTE: OWNER lines for needs_owner):
  - a setting without "place", without 2+ "signature" objects, or with fewer than 5 own objects;
  - a line that names a place no setting of its shot can show (by the settings' place text, id and signature);
  - a place the script talks about that no setting is designed for.
"""
import re

# words in a line that put it in a kind of place: a DETECTOR of what the words claim, not a list of places we can build
PLACE_WORDS = {
    "hospital": r"hospital|\bward\b|patients?|nurse station|\bclinic\b|emergency room|doctor'?s office",
    "cinema": r"cinema|movie theat(?:er|re)|\bthe movies\b|popcorn",
    "restaurant": r"restaurant|\bdiner\b|\bwaiter\b|waitress|\bbistro\b|\bthe bar\b|\bpub\b|dinner out",
    "bank": r"\bat the bank\b|\bto the bank\b|bank teller|\bteller\b|bank branch",
    "library": r"library|librarian",
    "gym": r"\b(?:at|in|to) the gym\b|treadmill|weights room",
    "park": r"\bpark\b(?!ing)|playground|\bpond\b",
    "street": r"\bstreet\b|\bthe road\b|crosswalk|pavement|sidewalk|bus stop",
    "kitchen": r"kitchen|\bstove\b|\boven\b|fridge",
    "bedroom": r"bedroom|\bin bed\b|\bher bed\b|\bhis bed\b|pillow",
    "cafe": r"\bcaf[eé]\b|coffee shop|barista",
    "shop": r"supermarket|grocery store|\bcheckout\b|\bthe aisle\b|\bthe till\b|\bthe shop\b|\bthe store\b",
    "school": r"classroom|lecture hall|\bschool\b|teacher'?s desk",
    "office": r"\b(?:at|in|to|into) the office\b|\b(?:her|his|my) office\b|cubicle|meeting room",
    "living room": r"living room|\bsofa\b|\bcouch\b",
    "bathroom": r"bathroom|\bshower\b",
    "car": r"\bin the car\b|\bdrove\b|\bdriving\b|steering wheel",
    "bus": r"\bon the bus\b|\bbus seat\b",
    "train": r"\bon the train\b|\bsubway\b|\bmetro\b|platform",
    "airport": r"airport|boarding gate|\bplane\b",
    "hotel": r"\bhotel\b|\blobby\b|reception desk",
    "church": r"\bchurch\b|chapel",
    "courtroom": r"courtroom|\bjudge\b|\bcourt\b",
    "police station": r"police station|interrogation room",
    "farm": r"\bfarm\b|\bbarn\b|\bfield\b",
    "beach": r"\bbeach\b|\bshore\b|\bwaves\b",
}
TALKED_ABOUT = re.compile(r"\b(never|didn't|won't|no longer|used to|someday|tomorrow|next week|yesterday|last year|one day)\b", re.I)
MIN_OBJECTS = 5


def _text_of(spec, sid):
    """everything that says what a setting is: its id, place text, signature, object names"""
    st = (spec.get("settings") or {}).get(sid)
    words = [str(sid).replace("_", " ")]
    if isinstance(st, dict):
        words += [str(st.get("place", "")), " ".join(map(str, st.get("signature", []) or []))]
        words += [str(o.get("n", "")) for o in st.get("objects", []) or [] if isinstance(o, dict)]
        if isinstance(st.get("set"), dict): words += [str(st["set"].get("style", "")), str(st["set"].get("type", ""))]
    elif isinstance(st, str):
        words.append(st)
    return " ".join(words).lower().replace("_", " ")


# what a setting's own text (id, place, signature) says when it IS this kind of place
SYN = {"shop": r"shop|store|market|bakery|till|counter|kiosk|supermarket|grocery|checkout|pharmacy|boutique",
       "street": r"street|road|pavement|sidewalk|outside|front|exterior|crossing|corner|alley|plaza|square",
       "office": r"office|desk|workplace|bank|meeting|studio|cubicle|reception|back ?room",
       "living room": r"living|flat|apartment|home|sofa|couch|lounge|house",
       "kitchen": r"kitchen|cook|stove|oven", "cafe": r"cafe|café|restaurant|diner|bakery|coffee|canteen|bar|pub",
       "bedroom": r"bed|dorm|sleep", "school": r"class|school|lecture|university|campus", "bathroom": r"bath|toilet|shower|washroom",
       "park": r"park|garden|pond|playground|green", "hospital": r"hospital|ward|clinic|nurse|medical|surgery",
       "bank": r"bank|teller|counter", "hotel": r"hotel|lobby|reception", "beach": r"beach|shore|sea|coast"}


def _shows(spec, sid, kind):
    t = _text_of(spec, sid)
    return bool(re.search(PLACE_WORDS[kind], t, re.I)) or kind in t or bool(re.search(SYN.get(kind, "$^"), t, re.I))


def _named(text):
    return [k for k, rx in PLACE_WORDS.items() if re.search(rx, text, re.I)]


def design_notes(spec):
    out = []
    for sid, st in (spec.get("settings") or {}).items():
        if not isinstance(st, dict) or str(sid).startswith("lib:"):
            continue
        if st.get("needs_owner"):
            out.append(f"NOTE: OWNER: setting '{sid}' needs a hand-made asset: {st['needs_owner']}")
        if not str(st.get("place", "")).strip():
            out.append(f"WARNING: place: setting '{sid}' has no \"place\": write what this place is in THIS story "
                       f"(\"night ward of a small city hospital\") and design it (references/filmmaker-checklist.md section 1)")
        sig = st.get("signature") or []
        if len(sig) < 2:
            out.append(f"WARNING: place: setting '{sid}' has no \"signature\": name 2-3 objects that make it recognisable "
                       f"in a close-up, and build them in its \"objects\"")
        own = [o for o in st.get("objects", []) or [] if isinstance(o, dict)]
        if len(own) < MIN_OBJECTS and not st.get("needs_owner"):
            out.append(f"WARNING: place: setting '{sid}' has {len(own)} object(s) of its own (want {MIN_OBJECTS}+): the shell "
                       f"alone is the same room in every film. Build this place from primitives / furn / prop, or say what "
                       f"is missing in \"needs_owner\"")
    return out


def place_match(spec):
    notes = design_notes(spec)
    settings = list((spec.get("settings") or {}).keys())
    missing = {}
    for sc in spec.get("scenes", []):
        for item in sc.get("shots", []):
            seq = item.get("sequence") or {}
            if seq:
                pool = [s for s in list(seq.get("settings", [])) + [seq.get("setting")] if s]
                lines = [(c.get("t", "") if isinstance(c, dict) else str(c), (c.get("at") if isinstance(c, dict) else None))
                         for c in seq.get("cues", [])] + [(l.get("t", "") if isinstance(l, dict) else str(l), None) for l in seq.get("lines", [])]
            else:
                pool = [item.get("setting")] if item.get("setting") else []
                lines = [(c.get("t", "") if isinstance(c, dict) else str(c), None) for c in item.get("cues", [])]
            for text, at in lines:
                if TALKED_ABOUT.search(text): continue
                for k in _named(text):
                    where = [at] if at else pool
                    if any(_shows(spec, s, k) for s in where): continue
                    if not any(_shows(spec, s, k) for s in settings):
                        missing.setdefault(k, text)
                    else:
                        good = [s for s in settings if _shows(spec, s, k)]
                        notes.append(f"WARNING: place: scene {sc.get('id')}: the line \"{text[:60]}\" happens in a {k}, but its shot "
                                     f"shows {', '.join(map(str, where)) or 'another place'}: put \"at\": \"{good[0]}\" on the line and add "
                                     f"'{good[0]}' to the sequence's settings")
    for k, text in missing.items():
        notes.append(f"WARNING: place: the script happens in a {k} (\"{text[:60]}\") but no setting is designed as one. Design it: "
                     f"a setting with \"place\", \"signature\" and its own \"objects\" (or \"needs_owner\" if it cannot be built)")
    return notes
