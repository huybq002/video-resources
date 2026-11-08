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
