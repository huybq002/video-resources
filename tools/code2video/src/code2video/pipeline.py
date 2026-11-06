from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from .alignment import FasterWhisperAligner
from .composition import render_composition
from .models import Timeline
from .srt import cues_from_lines, parse_srt
from .timeline import synthesize_cues
from .tts import DryRunTTS, TTSAdapter, VieNeuAdapter


def build(
    script_path: Path,
    output_dir: Path,
    *,
    voice: str | None = None,
    ref_audio: str | None = None,
    tts_mode: str = "v3turbo",
    align: bool = True,
    whisper_model: str = "small",
    whisper_device: str = "cpu",
    whisper_compute_type: str = "int8",
    dry_run: bool = False,
    language: str = "vi",
    tts: Optional[TTSAdapter] = None,
    aligner: Optional[FasterWhisperAligner] = None,
    on_stage: Optional[Callable[[str], None]] = None,
) -> dict:
    def stage(name: str) -> None:
        if on_stage is not None:
            on_stage(name)

    raw = script_path.read_text(encoding="utf-8-sig")
    cues = parse_srt(raw) if script_path.suffix.lower() == ".srt" else cues_from_lines(raw)
    if not cues:
        raise ValueError(f"Không tìm thấy nội dung trong {script_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    if tts is None:
        tts = DryRunTTS() if dry_run else VieNeuAdapter(voice=voice, ref_audio=ref_audio, mode=tts_mode)
    elif isinstance(tts, VieNeuAdapter):
        tts.voice = voice
        tts.ref_audio = ref_audio
    stage("tts")
    timeline = synthesize_cues(cues, tts, output_dir / "voiceover.wav", language=language)
    if align and not dry_run:
        if aligner is None:
            aligner = FasterWhisperAligner(whisper_model, whisper_device, whisper_compute_type, language=language)
        stage("align")
        aligner.align(output_dir / "voiceover.wav", timeline.cues)
    timeline_path = output_dir / "timeline.json"
    timeline_path.write_text(json.dumps(timeline.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    stage("compose")
    composition_path = render_composition(timeline, output_dir / "index.html")
    return {
        "outputDir": str(output_dir),
        "audio": str(output_dir / "voiceover.wav"),
        "timeline": str(timeline_path),
        "composition": str(composition_path),
        "durationMs": timeline.duration_ms,
        "cueCount": len(timeline.cues),
        "sceneCount": len(timeline.scenes),
    }



FORMATS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350)}


def _video_size(path: Path) -> tuple[int, int] | None:
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    result = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    parts = result.stdout.strip().split(",")
    if len(parts) < 2:
        return None
    return int(parts[0]), int(parts[1])


def apply_format(video_path: Path, fmt: str | None, mode: str = "fit") -> None:
    """Chuyển khung hình video sang tỉ lệ đích (YouTube 16:9, TikTok/Shorts 9:16, 1:1, 4:5)."""
    if not fmt or fmt not in FORMATS:
        return
    video_path = Path(video_path)
    if not video_path.is_file():
        return
    width, height = FORMATS[fmt]
    size = _video_size(video_path)
    if size == (width, height):
        return
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    if mode == "fill":
        vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    else:
        vf = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
              f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x0d1211")
    temp = video_path.with_name(video_path.stem + ".fmt.mp4")
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(video_path), "-vf", vf,
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "copy",
         "-movflags", "+faststart", str(temp)],
        check=True,
    )
    temp.replace(video_path)


def render_hyperframes(project_dir: Path, output_path: Path, hyperframes_command: str = "npx hyperframes", fps: int | None = None) -> None:
    project_dir = project_dir.resolve()
    output_path = output_path.resolve()
    command = hyperframes_command.split() + ["render", "--output", str(output_path)]
    # Tăng tốc tùy chọn qua env: -q draft, -w workers, -f fps (không đổi mặc định nếu không set).
    if os.environ.get("HF_RENDER_QUALITY"):
        command += ["--quality", os.environ["HF_RENDER_QUALITY"]]
    if os.environ.get("HF_RENDER_WORKERS"):
        command += ["--workers", os.environ["HF_RENDER_WORKERS"]]
    fps_value = fps or os.environ.get("HF_RENDER_FPS")
    if fps_value:
        command += ["--fps", str(fps_value)]
    # Trên Windows, "npx" thực chất là npx.cmd; shutil.which tìm đúng file theo PATHEXT.
    resolved = shutil.which(command[0])
    if resolved:
        command[0] = resolved
    subprocess.run(command, cwd=str(project_dir), check=True)
