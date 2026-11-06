import asyncio
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from code2video.studio import app as studio
from code2video.studio.jobs import Job, JobQueue


def upload(name: str, content: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(content), size=len(content))


def folder_uploads() -> list[UploadFile]:
    return [
        upload("scene-01/scene-01.png", b"png"),
        upload("scene-01/scene-01.annotation.json", b'{"elements":[{"sequence":1}]}'),
        upload("scene-01/script.srt", b"1\n00:00:00,000 --> 00:00:02,000\nHello\n"),
        upload("scene-02/scene-02.png", b"png"),
        upload("scene-02/scene-02.annotation.json", b'{"elements":[{"sequence":1}]}'),
        upload("scene-02/script.srt", b"1\n00:00:00,000 --> 00:00:02,000\nWorld\n"),
    ]


class FakeJob:
    def __init__(self, job_id: str) -> None:
        self.id = job_id


def test_whiteboard_folder_auto_merge_enqueues_dependent_merge(tmp_path: Path) -> None:
    scene_jobs = [FakeJob("job-1"), FakeJob("job-2")]
    with patch.object(studio, "RUNS_ROOT", tmp_path / "runs"), patch.object(
        studio.queue, "enqueue_many", return_value=scene_jobs
    ) as enqueue_many, patch.object(studio.queue, "enqueue", return_value=FakeJob("merge-1")) as enqueue:
        result = asyncio.run(studio.create_job(
            mode="whiteboard-folder", renderer="whiteboard",
            files=folder_uploads(), voDry=True, voVoice="", autoMerge=True,
        ))

    enqueue_many.assert_called_once()
    merge_params = enqueue.call_args.args[0]
    assert merge_params["mode"] == "merge-whiteboard"
    assert merge_params["dependsOn"] == ["job-1", "job-2"]
    assert len(merge_params["sceneDirs"]) == 2
    assert json.loads(result.body)["jobIds"] == ["job-1", "job-2", "merge-1"]


def test_whiteboard_folder_without_auto_merge_enqueues_only_scenes(tmp_path: Path) -> None:
    with patch.object(studio, "RUNS_ROOT", tmp_path / "runs"), patch.object(
        studio.queue, "enqueue_many", return_value=[FakeJob("job-1"), FakeJob("job-2")]
    ), patch.object(studio.queue, "enqueue") as enqueue:
        asyncio.run(studio.create_job(
            mode="whiteboard-folder", renderer="whiteboard",
            files=folder_uploads(), voDry=True, voVoice="", autoMerge=False,
        ))
    enqueue.assert_not_called()


def test_deps_pending_blocks_until_dependencies_finish() -> None:
    queue = JobQueue()
    dependency = Job(id="dep", params={}, status="running")
    merge = Job(id="merge", params={"dependsOn": ["dep"]})
    queue._jobs["dep"] = dependency
    queue._jobs["merge"] = merge

    assert queue._deps_pending(merge) is True
    dependency.status = "done"
    assert queue._deps_pending(merge) is False
    queue._jobs.pop("dep")
    assert queue._deps_pending(merge) is False  # dep bị prune không chặn merge


def test_ai_script_mode_builds_scenes_and_enqueues_merge(tmp_path) -> None:
    scenes_json = json.dumps([
        {"title": "Mở đầu", "cues": [
            {"text": "Câu một.", "doodle": "door", "label": "Cửa"},
            {"text": "Câu hai.", "doodle": "key", "label": "Khóa"},
        ]},
        {"title": "Kết", "cues": [
            {"text": "Câu ba.", "doodle": "wave", "label": "Tạm biệt"},
            {"text": "Câu bốn.", "doodle": "like", "label": "Like"},
        ]},
    ])
    scene_jobs = [FakeJob("job-1"), FakeJob("job-2")]
    with patch.object(studio, "RUNS_ROOT", tmp_path / "runs"), patch.object(
        studio.queue, "enqueue_many", return_value=scene_jobs
    ) as enqueue_many, patch.object(studio.queue, "enqueue", return_value=FakeJob("merge-1")) as enqueue:
        result = asyncio.run(studio.create_job(
            mode="ai-script", renderer="whiteboard", scenes=scenes_json,
            voDry=True, voVoice="", autoMerge=True, language="vi",
        ))

    enqueue_many.assert_called_once()
    entries = enqueue_many.call_args.args[0]
    assert len(entries) == 2
    assert entries[0][0]["renderer"] == "whiteboard"
    assert (Path(entries[0][0]["outputDir"]) / "script.srt").is_file()
    assert (Path(entries[0][0]["outputDir"]) / "scene-01.annotation.json").is_file()
    merge_params = enqueue.call_args.args[0]
    assert merge_params["mode"] == "merge-whiteboard"
    assert merge_params["dependsOn"] == ["job-1", "job-2"]
    assert json.loads(result.body)["jobIds"] == ["job-1", "job-2", "merge-1"]


def test_ai_settings_roundtrip(monkeypatch, tmp_path) -> None:
    import code2video.ai_settings as ai_settings
    monkeypatch.setattr(ai_settings, "SETTINGS_FILE", tmp_path / "ai.json")

    result = studio.get_ai_settings()
    assert "gemini" in {p["id"] for p in result["providers"]}
    assert result["doodles"]
    assert all("apiKey" not in p for p in result["providers"])

    result = asyncio.run(studio.put_ai_settings(studio._json_body({
        "providers": [{"id": "other", "label": "Mine", "baseUrl": "https://x/v1", "model": "m", "apiKey": "k"}],
        "skills": [{"id": "whiteboard", "name": "WB", "content": "Nội dung skill."}],
        "defaultProvider": "other",
        "defaultSkill": "whiteboard",
    })))
    assert result["saved"] is True
    settings = ai_settings.load()
    assert settings.providers["other"].apiKey == "k"
    assert settings.defaultProvider == "other"

    shown = {p["id"]: p for p in studio.get_ai_settings()["providers"]}
    assert shown["other"]["hasKey"] is True
    assert "apiKey" not in shown["other"]

    asyncio.run(studio.put_ai_settings(studio._json_body({
        "providers": [{"id": "other", "label": "Mine", "baseUrl": "https://x/v1", "model": "m2", "apiKey": ""}],
        "skills": [{"id": "whiteboard", "name": "WB", "content": "x"}],
    })))
    kept = ai_settings.load()
    assert kept.providers["other"].apiKey == "k"
    assert kept.providers["other"].model == "m2"


def test_ai_settings_save_allows_unfilled_preset_but_rejects_key_without_url(monkeypatch, tmp_path) -> None:
    import code2video.ai_settings as ai_settings
    monkeypatch.setattr(ai_settings, "SETTINGS_FILE", tmp_path / "ai.json")
    skills = [{"id": "whiteboard", "name": "WB", "content": "x"}]
    ok = asyncio.run(studio.put_ai_settings(studio._json_body({
        "providers": [
            {"id": "gemini", "label": "G", "baseUrl": "https://g/v1", "model": "m", "apiKey": "tok"},
            {"id": "other", "label": "O", "baseUrl": "", "model": "", "apiKey": ""},
        ],
        "skills": skills,
    })))
    assert ok["saved"] is True
    assert ai_settings.load().providers["gemini"].apiKey == "tok"

    with pytest.raises(HTTPException) as error:
        asyncio.run(studio.put_ai_settings(studio._json_body({
            "providers": [{"id": "other", "label": "O", "baseUrl": "", "model": "", "apiKey": "x"}],
            "skills": skills,
        })))
    assert error.value.status_code == 400 and "other" in error.value.detail


def test_generate_script_demo_provider(monkeypatch, tmp_path) -> None:
    import code2video.ai_settings as ai_settings
    monkeypatch.setattr(ai_settings, "SETTINGS_FILE", tmp_path / "ai.json")
    result = asyncio.run(studio.generate_ai_script(studio._json_body({
        "topic": "thói quen buổi sáng", "language": "vi", "providerId": "demo", "skillId": "", "minutes": 2,
    })))
    assert result["providerId"] == "demo"
    assert len(result["scenes"]) == 2


def test_generate_script_unknown_provider_400(monkeypatch, tmp_path) -> None:
    import code2video.ai_settings as ai_settings
    monkeypatch.setattr(ai_settings, "SETTINGS_FILE", tmp_path / "ai.json")
    with pytest.raises(HTTPException) as error:
        asyncio.run(studio.generate_ai_script(studio._json_body({
            "topic": "x", "language": "vi", "providerId": "khong-ton-tai", "skillId": "", "minutes": 2,
        })))
    assert "không tồn tại" in error.value.detail


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
