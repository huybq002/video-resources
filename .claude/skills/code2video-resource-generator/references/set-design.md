# Set design: places that look like places

Measured from frames of the reference channel (IfverseTales: "I Have 100% Luck", "Reaction Time", "One Second Felt Like
Forever", the stickman Shorts) next to our own night-job videos (2026-11-07/08).

## Design every place yourself (owner rule, 2026-11-14)

There is no menu of places. Before writing lines, read the story and list where each beat physically happens. Then
DESIGN each place the way a production designer would, for THIS film:
- a ward for a nurse;
- the bakery with its till;
- the cinema with its screen;
- a bus at night;
- a courtroom.

The stock `style` rooms (bedroom, kitchen ...) are only shells with default furniture. Every film that used them alone
looked like the last one (videos 003-007).

Each setting:

```jsonc
"ward": {
  "place": "night ward of a small city hospital: two beds behind curtains, a lit nurse station",   // what it is in THIS story
  "signature": ["drip stand", "heart monitor", "bed curtains", "nurse station"],                  // recognisable in a close-up
  "set": {"type": "room", "style": "generic", "time": "night",                                   // the SHELL
          "wall": "#cfe0de", "floor": "#9fb2b0", "window": "left", "finish": "tiles", "ceiling": "panels"},
  "objects": [                                                                                    // the design
    {"t":"furn","n":"bed","x":-4.2,"z":-2.6,"c":"#e8eef0","c2":"#9aa7ad"}, {"t":"furn","n":"bed","x":-1.4,"z":-2.6,"c":"#e8eef0","c2":"#9aa7ad"},
    {"t":"box","x":-3.0,"y":0,"z":-2.6,"w":0.06,"h":2.4,"d":2.4,"c":"#9fc9c4","op":0.9},          // privacy curtain
    {"t":"cylinder","x":-5.1,"y":0,"z":-3.4,"r":0.03,"h":1.9,"c":"#b9c2c8"},                      // drip stand pole
    {"t":"box","x":-5.1,"y":1.75,"z":-3.4,"w":0.22,"h":0.32,"d":0.06,"c":"#cfe9ff","op":0.85},   // drip bag
    {"t":"box","x":-2.3,"y":1.5,"z":-5.8,"w":0.55,"h":0.4,"d":0.06,"c":"#15121c"},              // monitor on the wall
    {"t":"glow","x":-2.3,"y":1.55,"z":-5.76,"w":0.48,"h":0.32,"c":"#3fc46e"},                   //   its green trace
    {"t":"furn","n":"shop_counter","x":3.0,"z":-0.6,"c":"#d9e4e8"}, {"t":"furn","n":"computer","x":2.6,"z":-0.8,"y":0.95},   // nurse station
    {"t":"glow","x":3.0,"y":2.8,"z":-5.8,"w":2.2,"h":0.45,"c":"#e35d4f"},                        // station sign
    {"t":"furn","n":"sink","x":4.8,"z":-5.5}, {"t":"furn","n":"plant","x":6.2,"z":1.6}
  ]
}
```

**What you build with**:
- primitives: `box`, `cylinder`, `sphere`, `cone`, `glow` (screens, signs, windows, light), `disc`, `grad`, `lamp`,
  `lamp_hang`, `light`; `op` for glass and see-through cloth; `rx`/`ry`/`rz` to turn them;
- the furniture macros (`{"t":"furn","n":...}`, scripts/furniture.py): bed, sofa, chair, table, desk, computer, tv,
  counters, shelves, fridge, oven, sink, washer, bathtub, toilet, whiteboard, projector_screen, podium, car, building,
  fence, door, window, plant, lamps, boxes, papers, mug ...;
- the Kenney models (`{"t":"prop","n":...}`, assets/kenney-glb): trees, rocks, tents, fences, signs, statues, crops,
  campfires, canoes, bridges, cliffs.

**Scale**:
- the floor is y=0;
- characters stand at z about 0.5-1.5;
- the back wall is z=-6 and the ceiling is y=4;
- the room is 14 m wide (x from -7 to 7);
- a person is about 1.65 m tall, a door 2.1 m, a table 0.75 m, a counter 1.0 m.

**Shell keys**:
- `wall` / `wall2` / `floor` / `ceil` colours;
- `window` (left | right | center | none);
- `ceiling` (panels | pendants | beams | plain);
- `finish` (plain | wainscot | tiles | stripes | brick);
- `time`.

The film seed varies everything you leave out (tint, window side, ceiling, finish, camera angle). Exteriors start from
`street` / `shopfront` / `beach` shells and get their own objects in the same way.

**When it cannot be built**, do not fake it with a near place: a ward built as a lab, a cinema as a meeting room or a
car interior as an office all look wrong. Examples of what cannot be built: a car or bus interior, an animal, a specific
machine, a crowd stadium. Write

```jsonc
"bus": {"place": "night bus, empty seats", "needs_owner": "a bus interior: seats in rows, poles, windows with the city passing; no bus model in furniture.py or assets/kenney-glb", ...}
```

The lint prints `NOTE: OWNER: ...`, the night job copies it into data/asset-requests.md and the morning report, and
shoots those lines in the nearest honest place it can build (e.g. the bus stop outside). The owner adds the asset by
hand: a GLB model dropped into assets/kenney-glb becomes `{"t":"prop","n":"<file name>"}`, a new furniture macro goes
into scripts/furniture.py.

The lint checks every setting:
- `place_lint.py`: it has `place`, 2+ `signature` objects and 5+ objects of its own;
- every line that names a place is shot in a setting whose place, id or signature says it is that place.

## What the reference frames do

| | Reference films | Our videos before `set` |
|---|---|---|
| Light | One strong source in every frame: a big window with a low sun over a city, a lit shop front, a gas-station canopy at night. Warm light against violet/blue shadow. | Even flat light, no visible source. Grey or purple colour fields. |
| Walls | Dense: posters and diagrams, clock, shelves with objects, screens, ceiling light panels, curtains. Any crop still reads as a room. | One wall box. A close-up showed an empty purple wall. |
| Depth | Three planes: blurred foreground objects at the frame edges (flasks, a desk corner, a plant), the room with the people, the city in haze behind the glass. | Floor box, wall box, characters. |
| Outside | One-point streets: road, lane marks, crosswalk, kerbs, building rows with lit windows, lamps, trees, poles and wires, a car, the skyline and the sun at the end. Night establishing shots of a lit building with nobody in it. | A few boxes and a lamp. |
| People in wides | Small (about a quarter of the frame height) and further back: the place dominates, then the cut to the medium. | As large in the wide as in the medium. |
| Actions | The person does something with the place: walks along the pavement, crouches by the kerb, points at the board, sits at the desk, works at the lab bench. | Standing and gesturing in the middle of an empty room. |
| Close-ups | Background blurred but still a window, a skyline and a sun glow behind the head. | Flat colour behind the head. |

## How to get it: start every setting from a set

```jsonc
"settings": {
  "bedroom": {"set": {"type": "room", "style": "bedroom", "time": "night", "key": {"x": 1.0, "z": 1.0}}},
  "office":  {"set": {"type": "room", "style": "office", "time": "day"},
              "objects": [{"t": "furn", "n": "chair", "x": 0.15, "z": 1.3}]},          // the story's own extras
  "street":  {"set": {"type": "street", "time": "dusk"}},
  "cafe_ext":{"set": {"type": "shopfront", "style": "cafe", "time": "night"}}        // establishing shot, nobody in it
}
```

- `type`: `room` | `street` | `shopfront`.
- `style` (room): `generic` (an empty shell you furnish yourself: the default for a designed place) or a stock shell with default
  furniture `bedroom office lab kitchen living classroom cafe shop laundry meeting bathroom grocery`; (shopfront): `cafe shop office`.
  A stock shell still needs the story's own `place`, `signature` and 5+ `objects` (see the section above).
- `time`: `day` | `dusk` (default; the reference look) | `night`. Use the time the script says ("2 a.m." = night, "nine o'clock" = day).
- `window`: `left` | `right` | `center` | `none` (default depends on the style). `key`: where the style's key furniture stands
  (bed, desk, sofa, table); put it where the character who uses it stands (z ≈ 0.5–1.5 is the characters' depth).
- `fg`: blurred foreground objects at the frame edges (default true for rooms). They go on the near depth layer and are
  blurred by `fg_blur` (top-level, px, default 5).
- `seed`: changes the skyline, posters and building rows, so two rooms of the same style do not look identical.
- Your own `objects` are added on top; your top-level keys (`camera`, `fog`, `exposure`, `layers`) override the set's.

## Rules

1. Every setting starts from a set unless the place is truly special (a ruined city, a cave). A setting with fewer than
   12 objects and no `set` is a lint warning: it will look like a colour block.
2. Match the time of day to the script and keep it across the shots of one scene.
3. Open each scene on the place: the narration's first line is an `establish` shot, and the coverage draws the people
   small and further back in it. For a new location, cut to a `shopfront`/`street` at night or dusk with nobody in it first.
4. Give the person something to do with the set on most lines: `sit` at the desk, `sleep` on the bed, `walkTo` along the
   street, `pickup` from the counter, `type` at the computer (spec-schema.md actions).
5. Use two or three times of day in a film (a day office, a dusk street, a night bedroom). Contrast between scenes reads as
   time passing.


## Scene logic and extras (extras.py)

Before writing a scene, answer three questions from the script, and let the answers pick the set:
1. **Where and when?** The place the line names, the time it says or implies ("2 a.m." = night, "lunch" = day).
2. **Who else would be there?** An office at 9 a.m. has colleagues; a street has cars and people; a cafe has customers
   and a barista; a beach has swimmers and people on towels; a home at night has nobody else.
3. **What are they doing?** Something the place explains: typing at the other desks, drinking coffee, crossing the
   road, swimming, sunbathing - never standing still facing the camera.

The skill does 2 and 3 for you: `extras.py` reads each setting's set type, style and time, and the words of its lines
("alone", "empty", "nobody" -> nobody; "busy", "packed", "colleagues", "people", "traffic" -> more), adds extras to the
cast with clothes that fit the place, and places them on the set: seated at the free chairs (typing / drinking /
listening), behind the counter (legs hidden), browsing the shelves, lying on towels, swimming (cut at the water line),
walking across the floor, crossing the street or walking along the pavement toward/away from the camera, and cars
driving along the lanes. Seated extras keep their seat in every shot of the setting.

| set | day | dusk | night |
|---|---|---|---|
| office | 3 colleagues typing + 1 walking | 1 working late | empty |
| classroom | 5 students | 2 | empty |
| cafe | 3 customers, barista, 1 walking | 2 + barista | 1 + barista |
| shop | cashier, 2 browsing | cashier, 1 | cashier |
| street | 4 on the pavements, 2 crossing, 4 cars | 3, 1, 3 cars | 1 walker, 2 cars |
| shopfront | 3 walking, 1 on the bench | 2, 1 | 1 |
| beach (`{"type": "beach"}`) | 4 swimming, 3 on towels, 2 walking | 1, 1, 2 | empty |
| bedroom / kitchen / living | nobody unless the script brings someone | | |

Override on the setting: `"extras": "none"` (a deliberately empty place), `0.5` / `2` (fewer / more), or an explicit
list `[{"role": "walk", "n": 3}, {"role": "sit_work", "n": 2}]`. Roles: sit_work, sit_drink, sit_listen, behind, browse,
walk, walk_street, cross, swim, sunbathe, traffic, bench.


## Detail and story places (2026-11-09)
- Every room is dressed automatically: things on every desk/table/counter (laptop, mug, papers, desk lamp, books, sticky
  notes; kettle, pot, fruit bowl; alarm clock on the bedside table), a door, a wall shelf, clothes/shoes/boxes on the
  floor by style, and a wall/floor palette per style (bathroom tiles, laundry concrete, grocery white). `sets._dress`.
- New styles for places stories keep visiting: `laundry` (washers in two stacks, folding table, baskets, bench),
  `meeting` (projector screen with a slide, podium, rows of chairs with listeners), `bathroom` (tiled wall, sink and
  mirror, tub, toilet, towel rail), `grocery` (open shelves of goods along an aisle, fridge displays, checkout, boxes).
- New furniture/props for your own objects: washer, folding_table, laundry_basket, podium, projector_screen, sink,
  mirror, bathtub, toilet, towel_rail, wall_shelf, coat_rack, cardboard_box, fridge_display, checkout, door_frame, mug,
  papers, laptop_open, desk_lamp, books_stack, kettle, pot, fruit_bowl, alarm_clock, clothes_pile, shoes, frame_photo,
  sticky_notes (small items take `y` = the surface height).
- A hand-written setting of a few boxes is the failure mode (night 003: five coloured blocks for a laundromat).
  `autofill.py` turns any sparse setting whose id/description names a known place into that set; still, add ONE object
  that belongs only to this story (the evidence board, the pizza box, the slide on the screen) - the reference channel
  dresses every set with the story's own objects.


## Any place, any action: the catalog (2026-11-09)
`scripts/catalog.py` is the one table behind places and actions. Each object says what scripts call it (`syn`), where it
stands (`zone`: back, wall, side, center, floor, surface), its footprint, the places it belongs in, and its affordances
(lie, sleep, sit, work, use + hand act, stand). From it:
- `layout.py` puts ANY catalog object into ANY room at a free spot of its zone (walkway in front of the camera kept
  clear; a desk/table brings a chair; a bedside table goes by the bed, a mirror over the sink).
- `autofill.py` builds places: a dressed style, a `catalog.PLACES` recipe (hospital, clinic, waiting room, library,
  restaurant, bar, hotel, reception, police, studio flat, dorm, garage, warehouse, attic, hallway, bank, pharmacy,
  bakery, salon, gym) as a `generic` room, or a generic room holding the objects its lines name.
  Abstract places (mind, head, thought, dream, nightmare, memory, flashback, void, limbo) not built by the author become
  the `void` style: a dark stage with one pool of light, the objects their lines name standing in it, `dream` /
  `flashback` grade on their lines. Places in another special state (ruined, flooded, haunted, alien...) stay as written.
- Lines become actions through `catalog.VERBS` (verb group -> affordance -> objects that offer it, in preference order):
  the object present in the setting is used, else the first that belongs there is added.
  `use:<act>@<object>` = stand at its front, a little to the side, turned to it, hands doing stir/reach/point/look/type
  for the whole shot (build_project.resolve, any object: the approach point comes from the footprint).
  Negation ("never cooks"), similes ("like a sleeping dog"), nouns ("an hour of sleep") and modals ("could sleep") are not actions.
  Object keys that change the pose: `stand="behind"` (podium: the user stands behind it facing the room, legs hidden by
  it), `via="podium"` (pointing at the slides is done from the podium when there is one).
- Synonyms that are also verbs or idioms (`catalog.WEAK`: tea, notes, screen, board, stage, books...) name the object
  only as a plain noun after a determiner ("her notes", not "she notes" / "phone screen" / "at this stage"); fixed
  phrases in `catalog.IDIOMS` are ignored.
- A seat facing away from the camera (desk at the back wall, audience rows) is drawn from behind, hero and extras alike.
- To support a new kind of scene, add DATA: an object in `C` (+ its primitives in furniture.py), a place in `PLACES`
  + `PLACE_WORDS`, or a verb group in `VERBS`. No per-case code.
