# Learnings

Kept by the night job's improvement phase. Every entry is dated and carries its evidence, so a
later night can tell a finding from a guess. Newest first. The writing rules in the skill
(`script-planning.md`, `youtube-craft.md`, `spec_lint.py`) change only when an entry here
supports it.

| date | topic | finding | evidence | action taken |
|---|---|---|---|---|
| | | | | |

## 2026-11-15 (videos 008, 009): write for the real voice, not the lint
- Evidence: 008 first render at 2.7-2.9 words/s per scene: 5 lines rushed, 7 cut; at 2.3-2.5 words/s: 0 rushed, 0 cut (voiceover_fit.json). 009 needed three renders: the cut lines were short dialogue lines ("Seven proofs, Sam. Seven." in a 1.9 s window), because each sentence break adds ~0.4 s of TTS pause.
- Rule: keep every scene at or below 2.5 words/s, merge short sentences with commas, give dialogue lines at least 6 words, and run `python scripts/voice_fit_check.py pre <script.srt>` before the first render. The spec_lint silence warning (it assumes ~3 words/s) then fires; that is expected and needs `--max-warnings`.
