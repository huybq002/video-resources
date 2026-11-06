import json
from pathlib import Path
from unittest.mock import patch

import pytest

from code2video.whiteboard import merge_whiteboard_scenes, render_whiteboard, render_whiteboard_preview, scene_pairs


def test_scene_pairs_match_annotations_to_pngs(tmp_path: Path) -> None:
    scene = tmp_path / "assets" / "whiteboard" / "demo"
    scene.mkdir(parents=True)
    (scene / "scene-02.png").touch()
    (scene / "scene-02.annotation.json").touch()
    (scene / "scene-01.annotation.json").touch()
    (scene / "unrelated.jpg").touch()

    assert scene_pairs(tmp_path) == [(scene / "scene-02.png", scene / "scene-02.annotation.json")]


def test_render_whiteboard_renders_one_scene_and_muxes_audio(tmp_path: Path) -> None:
    root = tmp_path / "whiteboard"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "render_stream_whiteboard.py").touch()
    (scripts / "merge_scenes.py").touch()
    project = tmp_path / "project"
    project.mkdir()
    (project / "scene-01.png").touch()
    (project / "scene-01.annotation.json").touch()
    (project / "voiceover.wav").touch()
    output = project / "output.mp4"
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if command[1].endswith("render_stream_whiteboard.py"):
            Path(command[4]).touch()
        else:
            Path(command[-1]).touch()

    with patch("code2video.whiteboard.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "code2video.whiteboard.subprocess.run", side_effect=run
    ):
        render_whiteboard(project, output, root=root, python="python-whiteboard")

    assert len(calls) == 2
    assert calls[0][1].endswith("render_stream_whiteboard.py")
    assert calls[1][0] == "/usr/bin/ffmpeg"
    assert str(project / "voiceover.wav") in calls[1]
    assert output.is_file()


def test_render_whiteboard_rejects_multiple_scenes(tmp_path: Path) -> None:
    root = tmp_path / "whiteboard"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "render_stream_whiteboard.py").touch()
    for name in ("scene-01", "scene-02"):
        (tmp_path / f"{name}.png").touch()
        (tmp_path / f"{name}.annotation.json").touch()
    with patch("code2video.whiteboard.shutil.which", return_value="/usr/bin/ffmpeg"):
        with pytest.raises(RuntimeError, match="đúng một cặp"):
            render_whiteboard(tmp_path, tmp_path / "output.mp4", root=root)


def test_merge_whiteboard_scenes_joins_scene_videos_and_audio(tmp_path: Path) -> None:
    root = tmp_path / "whiteboard"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "merge_scenes.py").touch()
    scene_dirs = [tmp_path / "scene-01", tmp_path / "scene-02"]
    for scene in scene_dirs:
        scene.mkdir()
        (scene / "output.mp4").touch()
        (scene / "voiceover.wav").touch()
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if command[1].endswith("merge_scenes.py"):
            Path(command[command.index("--output") + 1]).touch()
        else:
            Path(command[-1]).touch()

    output = tmp_path / "merged.mp4"
    with patch("code2video.whiteboard.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "code2video.whiteboard.subprocess.run", side_effect=run
    ):
        merge_whiteboard_scenes(scene_dirs, output, root=root, python="python-whiteboard")

    assert len(calls) == 3
    assert calls[0][1].endswith("merge_scenes.py")
    assert any("concat=n=2:v=0:a=1[aout]" in str(arg) for arg in calls[1])
    assert calls[2][-1] == str(output)
    assert output.is_file()


def test_render_whiteboard_requires_configured_root(tmp_path: Path) -> None:
    with patch("code2video.whiteboard.whiteboard_root", return_value=None):
        with pytest.raises(RuntimeError, match="WHITEBOARD_ROOT"):
            render_whiteboard(tmp_path, tmp_path / "output.mp4")


def test_render_whiteboard_preview_uses_fast_engine_flags(tmp_path):
    root = tmp_path / "whiteboard"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "render_stream_whiteboard.py").touch()
    image = tmp_path / "scene-01.png"
    image.touch()
    annotation = tmp_path / "scene-01.annotation.json"
    annotation.write_text(json.dumps({
        "sceneDurationMs": 20000,
        "elements": [{"sequence": 1, "reveal": {"startMs": 0, "durationMs": 20000}}],
    }), encoding="utf-8")
    output = tmp_path / "preview.mp4"
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        Path(command[4]).touch()

    with patch("code2video.whiteboard.subprocess.run", side_effect=run):
        render_whiteboard_preview(image, annotation, output, root=root, python="py-wb", seconds=10)

    assert len(calls) == 1
    command = calls[0]
    assert command[1].endswith("render_stream_whiteboard.py")
    assert command[command.index("--total-ms") + 1] == "10000"
    assert command[command.index("--cap-long-edge") + 1] == "640"
    assert command[command.index("--fps") + 1] == "30"
    assert "--full-color-ink" in command
    assert output.is_file()
    # annotation tạm đã co giãn về đúng 10s
    scaled = json.loads(Path(command[3]).read_text(encoding="utf-8"))
    assert scaled["sceneDurationMs"] == 10000
    assert scaled["elements"][0]["reveal"]["durationMs"] == 10000


def test_render_whiteboard_preview_caps_total_to_annotation(tmp_path):
    root = tmp_path / "whiteboard"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "render_stream_whiteboard.py").touch()
    image = tmp_path / "scene-01.png"
    image.touch()
    annotation = tmp_path / "scene-01.annotation.json"
    annotation.write_text(json.dumps({
        "sceneDurationMs": 4200,
        "elements": [{"sequence": 1, "reveal": {"startMs": 0, "durationMs": 4200}}],
    }), encoding="utf-8")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        Path(command[4]).touch()

    with patch("code2video.whiteboard.subprocess.run", side_effect=run):
        render_whiteboard_preview(image, annotation, tmp_path / "preview.mp4", root=root, python="py-wb", seconds=10)

    command = calls[0]
    assert command[command.index("--total-ms") + 1] == "4200"
    scaled = json.loads(Path(command[3]).read_text(encoding="utf-8"))
    assert scaled["sceneDurationMs"] == 4200
