---
name: hezb-story
description: Make a Hezb Stories video from a task: write the story script (characters, places, acted lines), voice it with our TTS, then direct and render the picture with the pinned stickman-video-director runtime in one of its visual styles. Use for every `type: video` task of the night job.
---

# Hezb Stories: story -> voice -> stickman-video-director picture

Since 2026-11-15 (owner decision) every video is made in three parts:

| part | who / what | where |
|---|---|---|
| 1. the story script | you write `stories/<id>.json`: cast, places, acted lines | this skill: `references/story-schema.md`, writing craft in `references/` |
| 2. the voice | our TTS: edge-tts conversational voices (en), VieNeu (vi), one voice per speaker, each line acted from its `emote` | `python scripts/stickman/narrate.py` |
| 3. the picture, captions, mix and render | **kaomei/stickman-video-director** (MIT), pinned in `stickman/lock.json`, in one of its visual styles | `$STICKMAN` = the runtime skill dir; `python scripts/stickman/assemble.py` |

The old generator (HyperFrames, preset 3D sets, stick rigs) was removed from main; it is kept on the branch
`backup/pre-stickman-director-2026-11-15`.

`$STICKMAN` is `$STICKMAN_HOME/skills/directing-stickman-videos`. It is `/opt/stickman-director/...` in the runner image;
elsewhere run `bash scripts/stickman/install.sh` once.

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

## 3. Direct the picture with stickman-video-director

You are the director now. Before authoring, READ from `$STICKMAN/references/`:
- `autopilot.md`;
- `autopilot-runtime.md` (the manifest, layers, keys, motion rules);
- `autopilot-production-qa.md`;
- `autopilot-sound-system.md`;
- `b-delivery-completeness.md`;
- the selected style's page: `b1-minimal-handdrawn.md` | `b2-colorful-handdrawn.md` | `b3-television.md` + `b3-semantic-motion.md`;
- `b1-b2-b3-reference-acceptance.md`;
- `b1-b2-b3-native-portrait.md` for the 9:16 cut.

Look at the style's bundled reference images in `$STICKMAN/assets/<b1|b2|b3>/`.

Write `outputs/<id>/shots-16x9.json` and `outputs/<id>/shots-9x16.json` (a native portrait composition, not a resized
landscape):

```jsonc
{
  "shots": [ {"start": 0, "end": 2.6, "layers": [ ... ]}, ... ],   // absolute seconds on timing.json; cover 0..duration, no gaps
  "assets": {"ward-bed.png": "<svg xmlns=...>...</svg>"},          // YOUR drawings for this story, rasterised to PNG
  "sfx": [{"time": 3.1, "name": "step"}, {"time": 7.0, "kind": "paper"}],
  "television": {"enabled": true, "intensity": 0.45}               // B3 only
}
```

**Layers**:
- B1/B2: `image` (your assets, `@b1/...` bundled B1 art), `text`, `line`, `arrow`, `underline`.
- B1 only: `pose` from the demo atlas, as a reference, not the only cast.
- B3 adds vector `path`, `rect`, `ellipse`, `group` with pivots, so characters and props can be drawn directly in JSON.
- Every moving actor/prop/information layer needs a unique `id` and `motion: {role: actor|prop|information, reason}`, with
  real keys.
- The runtime refuses more than 2.5 s without principal motion and refuses captions that wrap.

**Direction rules**, from the runtime's references and ours:
- Each scene is a relay of main visuals: a new place, object, person or graphic hands the stage on.
  `references/event-relay.md`.
- Draw the place the words name, with its signature objects; the same drawing grammar across the film, a new set per
  place.
- Draw the needed states before animating them: before, contact/peak, result.
- Characters keep the style's drawing grammar and their `look`. Faces are readable: eyes on every speaker, expressions
  that change with `emote`.
- Sound: our room tone follows each scene's `place`, and an original score follows the mood. You add story `sfx` at real
  actions, from our bank (`scripts/media/sfx_bank.py` names) or the runtime kinds tap/paper/pop/chime/jingle.
  `references/sound-script.md`.

**Render**:

`python scripts/stickman/assemble.py --story stories/<id>.json --voice outputs/<id>/voice --shots outputs/<id>/shots-16x9.json --ratio 16:9 --out outputs/<id>/landscape`

Same for `--ratio 9:16 --out outputs/<id>/portrait`. Add `--check` to validate only; add `--seconds 20` for a demo.
A validate failure names the shot and the rule: fix the shots, not the runtime.

**Look at the result as the runtime asks**:
- watch the contact sheet `outputs/<id>/<cut>/contact-sheet.png`;
- run `python scripts/media/director_pass.py outputs/<id>/<cut>/output.mp4` (dead air, frozen picture, black frames,
  contact sheets);
- run `python scripts/verify_bundle.py video outputs/<id>/<cut>/output.mp4 --story stories/<id>.json --aspect 16:9|9:16`.

Write what you saw, with times, in the report. The runtime's own acceptance (`approve`, `accept-visual`) needs a human
or an independent reviewer: never run it on your own judgement.

## Approval (owner decision 2026-11-15: once per style)

- `data/approval.json` has `styles: {"B1": {approved, skill_hash, demo, approved_at}, ...}`.
- A style is approved when its entry matches the current `python scripts/skill_hash.py`.
- An unapproved style gets a 20-30 s demo: a short story, `--seconds` cut, published as a demo Release.
- The owner approves with `python scripts/approve_demo.py --style B3 --demo <release url>`.
- An approved style makes full videos.
