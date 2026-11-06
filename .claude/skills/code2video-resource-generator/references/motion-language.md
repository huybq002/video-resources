# Motion language of the reference videos (measured from frames)

Source: 4 reference explainer videos made with HyperFrames (1920×1080, 30 fps, 7–8 min), inspected at 1 fps (≈1,500 frames, contact sheets), at 10 fps on ≈14 motion segments, plus scene-cut detection. Numbers below are measured; "→" says how this skill reproduces it. Original characters/stories only — copy the *techniques*, never the characters, logos or scripts.

## 1. Rhythm
- Hard-cut density (ffmpeg scene > 0.3): median shot 2.3–2.6 s, mean 3.8–7.3 s, p10 0.8 s, p90 8–23 s, longest single move 28–45 s. So: many short cuts + a few long "camera travel" shots (pan down an apartment facade, push through a street, orbit a table).
- Something visibly changes every 1–3 s (cut, camera accent, counter tick, label pop, character beat). Nothing is ever static: even holds have a 0.1–0.3 %/frame push-in.
- A reveal = cut to close-up + chip/label + sound beat; a gag = quick cartoon burst ("POW" starburst) + body tumble + cut away within ~1.5 s.
- → `shots[].cam` always moves; use ≥ 5 shots per 30 s; `cut:true` for punchlines; `overlays` for chips/counters.

## 2. Camera (all scenes are lit 3D-looking spaces, camera always travelling)
| Move | Look | Typical values | → spec |
|---|---|---|---|
| Slow dolly-in | holds & dialogue | scale 1.00→1.10–1.14 in 4–8 s, drift ±30 px | `cam:"push"` |
| Pull-back reveal | establishing | 1.16→1.04 | `cam:"pull"` |
| Lateral track / pan | street, facade, wall of posters | ±60–200 px over 5–10 s | `pan_left/right` |
| Punch-in | revelation, joke | 1.10→1.28 in ~1 s | `cam:"punch"` |
| Parallax travel | corridor/street depth | far layer moves 0.2×, mid 0.5×, near 1× | `layers:true` setting |
| Whip pan | scene change | 0.2–0.3 s horizontal smear (blur 30–60 px + translateX) | `trans:"whip"` |
| Zoom-through | into a window/phone/screen/photo → next scene | scale ×6–10 + fade, 0.5 s | `trans:"zoom"` |
| Impact shake | tumble, slam | 6 flips, ±12 px, decays in 0.25 s | `shake:[t]` |
- Rack focus / depth-of-field on close-ups (background softly blurred), bloom/god-rays on sun and lamps, strong vignette, warm-vs-cool split lighting. → `.vig`, `rays` overlay, setting lights.
- Dutch/low angles for drama (camera at 0.5–1 m looking up at the crowd); bird's-eye and top-down for scale (city grids, tile counters).

## 3. Transitions (≈ 40 % hard cut, rest effects)
hard cut · cross-dissolve 0.4 s · whip-pan smear · white flash (2–3 frames, after a punchline or at a time-jump) · zoom-through into a screen/window/photo · "photo/frame" transition (scene shrinks into a framed polaroid then becomes the next scene) · LED/dot-matrix wipe · dip to near-black before a title card · fade-through-white for flashbacks/sepia.
→ spec `trans`: `cut | fade | whip | flash | zoom | dip` (applies on entering the shot).

## 4. Information graphics (HUD language — this is what makes it feel "produced")
- **Counters**: big numerals counting up/down with ease-out, gold glow (#E8B84A), tabular/monospace or serif numerals; units under in small caps. Often paired with a pill chip.
- **Chips / lower-thirds**: rounded pill, dark translucent fill, 1 px light border, 22–28 px caps, ~0.3 s pop-in (y +12 → 0, opacity 0 → 1) and 0.2 s out; used for stat callouts ("2 IN 3 … ARE …"), place+time tags ("TOKYO · 2:14 AM"), chapter cards ("1 · THE MORNING AFTER"), name tags.
- **Title cards**: LED dot-matrix text typed in 2–3 s on a dark navy dotted background, or big gold serif on black.
- **Charts**: axes fade in, a line draws with a glowing leading dot while a counter above counts; world map with pulsing points / arcs growing to a "project" pin.
- **Speech**: comic bubbles typed character-by-character (≈ 25 chars/s) with a tail; starburst SFX balloons ("CRACK!", "IT'S A …!") scale-pop 0.6→1.1→1 with slight rotation; hearts/sparkle particles float up for "love" beats.
- **Screens inside the scene**: news-desk with map, phone call UI, chat feed, TV; camera pushes into them for the transition.
- **Captions**: small sentence-case subtitle strip, bottom third, white with thin dark outline; keywords highlighted in warm yellow. → `captions` already; highlight via `**word**`? (not implemented — plain text).
→ spec `overlays: [{type:"chip"|"counter"|"burst"|"bubble"|"title", …}]` (see spec-schema).

## 5. Characters (flat-lit toon "bean/black-sphere head", NO mouths)
- Head: pure black sphere with soft top-left specular; eyes = two white ovals/pills (or ^ ^ arcs for joy, slanted wedges for anger, half-lids, hearts for love, tears for sad); optional tiny cheek dots. Emotion comes from eyes + brows + head tilt + posture, not lip-sync.
- Body: thin capsule limbs, small mitten hands, clothes = few flat shapes with a subtle gradient + a thin warm rim-light (glow 4–8 px) on emphasis. Heads 1/4–1/5 of height in hero close-ups, smaller (1/8) for crowds.
- Acting vocabulary: breathe/idle sway, blink every 2–5 s (4 f), walk bob 3–6 %, lean 1–7°, arm gestures lagging the torso, jump-back surprise, tumble, slow nod, shrug, point, clap, hug. Hands/props animate separately (tail wag, hair sway).
- Crowds: 50–500 simplified instances, per-instance colour variation, desynchronised bob/sway, placed in perspective rows; often the camera flies over them.
→ `characters.py` eye states (`happy`, `heart`, `angry`, `sad`), `acts`, `crowd` prop, `glow:true`.

## 6. Colour & light
Each location has one signature palette: night city = indigo/violet + warm window dots + neon accents; golden hour = peach horizon, violet shadows, backlit sun bloom; hospitals/labs = cold white-blue; interiors = one warm lamp in a dark room. Hero colour for the protagonist (teal) stays constant across scenes. Dark navy HUD backgrounds with gold numerals. Saturated midtones, ink-free (no outlines) in the 3D-lit shots; thin outlines only on the flat 2D stick-figure sections.

## 7. Layout rules
Subject on thirds; wide establishing shot first, then medium, then close-up; characters ≤ 3 per shot except crowds; keep the bottom 25 % free for captions and the top-left/top-centre for chips.

## 8. Style variants seen
A) lit 3D-toon world with camera travel (most scenes) B) flat 2D stick figures on gradient/infographic backgrounds with animated dots and diagrams (science explainer) C) pure UI/HUD screens (maps, counters, charts). A single video mixes them: use B/C to explain, A to dramatise.

## 9. Per-video measurements (shot stats from ffmpeg scene > 0.3)
| Video (length) | hard cuts | median shot | p90 | longest | notes |
|---|---|---|---|---|---|
| Drama-explainer 1 (494 s) | 55 | 2.3 s | 23 s | 45 s | many continuous camera travels; HUD counters, map, news desk, crowds of hundreds, whip pans between cities |
| Drama-explainer 2 (488 s) | 113 | 2.6 s | 8 s | 29 s | dialogue scenes with bubbles, props gags (tank, bear), gameshow overlay, sepia/colour grade changes |
| Science explainer, flat 2D (418 s) | 16 | 8.2 s | 48 s | 91 s | flat stick figures; diagrams build up in place (gene dots, pair columns), slow push-ins, chip labels; long holds are filled by diagram animation |
| Science explainer, lit 3D (482 s) | 71 | 3.6 s | 16 s | 31 s | split-screen two-column comparison with a colour grade per side (cool teal vs warm pink), mission-control HUD, gauge dial, scoreboard pill, thought-cloud/ZZZ particles, grids of thousands of units (beds) in perspective, confetti, "REC / FILTER" camera-UI overlays |
Takeaways: (1) the more abstract the narration, the longer the shot but the busier the diagram inside it; (2) explainers alternate *world shot → close-up → data card* every 8–15 s; (3) split-screen (two settings side by side, each with its own colour grade) is the standard way to compare two things; (4) unit charts (hundreds of identical small figures/icons filling a grid, counted up) show "scale"; (5) a persistent mini scoreboard/HUD pill in a screen corner tracks a running tally.
→ Split-screen: `shots[].split` (two panes, each its own setting, characters and colour tint). Unit charts: use `crowd` with a high `n` and tight `by` range; scoreboard pill: a `counter` overlay with `pos:"tr"` kept across shots.
