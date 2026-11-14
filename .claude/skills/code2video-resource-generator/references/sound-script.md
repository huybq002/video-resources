# Sound script: the sound director's pass

Adapted 2026-11-14 from the "story-led sound system" of kaomei/stickman-video-director (MIT licence): the structure of
the three functional layers, spotting per beat and the mixing decisions. Wording and implementation are ours.

Sound communicates place, physical contact, information or emotion. It is not sprinkled on every cut. Strong narration
cannot rescue thin, unrelated effects. Our pipeline builds the layers automatically (`ci/score.py`, `ci/add_sfx.py`,
`ci/add_music.py`); this page says what each layer is for, what the spec must give it, and how to judge the result.

## The three functional layers (voice stays in front, separately)

| layer | job | what it is here | the writer gives |
|---|---|---|---|
| 1. place / continuity (ambience) | tells us where we are; never digital silence | room tone per setting (`score.ambience`), changes at every change of place | a clear `place` text and `signature` objects per setting |
| 2. physical events (foley) | contact, weight, material of what the picture shows | footsteps, keys, pops, paper, tick (`add_sfx`, from `assets/sfx_cues.json`) | `do` actions, `props`, `hud` counters |
| 3. emotional punctuation | anticipation, surprise, relief, the turn | sting, sparkle, plink, riser + impact at the power moment, the film's score | `emote`, `mood`, scene `value` +/- |

These are roles, not three tracks sounding at once. A layer may be absent when nothing justifies it. Music is not a
substitute for foley or room tone, and does not repeat every impact.

## Spot at the beat, not by the clock

Every cue answers: what caused it, where is it, why does this moment need it. Do not invent an unseen door, weapon or
character just to have a sound. A still camera push is not a whoosh. Study the ordinary middle of a scene: paper, a
latch, a card tapped on a counter, a cup set down establish material better than another trailer hit.

## Mixing decisions

- **Source before sweetener.** Identify what moved or touched what; pick the sound with that material and force. A click
  is not paper, plastic, wood and glass. A synthesised sketch is a prototype; a recording in `data/sfx/<name>.wav`
  (CC0 / owned) overrides it.
- **Contact -> body -> consequence.** Align the transient to the contact, keep a credible body and decay. A card slapped
  on a counter, the beep, then the character's reaction must read as one causal sequence.
- **Listener position.** Room, behind a wall, phone/radio are different sounds. A remote voice must not sound like it is in
  the room.
- **A recurring source keeps its identity but changes its meaning**: a phone ringing closer, a monitor beeping faster.
  Do not make progression only by gain, and do not replay the identical puff as several performances (`step`/`key`/`tick`
  already vary).
- **The environment has states.** Change the bed with place, time, weather, subjective attention.
- **Hierarchy over blanket ducking.** Foreground / support / background priority per event. A source-defining contact
  survives the voice; the music ducks, the contact does not vanish. A critical effect never masks the words.
- **Silence is designed.** An AUDIO CUT (everything but a breath stops, then returns on a trigger) is a storytelling
  tool for a reveal, written in the script. Accidental dead air is a defect: the room tone prevents it; 20 % of the
  film with no voice is the writer's fault (the `silence:` lint).

## What the pipeline records

`ci/add_sfx.py` writes `assets/sound_manifest.json` next to the project: every effect (time, name, layer, why), and the room
tone runs (place kind, in-out). The night job reads it in the director's pass and lists in the report which layers were
audible in the final mix (it measures the final mp4's loudness per 10 s: a stretch below -50 dB without a written AUDIO CUT
is a defect). Aesthetic approval is the owner's; a clean analysis is not approval.

## Judge it by listening, then fix the named defect

On "thin / cheap" feedback, first inventory what is actually audible in the encoded film. Name the defect (wrong source,
weak contact, masking, wrong perspective, causal gap, identical repetition, lost contrast), then change those cues. More
assets, more bass or more gain are not evidence that it was fixed.
