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
Rules: duration_s = sum of scenes[].target_s (to the second). Speaking rate ≈ 2.55 words/s (Vietnamese TTS) → **words per scene ≈ target_s × 2.2** (leaves room for pauses). A cue is one sentence or one line of dialogue (≤ 14 words, ≥ 0.5 s + 0.3 s per word on screen). The last cue of a scene must stay ≥ 2 s.

## 2. Write the scene plan before any line of script
For every scene: `id`, `title`, `goal` (what changes for the story / what the viewer learns), `target_s`, setting(s), characters present, mood, the 1–2 key visual beats. Put them in the spec (`scenes[].title / goal / target_s`). Typical shape for a story film:
1. Hook scene (≈ 20–30 s): strongest image/line, open loop, no greeting.
2. Setup (2–3 scenes), rising action (60 % of scenes, each ends on a small turn or question), turn/twist (2–3 scenes, with clues planted earlier), resolution (2 scenes), takeaway + CTA scene (≥ 20 s, a question for the comments).
3. A new fact, question or reversal every 30–45 s, i.e. about every scene; vary place and mood from scene to scene.
4. Dialogue scenes use `sequence: dialogue` (speaker per line), connective narration uses `sequence: narration`; hand-write only the key moments.

## 3. Write the lines to the budget
- Count words per scene while writing: target = target_s × 2.2 ± 10 %. `generate.py` reports `WARNING: scene N target 27s but its text naturally takes 33s: cut about 14 words`; fix by editing text (or the target) and re-run until no warnings remain.
- Speaker names: cast `id` is the file name (`an` → `assets/an.svg`), cast `name` is what appears in `script.srt` (`[An]`). Narration uses the cast entry `{ "id": "narrator", "name": "Người kể", "narrator": true }` (no body on screen).
- Never write numerals the TTS may misread; write numbers as words. Vietnamese with correct diacritics.

## 4. Output
`generate.py` writes `script.srt` (contiguous, exact total, per-scene durations = target_s), the project, and, next to it, `<project>_docs/scene-plan.md` (table of scenes with times, goals and every line) so the user can review the story before rendering.
