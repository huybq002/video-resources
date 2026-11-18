---
name: hezb-story
description: Make a Hezb Stories video from a task: write the story script (characters, places, acted lines), voice it with our TTS, then direct and render the picture with our film engine hezb-motion (motion/). Use for every `type: video` task of the night job.
---

# Hezb Stories: story -> voice -> hezb-motion picture

Since 2026-11-15 (owner decision) every video is made in three parts:

| part | who / what | where |
|---|---|---|
| 1. the story script | you write `stories/<id>.json`: cast, places, acted lines | this skill: `references/story-schema.md`, writing craft in `references/` |
| 2. the voice | our TTS: edge-tts conversational voices (en), VieNeu (vi), one voice per speaker, each line acted from its `emote` | `python scripts/stickman/narrate.py` |
| 3. the picture, captions, score, mix and render | **hezb-motion**, our engine in `motion/` (owner decision 2026-11-17, replaces stickman-video-director) | `python motion/make_film.py` |

The old generator (HyperFrames, preset 3D sets, stick rigs) was removed from main; it is kept on the branch
`backup/pre-stickman-director-2026-11-15`.

`bash motion/install.sh` prepares the engine (node modules, bundle); `make_film.py` runs it for you.

## Styles: which are on

`stickman/lock.json` lists them. Owner decision 2026-11-15: no paid image or video API, so only the styles the runtime
can draw with code are on. These are disclosed as best effort, not sample-equivalent:

| style | look | use it for |
|---|---|---|
| **B1** Minimal line art | near-white paper with a faint grid, slender hand-drawn stick figures, colored hand-drawn props, big short in-scene text | psychology and self-improvement explainers, "you" stories, lists of mechanisms |
| **B2** Colorful hand-drawn | warm paper, colored illustrated environments and props, ivory caption label | everyday life, money stories, relationships, habits |
| **B3** Retro TV | dark field, white and grey artwork, restrained CRT finish, uppercase captions | mysteries, night stories, puzzles, eerie or introspective stories |

Off until a key is added (the reason is in lock.json):
- A1-A6: Gemini Omni Flash video, Amber Noir;
- B4: needs an image tool that takes reference images;
- B5: presenter art from an image tool;
- B6: painted stills.

Never fake a disabled style with code drawings.

**Pick the style by content**:
1. mystery or scam -> B3;
2. money or everyday -> B2;
3. psychology explainer -> B1;
4. otherwise the closest feel.

Never use the same style as the channel's previous video: read the last `outputs/*/manifest.json`. A style must be
approved to make a full video (see Approval); for an unapproved style, tonight makes its demo.

## 1. Write the story (`stories/<id>.json`)

Read `references/story-schema.md`, then the craft pages:
- `story-formats.md`;
- `short-film-craft.md`;
- `spoken-voice.md`;
- `youtube-craft.md`;
- `data/growth-playbook.md` H1-H6.

What a story must have:
- **Places come from the words**: every scene has a `place` that says where THIS beat happens in THIS story (a night ward,
  a bakery till, a bus stop in the rain). There are no preset places: the picture of each place is drawn for the story in
  part 3.
- **Characters**: `cast` with name, gender and a one-line `look` (clothes, hair, one signature object). Style references
  decide how they are drawn.
- **Acted lines**: `emote` on every line with a feeling; short spoken sentences; a hook in line 1; a question to the viewer
  at the end.
- Then `python .claude/skills/hezb-story/scripts/lint_story.py stories/<id>.json`, and fix every WARNING.
- Then `python scripts/policy_check.py spec stories/<id>.json`: policy OK.

## 2. Voice it

`python scripts/stickman/narrate.py stories/<id>.json outputs/<id>/voice`
- It writes `narration.wav` and `timing.json`: line times, scene times and one-line captions.
- The voice is never sped up or slowed to fit a picture. The picture is timed to the voice.

## 3. Direct the picture with hezb-motion (owner decision 2026-11-17)

The picture is made by our own engine in `motion/`. It replaces the stickman-video-director runtime. Read
`motion/README.md` and the worked example `motion/examples/prodigal-son/direct.py` before you direct.

1. **Word timings**: `python motion/align.py outputs/<id>/voice --model small` writes `voice/words.json`. Fix any line it
   reports with `CHECK`.
2. **Direction**: write `outputs/<id>/direct.py` with `motion/director.py` and `motion/worlds.py`, line by line:
   - the places, from a `worlds.py` place with its elements changed for THIS story;
   - the cast looks, from `cast[].look`;
   - per line, the verbs (`f.act`), the objects (`f.prop`, `f.spill`, `f.hanger`, insert3d), the shots (`f.shot`, 1-3 per
     line) and the sound (`f.sfx`, `f.section`, `f.hit`).
3. **Look before rendering**: run `python motion/make_film.py --voice outputs/<id>/voice --direct outputs/<id>/direct.py --out outputs/<id>/landscape --stills-only`
   and look at `stills/contact-sheet.png`. Then run the same command without `--stills-only` to get
   `outputs/<id>/landscape/output.mp4`.

Rules (owner, 2026-11-17):
- **No motion without a purpose.**
  - A character at rest only breathes and blinks.
  - Every other movement is a verb the story asks for, timed to its line or its word: use `f.word(scene, line, "ran")`.
  - Never use gesture loops.
  - Mouths move only on the speaker's own words.
- **The world lives and reacts.**
  - Every place has ambient life (birds, smoke, wind in the grass, rain, passers-by, a crowd) and particles.
  - Story moments trigger the world: birds scatter, a gust blows, lanterns swing, coins spill.
- **A new picture often.**
  - No shot over about 6 s.
  - Vary the shot kinds.
  - `director.py` prints `CHECK` lines when it saves: fix every one.
- **The objects the words name** are on screen when they are named, big enough to read.
- **Sound**:
  - every visible action has an sfx;
  - each scene has a score section with its mood;
  - there is a silence before the turn;
  - there is a hit on the peak.
- **Style picks the light**:
  - B2: a warm, colourful day;
  - B3: night, rain or overcast grades;
  - B1: light paper with few colours.
- **Mysteries**: the death is never shown. Clues are props drawn large, on screen when the narrator names them.
- **Cut**: 16:9 only for now (`only_aspect: "16:9"`). The native portrait cut is not built yet.

Check the result:
- `python scripts/verify_bundle.py video outputs/<id>/landscape/output.mp4 --story stories/<id>.json --aspect 16:9`;
- look at the contact sheets of `director_pass`.

Write what you saw, with times, in the report.

## Approval (owner decision 2026-11-15: once per style)

- `data/approval.json` has `styles: {"B1": {approved, skill_hash, demo, approved_at}, ...}`.
- A style is approved when its entry matches the current `python scripts/skill_hash.py`.
- An unapproved style gets a 20-30 s demo: a short story, `--seconds` cut, published as a demo Release.
- The owner approves with `python scripts/approve_demo.py --style B3 --demo <release url>`.
- An approved style makes full videos.
