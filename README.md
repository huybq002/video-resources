# video-resources

Video resources and nightly automation (HyperFrames, YouTube).

- `channel.json`: **the only file you edit.** Niche, audience, seed keywords, formats, what to avoid.
- `tasks/pending/`: tasks to run (see `tasks/README.md`). Leave it empty and the job researches the market and writes the next task itself.
- `data/ideas.md`: the researched idea backlog; `data/research/latest.md`: last night's market digest.
- `data/approval.json`: the approved look. Until it matches `scripts/skill_hash.py`, nights make a short **demo** for you to approve (`scripts/approve_demo.py`), not full videos.
- `reports/YYYY-MM-DD.md`: **read this first each morning**: tonight's video, what research found, every pipeline improvement, what could not be verified. Improvements arrive as a pull request (or a compare link) on branch `improve/YYYY-MM-DD`; nothing reaches `main` without you.
- `data/learnings.md`: dated, evidenced findings that justify any change to the writing rules.
- `data/platform-policy.md`: the YouTube/TikTok rules the pipeline obeys, refreshed weekly by the job.
- `data/discovered_keywords.json`: keywords the job found, kept apart from `channel.json` so your edits never conflict with the job's.
- Actions → **Research check** (manual): tests whether YouTube answers yt-dlp from a GitHub runner. Costs no Claude usage.
- `data/known-issues.md`: what broke, why, and how it is prevented — Auto-fix reads this before fixing anything.
- `outputs/<id>/publish/`: the title, description, tags and hashtags to paste on YouTube, Shorts and TikTok.
- `tasks/done/`: finished tasks
- `outputs/<task id>/`: results
- `templates/`: task template
- `.github/workflows/night-job.yml`: runs at 00:00 (UTC+7), one 5h window
- `.github/workflows/claude.yml`: `@claude` mentions in issues and PRs

Each video task builds **both** 16:9 and 9:16 from one spec, with assets generated per frame shape. Videos and resource bundles are published as GitHub Releases (`scripts/publish_release.py`), not committed.

Requires the `CLAUDE_CODE_OAUTH_TOKEN` repository secret (from `claude setup-token`). YouTube upload additionally needs `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

Video tasks use `.claude/skills/code2video-resource-generator`. `tools/code2video` (VieNeu-TTS, faster-whisper, HyperFrames render, `code2video-job`) renders the video for `renderer: tool` tasks; `renderer: skill` uses the skill's own edge-tts + render as a fallback.

The night job runs inside a prebuilt image (`Dockerfile`, built by `build-image.yml` and stored at `ghcr.io/huybq002/video-resources-runner`), so nothing is installed or downloaded at night. Run **Build runner image** once (and whenever tools or dependencies change) before the first night.

## Skills (in `.claude/skills/`)

- `video-thumbnail` ([aabrole/claude-video-thumbnail-skill](https://github.com/aabrole/claude-video-thumbnail-skill)): thumbnails via Gemini. Needs secret `GEMINI_API_KEY` and a headshot in `.claude/skills/video-thumbnail/assets/headshots/`.
- `claude-youtube` ([AgriciDaniel/claude-youtube](https://github.com/AgriciDaniel/claude-youtube)): channel strategy, SEO, scripts, hooks, Shorts. Optional `YOUTUBE_API_KEY` for data scripts.

Python deps: `requirements.txt`. Licenses: `.claude/skills/_licenses/`.

## Thumbnails (default: no image API)

Skill `html-thumbnail`: Claude writes 3 HTML variants per video, renders PNGs with headless Chromium (Playwright), and logs them in `data/thumbnail-results.csv`. After you post them, fill in `ctr_percent`; the next run reads it and reuses what won. CTR is measured, not guaranteed.
