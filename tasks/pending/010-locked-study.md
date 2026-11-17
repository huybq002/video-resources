---
id: 010-locked-study
type: video
priority: 010
status: pending
lane: mystery
topic: mystery
keyword: "crime investigation story"
format: episode
idea: "classic fair-play locked-room murder: a publisher is found dead in a study locked from the inside, key on the desk; three suspects with alibis; Kiri breaks the locked-room trick and the faked time of death"
lang: en
only_aspect: ""
duration_min: 7
style: "B3"
script_prompt: "Format (classic fair-play fair-play whodunit, our own cast and cases): a detective duo (Kiri, a quiet sharp 12-year-old, and his cousin Hana, who says what the viewer is thinking), Inspector Dale from the police, and three suspects, each with an alibi that seems solid. Structure, about 7 minutes: (1) the crime and the impossible situation, in a scene the viewer can SEE (1.5 min); (2) the three suspects, their alibis and THREE clues planted in plain view, drawn large and named once by the narrator; ask the viewer to guess (3 min); (3) Kiri's reasoning: he takes the clues one by one, each one cancels an alibi or a suspect, then names the killer and shows the TRICK step by step with a re-enactment drawing (2 min); (4) the motive in two lines, then a question to the viewer. Rules: FICTION ONLY, invented names/places, no claim it is real anywhere. One person dies. The death is NEVER shown or described: the victim is off-screen or a closed door; no blood, no wound, no weapon on screen, no method of killing, no cause of death. The puzzle is the locked room / the alibi / the time, not how the person was harmed. The trick is a misdirection trick (a timing, a recording, snow, a clock), never a recipe to hurt someone. Not aimed at children. Do not copy any existing franchise character, case or line: only the genre structure.  Line 1: 'The study was locked from the inside. The key lay on the desk. He never opened the door.' Case: publisher Aldous Crane is found dead in his study (off-screen; show only the door and the desk). Suspects: his secretary (Mara), his nephew (Felix), his doctor (Dr. Voss). Three clues in plain view: (1) a tiny drop of candle wax on the door frame, (2) a thread fibre caught on the key's ring, (3) Crane's wristwatch stopped at 9:40 with an UNBROKEN glass while the study clock was still running. Trick: the door was locked from outside with a thread-and-wax loop that pulled the key... (the viewer sees the loop drawn, a harmless household trick), and the watch was stopped earlier to fake the time so the nephew's and secretary's alibis seemed to fit. Killer: Dr. Voss (alibi: on the phone at the hospital at 9:40, which the stopped watch gave him). Motive in two lines: Crane was about to publish Voss's secret. End: 'Which clue did you notice first?'"
series: ""
episode: ""
upload: false
privacy: private
---

# The Study Locked From the Inside

## Goal
7-minute English classic fair-play murder mystery in style B3, both cuts (16:9 and 9:16). Search phrase: "crime investigation story". Thumb: LOCKED FROM INSIDE. Owner approved this idea on 2026-11-15.

## Done when
- [ ] story lints clean (hezb-story lint_story.py), policy_check spec OK (no death shown or described)
- [ ] voice, both cuts rendered and verified (verify_bundle video + director_pass)
- [ ] Release published with both bundles and both videos, publish pack written

## Progress notes
- 2026-11-16 night: story lint+policy OK, voiced, both cuts authored (author.py + outputs/_lib/alib.py; portrait uses voice-portrait/ with captions re-split to 24 chars via outputs/_lib/portrait_voice.py), validate OK for both cuts, 60-s previews rendered. Full film NOT rendered: see 013's note (runtime preview cap 60 s, full render needs owner approval). Resume: when a render route is decided, run assemble.py (landscape: --voice voice, portrait: --voice voice-portrait).
- 2026-11-17 night: story SHORTENED to 154 s (Rule 0, time budget; full 6-min version in outputs/010-locked-study/story-long.json, line map in keep.json, author.py maps kept lines to overlay texts). Lint+policy OK, voiced, landscape rendered (22:07 UTC, 154 s, not yet verified/published). Portrait render hung in the runtime's `validate` (node autopilot.mjs, 100% CPU 24+ min) at the deadline. Resume: re-run assemble.py portrait (--voice voice-portrait) (kill any hung node first), then verify_bundle bundle+video for both cuts, publish_release.py 010-locked-study. Metadata, thumbnails, publish pack already written. Trending (014) is already published: 2 of 3 tonight (news 013, trending 014); mystery is the missing one.
- 2026-11-17 22:36 UTC: B3 9:16 'validate' (autopilot.mjs) alone takes 25-30+ min at 100% CPU for this story (the 2026-11-15 60-s portrait preview also took 31 min), landscape validate+render took 8 min. Start the portrait cut FIRST next time and in parallel with the landscape one. Stopped at the deadline with portrait validate still running; nothing of 010 is published yet.
