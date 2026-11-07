from pathlib import Path

from code2video.headless import build_params, project_roots


def _project(root: Path, script: str = "script.srt") -> Path:
    root.mkdir(parents=True)
    (root / "index.html").write_text("<html></html>", encoding="utf-8")
    (root / script).write_text("1\n00:00:00,000 --> 00:00:01,000\nxin chào\n", encoding="utf-8")
    return root


def test_project_roots_finds_nested(tmp_path):
    _project(tmp_path / "a")
    _project(tmp_path / "b")
    assert [p.name for p in project_roots(tmp_path)] == ["a", "b"]
    assert project_roots(tmp_path / "a") == [tmp_path / "a"]


def test_build_params_batch_and_script(tmp_path):
    _project(tmp_path / "a")
    _project(tmp_path / "b", script="story.txt")
    params = build_params({"project": str(tmp_path), "fps": 60, "dryRun": True}, tmp_path)
    assert len(params) == 2
    assert params[0]["scriptPath"].endswith("script.srt")
    assert params[1]["scriptPath"].endswith("story.txt")
    assert params[0]["fps"] == 60 and params[0]["dryRun"] is True


def test_build_params_requires_project_or_flow(tmp_path):
    try:
        build_params({}, tmp_path)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_cli_flags_override_job_file(tmp_path, monkeypatch):
    import json

    from code2video import headless

    job = tmp_path / "job.json"
    job.write_text(json.dumps({"jobs": [{"project": "p", "fps": 30}]}), encoding="utf-8")
    seen = {}

    def fake_run_jobs(specs, base=None, merge=None):
        seen["specs"] = specs
        return [{"status": "done"}]

    monkeypatch.setattr(headless, "run_jobs", fake_run_jobs)
    assert headless.main([str(job), "--dry-run", "--fps", "60"]) == 0
    assert seen["specs"][0]["dryRun"] is True
    assert seen["specs"][0]["fps"] == 60
    assert headless.main([str(job)]) == 0
    assert "dryRun" not in seen["specs"][0] and seen["specs"][0]["fps"] == 30


def test_reuse_voiceover_flag_reaches_params(tmp_path):
    _project(tmp_path / "p")
    off = build_params({"project": str(tmp_path / "p")}, tmp_path)[0]
    on = build_params({"project": str(tmp_path / "p"), "reuseVoiceover": True}, tmp_path)[0]
    assert off["reuseVoiceover"] is False and on["reuseVoiceover"] is True


def test_reuse_skips_synthesis_when_voiceover_is_present(tmp_path, monkeypatch):
    """Second cut: voiceover.wav + timeline.json already in the project, so the TTS engine must not be built."""
    from code2video.studio import engines
    from code2video.studio.jobs import Job, JobQueue

    project = _project(tmp_path / "p")
    (project / "voiceover.wav").write_bytes(b"RIFF")
    (project / "timeline.json").write_text("{}", encoding="utf-8")
    called = {"tts": 0, "render": 0}
    monkeypatch.setattr(engines, "get_tts", lambda *a, **k: called.__setitem__("tts", called["tts"] + 1))
    import code2video.pipeline as pipeline
    monkeypatch.setattr(pipeline, "render_hyperframes", lambda *a, **k: called.__setitem__("render", called["render"] + 1) or (project / "output.mp4").write_bytes(b"x"))
    monkeypatch.setattr(pipeline, "apply_format", lambda *a, **k: None)
    params = build_params({"project": str(project), "reuseVoiceover": True}, tmp_path)[0]
    job = Job(id="t1", params=params)
    JobQueue()._execute(job)
    assert job.status == "done", job.error
    assert called == {"tts": 0, "render": 1}
