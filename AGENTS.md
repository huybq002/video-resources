# AGENTS.md — project context for AI agents

Read this file instead of exploring the repo. It is accurate as of 2026-11-09. If code contradicts it, trust the code and fix this file.

## What this is
Automation for a YouTube channel ("Hezb Stories", English, US/UK/AU market): animated stick-figure short films about decisions and their cost (money, psychology, invented mysteries). A nightly GitHub job researches the market, writes a story spec, renders a video in both 16:9 and 9:16 with HyperFrames, and prepares a publishing pack. The owner only reviews and posts. Owner works in Vietnamese; narration language comes from `channel.json` (`lang`, now `en`).

## Layout
| path | what |
|---|---|
| `channel.json` | the only file the owner edits: niche, topics, seed keywords, hard rules |
| `.claude/skills/code2video-resource-generator/` | **the video generator (most work happens here)** |
| `.claude/skills/{claude-youtube,html-thumbnail,video-thumbnail}/` | strategy/SEO, HTML thumbnails (no API), Gemini thumbnails |
| `tools/code2video/` | Python app: VieNeu-TTS, faster-whisper alignment, HyperFrames render (`renderer: tool` tasks) |
| `scripts/` | night-job helpers: `research_youtube.py`, `policy_check.py`, `make_publish_pack.py`, `publish_release.py`, `verify_bundle.py`, `approve_demo.py`, `skill_hash.py` |
| `.github/workflows/` | `night-job.yml` (00:00 UTC+7, nine crons 09:17-17:17 UTC because GitHub starts them up to ~9 h late; a run starting after 22:45 UTC does nothing), `autofix.yml`, `build-image.yml`, `claude.yml`, `research-check.yml` |
| `data/` | `ideas.md` backlog, `learnings.md`, `known-issues.md` (read before any fix), `platform-policy.md`, `approval.json`, `thumbnail-results.csv` |
| `tasks/{pending,done}`, `outputs/<id>/`, `reports/YYYY-MM-DD.md` | task queue, results (videos go to GitHub Releases, not git), morning report |
| `Dockerfile` | prebuilt runner image (ghcr `video-resources-runner`); rebuild via "Build runner image" when tools/deps change |

Read `README.md` and `tasks/README.md` only for operations detail.

## Generator pipeline (`.claude/skills/code2video-resource-generator/`)
Idea + length → Claude writes `spec.json` → `scripts/build_both.py spec out` (runs `generate.py` once per aspect) → project folder (`index.html`, `script.srt`, `compositions/scene_N.html`, `assets/`) → `ci/run_pipeline.py` (TTS fitted to SRT, parallel slice render, ffmpeg, thumbnail, metadata, optional upload).

Key scripts (`scripts/`):
- `catalog.py`: single data table — every object (synonyms, zone, footprint, places, affordances lie/sit/sleep/work/use/stand), place recipes (`PLACES`), verb groups (`VERBS`). New scene types = add data here, not code.
- `layout.py`: places any catalog object into any room at a free spot of its zone.
- `autofill.py` (first step of `generate.py`): settings → furnished rooms (style / PLACES recipe / generic + named objects; special-state places like ruined/mind kept as authored); lines → `at`/`do` (verb → affordance → object present or added)/`props`/`emote`. Never overwrites the spec author.
- New pose `use:<act>@<object>` (coverage → build_project.resolve): stand at the object's approach point, turned to it, hands looping the act.
- `generate.py` lint → plan SRT → render 3D backgrounds → build project → validate. `--aspect 16:9|9:16`, `--skip-bg`, `--keep-srt`.
- `coverage.py` expands `sequence` blocks (dialogue/narration) into shots; `_cinematic_pass` fixes jump cuts, adds eyeline looks before inserts.
- `build_project.py` shots → scene HTML (anchors, extras, held poses, HUD, looks); `engine.js` GSAP runtime (acts: walk, sit, lie, gesture, blink, look…).
- `sets.py` (room styles: bedroom office lab kitchen living classroom cafe shop laundry meeting bathroom grocery generic void; `_dress` puts clutter on every surface, per-style palettes) + `furniture.py` (63 pieces incl. small props) + `bg_renderer/` (three.js via Chrome) = 3D toon backgrounds; `anchors.py` projects furniture so characters sit/lie ON it; `extras.py` populates places by logic.
- `characters.py` / `characters_stick.py` rigged SVG stick figures. `srt_tools.py` scene-budgeted SRT.
- Lints (every one prints `WARNING:`; **a spec with any WARNING is not finished**): `spec_lint.py` (visual match, pacing, format voice) → also runs `voice_lint.py` (spoken naturalness: contractions, clichés, show-don't-tell, dialogue shape; en + vi) and `craft_lint.py` (story: `spine`, per-scene `turn`/`value`, motif, 180° line, establishing shots).
- References to read per step (don't read all): `short-film-craft.md` + `spoken-voice.md` + `story-formats.md` + `script-planning.md` (writing), `wardrobe.md` (cast), `set-design.md` + `scene-dsl.md` (places), `spec-schema.md` (all spec keys), `film-language.md` (shot grammar from reference channel).
- Examples: `examples/film-demo-2am/spec.json` is the reference spec shape (has `spine`, scene `turn`/`value`); `zombie-portrait` is old 9:16.

## Spec essentials
`format` (what_if|character|episode|days|dilemma|explainer|wordless), `spine{want,obstacle,turn,choice,opening_image,ending_image,motif}`, `cast[]`, `settings{}` (use `set:{type,style,time}`), `scenes[]{id,title,goal,turn,value,target_s,shots[]}`; scene durations sum to `duration_s`; words per scene ≈ `target_s × 2.4–3` (en ≈ 3.3 w/s cap); cue ≤ 14 words; actions anchored to furniture (`lie@bed`, `sit@chair`); every ~3 s a cut; numbers appear as `hud`. Full key list: `references/spec-schema.md`.

## Commands
```bash
S=.claude/skills/code2video-resource-generator
python3 $S/scripts/spec_lint.py spec.json                      # lints incl. voice: and craft:
python3 $S/scripts/build_both.py spec.json OUT --only 16:9      # first run does npm install in scripts/bg_renderer; needs google-chrome
python3 $S/scripts/validate.py OUT/landscape --check --no-audio
npx hyperframes snapshot OUT/landscape --at 2,6,16 -o SNAP      # look at contact-sheet.jpg to judge visuals
python3 scripts/skill_hash.py                                   # approval fingerprint
cd tools/code2video && python -m pytest tests                   # tool tests
```
Environment: Linux, node, python3, google-chrome, ffmpeg available. Use the scratchpad/tmp, never write scratch into the project.

## Rules and gotchas
- **Lint gate:** `scripts/verify_bundle.py bundle` and `ci/run_pipeline.py` fail while any spec-lint WARNING is open (`--max-warnings N` to override, must be justified in the report).
- **Approval gate:** `skill_hash.py` hashes the skill's scripts/assets/references/SKILL.md and `tools/code2video/src` (not examples). Any change there invalidates `data/approval.json`, so the next night makes a short demo; the owner runs `scripts/approve_demo.py` after reviewing. Rebuild the runner image after skill changes.
- Content policy (`scripts/policy_check.py`, `data/platform-policy.md`): fiction only, invented names, no real people/brands/prices, no advice or returns, no graphic violence, AI disclosure in the publish pack.
- Nothing reaches `main` without the owner: improvements go to branch `improve/YYYY-MM-DD` via PR. Commit only when asked. Commit messages end with the attribution line from the session reminder.
- Render cost ≈ 7 s per video-second per cut at 30 fps. Do not claim a render, audio or alignment exists unless you ran it.
- Don't open generated HTML/SVG/SRT to "check" them: run lint/validate and look at snapshots.
- Characters: full stick figures, no long trousers (`bottom` none/shorts/skirt). Hero wears a colour no extra wears.
- Windows-era notes in SKILL.md (Git Bash paths) don't apply on this Linux box.

## Known visual weak spots (open work)
Fixed 2026-11-09: a seat facing away from the camera (back-wall desk, audience rows) is drawn from behind (engine `sit` dir `"b"`, `back_sit()` in build_project: feet on the floor, figure clipped at the seat); lying on a sofa rests on the cushion; meeting podium/screen sit at the back wall and the presenter stands behind the podium (catalog `stand="behind"`, legs clipped; `via="podium"` sends "presents the slides" there); abstract places (mind/dream/memory/void) become the `void` style (dark stage, one light pool, named objects, dream/flashback grade); WEAK synonyms ("tea", "notes", "screen", "stage"...) count only as plain nouns, idioms stripped (`catalog.WEAK`, `IDIOMS`). Fixed 2026-11-10: a close-up on someone seated from behind switches them to profile (reverse angle); a sleeper in a bed lies under a cover drawn over the body (`blanket` in build_project, bed colour from `anchors` `c`); a profile sitter rests the hands on the lap (engine `sit`); props come from nouns too ("A message lights up the screen" -> phone; `autofill` prop check uses `noun=True`); `policy_check.py spec` fails a spec that repeats one of the last 8 in `specs/` (inauthentic-content policy of 16 July 2026). Motion 2026-11-10: `use:<act>@<object>` walks the hero in from the side when the object is new in the scene, then acts (turned to it); reach/point have anticipation + overshoot; a line with no verb match that names an object with a `use` affordance uses it (generic fallback in `autofill.beats`); the room window is a synthetic anchor (`sets._win`, `anchors.compute`) so "looks out the window" stands at it. Remotion / Motion Canvas were evaluated and NOT adopted (the weak part is the rig/poses, not the renderer; Remotion is free only for <=3 people; Motion Canvas has no headless render, Revideo fork does). Still open: **close-up zoom on a small seated figure at the back of a room does not render** (data has zoom 2.2-2.6, the snapshot stays wide; reproduced on HEAD 0d4a09f, cause not found; see data/known-issues.md); standing idle is still stiff; dialogue close-ups crop feet by design; extras and settings still look stock. No long full video has yet been generated and reviewed end to end with the new `craft:`/`voice:` rules.

## Recent history (git log is the source of truth)
Scene logic (actions bring objects) → film devices (look, spot, angle, POV, graph, clock) → extras → hero stands out → spoken-voice lint, short-film craft lint, `_cinematic_pass`, lying-pose fix → autofill (picture follows words), 4 new room styles + surface clutter, lint gate in verify_bundle/run_pipeline (uncommitted as of 2026-11-09).
