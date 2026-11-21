# Known issues and what was done about them

The Auto-fix workflow reads this file **before** it touches anything. If a failure is already
listed here, the earlier fix did not hold, so it must go deeper instead of repeating itself.
It appends a row after every fix. You can add rows by hand too.

Be honest in the "prevented by" column: a retry or a longer timeout is a workaround, not a fix,
and saying so is what stops the same night failing again next week.

| date | workflow | error (one line) | root cause | change | prevented by |
|---|---|---|---|---|---|
| 2026-11-06 | Build runner image | `External data path escapes model directory` when loading VieNeu | HuggingFace cache stores model files as symlinks; onnxruntime refuses to follow them out of the model dir | Dockerfile replaces every symlink under the cache with a real file, then loads the model again to prove it works | the second load fails the build if the model is still unusable, so a broken image can never be pushed |
| 2026-11-07 | Night job (local) | `step failed: validate.py` on every `--check` run | `--check` asked hyperframes to lint a project whose `voiceover.wav` is made later, so it always found `audio_src_not_found` | validate.py ignores that one finding while `--no-audio` is set; generate.py passes it until the file exists | the rule comes back automatically as soon as the voice-over exists, so a genuinely silent project still fails |
| 2026-11-10 | generator (local test) | close-up on a seated figure at a back-wall desk renders as a wide: shot data has `cam` zoom 2.2-2.6 but the snapshot shows ~1.3x; forcing `cam` [3,0,0,3,0,0] gives ~1.8x | NOT FOUND. Same on HEAD 0d4a09f (not caused by the 2026-11-10 changes). Close-ups in examples/film-demo-2am (bed) zoom correctly. The scene has the chair-back occluder layer (`OC`), but removing it from `layers` did not help. Next: probe the layer transforms in the hyperframes runtime at a seeked time | none yet | open |
| 2026-11-15 | Night job | `The action has timed out` in Run Claude (17:00 to 22:17 UTC, 1 task, no output after init) | The step runs until the deadline-derived timeout; the log holds nothing after `init`, so what it was doing is unknown. Not a file-fixable error: no stack trace, no failing script | none (no code change can fix it from this log; the deadline cutoff is in .github/, off limits) | nothing new; the prompt already says to stop before DEADLINE_EPOCH and commit progress notes. If it repeats, check whether a render or TTS step hangs without output |
| 2026-11-21 | Night job | `Claude result reported subtype success with is_error:true` in Run Claude, 725 ms after init, 1 turn, $0, empty modelUsage, 0 tasks | The API call was rejected before any model work: the pattern of a usage/rate limit, billing or auth/token problem. The log hides the message (show_full_output is off). Not file-fixable | none (no code change can fix it; check the Claude usage limit / token / billing, then re-run) | nothing in the repo; to diagnose next time, the workflow in .github/ would need show_full_output: true (off limits for autofix) |
