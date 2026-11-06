# video-resources

Video resources and nightly automation (HyperFrames, YouTube).

- `tasks/pending/`: tasks to run (see `tasks/README.md`)
- `tasks/done/`: finished tasks
- `outputs/<task id>/`: results
- `templates/`: task template
- `.github/workflows/night-job.yml`: runs at 00:00 (UTC+7), one 5h window
- `.github/workflows/claude.yml`: `@claude` mentions in issues and PRs

Requires the `CLAUDE_CODE_OAUTH_TOKEN` repository secret (from `claude setup-token`).

## Skills (in `.claude/skills/`)

- `video-thumbnail` ([aabrole/claude-video-thumbnail-skill](https://github.com/aabrole/claude-video-thumbnail-skill)): thumbnails via Gemini. Needs secret `GEMINI_API_KEY` and a headshot in `.claude/skills/video-thumbnail/assets/headshots/`.
- `claude-youtube` ([AgriciDaniel/claude-youtube](https://github.com/AgriciDaniel/claude-youtube)): channel strategy, SEO, scripts, hooks, Shorts. Optional `YOUTUBE_API_KEY` for data scripts.

Python deps: `requirements.txt`. Licenses: `.claude/skills/_licenses/`.
