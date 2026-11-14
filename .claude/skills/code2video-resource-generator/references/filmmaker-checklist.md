# Filmmaker's checklist (read before writing a spec; the night job checks every point)

Written 2026-11-14 after the owner watched video 007 ("The Balance That Never Moved") and listed what made it look
cheap:
- every story uses the same 3D rooms;
- the words do not match the place on screen;
- there is no music and no sound, and the voice reads every line flat;
- characters lose their eyes.

A short film is judged in its first 30 seconds by people who do not know why it feels wrong. This page is what a
director, a production designer and a sound designer would check before shooting. Each point names the tool that
enforces it.

## 1. Pre-production: location scouting (production design)

- **List every place the story happens BEFORE writing lines.** Read the idea and ask where each beat physically
  happens: home, work, the place the problem shows up, the place it is solved.
  - A nurse works on a ward; a cinema story needs a screen and seats.
  - A money story shows the shop, the bank, the kitchen table with the bills.
  - Write `spec.settings` from that list.
- **Design each place yourself: there is no menu.**
  - Every setting has `place` (what it is in this story), `signature` (2-3 recognisable objects), a shell `set` and 5+
    `objects` of your own built from primitives, furniture macros and Kenney models.
  - The worked example (a hospital ward) is in set-design.md.
  - Never stand in a near place: a ward built as a lab, a cinema as a meeting room.
  - What you cannot build goes in `needs_owner` and the owner makes it.
  - `place_lint.py` enforces all of it.
- **Every film has its own rooms.**
  - generate.py seeds each setting from the film id. The seed changes the wall and floor tint, the window side, the
    ceiling (panels / pendants / beams / plain), the wall finish (plain / wainscot / tiles / stripes / brick) and the
    camera angle.
  - Do not copy a setting block from an earlier spec: describe the place this story needs.
- **Time of day is a choice.**
  - Night interiors keep their own colours (lamps), they are not all violet.
  - Use day for ordinary life, dusk for the turn, night for worry.

## 2. Blocking: the words and the picture agree (director)

- **A line that names a place is shot in that place.**
  - Give the line `"at": "<setting>"`, and include that setting in the sequence's `settings`.
  - `place_lint.py` warns: "the line ... happens in a hospital, but the shot shows a shop".
  - Lines only talked about ("she never went to the gym") are exempt.
- **Open each new place on a wide establishing shot**, people small in it, then move closer.
- **Two people talking: both are on screen at least once per exchange** (`ots` / two-shot).
  - The listener reacts: never a row of single faces.
- **The face in focus is always sharp, and so is the other person.**
  - No blur on main characters, ever: a blurred face reads as a face with no eyes.
  - Depth of field belongs to the set and the extras only (build_project.py).
- **Over-the-shoulder: the back of a head shows hair and skin**, never a black disc (characters_stick.py back view).
- **Titles stay inside the frame**: they break between words and shrink when long (build_project.py).
- **Continuity**: same clothes, same props in hand, same side of the frame across a cut (`logic_check.py`).

## 3. Sound: a film is never silent (sound designer)

Layers, bottom to top. The pipeline adds every layer; the writer only has to give it what it needs.

| layer | what | made by | what the writer gives |
|---|---|---|---|
| room tone | the air of each place: hum, traffic, murmur, monitor beeps, a clock | `ci/score.py ambience`, from each shot's setting | a clear `place` text and setting id per place |
| sound effects | cuts, steps, keys, pops, stings on the picture's beats | `ci/add_sfx.py` from `assets/sfx_cues.json` | `do` actions, props, `hud` beats |
| music | an original score that follows the scenes: mood, setbacks darken, the end resolves | `ci/score.py score` via `add_music.py` when the library has no licensed track | `mood` on sequences, `value` +/- on scenes |
| voice | each character a different voice; each line acted | edge-tts conversational voices + `assets/voice_direction.json` | `emote` on every line that carries a feeling |

- **Act every line.** Put `"emote"` on any line with a feeling: joy, surprise, worry, doubt, sad, angry, relief,
  think, tired, excited.
  - The voice changes pace, pitch and loudness from it (tts.py `PROSODY`).
  - Questions rise and short lines land slower by themselves.
  - The narrator colours a line; the characters act it.
- **No line read flat twice in a row**: alternate feelings and lengths the way a person talks.
- **Silence is a choice, not a gap**: a pause before a reveal is fine; 20 % of the film with no voice is not.
  - Write about 2.7-3 words per second of scene. The lint's `silence:` warning is a defect, not a style.

## 4. Characters (animation)

- **Eyes are the performance.** Every main character's face is readable in every shot it is in:
  - no blur;
  - not cut by the frame edge in a close-up;
  - not hidden behind furniture (`logic_check.py`: focus-off, cut-off, in-furniture).
- **Faces react on the line, not after it**: `emote` changes the face on the cue; listeners react.
- **Scale and floor**: same person, same depth, same size; feet on the floor (`logic_check.py`).

## 4b. Rhythm and sound craft

- The picture hands the stage to a new main visual at every beat: `references/event-relay.md`, checked by `relay_lint.py`.
- Sound has three functional layers with a reason for each cue: `references/sound-script.md`, recorded in
  `assets/sound_manifest.json` by `add_sfx.py`.

## 5. Before the render: the director's pass

Look at the frames of every scene (the snapshot step), as a viewer who has never seen the script:
1. Can I tell where we are in one second?
2. Does what I hear match what I see?
3. Do I see the face of whoever is speaking, with eyes?
4. Is there always something to hear: room, effect, music, voice?
5. Would I know this film from the last one by its rooms alone?

Any "no" goes into the report with the frame time, and gets fixed before the night's video ships.
