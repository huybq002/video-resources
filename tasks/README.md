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

- Everything for a video task is built under `outputs/<id>/` (resource bundle in `project/`, video `project/output.mp4`, or `final.mp4` with `renderer: skill`). At the end `scripts/publish_release.py` attaches `bundle.zip` (HyperFrames project incl. assets and `voiceover.wav`), the video, thumbnails and metadata to a **GitHub Release** (tag `<id>-<run id>`). Download them from the Releases page and delete the release if you wish. Only the small `outputs/<id>/manifest.json` (release URL, sizes, sha256), thumbnails, specs and series memory are committed.
- Before committing, the job runs `scripts/verify_bundle.py` twice: on the bundle (exact length, contiguous cues, <= 14 words per cue, scene count and length vs the spec, required files) and on the video (length, audio present and not silent, frame size). A failing check means the job fixes and re-renders instead of committing.
- Render takes about 7 s of wall time per video second at 30 fps (a 9-minute video is about 70 minutes). Keep the total of all tasks inside the 300-minute cap; long videos should go in their own night.
- YouTube upload only happens with `upload: true`, needs secrets `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`, and is `private` by default.
- Series memory (`series/<name>/series-bible.json`) is committed to the `night` branch.

- `renderer: tool` (default) uses `code2video-job` (VieNeu voice, Whisper alignment, HyperFrames) for the best voice and video quality; `renderer: skill` uses the skill's own edge-tts + render as a fallback.

## Time and usage limits

- The job starts at 00:00 Vietnam time. Claude stops at 05:45 and the whole job ends by 06:00 at the latest.
- Before starting a task or a render the job checks the time left (render takes about 7 s per video second). It does not start work it cannot finish.
- On a usage-limit error, or with less than 15 minutes left, Claude stops at once, commits its notes and leaves the task in `tasks/pending/` with `status: in-progress`. The next night picks it up again and continues from the notes.
- Bundles and voice-over of unfinished tasks are kept in the Actions cache (restored the next night; the cache is evicted after about 7 days without use).
