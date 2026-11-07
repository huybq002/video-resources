"""Chạy job tạo video không cần UI (dùng cho Claude Code / GitHub Actions).

Dùng lại ``JobQueue._execute`` của Studio nên kết quả giống hệt chạy tay:

    code2video-job job.json
    code2video-job --project examples/hyperframes-multi-scene --dry-run
    code2video-job --flow flows/x.flow.json --topic "chủ đề"

``job.json`` là một object job hoặc ``{"jobs": [...]}``. Mỗi job:

    {
      "engine": "hyperframes",          // hoặc "whiteboard"
      "project": "path/to/project",     // thư mục có index.html (+ script.srt)
      "script": "script.srt",           // tùy chọn, mặc định tự tìm trong project
      "fps": 60, "hfQuality": "delivery", "wbLongEdge": 1080,
      "voice": "Hải Đăng", "speakers": {"An": "Hải Đăng"},
      "ttsMode": "v3turbo", "language": "vi", "dryRun": false,
      "format": "16:9",
      "reuseVoiceover": true            // 2nd cut of a story: reuse voiceover.wav + timeline.json already in the project
    }

hoặc ``{"flow": "flows/x.flow.json", "topic": "...", "outputDir": "build/run1"}``.
Mã thoát 0 khi mọi job xong, 1 nếu có job lỗi.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from ._env import configure_cache, load_dotenv


def _find_script(project: Path) -> Path | None:
    for name in ("script.srt", "script.txt"):
        if (project / name).is_file():
            return project / name
    for pattern in ("*.srt", "*.txt"):
        for candidate in sorted(project.glob(pattern)):
            return candidate
    return None


def project_roots(base: Path) -> list[Path]:
    """Thư mục project = thư mục chứa index.html; base là project nếu nó tự có index.html."""
    if (base / "index.html").is_file():
        return [base]
    return sorted({p.parent for p in base.rglob("index.html") if "node_modules" not in p.parts})


def build_params(spec: dict, base: Path) -> list[dict]:
    """Chuyển một job spec thành danh sách params cho JobQueue (1 job / project)."""
    if spec.get("flow"):
        flow_path = Path(spec["flow"])
        if not flow_path.is_absolute():
            flow_path = base / flow_path
        flow = json.loads(flow_path.read_text(encoding="utf-8"))
        out = Path(spec.get("outputDir") or "build/flow-run")
        out.mkdir(parents=True, exist_ok=True)
        return [{
            "mode": "flow", "flow": flow, "flowId": flow_path.stem,
            "topic": str(spec.get("topic") or "").strip(), "outputDir": str(out),
        }]

    project = spec.get("project")
    if not project:
        raise ValueError("Job cần 'project' hoặc 'flow'.")
    root = Path(project)
    if not root.is_absolute():
        root = base / root
    engine = spec.get("engine", "hyperframes")
    roots = project_roots(root) if engine == "hyperframes" else [root]
    if not roots:
        raise ValueError(f"Không có index.html trong {root}")
    common = {
        "mode": "upload", "renderer": engine, "makeVoiceover": True,
        "voice": spec.get("voice") or None, "ttsMode": spec.get("ttsMode", "v3turbo"),
        "refAudio": spec.get("refAudio"), "dryRun": bool(spec.get("dryRun", False)),
        "reuseVoiceover": bool(spec.get("reuseVoiceover", False)),
        "speakers": spec.get("speakers") or {}, "fps": spec.get("fps"),
        "hfQuality": spec.get("hfQuality") or None, "wbLongEdge": spec.get("wbLongEdge") or None,
        "language": spec.get("language", "vi"),
        "format": spec.get("format"), "formatMode": spec.get("formatMode", "fit"),
    }
    jobs = []
    for r in roots:
        script = Path(spec["script"]) if spec.get("script") else _find_script(r)
        if script and not script.is_absolute() and not script.is_file():
            script = r / script
        params = {**common, "outputDir": str(r), "scriptPath": str(script) if script else None}
        jobs.append(params)
    return jobs


def merge_videos(videos: list[Path], output: Path) -> Path:
    """Ghép các mp4 (cùng khung hình) nối tiếp bằng ffmpeg concat filter, mã hóa lại h264/aac."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("Cần ffmpeg trong PATH để ghép video.")
    if len(videos) < 2:
        raise ValueError("Cần ít nhất 2 video để ghép.")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg, "-y", "-loglevel", "error"]
    for v in videos:
        cmd += ["-i", str(v)]
    n = len(videos)
    chains = "".join(
        f"[{i}:v:0]setsar=1,format=yuv420p[v{i}];[{i}:a:0]aresample=48000,aformat=channel_layouts=stereo[a{i}];"
        for i in range(n)
    )
    inputs = "".join(f"[v{i}][a{i}]" for i in range(n))
    cmd += [
        "-filter_complex", f"{chains}{inputs}concat=n={n}:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output),
    ]
    subprocess.run(cmd, check=True)
    return output


def run_jobs(specs: list[dict], base: Path | None = None, merge: Path | None = None) -> list[dict]:
    from .studio.jobs import Job, JobQueue

    base = base or Path.cwd()
    queue = JobQueue()
    report: list[dict] = []
    for spec in specs:
        try:
            all_params = build_params(spec, base)
        except Exception as error:  # spec sai: ghi lỗi, chạy tiếp job khác
            report.append({"status": "error", "error": str(error), "spec": spec})
            continue
        for params in all_params:
            job = Job(id=uuid.uuid4().hex[:12], params=params)
            print(f"[job {job.id}] {params.get('outputDir')}", file=sys.stderr, flush=True)
            queue._execute(job)  # đồng bộ, không dùng worker thread
            entry = {"id": job.id, "status": job.status, "outputDir": params.get("outputDir")}
            if job.status == "done":
                entry.update(job.result or {})
            else:
                entry["error"] = job.error
            report.append(entry)
    videos = [Path(r["video"]) for r in report if r.get("status") == "done" and r.get("video")]
    if merge:
        failed = [r for r in report if r.get("status") != "done"]
        if failed:
            report.append({"status": "error", "error": "Bỏ qua ghép vì có cảnh lỗi."})
        else:
            try:
                report.append({"status": "done", "merged": str(merge_videos(videos, merge)), "scenes": len(videos)})
            except Exception as error:
                report.append({"status": "error", "error": f"Ghép lỗi: {error}"})
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="code2video-job", description="Chạy job video không UI")
    parser.add_argument("spec", nargs="?", type=Path, help="file job.json")
    parser.add_argument("--project", type=Path, help="thư mục project (thay cho job.json)")
    parser.add_argument("--engine", default="hyperframes", choices=["hyperframes", "whiteboard"])
    parser.add_argument("--flow", type=Path, help="file *.flow.json (chạy AI workflow)")
    parser.add_argument("--topic", default="")
    parser.add_argument("--fps", type=int)
    parser.add_argument("--quality", dest="hfQuality")
    parser.add_argument("--dry-run", action="store_true", help="TTS giả, không cần model")
    parser.add_argument("--merge", type=Path, help="ghép video các project theo thứ tự thành file này")
    parser.add_argument("--report", type=Path, help="ghi báo cáo JSON ra file")
    args = parser.parse_args(argv)

    load_dotenv()
    configure_cache()
    base = Path.cwd()
    if args.spec:
        data = json.loads(args.spec.read_text(encoding="utf-8-sig"))
        specs = data["jobs"] if isinstance(data, dict) and "jobs" in data else [data]
        base = Path.cwd()  # đường dẫn tương đối trong job.json tính từ thư mục chạy (gốc repo)
    elif args.flow:
        specs = [{"flow": str(args.flow), "topic": args.topic}]
    elif args.project:
        specs = [{
            "project": str(args.project), "engine": args.engine, "fps": args.fps,
            "hfQuality": args.hfQuality, "dryRun": args.dry_run,
        }]
    else:
        parser.error("Cần job.json, --project hoặc --flow")

    # Cờ CLI ghi đè giá trị trong job.json (trước đây --dry-run/--fps/--quality bị bỏ qua khi dùng job.json).
    overrides = {"dryRun": True if args.dry_run else None, "fps": args.fps, "hfQuality": args.hfQuality}
    overrides = {k: v for k, v in overrides.items() if v is not None}
    if overrides:
        specs = [{**spec, **overrides} for spec in specs]

    report = run_jobs(specs, base, args.merge)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text)
    return 1 if any(r.get("status") != "done" for r in report) else 0


if __name__ == "__main__":
    raise SystemExit(main())
