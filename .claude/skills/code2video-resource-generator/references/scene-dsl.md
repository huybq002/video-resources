# Setting DSL (3D toon backgrounds → assets/bg_<id>.png, 1920x1080)

World units are metres; ground y=0; camera looks toward −z. Objects sit on the ground by their base: `y` = bottom, `h` = height.

```jsonc
{ "sky": ["#top", "#horizon"],  // outdoors; or "bg": "#solid" for interiors
  "fog": {"near": 18, "far": 70, "c": "#…"}, "stars": 120, "moon": {"x":-18,"y":19,"z":-60,"c":"#e9ecff"},
  "ambient": {"c": "#5a66c8", "i": 1.3}, "sun": {"c": "#7f8fff", "i": 0.9, "pos": [-6,10,6]},
  "ground": "#232a45",          // omit for interiors and add a floor box
  "exposure": 1.25,
  "camera": {"pos": [0,2.1,9.5], "look": [0,2.4,-4], "fov": 42},
  "objects": [
   {"t":"box","x":-9,"y":0,"z":-3,"w":7,"h":14,"d":16,"c":"#2c3358","ink":0.035,"ry":0,"rz":0},
   {"t":"cylinder","x":0,"y":0,"z":-5,"r":0.3,"h":1,"c":"#…"}, {"t":"sphere","x":0,"y":1,"z":-5,"r":0.4,"c":"#…"}, {"t":"cone","x":0,"y":3,"z":-5,"r":0.5,"h":0.6,"c":"#…"},
   {"t":"glow","x":2,"y":1.6,"z":-1.7,"w":0.9,"h":0.6,"c":"#fdf7e6","ry":0},   // unlit emissive quad: windows, screens, signs
   {"t":"disc","x":-5,"y":6,"z":-4.4,"r":0.75,"c":"#f4efe0"},                  // clock face / moon-like disc (unlit)
   {"t":"lamp","x":2.2,"z":-7,"h":4.2,"c":"#ffb45a","I":22,"dist":16},        // street lamp: pole + bulb + point light + halo
   {"t":"light","x":3.5,"y":1.2,"z":-3,"c":"#ff8a3a","I":180,"dist":18,"decay":1.5},
   {"t":"prop","n":"tree_oak","x":9.5,"y":0,"z":-1,"s":2.1,"ry":0.4,"tint":"#4e6a62"}   // Kenney CC0 model from assets/kenney-glb
  ] }
```

**Furniture — use it, a room is recognised by its furniture, not by its wall colour.**
`{"t":"furn","n":"bed","x":1.5,"z":-5,"ry":0.3,"s":1,"c":"#5b6f9a","c2":"#8a5a3c"}` expands into primitives (`scripts/furniture.py`).
Names: `bed bedside_table desk computer chair sofa table bookshelf kitchen_counter oven fridge window night_window door tv
lamp_floor plant rug picture wall_clock shop_counter shelf_goods car bench trash_bin building street_sign fence crate barrel whiteboard`.
A bedroom has a bed (+ bedside_table, night_window, rug); a kitchen has kitchen_counter + oven + fridge; an office has desk +
computer + chair; a shop has shop_counter + shelf_goods; a living room has sofa + tv + lamp_floor. Put the key piece where the
camera sees it (z between -3 and -7, x within ±3), keep the lower middle free for the characters. `spec_lint.py` fails a line
that talks about sleeping, cooking, a desk, a shop... when its setting does not contain the matching furniture.

Depth layers (parallax like the reference videos): add `"layers": [11, 22]` = split distances in metres from the camera. The renderer then also writes `bg_<id>_far.png` (the full opaque scene, so no holes ever show when layers slide apart), `_mid.png`, `_near.png` (transparent, foreground); the build stacks far → mid → characters → near and moves them at 0.35× / 0.7× / 0.85× / 1.2× of the camera move, so push-ins and pans have real depth. Put foreground props closer than d1 (small fences, plants, posts), buildings between d1 and d2, backdrop beyond d2. Skip `layers` for interiors whose walls are < 12 m away.

Tips
- Keep the lower-middle free for characters (feet at screen y≈900 ⇒ ground between z≈−1 and z≈−6 in front of the camera) and the bottom 25 % for captions.
- Night: low ambient + saturated blue/violet, 1–3 warm lamps/windows, stars/moon. Golden hour: sky `#2c2253 → #e0875a`, warm sun. Interior: `bg` colour, floor + back-wall boxes, one warm `light`, shelves/clocks/windows as boxes/discs/glows.
- Boxes get black ink outlines (inverted hull). Use `ink: 0` for tiny details.
- Props: `ls assets/kenney-glb` (tree_*, plant_*, fence_*, rock_*, log*, campfire_*, tent_*, crop*, flower_*, grass*, bridge_*, path_*, sign, statue_*, bed …). Unknown name = silently skipped. `tint` multiplies the model colour.
- Reuse one setting in several shots (cameras differ) instead of near-duplicates.
