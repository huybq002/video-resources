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

Requires the `CLAUDE_CODE_OAUTH_TOKEN` repository secret (from `claude setup-token`). Automatic YouTube upload additionally needs `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` (see **YouTube upload** below).

Video tasks use `.claude/skills/code2video-resource-generator`. `tools/code2video` (VieNeu-TTS, faster-whisper, HyperFrames render, `code2video-job`) renders the video for `renderer: tool` tasks; `renderer: skill` uses the skill's own edge-tts + render as a fallback.

The night job runs inside a prebuilt image (`Dockerfile`, built by `build-image.yml` and stored at `ghcr.io/huybq002/video-resources-runner`), so nothing is installed or downloaded at night. Run **Build runner image** once (and whenever tools or dependencies change) before the first night.

## Skills (in `.claude/skills/`)

- `video-thumbnail` ([aabrole/claude-video-thumbnail-skill](https://github.com/aabrole/claude-video-thumbnail-skill)): thumbnails via Gemini. Needs secret `GEMINI_API_KEY` and a headshot in `.claude/skills/video-thumbnail/assets/headshots/`.
- `claude-youtube` ([AgriciDaniel/claude-youtube](https://github.com/AgriciDaniel/claude-youtube)): channel strategy, SEO, scripts, hooks, Shorts. Optional `YOUTUBE_API_KEY` for data scripts.

Python deps: `requirements.txt`. Licenses: `.claude/skills/_licenses/`.

## YouTube upload (off until you switch it on)

After the Claude step, the night job runs `scripts/youtube_publish.py`. For every task that run published (Release tag ends with the run id) it uploads `landscape.mp4` (and `portrait.mp4` as a Short when the film is 3 min or less) with the title, description and tags from `outputs/<id>/publish/publish.json`, the hashtags, the music credit (`<cut>/*.music.json`), `channel.json` `publish.ai_disclosure`, the category, the matching thumbnail from `outputs/<id>/thumbnails/`, and YouTube's "altered or synthetic content" flag. Videos go up **private**: open YouTube Studio, review, then publish. The video ids land in `outputs/<id>/youtube.json` on the `night` branch; a cut listed there is never uploaded twice.

It uploads nothing unless all of these hold: `channel.json` `youtube_upload.enabled` is `true`; the three secrets exist; the look is approved (`data/approval.json` matches `scripts/skill_hash.py`, so a demo night never uploads); `policy_check.py publish` passes; the task does not say `upload: false`. Other `youtube_upload` keys: `dry_run` (print only), `cuts`, `privacy`, `allow_public` (needed for `public`), `schedule_utc` (`"14:00"` = private, scheduled to go public at the next 14:00 UTC at least 2 h ahead), `vertical_over_3min`, `thumbnail` (preferred variant, e.g. `"b"`).

Get the secrets once, on your own computer (not in CI):

1. Google Cloud Console: create a project, enable **YouTube Data API v3**, set up the OAuth consent screen (External, add the channel's Google account as a test user), then Credentials -> Create OAuth client ID -> type **Desktop app**. Copy the client id and secret.
2. `pip install requests` then `python .claude/skills/code2video-resource-generator/ci/get_refresh_token.py <CLIENT_ID> <CLIENT_SECRET>`. A browser opens; sign in with the channel's account and allow. Scope is `youtube.upload` only.
3. Repo Settings -> Secrets and variables -> Actions: add `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` with the printed values. Do not paste them anywhere else; the scripts never print them.
4. Optional check before switching on: set `youtube_upload.dry_run: true` (or run `python scripts/youtube_publish.py --id <id> --dry-run` locally) and read what it would send.

Notes: while the consent screen is in **Testing**, Google expires the refresh token after 7 days, so publish the app (it can stay unverified for your own account) or re-run step 2 when uploads fail with `invalid_grant`. An API project that has not passed YouTube's API audit can only upload private videos, which is the default here anyway. Custom thumbnails need a verified channel (phone verification); a thumbnail failure does not fail the upload. One upload costs about 1,600 of the 10,000 daily quota units.

## Thumbnails (default: no image API)

Skill `html-thumbnail`: Claude writes 3 HTML variants per video, renders PNGs with headless Chromium (Playwright), and logs them in `data/thumbnail-results.csv`. After you post them, fill in `ctr_percent`; the next run reads it and reuses what won. CTR is measured, not guaranteed.
