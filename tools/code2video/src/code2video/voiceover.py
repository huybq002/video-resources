from __future__ import annotations

import json
import re
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


import os as _os
# Pace (owner, 2026-11-12: "a bit faster, but not too fast"): every line is read slightly faster than the TTS default,
# a tight line may go up to the cap, never beyond. Override per run with C2V_VOICE_TEMPO / C2V_VOICE_MAX_TEMPO.
BASE_TEMPO = float(_os.environ.get("C2V_VOICE_TEMPO", "1.08"))
MAX_TEMPO = float(_os.environ.get("C2V_VOICE_MAX_TEMPO", "1.22"))
MAX_TEMPO_NATURAL = min(MAX_TEMPO, BASE_TEMPO + 0.08)   # above this a line is counted as "rushed"


def _fit_to_window(clip: np.ndarray, sample_rate: int, target_samples: int, room_samples: int | None = None,
                   stats: dict | None = None) -> np.ndarray:
    """Fit one cue's speech into its time, WITHOUT swallowing words.

    2026-11-12 (video 005): the TTS clip still carried its leading/trailing silence, so the WHOLE clip was sped up to
    the window (speech ran at 4-5 words/s, then silence), and anything over the window was cut off mid-word.
    Now: silence is trimmed first; the speech may run on into the pause before the next cue (room_samples); it is sped
    up only as much as needed, at most MAX_TEMPO; it is never cut except as a last resort, with a short fade.
    """
    if target_samples <= 0:
        return clip
    if clip.size == 0:
        return np.zeros(target_samples, dtype=np.float32)
    clip = _trim_silence(clip, sample_rate, pad_ms=40)
    room = max(target_samples, room_samples or target_samples)
    factor = max(BASE_TEMPO, min(clip.size / room, MAX_TEMPO))     # brisk by default, faster only when the line needs it
    if factor > 1.01:
        clip = _atempo(clip, sample_rate, factor)
    cut = False
    if clip.size > room:      # still too long even at the cap: fade out the last 40 ms rather than hard-cutting a word
        clip = clip[:room].copy(); f = min(room, int(0.04 * sample_rate))
        clip[-f:] *= np.linspace(1, 0, f, dtype=np.float32); cut = True
    if stats is not None:
        stats.setdefault("cues", []).append({"tempo": round(factor, 3), "cut": cut, "seconds": round(clip.size / sample_rate, 2)})
    if clip.size < target_samples:
        clip = np.pad(clip, (0, target_samples - clip.size))
    return clip


def _rooms(cues: list, sample_rate: int) -> list:
    """samples each cue may use: up to 60 ms before the next cue starts (the pause after a line is free room)"""
    starts = [int(c["startMs"]) for c in cues]
    out = []
    for i, c in enumerate(cues):
        nxt = min([st for st in starts if st > int(c["startMs"])] or [int(c["endMs"]) + 400])
        out.append(round(max(int(c["endMs"]) - int(c["startMs"]), nxt - int(c["startMs"]) - 60) * sample_rate / 1000))
    return out


def _write_fit_report(audio_path: Path, stats: dict) -> None:
    """voiceover_fit.json next to the wav: verify_bundle fails a video whose voice had to be rushed or cut"""
    cues = stats.get("cues", [])
    rep = {"maxTempo": max([c["tempo"] for c in cues] or [1.0]),
           "rushed": sum(1 for c in cues if c["tempo"] > MAX_TEMPO_NATURAL), "cut": sum(1 for c in cues if c["cut"]),
           "cues": len(cues)}
    Path(audio_path).with_name("voiceover_fit.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    if rep["rushed"] or rep["cut"]:
        print(f"voiceover: {rep['rushed']} line(s) sped past x{MAX_TEMPO_NATURAL} (max x{rep['maxTempo']}), {rep['cut']} cut: "
              f"the script gives those lines too little time")


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
    rooms = _rooms(cues, sample_rate); fit_stats: dict = {}
    direction = _direction(timeline_path.parent)
    for ci, cue in enumerate(cues):
        text = (cue.get("text") or "").strip()
        if not text:
            continue
        _direct(tts, direction, cue, text)
        start_ms = int(cue["startMs"])
        window_ms = max(0, int(cue["endMs"]) - start_ms)
        clip = np.asarray(tts.synthesize(text), dtype=np.float32).reshape(-1)
        if fit:
            clip = _fit_to_window(clip, sample_rate, round(window_ms * sample_rate / 1000), rooms[ci], fit_stats)
        placements.append((round(start_ms * sample_rate / 1000), clip))

    total = max((start + len(clip) for start, clip in placements), default=0) + sample_rate // 2
    track = np.zeros(total, dtype=np.float32)
    for start, clip in placements:
        track[start:start + len(clip)] += clip

    write_wav(track, sample_rate, Path(audio_path))
    if fit: _write_fit_report(Path(audio_path), fit_stats)
    return {
        "cues": len(placements),
        "durationMs": round(len(track) * 1000 / sample_rate),
        "audio": str(audio_path),
    }


def _auto_voices(tts, speakers: list[str], voices: dict[str, str], language: str,
                 genders: dict[str, str] | None = None) -> dict[str, str]:
    """Nhân vật chưa được chọn giọng → tự gán theo giới tính (đoán từ tên), mỗi người một giọng."""
    named = [name for name in speakers if name]
    if not named or not hasattr(tts, "voice"):
        return voices
    from .voice_assign import assign_voices

    return assign_voices(named, voices, mode=getattr(tts, "mode", "v3turbo"), language=language, genders=genders)


def _direction(project_dir: Path) -> dict:
    """assets/voice_direction.json (written by the generator): startMs -> {emote, narrator, mood}"""
    f = Path(project_dir) / "assets" / "voice_direction.json"
    try:
        return {int(d["startMs"]): d for d in json.loads(f.read_text(encoding="utf-8"))}
    except Exception:
        return {}


def _direct(tts, direction: dict, cue: dict, text: str) -> None:
    """set the TTS prosody for this line (emotion, narrator or character, punctuation)"""
    if not hasattr(tts, "prosody"):
        return
    from .tts import direction_prosody
    st = int(cue.get("startMs", 0))
    d = direction.get(st) or next((v for k, v in direction.items() if abs(k - st) < 400), {})
    tts.prosody = direction_prosody(d.get("emote", ""), text, bool(d.get("narrator")), d.get("mood", ""))


def _prepare_track(timeline_path: Path, tts: TTSAdapter, voices: dict[str, str], fit: bool) -> dict:
    data = json.loads(Path(timeline_path).read_text(encoding="utf-8"))
    cues = data.get("cues", [])
    direction = _direction(Path(timeline_path).parent)
    sample_rate = tts.sample_rate
    default_voice = voices.get("") or (next(iter(voices.values()), None) if voices else None)

    placements: list[tuple[int, np.ndarray]] = []
    rooms = _rooms(cues, sample_rate); fit_stats: dict = {}
    for ci, cue in enumerate(cues):
        text = (cue.get("text") or "").strip()
        if not text:
            continue
        speaker = cue.get("speaker", "")
        if voices and hasattr(tts, "voice"):
            tts.voice = voices.get(speaker, default_voice)
        _direct(tts, direction, cue, text)
        start_ms = int(cue["startMs"])
        window_ms = max(0, int(cue["endMs"]) - start_ms)
        clip = np.asarray(tts.synthesize(text), dtype=np.float32).reshape(-1)
        if fit:
            clip = _fit_to_window(clip, sample_rate, round(window_ms * sample_rate / 1000), rooms[ci], fit_stats)
        placements.append((round(start_ms * sample_rate / 1000), clip))

    total = max((start + len(clip) for start, clip in placements), default=0) + sample_rate // 2
    track = np.zeros(total, dtype=np.float32)
    for start, clip in placements:
        track[start:start + len(clip)] += clip
    write_wav(track, sample_rate, Path(timeline_path).parent / "voiceover.wav")
    if fit: _write_fit_report(Path(timeline_path).parent / "voiceover.wav", fit_stats)
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
    from .script_parse import parse_script, speaker_genders

    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    voices = voices or {}
    raw = Path(script_path).read_text(encoding="utf-8-sig")
    lines, speakers = parse_script(raw)
    voices = _auto_voices(tts, speakers, voices, language, speaker_genders(lines))
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

    synced = sync_composition_audio(project_dir, audio_path)
    extra = {"audioCopy": str(synced)} if synced else {}
    return {"timeline": str(timeline_path), "audio": str(audio_path), "speakers": speakers, "voices": voices, **stats, **extra}


_AUDIO_SRC = re.compile(r"""<audio[^>]*?\ssrc\s*=\s*(?P<q>['"])(?P<src>.+?)(?P=q)""", re.I | re.S)


def sync_composition_audio(project_dir: Path, audio_path: Path) -> Path | None:
    """index.html dựng sẵn (vd. của skill) trỏ tới assets/audio/voiceover.wav, còn tool ghi voiceover.wav ở gốc project.

    Chép file vào đúng đường dẫn mà <audio src> yêu cầu (chỉ trong project), nếu không HyperFrames render video câm.
    """
    project_dir = Path(project_dir)
    audio_path = Path(audio_path)
    index = project_dir / "index.html"
    if not index.is_file() or not audio_path.is_file():
        return None
    html = index.read_text(encoding="utf-8", errors="replace")
    root = project_dir.resolve()
    copied: Path | None = None
    for match in _AUDIO_SRC.finditer(html):
        src = match.group("src").strip()
        if "://" in src or src.startswith(("/", "data:")):
            continue
        target = (project_dir / src).resolve()
        if root not in target.parents or target == audio_path.resolve():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(audio_path, target)
        copied = target
    return copied


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
