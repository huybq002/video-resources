# video-resources

Video resources and nightly automation (HyperFrames, YouTube).

- `tasks/pending/`: tasks to run (see `tasks/README.md`)
- `tasks/done/`: finished tasks
- `outputs/<task id>/`: results
- `templates/`: task template
- `.github/workflows/night-job.yml`: runs at 00:00 (UTC+7), one 5h window
- `.github/workflows/claude.yml`: `@claude` mentions in issues and PRs

Requires the `CLAUDE_CODE_OAUTH_TOKEN` repository secret (from `claude setup-token`).
