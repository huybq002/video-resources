# Planning the script and scenes (idea + length → scene plan → script.srt)

The user gives an idea and a length (e.g. 8–10 minutes). The result must have **many scenes, each with its own duration, adding up exactly to the requested length**, and every scene must have enough text to fill its time.

## 1. Fix the budget first
| Length | Scenes | Seconds per scene | Cues (≈ lines) | Words in total |
|---|---|---|---|---|
| 1 min | 2–3 | 20–30 | 14–18 | 150–170 |
| 3 min | 6–8 | 22–30 | 45–55 | 430 |
| 5 min | 10–12 | 24–30 | 75–90 | 720 |
| 8 min | 16–20 | 24–30 | 120–140 | 1150 |
| 10 min | 20–24 | 24–30 | 150–175 | 1450 |
Rules: duration_s = sum of scenes[].target_s (to the second). Speaking rate ≈ 2.55 words/s → **words per scene ≈ target_s × 2.4**, i.e. about 5–6 words per second of two-cue pair; a 27 s scene needs ≈ 65 words, not 50. **English: aim for ≈ 2.7 words/s (target_s × 2.7), not 2.4.** Measured 2026-11-12 on two full specs: 2.48 w/s (743 words / 300 s) still left 17 % silence, 2.69 w/s (808 / 300 s) left 10 %; first drafts written to 2.4 came out at 1.8-2.3 w/s. Count words per scene before the first build, and split any cue over 12 words in two so a shorter scene target does not break its reading minimum.

**Dead air is the number-one defect.** The voice-over is one clip per cue placed at the cue's start: if the text is shorter than the window the scene simply runs on in silence. `generate.py` prints `WARNING: scene N target 27s but its text naturally takes 20s (33% of the scene would be silent): add about 15 words` and a closing `silence: about X%` line. **Aim for under 8 % and never ship over 12 %.** Write more lines rather than longer lines, and cut `target_s` for a scene that genuinely has little to say.

A cue is one sentence or one line of dialogue (≤ 14 words, ≥ 0.5 s + 0.3 s per word on screen). The last cue of a scene must stay ≥ 2 s.

## 2. Write the scene plan before any line of script
For every scene: `id`, `title`, `goal` (what changes for the story / what the viewer learns), `target_s`, setting(s), characters present, mood, the 1–2 key visual beats. Put them in the spec (`scenes[].title / goal / target_s`). Typical shape for a story film:
1. Hook scene (≈ 20–30 s): strongest image/line, open loop, no greeting.
2. Setup (2–3 scenes), rising action (60 % of scenes, each ends on a small turn or question), turn/twist (2–3 scenes, with clues planted earlier), resolution (2 scenes), takeaway + CTA scene (≥ 20 s, a question for the comments).
3. A new fact, question or reversal every 30–45 s, i.e. about every scene; vary place and mood from scene to scene.
4. Dialogue scenes use `sequence: dialogue` (speaker per line), connective narration uses `sequence: narration`; hand-write only the key moments.
5. **Every scene needs its own picture.** Decide the place, the time of day and who is on screen per scene, and make at least 60 % of the scenes visually distinct (own setting, or the same place changed by weather, damage, light or crowd). A scene that reuses a setting must at least change the camera and what is happening in frame. `generate.py` warns when the settings are too few or one setting carries more than a third of the film.
6. **Whoever the script mentions must be visible.** If the lines say "everyone", "they", "the crowd", "the zombies", "hundreds of them", put them on the screen: named cast for the ones who matter, a `crowd` block (spec-schema.md) for the mass. Narration over an empty street is the most common way these films turn boring; `generate.py` warns about it.
7. **Long scenes get more than one shot.** Over ~15 s, split the scene into 2–3 shots: a wide that establishes, a medium on the action, a close-up on the face or the object that matters. A single static shot for 27 s reads as a slideshow.

## 3. Write the lines to the budget
- Count words per scene while writing: target = target_s × 2.4, tolerance −12 % / +12 %. Re-run `generate.py` until no WARNING is left; the lines it prints say exactly how many words to add or cut.
- Write the lines in scene order and read them aloud in your head: concrete nouns, one image per line, no filler like "and so", "as you can see", "in this video". A line that adds no new fact, feeling or question is cut, and the time goes to a line that does.
- Speaker names: cast `id` is the file name (`an` → `assets/an.svg`), cast `name` is what appears in `script.srt` (`[An]`). Narration uses the cast entry `{ "id": "narrator", "name": "Người kể", "narrator": true }` (no body on screen).
- Never write numerals the TTS may misread; write numbers as words. Vietnamese with correct diacritics.

## 4. Output
`generate.py` writes `script.srt` (contiguous, exact total, per-scene durations = target_s), the project, and, next to it, `<project>_docs/scene-plan.md` (table of scenes with times, goals and every line) so the user can review the story before rendering.
