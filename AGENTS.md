# AGENTS.md — project context for AI agents

Read this file instead of exploring the repo. It is accurate as of 2026-11-15. If code contradicts it, trust the code and fix this file.

## What this is
Automation for a YouTube channel ("Hezb Stories", English, US/UK/AU market): animated stick-figure short films about decisions and their cost (money, psychology, invented mysteries). A nightly GitHub job researches the market, writes a story, voices it, directs and renders the picture in both 16:9 and 9:16 with the pinned kaomei/stickman-video-director runtime (one of its visual styles), and prepares a publishing pack. The owner only reviews and posts. Owner works in Vietnamese; narration language comes from `channel.json` (`lang`, now `en`).

## Layout
| path | what |
|---|---|
| `channel.json` | the only file the owner edits: niche, topics, seed keywords, hard rules |
| `.claude/skills/hezb-story/` | **how a video is made**: story script (`stories/<id>.json`), voice, directing the stickman runtime, style choice, approval |
| `stickman/lock.json`, `scripts/stickman/` | the pinned stickman-video-director runtime (MIT) + `install.sh`, `narrate.py` (voice + timing), `assemble.py` (project.json, sound, validate, render) |
| `scripts/media/` | `score.py` (room tone per place, original score), `sfx_bank.py`, `director_pass.py`, `make_metadata.py`, `upload_youtube.py` |
| `.claude/skills/{claude-youtube,html-thumbnail,video-thumbnail}/` | strategy/SEO, HTML thumbnails (no API), Gemini thumbnails |
| `tools/code2video/` | Python app; the night job uses its TTS (edge-tts voices, VieNeu for vi, `direction_prosody`) |
| `scripts/` | night-job helpers: `research_youtube.py`, `policy_check.py`, `make_publish_pack.py`, `publish_release.py`, `verify_bundle.py`, `approve_demo.py`, `skill_hash.py` |
| `.github/workflows/` | `night-job.yml` (00:00 UTC+7, nine crons 09:17-17:17 UTC because GitHub starts them up to ~9 h late; a run starting after 22:45 UTC does nothing), `autofix.yml`, `build-image.yml`, `claude.yml`, `research-check.yml` |
| `data/` | `ideas.md` backlog, `learnings.md`, `known-issues.md` (read before any fix), `platform-policy.md`, `approval.json`, `thumbnail-results.csv` |
| `tasks/{pending,done}`, `outputs/<id>/`, `reports/YYYY-MM-DD.md` | task queue, results (videos go to GitHub Releases, not git), morning report |
| `Dockerfile` | prebuilt runner image (ghcr `video-resources-runner`); rebuild via "Build runner image" when tools/deps change |

Read `README.md` and `tasks/README.md` only for operations detail.

## Video pipeline (2026-11-15, owner decision)
The old HyperFrames generator (preset 3D sets, stick rigs, `spec.json`) was removed from main; it is kept on the branch
`backup/pre-stickman-director-2026-11-15`.

1. **Story** `stories/<id>.json` (`.claude/skills/hezb-story/references/story-schema.md`): style, cast with a look, scenes
   with a story-specific `place`, acted lines (`emote`). Gate: `.claude/skills/hezb-story/scripts/lint_story.py` +
   `scripts/policy_check.py spec`.
2. **Voice** `scripts/stickman/narrate.py story outputs/<id>/voice` -> `narration.wav` + `timing.json` (line/scene times,
   one-line captions). Natural pace; the picture follows the voice.
3. **Picture** the night job directs it: `outputs/<id>/shots-16x9.json` / `shots-9x16.json` written against the runtime's
   references (`$STICKMAN/references/`), with its own SVG drawings in `assets`.
   `scripts/stickman/assemble.py` writes the runtime's `project.json` (adds captions, room tone, score, sfx), runs
   `validate` and renders.
4. **Check** `scripts/verify_bundle.py bundle|video` (+ `scripts/media/director_pass.py`), publishing pack, Release.

Styles: `stickman/lock.json` `enabled_styles` (B1, B2, B3: code-drawn, no paid API). A1-A6, B4, B5 and B6 need an image or
video generation API and are off until a key is added. Each style is approved once
(`python scripts/approve_demo.py --style B3 --demo <url>`); `data/approval.json` `styles`.

## Commands
```bash
bash scripts/stickman/install.sh                                # pinned runtime into .cache/stickman-director (image: /opt/stickman-director)
python3 .claude/skills/hezb-story/scripts/lint_story.py stories/<id>.json
python3 scripts/stickman/narrate.py stories/<id>.json outputs/<id>/voice [--dry-run]
python3 scripts/stickman/assemble.py --story stories/<id>.json --voice outputs/<id>/voice --shots outputs/<id>/shots-16x9.json --ratio 16:9 --out outputs/<id>/landscape [--check | --seconds 20]
python3 scripts/media/director_pass.py outputs/<id>/landscape/output.mp4
python3 scripts/skill_hash.py                                   # approval fingerprint
```

## Rules and gotchas
- **Night volume** (`channel.json` `night`): every run writes >= 3 new ideas dated tonight into `data/ideas.md` (`scripts/plan_night.py check-ideas` gates it) and makes >= 2 videos; each video's length is chosen per idea inside `night.duration_range_min` (1-8 min), and `plan_night.py budget --durations a,b` checks they fit before `$DEADLINE_EPOCH`. A scheduled run GitHub starts after the 22:45 UTC window (up to 05:00 UTC) catches up with a 5 h budget instead of doing nothing.
- **Lint gate:** `scripts/verify_bundle.py bundle` fails while any story-lint WARNING is open or the runtime's validate has not passed (`--max-warnings N` to override, must be justified in the report).
- **Approval gate:** `skill_hash.py` hashes the skill's scripts/assets/references/SKILL.md and `tools/code2video/src` (not examples). Any change there invalidates `data/approval.json`, so the next night makes a short demo; the owner runs `scripts/approve_demo.py` after reviewing. Rebuild the runner image after skill changes.
- Content policy (`scripts/policy_check.py`, `data/platform-policy.md`): fiction only, invented names, no real people/brands/prices, no advice or returns, no graphic violence, AI disclosure in the publish pack.
- Nothing reaches `main` without the owner: improvements go to branch `improve/YYYY-MM-DD` via PR. Commit only when asked. Commit messages end with the attribution line from the session reminder.
- Render cost ≈ 7 s per video-second per cut at 30 fps. Do not claim a render, audio or alignment exists unless you ran it.
- Don't open generated HTML/SVG/SRT to "check" them: run lint/validate and look at snapshots.
- Characters: full stick figures, no long trousers (`bottom` none/shorts/skirt). Hero wears a colour no extra wears.
- Windows-era notes in SKILL.md (Git Bash paths) don't apply on this Linux box.

## Known visual weak spots (open work)
Fixed 2026-11-09: a seat facing away from the camera (back-wall desk, audience rows) is drawn from behind (engine `sit` dir `"b"`, `back_sit()` in build_project: feet on the floor, figure clipped at the seat); lying on a sofa rests on the cushion; meeting podium/screen sit at the back wall and the presenter stands behind the podium (catalog `stand="behind"`, legs clipped; `via="podium"` sends "presents the slides" there); abstract places (mind/dream/memory/void) become the `void` style (dark stage, one light pool, named objects, dream/flashback grade); WEAK synonyms ("tea", "notes", "screen", "stage"...) count only as plain nouns, idioms stripped (`catalog.WEAK`, `IDIOMS`). Fixed 2026-11-10: a close-up on someone seated from behind switches them to profile (reverse angle); a sleeper in a bed lies under a cover drawn over the body (`blanket` in build_project, bed colour from `anchors` `c`); a profile sitter rests the hands on the lap (engine `sit`); props come from nouns too ("A message lights up the screen" -> phone; `autofill` prop check uses `noun=True`); `policy_check.py spec` fails a spec that repeats one of the last 8 in `specs/` (inauthentic-content policy of 16 July 2026). Motion 2026-11-10: `use:<act>@<object>` walks the hero in from the side when the object is new in the scene, then acts (turned to it); reach/point have anticipation + overshoot; a line with no verb match that names an object with a `use` affordance uses it (generic fallback in `autofill.beats`); the room window is a synthetic anchor (`sets._win`, `anchors.compute`) so "looks out the window" stands at it. Remotion / Motion Canvas were evaluated and NOT adopted (the weak part is the rig/poses, not the renderer; Remotion is free only for <=3 people; Motion Canvas has no headless render, Revideo fork does). Still open: **close-up zoom on a small seated figure at the back of a room does not render** (data has zoom 2.2-2.6, the snapshot stays wide; reproduced on HEAD 0d4a09f, cause not found; see data/known-issues.md); standing idle is less stiff since 2026-11-10 (breathing/sway periods and phase vary per character; listeners nod and blink once per line someone else speaks) but arms still hang still; OpenMontage was checked for idle/pose code and NOT used (AGPL-3.0, and it has no idle logic; its mocap clips are CMU data, free to use directly if mocap is ever added); dialogue close-ups crop feet by design; extras and settings still look stock. No long full video has yet been generated and reviewed end to end with the new `craft:`/`voice:` rules.

## Recent history (git log is the source of truth)
Scene logic (actions bring objects) → film devices (look, spot, angle, POV, graph, clock) → extras → hero stands out → spoken-voice lint, short-film craft lint, `_cinematic_pass`, lying-pose fix → autofill (picture follows words), 4 new room styles + surface clutter, lint gate in verify_bundle/run_pipeline (uncommitted as of 2026-11-09).
