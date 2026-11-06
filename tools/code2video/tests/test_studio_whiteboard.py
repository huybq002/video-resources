import asyncio
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from code2video.studio import app as studio


def upload(name: str, content: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(content), size=len(content))


class FakeJob:
    def __init__(self, job_id: str) -> None:
        self.id = job_id


def test_invalid_later_scene_does_not_enqueue_or_write_earlier_scene(tmp_path: Path) -> None:
    scripts = [
        upload("one.srt", b"1\n00:00:00,000 --> 00:00:02,000\nScene one\n"),
        upload("two.srt", b"1\n00:00:00,000 --> 00:00:02,000\nScene two\n"),
    ]
    images = [upload("one.png", b"png-one"), upload("two.png", b"png-two")]
    annotations = [
        upload("one.annotation.json", b'{"elements":[{}]}'),
        upload("two.annotation.json", b"not-json"),
    ]
    run_root = tmp_path / "runs"
    enqueue_many = patch.object(studio.queue, "enqueue_many")

    with patch.object(studio, "RUNS_ROOT", run_root), enqueue_many as enqueue:
        with pytest.raises(HTTPException) as error:
            asyncio.run(studio.create_job(
                mode="whiteboard-scenes",
                renderer="whiteboard",
                sceneScripts=scripts,
                sceneImages=images,
                sceneAnnotations=annotations,
                voRef=None,
                voVoice="",
                voTtsMode="v3turbo",
                voDry=True,
                speakers="{}",
            ))

    assert "Script hoặc annotation không hợp lệ" in error.value.detail
    enqueue.assert_not_called()
    assert not run_root.exists()


def test_preview_whiteboard_enqueues_first_scene(tmp_path):
    images = [upload("one.png", b"png")]
    annotations = [upload("one.annotation.json", b'{"elements":[{"sequence":1}]}')]
    with patch.object(studio, "RUNS_ROOT", tmp_path / "runs"), patch.object(
        studio.queue, "enqueue", return_value=FakeJob("preview-1")
    ) as enqueue:
        result = asyncio.run(studio.create_job(
            mode="preview-whiteboard", renderer="whiteboard",
            sceneImages=images, sceneAnnotations=annotations,
        ))
    params = enqueue.call_args.args[0]
    assert params["mode"] == "preview-whiteboard"
    assert params["image"].endswith("one.png")
    assert params["annotation"].endswith("one.annotation.json")
    assert json.loads(result.body)["jobIds"] == ["preview-1"]


def test_preview_whiteboard_requires_image_and_annotation(tmp_path):
    with patch.object(studio, "RUNS_ROOT", tmp_path / "runs"):
        with pytest.raises(HTTPException) as error:
            asyncio.run(studio.create_job(mode="preview-whiteboard", renderer="whiteboard"))
    assert "PNG và annotation" in error.value.detail


def test_whiteboard_folder_local_path_enqueues_scenes(tmp_path):
    source = tmp_path / "src"
    for name in ("scene-01", "scene-02"):
        scene = source / name
        scene.mkdir(parents=True)
        (scene / f"{name}.png").write_bytes(b"png")
        (scene / f"{name}.annotation.json").write_text('{"elements":[{"sequence":1}]}', encoding="utf-8")
        (scene / "script.srt").write_text("1\n00:00:00,000 --> 00:00:02,000\nHello\n", encoding="utf-8")
    scene_jobs = [FakeJob("job-1"), FakeJob("job-2")]
    with patch.object(studio, "RUNS_ROOT", tmp_path / "runs"), patch.object(
        studio.queue, "enqueue_many", return_value=scene_jobs
    ) as enqueue_many, patch.object(studio.queue, "enqueue") as enqueue:
        asyncio.run(studio.create_job(
            mode="whiteboard-folder", renderer="whiteboard",
            localFolder=str(source), voDry=True, voVoice="",
        ))
    enqueue_many.assert_called_once()
    entries = enqueue_many.call_args.args[0]
    assert len(entries) == 2
    assert (Path(entries[0][0]["outputDir"]) / "script.srt").is_file()
    enqueue.assert_not_called()


def test_whiteboard_folder_local_path_invalid_400(tmp_path):
    with patch.object(studio, "RUNS_ROOT", tmp_path / "runs"):
        with pytest.raises(HTTPException) as error:
            asyncio.run(studio.create_job(
                mode="whiteboard-folder", renderer="whiteboard",
                localFolder=str(tmp_path / "khong-co"), voVoice="",
            ))
    assert "không tồn tại" in error.value.detail


def test_fs_browse_lists_drives():
    result = studio.browse_filesystem(path="")
    assert result["path"] == ""
    assert any(d.endswith(":/") for d in result["dirs"])


def test_fs_browse_lists_subdirs(tmp_path):
    (tmp_path / "alpha").mkdir()
    (tmp_path / "beta").mkdir()
    (tmp_path / "file.txt").touch()
    result = studio.browse_filesystem(path=str(tmp_path))
    assert result["path"] == str(tmp_path)
    assert [Path(d).name for d in result["dirs"]] == ["alpha", "beta"]
    assert result["parent"] is not None


def test_fs_browse_missing_path_400(tmp_path):
    with pytest.raises(HTTPException) as error:
        studio.browse_filesystem(path=str(tmp_path / "khong-co"))
    assert "không tồn tại" in error.value.detail
