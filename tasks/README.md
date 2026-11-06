# Tasks

1. Copy `templates/task-template.md` to `tasks/pending/NNN-name.md` (NNN = run order).
2. Fill it in, commit, and push to `main` before 00:00.
3. At night the job takes pending tasks in order, works until the usage limit, and:
   - writes results to `outputs/<id>/`
   - notes progress in the task's "Progress notes"
   - moves finished tasks to `tasks/done/` with `status: done`
   - leaves unfinished tasks in `tasks/pending/` with `status: in-progress`
4. All work is committed to the `night` branch. Merge `night` into `main` when you have reviewed it.

If `tasks/pending/` has no runnable task at 00:00, the job does nothing (Claude is not started).

## Video tasks

Use `templates/video-task-template.md` (`type: video`). The job follows the `code2video-resource-generator` skill in CI mode:
spec in `specs/<id>.json`, then ONE command `ci/run_pipeline.py` (resources, voice-over, render, thumbnail, metadata).

- Rendered files (`final.mp4`, `script.srt`, `thumb.jpg`, logs) are **not committed**. Download them from the run's **Artifacts** on GitHub Actions.
- Render takes about 7 s of wall time per video second at 30 fps (a 9-minute video is about 70 minutes). Keep the total of all tasks inside the 300-minute cap; long videos should go in their own night.
- YouTube upload only happens with `upload: true`, needs secrets `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`, and is `private` by default.
- Series memory (`series/<name>/series-bible.json`) is committed to the `night` branch.

- `renderer: tool` (default) uses `code2video-job` (VieNeu voice, Whisper alignment, HyperFrames) for the best voice and video quality; `renderer: skill` uses the skill's own edge-tts + render as a fallback.
