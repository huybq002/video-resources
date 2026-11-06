from pathlib import Path
from unittest.mock import patch

import pytest

from code2video.whiteboard import merge_whiteboard_scenes, render_whiteboard, scene_pairs


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


def test_render_whiteboard_passes_long_edge_to_renderer(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "wb"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "render_stream_whiteboard.py").write_text("", encoding="utf-8")
    project = tmp_path / "scene"
    project.mkdir()
    (project / "scene-01.png").write_bytes(b"png")
    (project / "scene-01.annotation.json").write_text("{}", encoding="utf-8")
    (project / "voiceover.wav").write_bytes(b"wav")
    commands = []
    monkeypatch.setattr("code2video.whiteboard.subprocess.run", lambda cmd, **kw: commands.append(cmd))
    monkeypatch.setattr("code2video.whiteboard.shutil.which", lambda name: "ffmpeg")
    monkeypatch.delenv("WHITEBOARD_LONG_EDGE", raising=False)
    render_whiteboard(project, tmp_path / "o.mp4", root=root, python="py", long_edge=1920)
    assert commands[0][commands[0].index("--cap-long-edge") + 1] == "1920"
    commands.clear()
    render_whiteboard(project, tmp_path / "o.mp4", root=root, python="py")
    assert "--cap-long-edge" not in commands[0]
