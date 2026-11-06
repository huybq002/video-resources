import json
from pathlib import Path

import numpy as np

from code2video.tts import DryRunTTS
from code2video.voiceover import _trim_silence, build_whiteboard_from_script
from code2video.whiteboard import apply_windows_to_annotations

SRT = "1\n00:00:00,000 --> 00:00:09,000\nHello\n\n2\n00:00:09,000 --> 00:00:19,000\nA much longer sentence for the second cue\n\n3\n00:00:19,000 --> 00:00:29,000\nThird\n"


def test_build_whiteboard_from_script_derives_windows_from_speech(tmp_path: Path) -> None:
    script = tmp_path / "script.srt"
    script.write_text(SRT, encoding="utf-8")
    tts = DryRunTTS()
    stats = build_whiteboard_from_script(tmp_path, script, tts, language="en")

    windows = stats["windows"]
    assert len(windows) == 3
    # DryRunTTS: dur = max(250, 65ms/char); window = max(700, dur + 300), bắt đầu sau lead 350ms.
    assert windows[0] == (350, 350 + 700)
    dur2 = 65 * len("A much longer sentence for the second cue")
    assert windows[1][0] == windows[0][1]
    assert windows[1][1] - windows[1][0] == dur2 + 300
    assert windows[2][0] == windows[1][1]

    timeline = json.loads((tmp_path / "timeline.json").read_text(encoding="utf-8"))
    assert [c["startMs"] for c in timeline["cues"]] == [w[0] for w in windows]
    assert [c["endMs"] for c in timeline["cues"]] == [w[1] for w in windows]
    assert (tmp_path / "voiceover.wav").is_file()
    # Timeline chỉ dài bằng lead + các cửa sổ giọng thật, không pad im lặng theo SRT cũ.
    assert stats["durationMs"] == windows[-1][1]


def test_trim_silence_cuts_leading_and_trailing_silence() -> None:
    rate = 24000
    clip = np.concatenate([
        np.zeros(rate * 2, dtype=np.float32),
        0.5 * np.ones(rate, dtype=np.float32),
        np.zeros(rate * 2, dtype=np.float32),
    ])
    out = _trim_silence(clip, rate)
    assert 0.8 * rate < len(out) < 1.4 * rate
    assert np.allclose(_trim_silence(np.zeros(rate, dtype=np.float32), rate), np.zeros(rate))


def test_apply_windows_to_annotations_rewrites_reveals(tmp_path: Path) -> None:
    annotation = tmp_path / "scene-01.annotation.json"
    annotation.write_text(json.dumps({
        "sceneId": "scene-01",
        "sceneDurationMs": 99999,
        "elements": [
            {"sequence": 2, "reveal": {"startMs": 0, "durationMs": 1400}},
            {"sequence": 1, "reveal": {"startMs": 0, "durationMs": 1400}},
        ],
    }), encoding="utf-8")
    (tmp_path / "scene-01.png").touch()

    windows = [(350, 1050), (1050, 3200)]
    apply_windows_to_annotations(tmp_path, windows)

    data = json.loads(annotation.read_text(encoding="utf-8"))
    elements = sorted(data["elements"], key=lambda e: e["sequence"])
    assert elements[0]["reveal"] == {"startMs": 350, "durationMs": 600}
    assert elements[1]["reveal"] == {"startMs": 1050, "durationMs": 2150 - 120}
    assert data["sceneDurationMs"] == 3200
