from __future__ import annotations

import argparse
import json
from pathlib import Path

from .alignment import FasterWhisperAligner
from ._env import configure_cache
from .pipeline import build, render_hyperframes
from .tts import DryRunTTS, VieNeuAdapter


SCRIPT_SUFFIXES = (".srt", ".txt")


def resolve_inputs(paths: list[Path]) -> list[Path]:
    """Mở rộng thư mục thành danh sách file script, giữ thứ tự và loại trùng."""
    resolved: list[Path] = []
    seen: set[Path] = set()
    for entry in paths:
        candidates = (
            sorted(p for p in entry.rglob("*") if p.suffix.lower() in SCRIPT_SUFFIXES)
            if entry.is_dir()
            else [entry]
        )
        for candidate in candidates:
            key = candidate.resolve()
            if key not in seen:
                seen.add(key)
                resolved.append(candidate)
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(prog="code2video", description="VieNeu-TTS + faster-whisper + HyperFrames pipeline")
    parser.add_argument("script", type=Path, nargs="+", help=".srt/.txt file, hoặc thư mục (đệ quy) để chạy hàng loạt")
    parser.add_argument("--output-dir", type=Path, default=Path("build/video"))
    parser.add_argument("--voice")
    parser.add_argument("--ref-audio", type=str)
    parser.add_argument("--tts-mode", default="v3turbo")
    parser.add_argument("--whisper-model", default="small")
    parser.add_argument("--whisper-device", default="cpu")
    parser.add_argument("--whisper-compute-type", default="int8")
    parser.add_argument("--skip-alignment", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Build silent deterministic audio without loading TTS/alignment models")
    parser.add_argument("--render", action="store_true", help="Run npx hyperframes render after building the project")
    parser.add_argument("--video-output", type=Path, default=Path("build/video/output.mp4"))
    parser.add_argument("--hyperframes-command", default="npx hyperframes")
    args = parser.parse_args()

    configure_cache()
    scripts = resolve_inputs(args.script)
    if not scripts:
        parser.error(f"Không tìm thấy file .srt/.txt nào trong {args.script}")
    batch = len(scripts) > 1

    # Nạp model một lần rồi tái dùng cho mọi file trong lô.
    tts = DryRunTTS() if args.dry_run else VieNeuAdapter(mode=args.tts_mode)
    aligner = None
    if not args.dry_run and not args.skip_alignment:
        aligner = FasterWhisperAligner(args.whisper_model, args.whisper_device, args.whisper_compute_type)

    results = []
    failures = 0
    for script in scripts:
        out_dir = args.output_dir / script.stem if batch else args.output_dir
        try:
            result = build(
                script,
                out_dir,
                voice=args.voice,
                ref_audio=args.ref_audio,
                tts_mode=args.tts_mode,
                align=not args.skip_alignment,
                whisper_model=args.whisper_model,
                whisper_device=args.whisper_device,
                whisper_compute_type=args.whisper_compute_type,
                dry_run=args.dry_run,
                tts=tts,
                aligner=aligner,
            )
            if args.render:
                video_output = out_dir / "output.mp4" if batch else args.video_output
                render_hyperframes(out_dir, video_output, args.hyperframes_command)
                result["video"] = str(video_output)
            results.append(result)
        except Exception as error:
            failures += 1
            results.append({"script": str(script), "error": str(error)})

    payload = results if batch else results[0]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
