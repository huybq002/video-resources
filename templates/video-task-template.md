---
id: 002-video-short-name
type: video            # video | thumbnail
priority: 2            # lower number = run first
status: pending        # pending | in-progress | done | blocked
# --- video fields (skill: code2video-resource-generator, CI mode) ---
idea: "One-sentence idea or topic"
lang: vi               # script language
aspect: "16:9"         # "16:9" or "9:16"
duration_min: 9        # exact length in minutes, e.g. 9 or 0.5
script_prompt: ""      # optional: your own script, outline or tone
renderer: tool         # tool (VieNeu voice + HyperFrames, best quality) | skill (edge-tts, fallback)
series: ""             # optional: folder name under series/ (empty = stand-alone)
episode: ""            # optional: episode number (series only)
upload: false          # true = upload to YouTube after rendering (needs YT_* secrets)
privacy: private       # private | unlisted | public
---

# Title

## Goal
What the finished video should be.

## Done when
- [ ] final.mp4 rendered (in the workflow artifact)
- [ ] specs/<id>.json committed
- [ ] thumbnail variants made (html-thumbnail skill) if requested

## Progress notes
(The job writes here. Leave empty.)
