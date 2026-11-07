---
id: 002-video-short-name
type: video            # video | thumbnail
priority: 2            # lower number = run first
status: pending        # pending | in-progress | done | blocked
# --- video fields (skill: code2video-resource-generator, CI mode) ---
topic: ""              # topic id from channel.json (money | psychology | mystery)
keyword: ""            # the target search keyword this video is built around
idea: "One-sentence idea or topic"
lang: en               # script language (channel.json lang)
only_aspect: ""        # leave empty: every task builds BOTH 16:9 and 9:16 (own assets per frame). "16:9" or "9:16" to build just one.
duration_min: 5        # exact length in minutes, e.g. 5 or 0.5
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
- [ ] both cuts generated and verified (landscape 16:9 + portrait 9:16, exact length)
- [ ] both videos rendered and verified (audio present, right frame size)
- [ ] Release published with both bundles and both videos
- [ ] specs/<id>.json committed
- [ ] thumbnail variants made (html-thumbnail skill) if requested

## Progress notes
(The job writes here. Leave empty.)
