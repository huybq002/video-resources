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


def _pen_path(project_dir: Path) -> Path | None:
    """Ảnh cây bút: env WHITEBOARD_PEN > pen.png/hand.png trong project > asset mặc định của repo."""
    env = os.environ.get("WHITEBOARD_PEN")
    if env:
        if env.strip().lower() in ("none", "default", "off"):
            return None
        candidate = Path(env).expanduser()
        if candidate.is_file():
            return candidate
    for name in ("pen.png", "hand.png"):
        local = Path(project_dir) / name
        if local.is_file():
            return local
    default = Path(__file__).resolve().parents[2] / "assets" / "whiteboard-pen.png"
    return default if default.is_file() else None


def apply_windows_to_annotations(project_dir: Path, windows: list[tuple[int, int]]) -> None:
    """Ghi đè reveal.startMs/durationMs của mọi scene trong project theo cửa sổ giọng đọc.

    Cue thứ i (theo thứ tự SRT) ánh xạ tới element có sequence = i+1; nét vẽ kéo dài
    gần hết cửa sổ (chừa 120ms lấy hơi) để bút không dừng giữa các đoạn thoại.
    """
    for _, annotation in scene_pairs(project_dir):
        data = json.loads(annotation.read_text(encoding="utf-8"))
        elements = sorted(data.get("elements", []), key=lambda e: int(e.get("sequence", 0)))
        for idx, element in enumerate(elements[: len(windows)]):
            start, end = windows[idx]
            reveal = element.setdefault("reveal", {})
            reveal["startMs"] = start
            reveal["durationMs"] = max(600, end - start - 120)
        if windows:
            data["sceneDurationMs"] = max(end for _, end in windows)
        annotation.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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
    long_edge: int | None = None,
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
        pen = _pen_path(project_dir)
        if pen is not None:
            command.append(str(pen))
        command += ["--fps", str(fps or os.environ.get("WHITEBOARD_FPS", "60")),
                    "--pause", os.environ.get("WHITEBOARD_PAUSE", "off"),
                    "--full-color-ink"]
        edge = long_edge or os.environ.get("WHITEBOARD_LONG_EDGE")
        if edge:
            command += ["--cap-long-edge", str(edge)]
        subprocess.run(command, cwd=root, check=True, env=_child_env())
        subprocess.run(
            [
                ffmpeg, "-y", "-loglevel", "error", "-i", str(silent_scene), "-i", str(voiceover),
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                "-af", "apad", "-shortest", str(output_path),
            ],
            check=True,
        )


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
