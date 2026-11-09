# Film language (measured on the reference films, 2026-11-08)

Reference: the IfverseTales channel ("What If Your Reaction Time Was 10x Faster?", 4.6 M views, 433 s;
"Everyone Has a Power Level. Mine Is 1.", 606 s) and the Stickman Survival Guide short (12 s, 469 k views).
Measured with ffmpeg scene detection and silence detection against our 2026-11-07 night video.

| | ours (003) | Reaction Time | Power Level | stickman short |
|---|---|---|---|---|
| average shot | 7.9 s | **2.8 s** | 5.2 s | continuous action |
| time with no voice | **37-47 %** | 0 % | 0 % | 5 % |
| framings | one: hero centre, facing camera | establishing wide, over-the-shoulder, insert on hands/objects, top-down, silhouette, close-up | wide office, close-up, insert | insert on hands, wide |
| action | almost none | sits, drinks, reaches, catches, walks, hands over flowers, kicks a ball, games at a PC | sits at desk, mops, sits at a bar | carries, kneels, lights fire, roasts, eats |
| on-screen graphics | captions only | timer "0.25 s", EYES -> BRAIN -> MUSCLES diagram, "VICTORY x28" | power numbers over heads, "LEVEL 1" badge, comparison scale | "YUM" |
| title card | none | after the cold open | after the cold open | none |

## What to do, and how the skill does it

1. **Cut every 2.5-3.5 s.** One line = one shot, and a line over ~9 words gets a second angle. A line that names an
   object cuts to an **insert** of that object in its second half (automatic when the line has `props`). `spec_lint`
   warns above 4.5 s per shot.
2. **No dead air.** The planner uses the measured speaking rate, capped by the caption reading rule (`srt_tools.SPEECH_RATE`, en 3.3 w/s);
   write ~3 words per second of scene in English. Our first night assumed 2.55 and left 37 % of the film silent.
3. **Open every scene on the place** (`shot: "establish"`, automatic on a scene's first line), then go closer.
   Use `ots` (over the shoulder) for two people talking, `insert` for objects, `cu` for the reaction.
4. **Characters act all the time.** Every line that says someone does something has `do`. Prefer the film actions:
   sit, stand, run, jump, fall, lie, sleep, pickup, type, drink, phone, throw, crouch, panic, walkTo.
5. **Show the idea, not only the people.** Every number the narrator says is a `hud` counter or chip; a rule or a
   mechanism is a chip or a title; the premise gets a **title card** (`hud` type `title`) at the end of the hook.
6. **Smooth characters.** Limbs are single round-capped tubes with no visible elbow or knee (the reference style);
   no long trousers.
7. **Real places.** Furniture the characters use sits at their depth (z about +1, see scene-dsl.md), decor behind;
   a dusk or night grade with warm window light reads like the reference films.

## More from the dense frame study ("I Have 100% Luck", "One Second Felt Like Forever")
- **Dialogue is shot over the shoulder** almost every time: the listener's back, large and dark at the frame edge,
  the speaker in the middle. `dialogue` sequences now alternate this with close-ups and the two-shot.
- **Every figure has an edge light** that separates it from the background (`rim`, on by default; `"rim": false` to turn off).
- **Diegetic screens carry the plot**: a trading app showing "Balance $9,000,000 +10,000 %", a lottery ticket, a speed graph.
  Use the `screen` HUD: `{"type":"screen","app":"Ribbit","label":"Balance","value":"$9,000,000","trend":"up"}` on an
  `insert` shot of a phone or laptop.
- **Time jumps and parts are captions**: chip "TWO DAYS EARLIER", title "FINAL PART".
- **Comparisons are split screens** (normal eye | max): a `split` shot (spec-schema.md).
- **Big rooms are full of people**: a `crowd` in an exam hall, an office floor, a bus stop.
- **Long, slow camera moves** carry slow-motion moments instead of cuts (the stadium opening): `cam: "push_slow"` on a wide.

## Story shape that works on this channel type
"What if you ..." in the second person, one concrete measurable premise (10x faster, 500 IQ, level 1, day 1 -> day 28),
escalate it scene by scene, show it as a game mechanic on screen (numbers, levels, timers), pay it off, end on the
question. Titles: "What If You ...?" with the number in it.


## Acting and staging (6 fps study of the store, subway, bar and lab scenes, 2026-11-08)
- **Act small.** Over 4 s a character in a reference shot barely moves: eyes shift, the head tilts a few degrees, one
  hand lifts a ticket. One meaningful action per shot, never a gesture on every line. The coverage now adds a small
  look/nod/think on about a third of narration shots and no random walking; speakers gesture only on long lines.
- **Two people talking are shot side-on, facing each other** in the wide/two-shot (both in profile, `face`), then
  over the shoulder (the listener's back big and dark in the foreground), then close-ups turned three-quarter.
- **Groups are a tableau**: a row of people at different heights and poses (sitting on a bench, standing at a pole,
  leaning on a counter), each with something in hand, the camera trucking slowly sideways. Use `crowd` plus 2-3 cast
  members with their own actions, and `cam: "pan_left"`.
- **Stagger depth**: never line everybody up on one baseline; the person who matters is nearer and larger.
- **Use the furniture**: people sit on stools, lean on counters, lie on beds (`sit@chair`, `lie@bed`, anchors.py), and the
  pose holds across the cuts of the scene.
- **First-person inserts**: a hand from the frame edge holding the object (a ticket, a phone) - an `insert` with the prop
  large and low in frame.


## Devices from "One Second Felt Like Forever" (frame study 2026-11-08)
- Flashbacks are graded warm and hazy (`"look": "flashback"`); night scenes get a cool blue rim on every figure (the rim
  light now follows the setting's time of day).
- A decision or a confession is lit by one cone of light in the dark (`"spot": true`).
- Bedrooms and labs are also shown from above (`"angle": "high"`), and the hero from below in moments of power (`"low"`).
- Objects are shown first-person: a hand from the frame edge holding the photo, the tablet, the phone (automatic on inserts).
- Progress is a full-frame stat panel with a rising line and labelled points (`graph` HUD), the number big in the corner.

## Logic and framing rules (study of Stick Saga, IFNation, The If Lab, Nobody Gets In + the five reference films, 2026-11-09)
The tool enforces these by itself; a spec does not have to ask for them.
- Turned people are drawn in 3/4, not as a plank: chest a little narrower, one arm on each edge, two legs apart,
  both eyes shifted toward the direction they face, ear and the hair mass at the back of the head.
- Nobody is ever hidden by someone else. A main character who would stand on top of another steps aside; a background
  person who overlaps a main character leaves the shot (no second head sticking out behind the hero).
- Background people support, never crowd: not at the hero's table, the far side of the room first, at most 3 (9:16)
  or 5 (16:9) in frame, out of focus in medium and close shots.
- Furniture between the camera and a person covers them: a chair seen from behind hides the sitter's back (the
  backrest is cut from the rendered background, so colour and outline match exactly).
- People and the furniture/floor they use move as one under camera moves (no sitter sliding off a chair, no feet
  skating); parallax only between far walls/sky and the blurred near foreground.
- An object put down lies flat on the surface; an object being used is in the hand, drawn inside the hand so it
  follows the arm (phone at the ear, cup at the mouth); an action brings its object (type -> desk + computer/laptop or
  a phone, drink -> cup, phone -> phone).
- An insert (screen, clock, object with nobody in frame) is a close shot: the room behind it is a soft blur.
- Walking has a goal: "walks (back) to Ana" goes to Ana, stops beside her, both turn to face each other; a walk never
  leaves the frame; where a walk ends is where that person stands on the next line; a line that names someone puts
  them in the shot; "they" puts everyone of the sequence in it.
- Conversation: in every framing the two turn toward each other (3/4), never to the lens; the other person in a
  close-up is a soft foreground shape.
- Faces: the speaker's face fills the frame for part of the line (CU), a feeling line gets a slow push in, a shock
  line an extreme close-up on the eyes (ECU); a master/two-shot held for a whole line cuts in to the speaker's face.
- A held pose (lying, seated) is already there on the first frame of every shot (no one-frame flash of standing).
- The moment a power fires: white flash + action lines + rings rippling from the person (`"trans": "power"`).
