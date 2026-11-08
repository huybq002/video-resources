---
name: code2video-resource-generator
description: Turn a video idea + length (e.g. 8-10 minutes) into a Code2Video / HyperFrames project that follows the user's hyperframes-asset-contract (index.html, script.srt multi-speaker, compositions/scene_N.html, assets/ with 3D-toon backgrounds, rigged SVG stick-figure characters with story wardrobe, props, fonts) with a many-scene script whose scene durations add up exactly to the requested length, plus Gemini prompts for characters and backgrounds. Use when the user gives an idea/topic/story and a duration for Code2Video Studio. No audio and no mp4 are produced (the app makes voiceover.wav and renders). Supports 16:9 and 9:16, series with recurring characters, optional user script. Default Vietnamese.
---

# Code2Video resource generator

Input from the user: **an idea + a length** (optional: tone, cast size, language). You plan the story as scenes, write the script to the second, design the cast and settings, write `spec.json`, then run `scripts/generate.py`. Output follows `references/hyperframes-asset-contract.md` exactly:

```
<out>/                                  <- the project (upload this folder to Code2Video Studio)
  index.html                            root: data-composition-id="story", data-duration = total seconds, scene hosts, <audio id="voice" src="assets/audio/voiceover.wav">
  script.srt                            [Name][00:00:00,000 --> 00:00:03,500]: line   (multi-speaker, contiguous, ends exactly at the total length)
  compositions/scene_1.html … scene_N.html   one scene = one <template>, id scene-N
  assets/   bg_<setting>.png (+ _far/_mid/_near), <id>.svg (characters), props/, fonts/, vendor/gsap.min.js, character-rigs.json
<out>_docs/                             <- for the user, outside the project
  scene-plan.md        every scene: time range, duration vs target, goal, all lines
  gemini-prompts.md    ready-to-paste Gemini prompts: characters (SVG) + backgrounds (PNG) with the exact file name to save each as
  asset-checklist.md   which file is made by whom and its status
```
`assets/audio/voiceover.wav` is made by the app from `script.srt` (it stretches the voice into each cue window), so the cue windows ARE the timeline: no `timeline.json`, `hyperframes.json` or `package.json` is written.

## Inputs (collect in ONE message; ask only for what is missing)
| Input | Spec key | Notes |
|---|---|---|
| idea / topic | `idea` | required |
| language | `lang` | default `vi` (narration, captions, chips) |
| frame | `aspect` | `16:9` (1920×1080, default) or `9:16` (1080×1920, Shorts) |
| duration | `duration_s` | required (8–10 min → 16–24 scenes) |
| script prompt (optional) | `script_prompt` | the user's own script/outline/tone: keep their wording, only split it into scenes and cues |
| series (optional) | `series: {name, episode, open_loops}` + `--series <series-bible.json>` | recurring characters keep identical look, Gemini art and settings are reused across episodes; episode 2+ only needs the new lines (cast may be empty: it comes from the bible) |
| reference style (optional) | `style_dna` | from a reference channel/transcripts, see `references/youtube-craft.md` |

## Series: every episode is an independent run, same characters, continuous story
All memory lives in ONE file, `series-bible.json` (keep it in a folder of your own, e.g. `MySeries/series-bible.json` with `MySeries/assets/` for the Gemini art made once). A new session needs nothing else.
- **Episode 1:** write the spec with the full cast (`look` for every character) and a `series` block, run `generate.py spec.json out1 --series MySeries/series-bible.json`. The bible is created and filled.
- **Episode N ≥ 2 (new session):** (1) `python scripts/series.py brief MySeries/series-bible.json` (≈ 400 words: cast looks and current state, story so far, last 3 episodes, open loops, rules); (2) write ONLY the new scenes: `cast: []` is fine, character design comes from the bible and cannot drift (differences produce `SERIES WARNING`); pay off the last open loop within 15 s and list it in `series.resolved`; end on a new loop; (3) `generate.py spec.json outN --series …`. Shared `<id>.svg` / `bg_*.png` art in the bible's `assets_dir` is copied into every episode.
- **Fill the `series` block every time** so the next run can continue: `episode`, `summary`, `key_events`, `clues`, `last_line`, `next_hook`, `resolved`, `open_loops`, `character_state` (per character, end of episode), `story_so_far` (updated rolling summary ≤ 200 words). Change a design deliberately (new outfit) by editing the character in the bible, not in the episode.

## Token economy (important: do not burn tokens)
- Read ONLY what the current step needs: planning → `story-formats.md` + `script-planning.md` (+ `youtube-craft.md` for hook/CTA/Shorts/series); cast → `wardrobe.md`; settings → `set-design.md` then `scene-dsl.md`; shots → `spec-schema.md` (the "Film coverage" part). Skip `motion-language.md` and `animation-principles.md` unless you hand-write motion.
- Write scenes as `sequence` blocks (dialogue/narration); hand-write shots only for key moments. Never write per-shot acts for a whole film.
- Saving tokens must never cost the picture: the four things below are the job, not the trimming. Budget your effort there and save tokens by not re-reading generated files.
- Do not open generated HTML/SVG, `script.srt` or `_docs` files to "check" them: run `generate.py`/`validate.py` and read their short output; look at 3–4 snapshot frames at most.
- Do not install or read the external repos (claude-youtube, faceless-youtube-agents): their useful parts are already in `youtube-craft.md`.

## Rules that decide whether the video is watchable
`generate.py` lints the spec and prints a WARNING for each of these. **A spec that still prints WARNINGs is not finished.**
0. **The first 30 s earn the rest.** Scene 1 is 15-30 s and opens on the strongest line in the film (<= 14 words, <= 10 in 9:16); no greeting, no title card, no logo. Something stays open inside the first 30 s (a question, or a promise paid at the end). At least 4 shots there (8+ in 9:16) across two places. The last scene ends on a question for the comments. (`youtube-craft.md`)
1. **The script fills the time.** Words per scene ≈ `target_s × 2.4`. Under-writing leaves the scene running after the voice stops; the closing `silence: about X%` line must be under 8 %, never over 12 %. (`script-planning.md`)
2. **Places belong to the story.** The `lib:` library holds six ordinary places only (cafe, office, bedroom, street, park, rooftop). Anything else — a ruined city, a barricaded flat, a hospital corridor, a flooded field — you write yourself in `spec.settings` with `scene-dsl.md`. Aim for a distinct setting in at least 60 % of the scenes, and never let one setting carry more than a third of the film. Reusing a place is fine when the place itself changed (night, damage, fog, crowd) and the camera moved.
3. **Everyone the script mentions is on screen.** "Everyone turned", "hundreds of them", "the soldiers came": that is a `crowd` block (`spec-schema.md`) and/or named cast entries, drawn in `wardrobe.md`, present in the shot's `actors`. A whole film of one figure narrating over an empty street is the failure mode to avoid.
4. **No long static shot.** A scene over ~15 s needs 2–3 shots (wide → medium → close-up, or a cut to another place). A `sequence` already cuts per cue, but the picture behind it must change too.
6. **The picture follows the words, line by line.** The viewer must SEE what the narrator says: a line about going to bed is shot in a bedroom that has a bed; a line about a phone shows a phone; a line about the office happens at a desk. Write a visual beat on at least every other line (`at`, `on`, `do`, `emote`, `props`, `shot` — `spec-schema.md`), build each place with furniture (`scene-dsl.md`), and use the 32 props. `spec_lint.py` checks every line against its setting and props and warns on three bare lines in a row. A video whose pictures ignore the script is the main reason viewers leave.
7. **Every character is a full stick figure: no long trousers for anyone.** `bottom` is `none` (default), `shorts` or `skirt`; `pants` is drawn as bare legs.
8. **Cut like a film: about every 3 s, no dead air, the idea on screen.** Read `references/film-language.md` (measured on the reference channel). Scenes open on an establishing shot, lines that name an object cut to an insert of it, two-person lines use `ots`, every number the narrator says is a `hud` counter or chip, and the hook ends on a title card. Write ~3 words per second of scene in English (the planner uses the measured voice speed, capped by the caption reading rule). `spec_lint.py` warns above 4.5 s per shot and on numbers nobody sees.
9. **Every place is a full set, lit like a film.** Start each setting from a `set` (`references/set-design.md`): `{"set": {"type": "room", "style": "bedroom|office|lab|kitchen|living|classroom|cafe|shop", "time": "day|dusk|night"}}`, `{"type": "street"}` or `{"type": "shopfront"}`, then add the story's own objects. A set gives the window with the city and the sun, ceiling lights, posters, clock, shelves, a light pool on the floor and blurred foreground objects, so even a close-up shows a room. Open each scene on the place with people small in it, and use a shopfront/street at night as an establishing shot with nobody in it.
10. **Pick a format and write like the best channels do** (`references/story-formats.md`): set `"format"` (what_if, character, episode, days, dilemma, explainer, wordless). Open on the impossible moment before explaining it; state one rule + one limit; make it measurable (a test, a scale, numbers on screen); climb an escalation ladder with a new place per step; turn on the cost at 55-70 %; plant early and pay off late (`plant`/`payoff` on lines); 5-7 words per sentence, one-word payoffs. `spec_lint.py` checks the format voice, the title question, sentence length, the turn, plants and numbers.
5. **Both frame shapes, every time.** One spec, two finished films: `python scripts/build_both.py <spec.json> <out_dir>` writes `<out>/landscape` (16:9 1920x1080) and `<out>/portrait` (9:16 1080x1920). Each is generated for its own frame, so the assets genuinely differ: three.js re-renders every background at that resolution with the camera pulled back in portrait, characters are rescaled and re-placed, focus zooms are eased, captions are lifted out of the Shorts UI. `script.srt` is identical, so make `voiceover.wav` once in `landscape/` and copy it with `timeline.json` into `portrait/` before rendering. Write so the story reads in both: 1-2 characters per shot, the important thing in the middle third. (`youtube-craft.md`, "Two cuts from one spec")

## Workflow
1. **Intake.** idea + length. Ask ONE combined question only if either is missing; otherwise state assumptions in one line and go.
2. **Plan scenes first** (`references/script-planning.md`): 8–10 min → 16–24 scenes of 24–30 s, `scenes[].target_s` adding up to `duration_s`; per scene `title`, `goal`, **its own place and time of day**, who is on screen (hero, supporting cast, crowd), mood, and the 1–2 visual beats. Hook, setup, rising action with a turn every scene, twist with clues, resolution, takeaway + CTA. Write the place list before the lines: a story that visits 8 places is worth watching, a story told from one bedroom is not.
3. **Write the lines to the budget:** ≈ `target_s × 2.4` words per scene, ≤ 14 words per cue, speaker per cue (`{"t","who"}`), narrator = cast entry `{"id":"narrator","name":"Người kể","narrator":true}`. Use `sequence` blocks (`references/spec-schema.md`) so the generator adds master / medium / close-up / reaction shots for you. Count the words per scene as you write; do not leave it to the warning.
4. **Cast and places** (`references/wardrobe.md`, `references/scene-dsl.md`): stick figure, big white head, outfit chosen from the script (`top`, `bottom`, `shoes`, `hat`, …), unique silhouette + colour per character; give each a hand-written `look` sentence for the Gemini prompt. **Male characters keep bare stick legs (`bottom:"none"`) or wear `shorts`, never `pants`** — put the character into the top, shoes and accessories instead. Cast the supporting characters too, not only the hero, and add a `crowd` block wherever the story has a group. Settings: write the ones the story needs in `spec.settings` (`scene-dsl.md`); use `lib:` only where an ordinary cafe/office/bedroom/street/park/rooftop is genuinely right. Optional `setting_desc` text feeds the background prompts.
5. **Generate both cuts:** `python scripts/build_both.py <spec.json> <out_dir> [--check]` (add `--only 16:9` for a single one). It runs `generate.py <spec> <out>/<cut> --aspect <cut>` twice, which:
   - lints the spec (settings variety, cast, crowds, static scenes, wardrobe) and plans `script.srt` (exact total, exact scene lengths), printing lines like `WARNING: scene 2 target 27s but its text naturally takes 20s (33% of the scene would be silent): add about 15 words` and `WARNING: only 6 distinct setting(s) for 11 scenes`. **Fix every warning and re-run until none remain**; they are the difference between a watchable film and a slideshow.
   - renders the 3D backgrounds (first run does `npm install` in `scripts/bg_renderer`; needs Chrome/Edge, `CHROME_PATH` overrides), builds characters, scenes, `index.html`, validates the contract.
   - Re-run after the user hand-edits timings: `--keep-srt --skip-bg`. Generate into a new folder name rather than deleting a folder.
6. **Verify:** `python scripts/validate.py <out> --check --no-audio` (contract + `hyperframes check`: ok, 0 errors) and `npx hyperframes snapshot <out> --at 3,15,40,80 -o <tmp outside out>`; look at the frames (≤ 3 characters per shot, feet on the ground, captions readable, overlays off faces).
7. **Hand-off:** project path, `_docs` path, total length, scene count, list of characters/settings, which files the user still has to add (Gemini SVGs/backgrounds, optional), and what was and was not checked (e.g. "snapshots viewed, no full render").

## Characters and backgrounds from Gemini (optional, per character / setting)
- Default: the skill draws characters (rigged inline SVG, written to `assets/<id>.svg`) and 3D backgrounds, so the project renders immediately.
- To use Gemini art: open `<out>_docs/gemini-prompts.md`, paste each prompt, save the SVG/PNG under the exact file name shown (`assets/<id>.svg`, `assets/bg_<setting>.png`). Then set `"external": true` on the cast entry (character is used as one animated image: breathe, walk, tilt, hop; no limb joints) and/or `"external_bg": true` (or a list of setting ids) at the top of the spec, and run `generate.py … --keep-srt --skip-bg`. The skill never overwrites a file the user placed.

## CI mode (GitHub job: Claude makes the resources, then renders with tools, then optionally uploads)
Only when the prompt says CI mode / runs in GitHub Actions (`ci/workflow.yml`). Normal mode above is unchanged (no audio, no mp4).
1. **Job = create resources exactly as in Workflow steps 1–6** (same spec, same project structure, same contract; series via `series.py brief` + `--series`). No shortcuts on scenes or script length. Stand-alone defaults: no Gemini files (built-in characters/backgrounds).
2. **Render is run by Claude through tools**, as ONE foreground command: `python ci/run_pipeline.py <spec> <out> [--series bible] [--upload --privacy private]`. It does generate → `ci/tts.py` (voice-over fitted to `script.srt`) → parallel slice render (`ci/render_chunks.py`, `npx hyperframes render --start/--end`) → ffmpeg assemble + mux → `thumb.jpg` → `metadata.json` (chapters from scene titles) → upload. Read only its short status lines; the full log is `<out>_pipeline.log`. `--stop-after generate|tts|render` to run in parts; on failure fix the cause and re-run (idempotent), or run the `ci/*.py` steps by hand.
3. **Fix every script-length WARNING** before the render (edit spec text/targets, re-run) because the voice-over is fitted to the SRT windows (max ×1.5 speed-up).
4. **Upload is opt-in**: only with `--upload`; default privacy `private`; `public` needs both `--privacy public` and `--allow-public`. Secrets `YT_CLIENT_ID/SECRET/REFRESH_TOKEN` from the env (create once with `ci/get_refresh_token.py`); never print them. Unaudited API projects can only upload private; ≈1600 of 10,000 quota units per upload.
5. Cost: render ≈ 7 s per video-second at 30 fps on one machine (9 min ≈ 70 min, slices run in parallel with `--jobs`); set the job timeout and `BASH_MAX_TIMEOUT_MS` accordingly. After a series episode, commit the updated series bible back.

## Rules
- Several speakers → set `gender` on every cast entry (+ `narrator_gender`): `script.srt` then carries `[Name][time][gender-label]: text` in the script's language (see `references/spec-schema.md`).
- Contract rules (`references/hyperframes-asset-contract.md`): seconds in HTML, ms in SRT, `class="clip"` + `data-start/duration`, one paused GSAP timeline per composition registered after its tweens, no `repeat:-1` / random / fetch / timers, no tween of display/visibility on `.clip`, asset paths `assets/...` without leading `/`, caption ≥ 0.5 s + 0.3 s/word and the last caption of a scene stays to the end (≥ 2 s), first frame already has content, no slide look (characters + background + motion in every scene). The builder already follows them; edit the spec, not the HTML.
- Fiction by default, invented names, no graphic violence, moral ambiguity kept, no real people/brands/team kits.
- Never claim audio, alignment or a render exists. Keep scratch files outside `<out>`.
- Look/motion: `references/animation-principles.md` (film grammar, acting), `references/motion-language.md` (camera, transitions, HUD overlays measured from reference videos), `references/wardrobe.md`.

## Defaults (already decided with the user)
16:9 1920×1080 (or 9:16 1080×1920 with `aspect`), 60 fps for videos ≤ 3 min and 30 fps for longer ones (`fps`, `motion_blur` in the spec). **Render cost measured on this laptop: ≈ 7 s of wall time per second of video at 30 fps (a 9-minute film ≈ 70 min, 60 fps ≈ double)**; tell the user before they start a render, Vietnamese, lit 3D-toon backgrounds in depth layers, stick-figure characters in three views (front / profile / back) with lip-sync on `who` cues, close-ups via `focus`, transitions whip/zoom/flash/dip, overlays chip/counter/burst/bubble/title.

## Environment gotchas (Windows + Git Bash)
Write long files with the Write tool (heredocs with quotes break); print Vietnamese with `PYTHONIOENCODING=utf-8`; Python cannot read `/tmp/...` from Git Bash (use `C:/…`); `hyperframes check` prints progress lines, parse JSON from the first `{`; transparent-background screenshots need a transparent page body (already set).

## Files
`ci/`: `workflow.yml` · `run_pipeline.py` · `tts.py` · `render_chunks.py` · `make_metadata.py` · `upload_youtube.py` · `get_refresh_token.py`
`scripts/`: `build_both.py` (one spec, both cuts) · `generate.py` · `spec_lint.py` · `series.py` · `srt_tools.py` (scene-budgeted script.srt) · `coverage.py` · `docs_gen.py` · `characters.py` + `characters_stick.py` · `build_project.py` · `engine.js` · `lipsync.py` · `validate.py` · `bg_renderer/`
`references/`: `hyperframes-asset-contract.md` · `youtube-craft.md` · `script-planning.md` · `spec-schema.md` · `wardrobe.md` · `scene-dsl.md` · `animation-principles.md` · `motion-language.md` · `story-guidelines.md`
`examples/film-demo-2am/spec.json`: **the reference for the current look** — every line has a visual beat, furniture at the characters' depth (bed, desk, oven), film actions (sleep, sit, drink, type, pickup), a screen insert, an over-the-shoulder dialogue, HUD chips/counter and a title card. Copy its shape.
`examples/zombie-portrait/spec.json`: an older 9:16 example (predates sets and formats; copy only its crowd/horde use) — own 3D settings, a `crowd` horde on a sequence, a male character with bare stick legs, 2.5 words/s and 0 % silence. Copy its shape.
`assets/`: `settings-library/` · `kenney-glb/` · `props/` · `fonts/` · `vendor/` · `examples/film-demo` (70 s, 2 scenes) · `examples/silent-samaritan` · `examples/split-demo`
