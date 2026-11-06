from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _child_env() -> dict:
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return env


def whiteboard_root() -> Path | None:
    configured = os.environ.get("WHITEBOARD_ROOT")
    if not configured:
        return None
    return Path(configured).expanduser().resolve()


def _hand_path(project_dir: Path) -> Path | None:
    """Ảnh tay/bút: env WHITEBOARD_HAND > hand.png trong project > asset mặc định của repo."""
    env = os.environ.get("WHITEBOARD_HAND")
    if env:
        if env.strip().lower() in ("none", "default", "off"):
            return None
        candidate = Path(env).expanduser()
        if candidate.is_file():
            return candidate
    local = Path(project_dir) / "hand.png"
    if local.is_file():
        return local
    default = Path(__file__).resolve().parents[2] / "assets" / "whiteboard-hand.png"
    return default if default.is_file() else None


def scene_pairs(project_dir: Path) -> list[tuple[Path, Path]]:
    pairs = []
    for annotation in sorted(project_dir.rglob("*.annotation.json")):
        image = annotation.with_name(annotation.name.removesuffix(".annotation.json") + ".png")
        if image.is_file():
            pairs.append((image, annotation))
    return pairs


def render_whiteboard(
    project_dir: Path,
    output_path: Path,
    *,
    root: Path | None = None,
    python: str | None = None,
    fps: int | None = None,
) -> None:
    project_dir = Path(project_dir).resolve()
    output_path = Path(output_path).resolve()
    root = (root or whiteboard_root())
    if root is None:
        raise RuntimeError("Whiteboard chưa được cấu hình. Đặt WHITEBOARD_ROOT tới thư mục srt-whiteboard-animation.")
    root = root.resolve()
    render_script = root / "scripts" / "render_stream_whiteboard.py"
    if not render_script.is_file():
        raise RuntimeError(f"Không tìm thấy scripts của whiteboard trong {root / 'scripts'}.")
    pairs = scene_pairs(project_dir)
    if len(pairs) != 1:
        raise RuntimeError(f"Mỗi scene cần đúng một cặp PNG/annotation; tìm thấy {len(pairs)} cặp.")

    python = python or os.environ.get("WHITEBOARD_PYTHON") or sys.executable
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("Whiteboard cần ffmpeg trong PATH để ghép voiceover.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    voiceover = project_dir / "voiceover.wav"
    if not voiceover.is_file():
        raise RuntimeError("Cần script để tạo voiceover trước khi render scene whiteboard.")
    with tempfile.TemporaryDirectory(prefix="code2video-whiteboard-") as temp_dir:
        silent_scene = Path(temp_dir) / "scene.mp4"
        image, annotation = pairs[0]
        command = [python, str(render_script), str(image), str(annotation), str(silent_scene)]
        hand = _hand_path(project_dir)
        if hand is not None:
            command.append(str(hand))
        command += ["--fps", str(fps or os.environ.get("WHITEBOARD_FPS", "60")),
                    "--pause", os.environ.get("WHITEBOARD_PAUSE", "light")]
        if os.environ.get("WHITEBOARD_LONG_EDGE"):
            command += ["--cap-long-edge", os.environ["WHITEBOARD_LONG_EDGE"]]
        subprocess.run(command, cwd=root, check=True, env=_child_env())
        subprocess.run(
            [
                ffmpeg, "-y", "-loglevel", "error", "-i", str(silent_scene), "-i", str(voiceover),
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
                "-af", "apad", "-shortest", str(output_path),
            ],
            check=True,
        )


def render_whiteboard_preview(
    image_path: Path,
    annotation_path: Path,
    output_path: Path,
    *,
    root: Path | None = None,
    python: str | None = None,
    seconds: int = 10,
    fps: int = 30,
    long_edge: int = 640,
) -> None:
    """Render nhanh không giọng: thấp độ phân giải + fps để soi nét vẽ trước khi render thật."""
    image_path = Path(image_path).resolve()
    annotation_path = Path(annotation_path).resolve()
    root = (root or whiteboard_root())
    if root is None:
        raise RuntimeError("Whiteboard chưa được cấu hình. Đặt WHITEBOARD_ROOT tới thư mục srt-whiteboard-animation.")
    root = root.resolve()
    render_script = root / "scripts" / "render_stream_whiteboard.py"
    if not render_script.is_file():
        raise RuntimeError(f"Không tìm thấy scripts của whiteboard trong {root / 'scripts'}.")
    python = python or os.environ.get("WHITEBOARD_PYTHON") or sys.executable
    total_ms = seconds * 1000
    try:
        data = json.loads(annotation_path.read_text(encoding="utf-8"))
        annotated_ms = int(data.get("sceneDurationMs") or 0)
        if annotated_ms < total_ms:
            total_ms = annotated_ms
        elif annotated_ms > total_ms:
            # engine không cắt ngắn được — co giãn timeline về đúng cửa sổ preview
            scale = total_ms / annotated_ms
            for element in data.get("elements", []):
                reveal = element.get("reveal", {})
                reveal["startMs"] = int(float(reveal.get("startMs", 0)) * scale)
                reveal["durationMs"] = max(100, int(float(reveal.get("durationMs", 0)) * scale))
            data["sceneDurationMs"] = total_ms
    except (json.JSONDecodeError, OSError, ValueError):
        data = None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    engine_annotation = annotation_path
    if data is not None:
        engine_annotation = output_path.parent / "preview-annotation.json"
        engine_annotation.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    command = [python, str(render_script), str(image_path), str(engine_annotation), str(output_path)]
    pen = _hand_path(annotation_path.parent)
    if pen is not None:
        command.append(str(pen))
    command += ["--fps", str(fps), "--cap-long-edge", str(long_edge), "--total-ms", str(total_ms), "--full-color-ink"]
    subprocess.run(command, cwd=root, check=True, env=_child_env())


def merge_whiteboard_scenes(
    scene_dirs: list[Path],
    output_path: Path,
    *,
    root: Path | None = None,
    python: str | None = None,
) -> None:
    root = root or whiteboard_root()
    if root is None:
        raise RuntimeError("Whiteboard chưa được cấu hình. Đặt WHITEBOARD_ROOT tới thư mục srt-whiteboard-animation.")
    root = root.resolve()
    merge_script = root / "scripts" / "merge_scenes.py"
    if not merge_script.is_file():
        raise RuntimeError(f"Không tìm thấy script ghép cảnh: {merge_script}.")
    python = python or os.environ.get("WHITEBOARD_PYTHON") or sys.executable
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("Whiteboard cần ffmpeg trong PATH để ghép video và voiceover.")

    videos = [Path(folder).resolve() / "output.mp4" for folder in scene_dirs]
    if len(videos) < 2:
        raise ValueError("Cần chọn ít nhất hai scene whiteboard để ghép.")
    missing = [str(path) for path in videos if not path.is_file()]
    if missing:
        raise ValueError(f"Thiếu video của scene: {', '.join(missing)}")

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="code2video-whiteboard-merge-") as temp_dir:
        temp = Path(temp_dir)
        merged_video = temp / "scenes.mp4"
        merged_audio = temp / "voiceover.wav"
        subprocess.run(
            [python, str(merge_script), "--inputs", *map(str, videos), "--output", str(merged_video)],
            cwd=root,
            check=True,
            env=_child_env(),
        )
        audio_labels = "".join(f"[a{index}]" for index in range(len(videos)))
        normalized = ";".join(
            f"[{index}:a:0]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a{index}]"
            for index in range(len(videos))
        )
        audio_graph = f"{normalized};{audio_labels}concat=n={len(videos)}:v=0:a=1[aout]"
        subprocess.run(
            [
                ffmpeg, "-y", "-loglevel", "error",
                *[arg for video in videos for arg in ("-i", str(video))],
                "-filter_complex", audio_graph, "-map", "[aout]", "-c:a", "pcm_s16le", str(merged_audio),
            ],
            check=True,
        )
        subprocess.run(
            [
                ffmpeg, "-y", "-loglevel", "error", "-i", str(merged_video), "-i", str(merged_audio),
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-af", "apad", "-shortest",
                str(output_path),
            ],
            check=True,
        )
