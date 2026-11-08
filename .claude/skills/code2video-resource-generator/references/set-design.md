# Set design: places that look like places

Measured from frames of the reference channel (IfverseTales: "I Have 100% Luck", "Reaction Time", "One Second Felt Like
Forever", the stickman Shorts) next to our own night-job videos (2026-11-07/08).

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
- `style` (room): `bedroom office lab kitchen living classroom cafe shop`; (shopfront): `cafe shop office`.
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
