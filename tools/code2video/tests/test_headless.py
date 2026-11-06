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
