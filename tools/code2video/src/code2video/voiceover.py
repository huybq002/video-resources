from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

from .models import Timeline
from .srt import cues_from_lines, group_scenes, parse_srt
from .timeline import synthesize_cues
from .tts import TTSAdapter, write_wav


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as handle:
        frames = handle.readframes(handle.getnframes())
        channels = handle.getnchannels()
        rate = handle.getframerate()
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio, rate


def _atempo(clip: np.ndarray, sample_rate: int, factor: float) -> np.ndarray:
    """Đổi tốc độ giữ nguyên cao độ bằng ffmpeg atempo."""
    if abs(factor - 1.0) < 0.01 or clip.size == 0:
        return clip
    factor = min(max(factor, 0.5), 100.0)
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "in.wav"
        target = Path(tmp) / "out.wav"
        write_wav(clip, sample_rate, source)
        ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-i", str(source),
             "-filter:a", f"atempo={factor:.4f}", str(target)],
            check=True,
        )
        audio, _ = _read_wav(target)
    return audio


def _fit_to_window(clip: np.ndarray, sample_rate: int, target_samples: int) -> np.ndarray:
    """Co giãn/pad để clip lấp đúng cửa sổ thời gian của cue.

    Chỉ gọi atempo (ffmpeg) khi lệch rõ (>8%); lệch nhỏ thì trim/pad để tránh spawn ffmpeg mỗi cue.
    """
    if target_samples <= 0:
        return clip
    if clip.size == 0:
        return np.zeros(target_samples, dtype=np.float32)
    if clip.size > target_samples:
        if clip.size / target_samples > 1.08:
            clip = _atempo(clip, sample_rate, clip.size / target_samples)
        clip = clip[:target_samples]
    elif clip.size < target_samples:
        clip = np.pad(clip, (0, target_samples - clip.size))
    return clip


def synthesize_voiceover_from_timeline(
    timeline_path: Path,
    audio_path: Path,
    tts: TTSAdapter,
    fit: bool = True,
) -> dict:
    """Sinh voiceover.wav từ text của từng cue trong timeline, neo đúng startMs.

    fit=True: mỗi cue được co giãn/pad vừa đúng cửa sổ [startMs, endMs] để khớp timeline.
    """
    timeline_path = Path(timeline_path)
    data = json.loads(timeline_path.read_text(encoding="utf-8"))
    cues = data.get("cues", [])
    sample_rate = tts.sample_rate

    placements: list[tuple[int, np.ndarray]] = []
    for cue in cues:
        text = (cue.get("text") or "").strip()
        if not text:
            continue
        start_ms = int(cue["startMs"])
        window_ms = max(0, int(cue["endMs"]) - start_ms)
        clip = np.asarray(tts.synthesize(text), dtype=np.float32).reshape(-1)
        if fit:
            clip = _fit_to_window(clip, sample_rate, round(window_ms * sample_rate / 1000))
        placements.append((round(start_ms * sample_rate / 1000), clip))

    total = max((start + len(clip) for start, clip in placements), default=0) + sample_rate // 2
    track = np.zeros(total, dtype=np.float32)
    for start, clip in placements:
        track[start:start + len(clip)] += clip

    write_wav(track, sample_rate, Path(audio_path))
    return {
        "cues": len(placements),
        "durationMs": round(len(track) * 1000 / sample_rate),
        "audio": str(audio_path),
    }


def _auto_voices(tts, speakers: list[str], voices: dict[str, str], language: str) -> dict[str, str]:
    """Nhân vật chưa được chọn giọng → tự gán theo giới tính (đoán từ tên), mỗi người một giọng."""
    named = [name for name in speakers if name]
    if not named or not hasattr(tts, "voice"):
        return voices
    from .voice_assign import assign_voices

    return assign_voices(named, voices, mode=getattr(tts, "mode", "v3turbo"), language=language)


def _prepare_track(timeline_path: Path, tts: TTSAdapter, voices: dict[str, str], fit: bool) -> dict:
    data = json.loads(Path(timeline_path).read_text(encoding="utf-8"))
    cues = data.get("cues", [])
    sample_rate = tts.sample_rate
    default_voice = voices.get("") or (next(iter(voices.values()), None) if voices else None)

    placements: list[tuple[int, np.ndarray]] = []
    for cue in cues:
        text = (cue.get("text") or "").strip()
        if not text:
            continue
        speaker = cue.get("speaker", "")
        if voices and hasattr(tts, "voice"):
            tts.voice = voices.get(speaker, default_voice)
        start_ms = int(cue["startMs"])
        window_ms = max(0, int(cue["endMs"]) - start_ms)
        clip = np.asarray(tts.synthesize(text), dtype=np.float32).reshape(-1)
        if fit:
            clip = _fit_to_window(clip, sample_rate, round(window_ms * sample_rate / 1000))
        placements.append((round(start_ms * sample_rate / 1000), clip))

    total = max((start + len(clip) for start, clip in placements), default=0) + sample_rate // 2
    track = np.zeros(total, dtype=np.float32)
    for start, clip in placements:
        track[start:start + len(clip)] += clip
    write_wav(track, sample_rate, Path(timeline_path).parent / "voiceover.wav")
    return {"cues": len(placements), "durationMs": round(len(track) * 1000 / sample_rate)}


def build_from_script(
    project_dir: Path,
    script_path: Path,
    tts: TTSAdapter,
    voices: dict[str, str] | None = None,
    language: str = "vi",
) -> dict:
    """Dựng timeline.json + voiceover.wav (đa giọng theo nhân vật) từ script cho composition có sẵn."""
    from .models import Cue
    from .script_parse import parse_script

    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    voices = voices or {}
    raw = Path(script_path).read_text(encoding="utf-8-sig")
    lines, speakers = parse_script(raw)
    voices = _auto_voices(tts, speakers, voices, language)
    if not lines:
        raise ValueError(f"Không tìm thấy nội dung trong {script_path}")

    timeline_path = project_dir / "timeline.json"
    audio_path = project_dir / "voiceover.wav"
    timed = all(line.end_ms > line.start_ms for line in lines)

    if timed:
        cues = [Cue(line.index, line.text, line.start_ms, line.end_ms) for line in lines]
        scenes = group_scenes(cues)
        timeline = Timeline(
            audio=audio_path.name,
            duration_ms=max(cue.end_ms for cue in cues),
            cues=cues,
            scenes=scenes,
            sample_rate=tts.sample_rate,
            language=language,
        )
        payload = timeline.to_dict()
        for cue_dict in payload["cues"]:
            cue_dict["speaker"] = next((line.speaker for line in lines if line.index == cue_dict["index"]), "")
        timeline_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        stats = _prepare_track(timeline_path, tts, voices, fit=True)
    else:
        cues = [Cue(line.index, line.text, 0, 0) for line in lines]
        timeline = synthesize_cues(cues, tts, audio_path, language=language)
        timeline_path.write_text(json.dumps(timeline.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        stats = {"cues": len(cues), "durationMs": timeline.duration_ms}

    return {"timeline": str(timeline_path), "audio": str(audio_path), "speakers": speakers, "voices": voices, **stats}


def _trim_silence(clip: np.ndarray, sample_rate: int, threshold: float = 0.008, pad_ms: int = 80) -> np.ndarray:
    """Cắt khoảng lặng ở đầu/cuối clip TTS (edge-tts thường đệm ~0.7s im lặng cuối)."""
    if clip.size == 0:
        return clip
    frame = max(1, sample_rate // 100)  # 10ms
    n = len(clip) // frame
    if n == 0:
        return clip
    energy = np.abs(clip[: n * frame].reshape(n, frame)).mean(axis=1)
    active = np.where(energy > threshold)[0]
    if active.size == 0:
        return clip
    pad = max(1, round(pad_ms * sample_rate / 1000 / frame))
    start = max(0, int(active[0] - pad) * frame)
    end = min(len(clip), int(active[-1] + 1 + pad) * frame)
    return clip[start:end]


def build_whiteboard_from_script(
    project_dir: Path,
    script_path: Path,
    tts: TTSAdapter,
    voices: dict[str, str] | None = None,
    language: str = "vi",
    tail_ms: int = 300,
    lead_ms: int = 350,
) -> dict:
    """Dựng timeline + voiceover cho scene whiteboard: cửa sổ mỗi cue = độ dài giọng đọc thật + đệm ngắn.

    Khác build_from_script ở chỗ không dùng timestamp trong SRT làm cửa sổ (cửa sổ tĩnh thường dài
    hơn giọng thật, khiến voiceover bị pad im lặng và giọng "chờ" nét vẽ). Audio được đặt thô
    (không co giãn) vào các cửa sổ suy từ chính audio, đảm bảo giọng và nét vẽ kết thúc cùng lúc.
    Trả về "windows" = [[startMs, endMs], ...] để ghi đè timing annotation trước khi render.
    """
    from .models import Cue, Timeline
    from .script_parse import parse_script

    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    voices = voices or {}
    lines, speakers = parse_script(Path(script_path).read_text(encoding="utf-8-sig"))
    voices = _auto_voices(tts, speakers, voices, language)
    if not lines:
        raise ValueError(f"Không tìm thấy nội dung trong {script_path}")
    default_voice = voices.get("") or (next(iter(voices.values()), None) if voices else None)
    sample_rate = tts.sample_rate

    windows: list[tuple[int, int]] = []
    placements: list[tuple[int, np.ndarray]] = []
    t = lead_ms
    for line in lines:
        if voices and hasattr(tts, "voice"):
            tts.voice = voices.get(line.speaker or "", default_voice)
        clip = np.asarray(tts.synthesize(line.text), dtype=np.float32).reshape(-1)
        clip = _trim_silence(clip, sample_rate)
        dur_ms = round(len(clip) * 1000 / sample_rate)
        window_ms = max(700, dur_ms + tail_ms)
        placements.append((round(t * sample_rate / 1000), clip))
        windows.append((t, t + window_ms))
        t += window_ms

    total = round(t * sample_rate / 1000) + sample_rate // 2
    track = np.zeros(total, dtype=np.float32)
    for start, clip in placements:
        track[start:start + len(clip)] += clip
    audio_path = project_dir / "voiceover.wav"
    write_wav(track, sample_rate, audio_path)

    cues = [Cue(line.index, line.text, start, end) for line, (start, end) in zip(lines, windows)]
    timeline = Timeline(
        audio=audio_path.name,
        duration_ms=t,
        cues=cues,
        scenes=group_scenes(cues),
        sample_rate=sample_rate,
        language=language,
    )
    timeline_path = project_dir / "timeline.json"
    payload = timeline.to_dict()
    for cue_dict in payload["cues"]:
        cue_dict["speaker"] = next((line.speaker for line in lines if line.index == cue_dict["index"]), "")
    timeline_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "timeline": str(timeline_path),
        "audio": str(audio_path),
        "windows": windows,
        "speakers": speakers,
        "voices": voices,
        "cues": len(windows),
        "durationMs": t,
    }


def prepare_composition_audio(project_dir: Path, script_path: Path, tts: TTSAdapter) -> Path:
    """Dựng timeline.json + voiceover.wav cho một composition có sẵn (index.html) từ script.

    Script SRT: dùng trực tiếp timestamp của SRT làm timeline, TTS fit đúng cửa sổ từng cue.
    Script text thường: TTS tự tính thời lượng (như pipeline), rồi ghi timeline.
    """
    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    raw = Path(script_path).read_text(encoding="utf-8-sig")
    timeline_path = project_dir / "timeline.json"
    audio_path = project_dir / "voiceover.wav"

    if "-->" in raw:
        cues = parse_srt(raw)
        if not cues:
            raise ValueError(f"Không tìm thấy cue trong {script_path}")
        scenes = group_scenes(cues)
        timeline = Timeline(
            audio=audio_path.name,
            duration_ms=max(cue.end_ms for cue in cues),
            cues=cues,
            scenes=scenes,
            sample_rate=tts.sample_rate,
        )
        timeline_path.write_text(json.dumps(timeline.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        synthesize_voiceover_from_timeline(timeline_path, audio_path, tts, fit=True)
    else:
        cues = cues_from_lines(raw)
        if not cues:
            raise ValueError(f"Không tìm thấy nội dung trong {script_path}")
        timeline = synthesize_cues(cues, tts, audio_path)
        timeline_path.write_text(json.dumps(timeline.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return timeline_path
