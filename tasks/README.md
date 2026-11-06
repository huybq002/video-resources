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
