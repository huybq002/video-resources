from __future__ import annotations

import os
import queue
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

from . import engines  # noqa: F401  (re-exported helpers below)


STAGE_PROGRESS = {"parse": 0.05, "tts": 0.15, "align": 0.45, "compose": 0.70, "render": 0.85, "whiteboard": 0.85, "done": 1.0}
STAGE_LABEL = {
    "queued": "Đang chờ trong hàng đợi",
    "parse": "Đọc script",
    "tts": "Tạo voiceover",
    "align": "Căn timing word-level",
    "compose": "Dựng composition HTML",
    "render": "Render HyperFrames MP4",
    "whiteboard": "Render Whiteboard MP4",
    "done": "Hoàn tất",
}
ARTIFACT_FILES = {
    "audio": "voiceover.wav",
    "video": "output.mp4",
    "timeline": "timeline.json",
    "composition": "index.html",
}


@dataclass
class Job:
    id: str
    params: dict
    status: str = "queued"
    stage: str = "queued"
    progress: float = 0.0
    label: str = STAGE_LABEL["queued"]
    result: dict | None = None
    error: str | None = None
    output_dir: Path | None = None
    version: int = 0
    created_at: float = field(default_factory=time.time)


class JobQueue:
    """Hàng đợi chạy song song N worker; TTS/Whisper được tuần tự hóa, render chạy song song."""

    def __init__(self, max_keep: int = 50) -> None:
        self._jobs: "OrderedDict[str, Job]" = OrderedDict()
        self._pending: "queue.Queue[str]" = queue.Queue()
        self._lock = threading.Lock()
        self._tts_lock = threading.Lock()
        self._worker_threads: list[threading.Thread] = []
        self._max_workers = 4
        self._worker_count = max(1, min(self._max_workers, int(os.environ.get("STUDIO_WORKERS", "3"))))
        self._max_keep = max_keep

    @property
    def worker_count(self) -> int:
        return self._worker_count

    def set_workers(self, count: int) -> int:
        count = max(1, min(self._max_workers, int(count)))
        with self._lock:
            previous = self._worker_count
            self._worker_count = count
        if count > previous:
            self._ensure_workers()
        elif count < previous:
            for _ in range(previous - count):
                self._pending.put(None)  # sentinel: worker tự thoát
        return count

    def enqueue(self, params: dict, job_id: str | None = None) -> Job:
        return self.enqueue_many([(params, job_id)])[0]

    def enqueue_many(self, entries: list[tuple[dict, str | None]]) -> list[Job]:
        jobs = [Job(id=job_id or uuid.uuid4().hex[:12], params=params) for params, job_id in entries]
        with self._lock:
            for job in jobs:
                self._jobs[job.id] = job
            self._prune_locked()
            for job in jobs:
                self._pending.put(job.id)
        self._ensure_workers()
        return jobs

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def clear(self) -> None:
        """Xóa toàn bộ lịch sử job trong bộ nhớ và bỏ các job đang chờ."""
        with self._lock:
            self._jobs.clear()
        while True:
            try:
                self._pending.get_nowait()
                self._pending.task_done()
            except queue.Empty:
                break

    def list(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())

    def queue_position(self, job: Job) -> int:
        with self._lock:
            return sum(1 for other in self._jobs.values() if other.status == "queued" and other.created_at < job.created_at)

    def snapshot(self, job: Job) -> dict:
        with self._lock:
            return {
                "jobId": job.id,
                "status": job.status,
                "stage": job.stage,
                "progress": job.progress,
                "label": job.label,
                "error": job.error,
                "result": job.result,
                "queuePosition": sum(
                    1 for other in self._jobs.values()
                    if other.status == "queued" and other.created_at < job.created_at
                ),
                "created": job.created_at,
                "version": job.version,
            }

    def _ensure_workers(self) -> None:
        with self._lock:
            self._worker_threads = [t for t in self._worker_threads if t.is_alive()]
            for _ in range(self._worker_count - len(self._worker_threads)):
                thread = threading.Thread(target=self._run_worker, name="studio-worker", daemon=True)
                thread.start()
                self._worker_threads.append(thread)

    def _run_worker(self) -> None:
        while True:
            job_id = self._pending.get()
            try:
                if job_id is None:
                    return
                job = self.get(job_id)
                if job is not None:
                    self._execute(job)
            finally:
                self._pending.task_done()

    def _set_stage(self, job: Job, stage: str) -> None:
        with self._lock:
            job.stage = stage
            job.progress = STAGE_PROGRESS.get(stage, job.progress)
            job.label = STAGE_LABEL.get(stage, job.label)
            job.version += 1

    def _execute(self, job: Job) -> None:
        from ..pipeline import apply_format, build, render_hyperframes

        p = job.params
        job.status = "running"
        mode = p.get("mode", "script")
        try:
            if mode == "preview-whiteboard":
                self._set_stage(job, "whiteboard")
                from ..whiteboard import render_whiteboard_preview
                output_dir = Path(p["outputDir"])
                output_dir.mkdir(parents=True, exist_ok=True)
                video_path = output_dir / "preview.mp4"
                render_whiteboard_preview(
                    Path(p["image"]), Path(p["annotation"]), video_path,
                    seconds=int(p.get("seconds", 10)),
                )
                job.output_dir = output_dir
                with self._lock:
                    job.result = {
                        "outputDir": str(output_dir),
                        "video": str(video_path),
                        "renderer": "whiteboard-preview",
                    }
                    job.status = "done"
                    job.version += 1
                self._set_stage(job, "done")
                return

            if mode == "merge-whiteboard":
                self._set_stage(job, "whiteboard")
                from ..whiteboard import merge_whiteboard_scenes
                output_dir = Path(p["outputDir"])
                output_dir.mkdir(parents=True, exist_ok=True)
                video_path = output_dir / "output.mp4"
                merge_whiteboard_scenes([Path(path) for path in p["sceneDirs"]], video_path)
                apply_format(video_path, p.get("format"), p.get("formatMode", "fit"))
                job.output_dir = output_dir
                with self._lock:
                    job.result = {
                        "outputDir": str(output_dir),
                        "video": str(video_path),
                        "renderer": "whiteboard-merge",
                    }
                    job.status = "done"
                    job.version += 1
                self._set_stage(job, "done")
                return

            if mode in ("project", "html", "upload", "files"):
                project_dir = Path(p["outputDir"])
                renderer = p.get("renderer", "hyperframes")
                if renderer == "hyperframes" and not (project_dir / "index.html").is_file():
                    raise ValueError(f"Không tìm thấy index.html trong {project_dir}")
                script_path = p.get("scriptPath")
                language = p.get("language", "vi")
                if script_path or p.get("makeVoiceover"):
                    from ..tts import VieNeuAdapter
                    from ..voiceover import build_from_script, synthesize_voiceover_from_timeline
                    with self._tts_lock:
                        self._set_stage(job, "tts")
                        tts = engines.get_tts(p.get("dryRun", False), p.get("ttsMode", "v3turbo"), language, p.get("voice"))
                        if isinstance(tts, VieNeuAdapter):
                            tts.voice = p.get("voice")
                            tts.ref_audio = p.get("refAudio")
                        if script_path:
                            voices = p.get("speakers") or {}
                            if isinstance(voices, str):
                                import json as _json
                                voices = _json.loads(voices) if voices.strip() else {}
                            build_from_script(project_dir, Path(script_path), tts, voices, language=language)
                        else:
                            timeline_path = project_dir / "timeline.json"
                            if not timeline_path.is_file():
                                raise ValueError("Cần script hoặc timeline.json để sinh voiceover.")
                            synthesize_voiceover_from_timeline(timeline_path, project_dir / "voiceover.wav", tts, fit=True)
                video_path = project_dir / "output.mp4"
                if p.get("renderer", "hyperframes") == "whiteboard":
                    self._set_stage(job, "whiteboard")
                    from ..whiteboard import render_whiteboard, scene_pairs
                    render_whiteboard(project_dir, video_path, fps=p.get("fps"))
                    result_scene = scene_pairs(project_dir)[0][0].stem
                else:
                    self._set_stage(job, "render")
                    render_hyperframes(project_dir, video_path, fps=p.get("fps"))
                    result_scene = None
                apply_format(video_path, p.get("format"), p.get("formatMode", "fit"))
                job.output_dir = project_dir
                result = {
                    "outputDir": str(project_dir),
                    "video": str(video_path),
                    "renderer": renderer,
                }
                if result_scene:
                    result["sceneName"] = result_scene
                if (project_dir / "index.html").is_file():
                    result["composition"] = str(project_dir / "index.html")
                for key, fname in (("timeline", "timeline.json"), ("audio", "voiceover.wav")):
                    if (project_dir / fname).is_file():
                        result[key] = str(project_dir / fname)
                with self._lock:
                    job.result = result
                    job.status = "done"
                    job.version += 1
                self._set_stage(job, "done")
                return

            self._set_stage(job, "parse")
            language = p.get("language", "vi")
            tts = engines.get_tts(p["dryRun"], p["ttsMode"], language, p.get("voice"))
            aligner = None
            if p["align"] and not p["dryRun"]:
                aligner = engines.get_aligner(p["whisperModel"], p["whisperDevice"], p["computeType"], language)
            with self._tts_lock:
                result = build(
                    Path(p["scriptPath"]),
                    Path(p["outputDir"]),
                    voice=p.get("voice"),
                    ref_audio=p.get("refAudio"),
                    tts_mode=p["ttsMode"],
                    align=p["align"],
                    whisper_model=p["whisperModel"],
                    whisper_device=p["whisperDevice"],
                    whisper_compute_type=p["computeType"],
                    dry_run=p["dryRun"],
                    language=language,
                    tts=tts,
                    aligner=aligner,
                    on_stage=lambda name: self._set_stage(job, name),
                )
            job.output_dir = Path(result["outputDir"])
            if p.get("renderer") == "whiteboard":
                self._set_stage(job, "whiteboard")
                from ..whiteboard import render_whiteboard
                video_path = job.output_dir / "output.mp4"
                render_whiteboard(job.output_dir, video_path, fps=p.get("fps"))
                result["video"] = str(video_path)
            elif p["renderMp4"]:
                self._set_stage(job, "render")
                video_path = job.output_dir / "output.mp4"
                render_hyperframes(job.output_dir, video_path, fps=p.get("fps"))
                result["video"] = str(video_path)
            if (job.output_dir / "output.mp4").is_file():
                apply_format(job.output_dir / "output.mp4", p.get("format"), p.get("formatMode", "fit"))
            with self._lock:
                job.result = result
                job.status = "done"
                job.version += 1
            self._set_stage(job, "done")
        except Exception as error:
            with self._lock:
                job.status = "error"
                job.error = str(error)
                job.version += 1

    def _prune_locked(self) -> None:
        finished = [jid for jid, j in self._jobs.items() if j.status in ("done", "error")]
        overflow = len(finished) - self._max_keep
        for jid in finished[: max(0, overflow)]:
            self._jobs.pop(jid, None)


def artifact_path(job: Job, kind: str) -> Path | None:
    if job.output_dir is None or kind not in ARTIFACT_FILES:
        return None
    return (job.output_dir / ARTIFACT_FILES[kind]).resolve()
