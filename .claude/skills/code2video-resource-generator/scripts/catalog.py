"""One table that says, for every object the 3D sets can build, what it is called in a script, where it stands in a
room, how big it is, which places it belongs in, and what a character can DO with it.

Everything else is derived from this table, so supporting a new kind of scene means adding DATA here, not code:
- autofill.py reads a line ("she collapses onto the sofa", "he loads the washing machine") -> a verb group (VERBS)
  -> an affordance -> the object in the setting that offers it (or adds one with layout.py) -> a `do` like
  "lie@sofa" / "use@washer:reach".
- layout.py places any object of the catalog into any room by its `zone` and footprint.
- anchors.py gets the interaction points (seat, head/foot, approach) of every object from here.

Affordances (what the body does, see coverage.HOLD_POSES and build_project.resolve):
  lie / sleep  lying ON it (head/foot points)          sit   seated ON it (seat point)
  work         seated at it, hands on it (desk/table + a chair; laptop added when there is no screen)
  use          standing at its front, turned to it, the hands doing `act` (stir, reach, point, look, type)
  stand        standing beside it (arrived there)
"""

# zone: back = against the back wall, side = against a side wall, center = free standing on the floor,
#       surface = on top of a desk/table/counter, floor = small thing on the floor near a wall, wall = hung on a wall
# w, d: footprint in metres (before scale). places: room styles it belongs in ("*" = anywhere).
# aff: affordance -> hand act for "use" (None for the body poses). syn: regex of words a script uses for it.
C = {
    "bed":            dict(zone="center", w=1.7, d=2.2, places="bedroom hospital hotel dorm", syn=r"bed|mattress|bunk", aff={"lie": None, "sleep": None, "sit": None}),
    "sofa":           dict(zone="center", w=2.1, d=1.0, places="living office cafe lounge waiting", syn=r"sofa|couch|settee", aff={"sit": None, "lie": None, "sleep": None}),
    "bench":          dict(zone="center", w=1.8, d=0.5, places="* park street laundry", syn=r"bench", aff={"sit": None, "lie": None}),
    "chair":          dict(zone="center", w=0.5, d=0.5, places="*", syn=r"chair|seat|stool", aff={"sit": None}),
    "toilet":         dict(zone="back", w=0.45, d=0.6, places="bathroom", syn=r"toilet|loo", aff={"sit": None}),
    "bathtub":        dict(zone="back", w=1.7, d=0.8, places="bathroom", syn=r"bath(tub)?|tub|shower", aff={"lie": None, "use": "stir"}),
    "towel":          dict(zone="center", w=0.8, d=1.8, places="beach", syn=r"towel", aff={"lie": None, "sit": None}),
    "desk":           dict(zone="back", w=1.6, d=0.75, places="office bedroom lab classroom study", syn=r"desk|workstation", aff={"work": None, "use": "type"}),
    "table":          dict(zone="center", w=1.6, d=0.9, places="kitchen cafe living restaurant meeting", syn=r"table", aff={"work": None, "use": "reach"}),
    "folding_table":  dict(zone="center", w=1.8, d=0.7, places="laundry", syn=r"folding table", aff={"use": "stir"}),
    "computer":       dict(zone="surface", w=0.7, d=0.3, places="office bedroom lab", syn=r"computer|monitor|screen|pc", aff={"use": "type"}, on="desk"),
    "kitchen_counter":dict(zone="back", w=2.4, d=0.65, places="kitchen", syn=r"counter|worktop|kitchen", aff={"use": "stir"}),
    "oven":           dict(zone="back", w=0.65, d=0.62, places="kitchen", syn=r"oven|stove|cooker|hob", aff={"use": "stir"}),
    "fridge":         dict(zone="back", w=0.75, d=0.7, places="kitchen", syn=r"fridge|refrigerator|freezer", aff={"use": "reach"}),
    "sink":           dict(zone="back", w=0.9, d=0.55, places="bathroom kitchen", syn=r"sink|basin|tap|faucet", aff={"use": "stir"}),
    "washer":         dict(zone="back", w=0.68, d=0.65, places="laundry bathroom kitchen", syn=r"washing machines?|washers?|dryers?|laundry machines?", aff={"use": "reach"}),
    "mirror":         dict(zone="wall", w=0.8, d=0.05, places="bathroom bedroom", syn=r"mirror", aff={"use": "look"}, near="sink"),
    "window":         dict(zone="wall", w=1.4, d=0.1, places="*", syn=r"window", aff={"use": "look"}),
    "door_frame":     dict(zone="wall", w=1.1, d=0.12, places="*", syn=r"door(way)?", aff={"stand": None}),
    "bookshelf":      dict(zone="back", w=1.2, d=0.35, places="bedroom office living library classroom", syn=r"bookshel(f|ves)|bookcase|library", aff={"use": "reach"}),
    "shelf_goods":    dict(zone="center", w=2.0, d=0.45, places="grocery shop", syn=r"shel(f|ves)|aisle|groceries", aff={"use": "reach"}),
    "fridge_display": dict(zone="back", w=1.4, d=0.7, places="grocery shop", syn=r"drinks? fridge|chiller|display fridge", aff={"use": "reach"}),
    "shop_counter":   dict(zone="center", w=2.4, d=0.65, places="shop cafe grocery bar hotel", syn=r"till|cashier|checkout|reception|bar counter|front desk", aff={"use": "reach"}),
    "checkout":       dict(zone="center", w=2.2, d=0.7, places="grocery shop", syn=r"checkout|cash register|register", aff={"use": "reach"}),
    "whiteboard":     dict(zone="wall", w=1.8, d=0.05, places="office classroom meeting lab", syn=r"whiteboard|blackboard|board", aff={"use": "point"}),
    "projector_screen": dict(zone="wall", w=3.4, d=0.12, places="meeting classroom", syn=r"projector|slides?|presentation", aff={"use": "point"}, via="podium"),
    "podium":         dict(zone="center", w=0.7, d=0.5, places="meeting classroom", syn=r"podium|lectern|stage", aff={"use": "point"}, near="projector_screen", stand="behind", h=1.14),
    "tv":             dict(zone="back", w=1.3, d=0.4, places="living bedroom", syn=r"tv|television|telly", aff={"use": "look"}),
    "bedside_table":  dict(zone="center", w=0.5, d=0.45, places="bedroom", syn=r"bedside|nightstand", aff={"use": "reach"}, near="bed"),
    "lamp_floor":     dict(zone="floor", w=0.4, d=0.4, places="living bedroom", syn=r"floor lamp", aff={}),
    "plant":          dict(zone="floor", w=0.5, d=0.5, places="*", syn=r"plants?|flowers?", aff={"use": "reach"}),
    "rug":            dict(zone="center", w=2.6, d=1.7, places="living bedroom", syn=r"rug|carpet", aff={}),
    "picture":        dict(zone="wall", w=0.8, d=0.04, places="*", syn=r"painting|picture on the wall|portrait", aff={"use": "look"}),
    "wall_clock":     dict(zone="wall", w=0.6, d=0.03, places="*", syn=r"wall clock", aff={"use": "look"}),
    "wall_shelf":     dict(zone="wall", w=1.2, d=0.25, places="*", syn=r"wall shelf", aff={"use": "reach"}),
    "coat_rack":      dict(zone="floor", w=0.4, d=0.4, places="office living cafe hall", syn=r"coat rack|coat stand|coats?", aff={"use": "reach"}),
    "trash_bin":      dict(zone="floor", w=0.5, d=0.5, places="*", syn=r"bin|trash|rubbish|garbage", aff={"use": "reach"}),
    "cardboard_box":  dict(zone="floor", w=0.55, d=0.45, places="*", syn=r"boxes|cardboard box|moving box|parcel", aff={"use": "reach"}),
    "laundry_basket": dict(zone="floor", w=0.6, d=0.6, places="laundry bedroom bathroom", syn=r"laundry basket|hamper|laundry", aff={"use": "reach"}),
    "crate":          dict(zone="floor", w=0.8, d=0.8, places="* warehouse", syn=r"crate", aff={"use": "reach"}),
    "barrel":         dict(zone="floor", w=0.7, d=0.7, places="* warehouse", syn=r"barrel", aff={}),
    "towel_rail":     dict(zone="wall", w=0.7, d=0.05, places="bathroom", syn=r"towel rail", aff={"use": "reach"}),
    # small things on surfaces (zone surface): they come with a line ("she pours the kettle"), on the nearest work surface
    "kettle":         dict(zone="surface", w=0.2, d=0.2, places="kitchen", syn=r"kettle|tea", aff={}, on="kitchen_counter table"),
    "laptop_open":    dict(zone="surface", w=0.4, d=0.3, places="*", syn=r"laptop", aff={}, on="desk table"),
    "desk_lamp":      dict(zone="surface", w=0.2, d=0.2, places="*", syn=r"desk lamp|lamp", aff={}, on="desk bedside_table"),
    "alarm_clock":    dict(zone="surface", w=0.15, d=0.1, places="bedroom", syn=r"alarm( clock)?", aff={}, on="bedside_table desk"),
    "books_stack":    dict(zone="surface", w=0.25, d=0.2, places="*", syn=r"books|textbooks?|notes", aff={}, on="desk table"),
    "fruit_bowl":     dict(zone="surface", w=0.3, d=0.3, places="kitchen", syn=r"fruit|apples?|bananas?", aff={}, on="table kitchen_counter"),
    "pot":            dict(zone="surface", w=0.3, d=0.3, places="kitchen", syn=r"pot|pan|soup|pasta", aff={}, on="oven kitchen_counter"),
    "papers":         dict(zone="surface", w=0.3, d=0.25, places="*", syn=r"papers|forms?|paperwork|bills", aff={}, on="desk table"),
    "clothes_pile":   dict(zone="surface", w=0.4, d=0.3, places="*", syn=r"shirts?|socks|clothes|laundry", aff={}, on="folding_table bed table"),
    "frame_photo":    dict(zone="surface", w=0.2, d=0.05, places="*", syn=r"framed photo|photo frame", aff={"use": "look"}, on="desk bedside_table"),
    "sticky_notes":   dict(zone="surface", w=0.3, d=0.1, places="office bedroom", syn=r"sticky notes?|post-its?", aff={}, on="desk"),
    "mug":            dict(zone="surface", w=0.1, d=0.1, places="*", syn=r"mug|cup", aff={}, on="desk table kitchen_counter"),
}

# what a kind of place contains when nobody wrote it down. A place word not in sets.STYLES is built as a generic room
# from this list (layout.py places the pieces), so "hospital", "library", "bar", "waiting room" all come out furnished.
# Adding a place = one line here.
PLACES = {
    "hospital":   ["bed", "bedside_table", "chair", "computer", "sink", "plant", "window"],
    "clinic":     ["desk", "computer", "chair", "chair", "bed", "sink", "bookshelf"],
    "waiting":    ["bench", "bench", "chair", "chair", "plant", "wall_clock", "trash_bin"],
    "library":    ["bookshelf", "bookshelf", "bookshelf", "table", "chair", "chair", "desk_lamp"],
    "restaurant": ["table", "chair", "chair", "table", "chair", "chair", "shop_counter", "plant"],
    "bar":        ["shop_counter", "chair", "chair", "chair", "table", "chair", "wall_shelf", "wall_shelf"],
    "hotel":      ["bed", "bedside_table", "desk", "chair", "tv", "window", "laundry_basket"],
    "reception":  ["shop_counter", "computer", "sofa", "plant", "wall_clock", "chair"],
    "police":     ["desk", "computer", "chair", "chair", "whiteboard", "bookshelf", "trash_bin"],
    "studio":     ["bed", "desk", "computer", "chair", "kitchen_counter", "fridge", "sofa"],
    "dorm":       ["bed", "desk", "computer", "chair", "bookshelf", "laundry_basket"],
    "garage":     ["crate", "crate", "cardboard_box", "cardboard_box", "wall_shelf", "barrel", "trash_bin"],
    "warehouse":  ["crate", "crate", "crate", "barrel", "barrel", "cardboard_box", "shelf_goods"],
    "attic":      ["cardboard_box", "cardboard_box", "crate", "chair", "lamp_floor", "rug"],
    "hall":       ["door_frame", "coat_rack", "picture", "plant", "rug"],
    "bank":       ["shop_counter", "computer", "desk", "chair", "chair", "plant", "wall_clock"],
    "pharmacy":   ["shop_counter", "shelf_goods", "shelf_goods", "checkout"],
    "bakery":     ["shop_counter", "shelf_goods", "table", "chair", "chair", "oven"],
    "salon":      ["mirror", "chair", "chair", "sink", "shop_counter", "plant"],
    "gym":        ["bench", "bench", "mirror", "wall_clock", "towel_rail", "trash_bin"],
    "classroom":  None, "office": None, "bedroom": None, "kitchen": None, "living": None, "cafe": None, "shop": None,
    "lab": None, "laundry": None, "meeting": None, "bathroom": None, "grocery": None,    # None: a dressed style exists in sets.py
}
PLACE_WORDS = {   # words in a setting id / description / line -> PLACES key
    "hospital": r"hospital|ward|patient|icu", "clinic": r"clinic|doctor'?s office|surgery|therapist", "waiting": r"waiting room|lobby",
    "library": r"library", "restaurant": r"restaurant|diner|dining", "bar": r"\bbar\b|\bpub\b|club", "hotel": r"hotel|motel",
    "reception": r"reception", "police": r"police|station|precinct|interrogation", "studio": r"studio flat|bedsit",
    "dorm": r"dorm", "garage": r"garage|workshop|shed", "warehouse": r"warehouse|storage", "attic": r"attic|loft",
    "hall": r"hallway|corridor|entrance|hall\b", "bank": r"\bbank\b", "pharmacy": r"pharmacy|chemist", "bakery": r"bakery",
    "salon": r"salon|barber|hairdresser", "gym": r"\bgym\b|fitness",
}

# verbs -> affordance (+ the hand act for "use"). Order matters: first match wins. Each group lists the objects that
# offer it in order of preference; the first one the setting has is used, else the first plausible one is ADDED.
VERBS = [
    (r"\b(falls? asleep|fell asleep|asleep|sleep(s|ing)?|naps?|napping|doz(es|ed|ing))\b", "sleep", ["bed", "sofa", "bench", "towel"]),
    (r"\b(lies?|lay|lying|lies down|collaps(es|ed) (on|onto)|sprawl\w*|flops? (on|onto))\b", "lie", ["bed", "sofa", "bench", "towel", "bathtub"]),
    (r"\b(sits?|sat|sitting|seated|takes? a seat|perch\w*|sinks? into)\b", "sit", ["chair", "sofa", "bench", "bed", "toilet"]),
    (r"\b(works? (on|at|late)|typ(es|ed|ing)|stud(y|ies|ied|ying)|cod(es|ing)|emails?|spreadsheet|cursor|opens? the (file|laptop|document)|blank (slide|page))\b", "work", ["desk", "table"]),
    (r"\b(cook\w*|stir\w*|fr(y|ies|ied)|boil\w*|chop\w*|bak(e|es|ed|ing)|make[s]? (dinner|breakfast|lunch|tea|coffee))\b", "use:stir", ["oven", "kitchen_counter"]),
    (r"\b(scrub\w*|wip(e|es|ed|ing)|polish\w*|clean(s|ed|ing)? (the|a|her|his)|wash(es|ed|ing)? (the )?(dishes|hands|face))\b", "use:stir", ["sink", "oven", "kitchen_counter", "table", "desk"]),
    (r"\b(laundry|load(s|ed|ing)? the (machine|washer)|washing machines?|dryer)\b", "use:reach", ["washer"]),
    (r"\b(fold(s|ed|ing)?|iron(s|ed|ing)?|sort(s|ed|ing)? (her|his|the) (socks|clothes|laundry))\b", "use:stir", ["folding_table", "table", "bed"]),
    (r"\b(brows\w*|compar(es|ed|ing)|picks? (something|it|one) off|shopping for)\b", "use:reach", ["shelf_goods", "bookshelf", "fridge_display"]),
    (r"\b(dig(s|ging)? through|rummag\w*|search(es|ed|ing)? (through|the)|unpack\w*|pack(s|ed|ing)? (up|the|her|his)|sort(s|ed|ing)? through|looks? for)\b", "use:reach", ["crate", "cardboard_box", "wall_shelf", "bookshelf", "laundry_basket", "bedside_table"]),
    (r"\b(pays?|paid|checkout|cashier|scans?)\b", "use:reach", ["checkout", "shop_counter"]),
    (r"\b(present(s|ed|ing)?|pitch(es|ed|ing)|lectur\w*|teach(es|ing)?|gives? (a|the|her|his) talk|on stage)\b", "use:point", ["podium", "projector_screen", "whiteboard"]),
    (r"\b(writes? on the board|draws? on the board)\b", "use:point", ["whiteboard"]),
    (r"\b(looks?|stares?|gazes?|peers?|watches?) (out|outside|through)\b", "use:look", ["window"]),
    (r"\b(looks?|stares?|gazes?|peers?) (out|through)( of)? the window\b", "use:look", ["window"]),
    (r"\b(looks?|stares?) (at herself|at himself|in(to)? the mirror)\b", "use:look", ["mirror"]),
    (r"\b(opens? the fridge|raids? the fridge|grabs? (a|the) (drink|snack|beer|milk))\b", "use:reach", ["fridge", "fridge_display"]),
    (r"\b(watch(es|ed|ing)? (tv|television|the news|a show|a film|a movie))\b", "sit", ["sofa", "chair"]),
    (r"\b(takes? a bath|in the bath|showers?)\b", "use:stir", ["bathtub"]),
    (r"\b(walks? (in|out|through the door)|leaves|opens? the door|knocks?)\b", "stand", ["door_frame"]),
]


# synonyms that are also verbs, idioms or parts of other nouns ("she notes", "books a flight", "her phone screen",
# "at this stage", "a cup of tea"): they name the object only as a plain noun after a determiner, optionally with one
# adjective ("the old books", "her tea"), and not as the second half of a compound ("phone screen", "board meeting").
WEAK = {"tea", "notes", "board", "stage", "seat", "screen", "monitor", "bin", "trash", "register", "slides", "slide", "counter",
        "kitchen", "pot", "pan", "tap", "forms", "form", "bills", "alarm", "lamp", "tub", "shower", "bath", "fruit", "cup",
        "coats", "coat", "flowers", "flower", "papers", "picture", "books", "laundry", "library", "presentation", "reception",
        "till", "plants", "plant", "boxes", "soup", "pasta", "apples", "apple", "bananas", "socks", "shirts", "shirt", "clothes",
        "stool", "basin", "pc", "loo", "garbage", "rubbish", "portrait", "painting", "parcel", "carpet", "faucet", "groceries"}
_DET = r"(the|a|an|her|his|their|my|your|our|its|this|that|these|those|some|two|three|every|each|one|old|new|empty|full)"
_COMPOUND_BEFORE = {"phone", "laptop", "tablet", "lock", "home", "touch", "loading", "splash", "title", "chess", "circuit", "bulletin",
                    "notice", "score", "key", "surf", "snow", "skate", "dart", "cutting", "bread", "ironing", "world", "coffee", "tea"}
_COMPOUND_AFTER = {"meeting", "member", "members", "game", "games", "room", "rooms", "fright", "presence", "time", "name", "names",
                   "bag", "talk", "offer", "argument", "attack", "point"}


def _plain_noun(text, m):
    import re
    if m.group(0).lower() not in WEAK:
        return True
    pre = re.findall(r"[A-Za-z']+", text[:m.start()])[-3:]
    post = re.findall(r"[A-Za-z']+", text[m.end():])[:1]
    if post and post[0].lower() in _COMPOUND_AFTER:
        return False
    if pre and pre[-1].lower() in _COMPOUND_BEFORE:
        return False
    w = [x.lower() for x in pre]
    return bool(w) and (re.fullmatch(_DET, w[-1]) is not None or (len(w) > 1 and re.fullmatch(_DET, w[-2]) is not None
                                                                  and not re.fullmatch(r"\w+(s|ed|ing)", w[-1])))


# fixed phrases that hold an object word but no object: removed before matching
IDIOMS = r"\b(at|by|from) (this|that|some|one|any|an early|a later|the next) stage\b|\bon board\b|\bacross the board\b|\bin the picture\b|" \
         r"\bbig picture\b|\bpicture this\b|\boff the table\b|\bturn(s|ed)? the tables\b|\bbehind the screen(s)?\b|\bcup of (tea|coffee)\b|" \
         r"\bnot my cup of tea\b|\bpot of (tea|coffee|gold)\b|\bpay(s|ing)? the bills\b|\braises? the alarm\b|\bfalse alarm\b"


def syn_find(text):
    """objects a line names: ["washer", "kettle"] (longest synonyms first so 'folding table' beats 'table').
    A WEAK synonym counts only as a plain noun (see _plain_noun)."""
    import re
    text = re.sub(IDIOMS, lambda m: " " * len(m.group(0)), text, flags=re.I)
    hits = []
    for n, e in sorted(C.items(), key=lambda kv: -len(kv[1]["syn"])):
        if n not in hits and any(_plain_noun(text, m) for m in re.finditer(r"\b(" + e["syn"] + r")\b", text, re.I)):
            hits.append(n)
    return hits


def plausible(name, style):
    p = C.get(name, {}).get("places", "*").split()
    return "*" in p or (style or "") in p
