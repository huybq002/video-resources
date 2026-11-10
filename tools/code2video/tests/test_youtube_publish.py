"""scripts/youtube_publish.py (night-job YouTube upload): gates, metadata, dry run, idempotency. No network."""
import datetime as dt
import importlib.util
import json
import pathlib
import shutil
import struct
import types
import zlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


yp = _load("youtube_publish", REPO / "scripts/youtube_publish.py")
real_up = _load("upload_youtube", REPO / ".claude/skills/code2video-resource-generator/ci/upload_youtube.py")

DISC = "Voice and visuals in this video are AI-generated. Characters and events are fictional."
TID = "007-the-quiet-raise"
RUN = "4242"


def png(path, w, h):
    raw = b"".join(b"\x00" + b"\x00" * w * 3 for _ in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


@pytest.fixture
def root(tmp_path):
    (tmp_path / "scripts").mkdir()
    shutil.copy(REPO / "scripts/policy_check.py", tmp_path / "scripts/policy_check.py")
    ch = {"lang": "en", "publish": {"youtube_category_id": "27", "ai_disclosure": DISC, "require_ai_label": True},
          "youtube_upload": {"enabled": True}}
    (tmp_path / "channel.json").write_text(json.dumps(ch))
    out = tmp_path / "outputs" / TID
    (out / "publish").mkdir(parents=True)
    (out / "thumbnails").mkdir()
    (out / "landscape").mkdir()
    (out / "manifest.json").write_text(json.dumps({"id": TID, "tag": f"{TID}-{RUN}", "duration_s": 60,
                                                   "release_url": "https://github.com/x/y/releases/tag/t"}))
    pub = {"keywords": ["sunk cost"],
           "youtube": {"title": "Why Mara kept paying for a gym she hated", "description": "Mara signs up.\n\n" + DISC,
                       "tags": ["sunk cost fallacy", "psychology"], "hashtags": ["#psychology", "#storytime"]},
           "youtube_shorts": {"title": "The gym she never used", "description": "One choice, a year of cost.", "hashtags": ["#psychology"]}}
    (out / "publish/publish.json").write_text(json.dumps(pub))
    (out / "landscape.mp4").write_bytes(b"\x00" * 1000)
    (out / "portrait.mp4").write_bytes(b"\x00" * 800)
    (out / "landscape/output.music.json").write_text(json.dumps({"credit": "Music: Quiet Steps by Someone (CC BY 4.0)"}))
    png(out / "thumbnails/a.png", 1280, 720)
    png(out / "thumbnails/b.png", 720, 1280)
    (tmp_path / "tasks/done").mkdir(parents=True)
    (tmp_path / "tasks/done" / f"{TID}.md").write_text("---\nid: x\nupload: auto     # comment\nprivacy: private\n---\n# t\n")
    return tmp_path


@pytest.fixture
def fake(monkeypatch):
    calls = {"upload": [], "thumb": [], "token": 0}
    mod = types.SimpleNamespace(
        missing_secrets=lambda: [],
        check_meta=real_up.check_meta,
        token=lambda: calls.__setitem__("token", calls["token"] + 1) or "ACCESS",
        upload=lambda video, m, acc: calls["upload"].append((pathlib.Path(video).name, m)) or {"id": f"vid{len(calls['upload'])}"},
        thumbnail=lambda vid, thumb, acc: calls["thumb"].append((vid, pathlib.Path(thumb).name)) or 200,
    )
    monkeypatch.setattr(yp, "load_uploader", lambda: mod)
    monkeypatch.setattr(yp, "approved", lambda root=None: True)
    return calls, mod


def run(root, *args):
    return yp.main(["--run-id", RUN, *args], root=root, env={})


def test_uploads_both_cuts_with_thumbnails_credit_and_disclosure(root, fake):
    calls, _ = fake
    assert run(root) == 0
    names = [c[0] for c in calls["upload"]]
    assert names == ["landscape.mp4", "portrait.mp4"]
    long_m, short_m = calls["upload"][0][1], calls["upload"][1][1]
    assert long_m["privacy"] == "private" and long_m["categoryId"] == "27" and long_m["language"] == "en"
    assert long_m["description"].count(DISC) == 1                      # already there: not added twice
    assert "Music: Quiet Steps" in long_m["description"] and "#storytime" in long_m["description"]
    assert short_m["title"] == "The gym she never used" and "#Shorts" in short_m["description"] and DISC in short_m["description"]
    assert short_m["tags"] == ["sunk cost fallacy", "psychology"]
    assert calls["thumb"] == [("vid1", "a.png"), ("vid2", "b.png")]   # picked by shape
    rec = json.loads((root / "outputs" / TID / "youtube.json").read_text())
    assert rec["landscape"]["url"] == "https://youtu.be/vid1" and rec["portrait"]["privacy"] == "private"
    assert calls["token"] == 1
    # second run: nothing uploaded twice
    assert run(root) == 0 and len(calls["upload"]) == 2


def test_dry_run_touches_nothing(root, fake, capsys):
    calls, _ = fake
    assert run(root, "--dry-run") == 0
    assert calls["upload"] == [] and calls["token"] == 0
    assert not (root / "outputs" / TID / "youtube.json").exists()
    assert "DRY RUN" in capsys.readouterr().out


def test_switch_off_by_default(root, fake, capsys):
    calls, _ = fake
    ch = json.loads((root / "channel.json").read_text()); ch["youtube_upload"] = {}
    (root / "channel.json").write_text(json.dumps(ch))
    assert run(root) == 0 and calls["upload"] == []
    assert "off" in capsys.readouterr().out


def test_no_upload_while_look_not_approved(root, fake, monkeypatch, capsys):
    calls, _ = fake
    monkeypatch.setattr(yp, "approved", lambda root=None: False)
    assert run(root) == 0 and calls["upload"] == []
    assert "not approved" in capsys.readouterr().out


def test_missing_secrets_skip(root, fake, capsys):
    calls, mod = fake
    mod.missing_secrets = lambda: ["YT_REFRESH_TOKEN"]
    assert run(root) == 0 and calls["upload"] == []
    assert "YT_REFRESH_TOKEN" in capsys.readouterr().out


def test_only_tasks_of_this_run(root, fake):
    calls, _ = fake
    assert yp.main(["--run-id", "9999"], root=root, env={}) == 0 and calls["upload"] == []


def test_task_opt_out_and_long_vertical(root, fake):
    calls, _ = fake
    man = root / "outputs" / TID / "manifest.json"
    m = json.loads(man.read_text()); m["duration_s"] = 300; man.write_text(json.dumps(m))
    assert run(root) == 0
    assert [c[0] for c in calls["upload"]] == ["landscape.mp4"]          # a 5-min vertical is not a Short
    (root / "outputs" / TID / "youtube.json").unlink()
    (root / "tasks/done" / f"{TID}.md").write_text("---\nupload: false\n---\n")
    assert run(root) == 0 and len(calls["upload"]) == 1


def test_policy_failure_blocks_upload(root, fake, capsys):
    calls, _ = fake
    p = root / "outputs" / TID / "publish/publish.json"
    pub = json.loads(p.read_text()); pub["youtube"]["description"] = "A cozy story."; pub["youtube_shorts"]["description"] = "Short."
    p.write_text(json.dumps(pub))
    assert run(root) == 0 and calls["upload"] == []
    assert "policy_check publish fails" in capsys.readouterr().out


def test_schedule_and_public_guard():
    now = dt.datetime(2026, 11, 10, 13, 0, tzinfo=dt.timezone.utc)
    assert yp.next_slot("14:00", now) == "2026-11-11T14:00:00Z"        # < 2 h ahead -> next day
    assert yp.next_slot("18:30", now) == "2026-11-10T18:30:00Z"
    m = yp.build_meta({"youtube": {"title": "T", "description": "d"}}, "landscape", {"publish": {}}, privacy="public",
                      publish_at="2026-11-11T14:00:00Z")
    assert m["privacy"] == "private" and m["publishAt"] == "2026-11-11T14:00:00Z"
    assert real_up.check_meta({"title": "T", "privacy": "public"}, False)
    assert not real_up.check_meta({"title": "T", "privacy": "public"}, True)
    assert real_up.check_meta({"title": "T", "privacy": "unlisted", "publishAt": "x"}, True)
