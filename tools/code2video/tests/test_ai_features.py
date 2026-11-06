"""Kiểm tra provider (test/models/ảnh), upload skill, luật nối card, card ai-image, lưu kết quả run."""
import asyncio
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from PIL import Image

from code2video import ai_settings, uploads
from code2video.ai_client import AiClientError, generate_image, list_models, ping
from code2video.ai_settings import Provider
from code2video.flow import rules, store
from code2video.flow.nodes import NODES, FlowContext
from code2video.flow.runner import execute_flow_job, validate_for_engine
from code2video.studio import app as studio


def _png_b64() -> str:
    buf = BytesIO()
    Image.new("RGB", (640, 360), (250, 250, 250)).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _authed(self) -> bool:
        if self.headers.get("Authorization") != "Bearer good-key":
            self._send(401, {"error": "bad key"})
            return False
        return True

    def do_GET(self):
        if self._authed() and self.path == "/v1/models":
            self._send(200, {"data": [{"id": "models/zeta"}, {"id": "alpha"}]})

    def do_POST(self):
        raw = self.rfile.read(int(self.headers["Content-Length"]))  # đọc hết body trước khi trả lời (tránh reset kết nối)
        if not self._authed():
            return
        body = json.loads(raw)
        if self.path == "/v1/chat/completions":
            self._send(200, {"choices": [{"message": {"content": "OK"}}], "echo": body["model"]})
        elif self.path == "/v1/images/generations":
            if body.get("model") == "broken":
                self._send(500, {"error": "boom"})
            else:
                self._send(200, {"data": [{"b64_json": _png_b64()}]})
        else:
            self._send(404, {})


@pytest.fixture()
def server():
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}/v1"
    httpd.shutdown()


def provider(url: str, key: str = "good-key", **kw) -> Provider:
    return Provider(id="p", label="P", baseUrl=url, model="m", apiKey=key, **kw)


@pytest.fixture()
def local_settings(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(ai_settings, "SETTINGS_FILE", tmp_path / "settings" / "ai.json")
    monkeypatch.setattr(ai_settings, "UPLOADS_ROOT", tmp_path / "settings" / "uploads")
    return tmp_path


def test_list_models_strips_prefix_and_sorts(server):
    assert list_models(provider(server)) == ["alpha", "zeta"]


def test_wrong_key_reports_api_error(server):
    with pytest.raises(AiClientError, match="401"):
        list_models(provider(server, key="nope"))
    with pytest.raises(AiClientError, match="401"):
        ping(provider(server, key="nope"))


def test_ping_returns_latency_and_reply(server):
    result = ping(provider(server))
    assert result["reply"] == "OK" and result["model"] == "m" and result["latencyMs"] >= 0


def test_generate_image_needs_image_model_and_decodes(server):
    with pytest.raises(AiClientError, match="model ảnh"):
        generate_image(provider(server), "x")
    raw = generate_image(provider(server, imageModel="img"), "x")
    assert Image.open(BytesIO(raw)).size == (640, 360)


def test_api_test_route_reports_ok_and_failure(server, local_settings):
    ok = asyncio.run(studio.test_ai_provider(studio._json_body(
        {"id": "p", "baseUrl": server, "model": "m", "apiKey": "good-key"})))
    assert ok["ok"] is True
    bad = asyncio.run(studio.test_ai_provider(studio._json_body(
        {"id": "p", "baseUrl": server, "model": "m", "apiKey": "wrong"})))
    assert bad["ok"] is False and "401" in bad["message"]
    models = asyncio.run(studio.list_ai_models(studio._json_body(
        {"id": "p", "baseUrl": server, "apiKey": "good-key"})))
    assert models["models"] == ["alpha", "zeta"]
    with pytest.raises(HTTPException) as err:
        asyncio.run(studio.list_ai_models(studio._json_body({"id": "p", "baseUrl": server, "apiKey": "wrong"})))
    assert err.value.status_code == 502


def test_models_route_falls_back_to_saved_key(server, local_settings):
    settings = ai_settings.load()
    settings.providers["p"] = provider(server)
    ai_settings.save(settings)
    result = asyncio.run(studio.list_ai_models(studio._json_body({"id": "p", "baseUrl": server})))
    assert result["models"] == ["alpha", "zeta"]


def test_upload_skill_list_delete_roundtrip(local_settings):
    skill = uploads.save_skill_file("Phong cách kể chuyện.md", "Hãy viết như kể chuyện.".encode(), "")
    assert skill.id == "phong-cach-ke-chuyen" and skill.source == "phong-cach-ke-chuyen.md"
    assert ai_settings.load().skills[skill.id].content.startswith("Hãy viết")
    files = uploads.list_files()
    assert files[0]["usedBy"] == ["Phong cách kể chuyện"] and files[0]["size"] > 0
    again = uploads.save_skill_file("Phong cách kể chuyện.md", b"khac", "")
    assert again.id == "phong-cach-ke-chuyen-2"
    assert uploads.delete_file("skills", skill.source) == [skill.id]
    assert skill.id not in ai_settings.load().skills
    assert [f["name"] for f in uploads.list_files()] == ["phong-cach-ke-chuyen-2.md"]


@pytest.mark.parametrize("name,data,message", [
    pytest.param("a.exe", b"x", ".md", id="extension"),
    pytest.param("a.md", b"", "rỗng", id="empty"),
    pytest.param("a.md", b"x" * (uploads.MAX_SKILL_BYTES + 1), "quá lớn", id="too-big"),
    pytest.param("a.md", b"\xff\xfe\x00bad", "UTF-8", id="not-utf8"),
    pytest.param("a.md", b"   \n ", "khoảng trắng", id="blank"),
])
def test_upload_skill_rejects_bad_files(local_settings, name, data, message):
    with pytest.raises(ValueError, match=message):
        uploads.save_skill_file(name, data)


def test_delete_file_rejects_traversal(local_settings):
    for bad in ("../ai.json", "..", "a/b.md", ""):
        with pytest.raises(ValueError):
            uploads.delete_file("skills", bad)
    with pytest.raises(ValueError):
        uploads.delete_file("other", "a.md")
    with pytest.raises(FileNotFoundError):
        uploads.delete_file("skills", "missing.md")


def test_put_settings_keeps_valid_source_and_image_model(local_settings):
    skill = uploads.save_skill_file("s.md", b"noi dung")
    payload = {
        "providers": [{"id": "p", "baseUrl": "http://x/v1", "model": "m", "apiKey": "k", "imageModel": "img"}],
        "skills": [{"id": skill.id, "name": "S", "content": "sua", "source": skill.source},
                   {"id": "fake", "name": "F", "content": "", "source": "../ai.json"}],
    }
    asyncio.run(studio.put_ai_settings(studio._json_body(payload)))
    saved = ai_settings.load()
    assert saved.providers["p"].imageModel == "img"
    assert saved.skills[skill.id].source == skill.source and saved.skills["fake"].source == ""


# ---- luật nối ----

def flow_with(edges, types):
    nodes = {nid: {"type": t, "config": {}} for nid, t in types.items()}
    return {"engine": "whiteboard", "start": next(iter(types)), "nodes": nodes, "edges": edges}


def test_rules_reject_backward_skip_and_same_step():
    assert rules.edge_problem("idea", "ai-script") is None
    assert rules.edge_problem("ai-script", "ai-script") is None
    assert "ngược" in rules.edge_problem("render", "tts")
    assert "ngược" in rules.edge_problem("ai-script", "idea")
    assert "cùng bước" in rules.edge_problem("build-scenes", "ai-image")
    assert "chỉ nối được" in rules.edge_problem("idea", "render")
    assert "vòng thử lại" in rules.edge_problem("tts", "tts")
    assert rules.edge_problem("merge", "idea")


def test_validate_for_engine_reports_bad_edges():
    ok = flow_with([{"from": "a", "to": "b"}, {"from": "b", "to": "c"}],
                   {"a": "idea", "b": "ai-script", "c": "ai-image"})
    assert validate_for_engine(ok) == []
    bad = flow_with([{"from": "a", "to": "b"}, {"from": "b", "to": "a"}], {"a": "idea", "b": "ai-script"})
    errors = validate_for_engine(bad)
    assert any("ngược" in e for e in errors)
    hyper = {**ok, "engine": "hyperframes"}
    assert any("ai-image" in e for e in validate_for_engine(hyper))


def test_every_rule_target_is_a_known_node():
    for source, targets in rules.NEXT.items():
        assert source in NODES and set(targets) <= set(NODES)
        assert all(rules.STEP[t] >= rules.STEP[source] for t in targets)


def test_rules_api_payload():
    payload = studio.get_flow_rules()
    assert payload["step"]["tts"] < payload["step"]["render"] and "ai-image" in payload["next"]["ai-script"]


# ---- node ai-image / skill ----

SCENES = [{"title": "Cảnh 1", "cues": [{"doodle": "key", "label": "Chìa", "text": "Một chiếc chìa."},
                                         {"doodle": "door", "label": "Cửa", "text": "Một cánh cửa."}]}]


def test_ai_image_node_builds_scene_with_ai_picture(server, local_settings, tmp_path):
    settings = ai_settings.load()
    settings.providers["p"] = provider(server, imageModel="img")
    ai_settings.save(settings)
    run = tmp_path / "run"
    ctx = FlowContext(run_dir=run)
    out = NODES["ai-image"]({"_types": {"ai-script": {"scenes": SCENES}, "idea": {"language": "vi"}}}, {"provider": "p"}, ctx)
    assert "error" not in out and len(out["images"]) == 1
    folder = Path(out["dirs"][0])
    assert Image.open(out["images"][0]).size == (1920, 1080)
    annotation = json.loads((folder / "scene-01.annotation.json").read_text(encoding="utf-8"))
    regions = [e["region"] for e in annotation["elements"]]
    assert len(regions) == 2 and regions[0]["x"] < regions[1]["x"]  # 2 ô lưới phủ cả khung, thứ tự trái→phải
    assert (folder / "script.srt").is_file()


def test_ai_image_node_errors_are_recoverable(server, local_settings, tmp_path):
    settings = ai_settings.load()
    settings.providers["p"] = provider(server, imageModel="broken")
    settings.providers["noimg"] = provider(server)
    ai_settings.save(settings)
    ctx = FlowContext(run_dir=tmp_path / "r")
    state = {"_types": {"ai-script": {"scenes": SCENES}}}
    assert "500" in NODES["ai-image"](state, {"provider": "p"}, ctx)["error"]
    assert "model ảnh" in NODES["ai-image"](state, {"provider": "noimg"}, ctx)["error"]
    assert "provider thật" in NODES["ai-image"](state, {"provider": ""}, ctx)["error"]


def test_skill_card_feeds_ai_script_and_missing_skill_fails(local_settings, monkeypatch):
    skill = uploads.save_skill_file("giong.md", b"HAY NOI THAT VUI")
    state: dict = {}
    out = NODES["skill"](state, {"skill": skill.id}, None)
    state.update(out.pop("_global"))
    assert state["_skill"]["content"] == "HAY NOI THAT VUI" and out["chars"] == 16
    seen = {}

    def fake_chat(provider_, messages, **kw):
        seen["system"] = messages[0]["content"]
        return {"scenes": [{"title": "t", "cues": [{"text": "x", "label": "l", "doodle": "key"}]}]}

    monkeypatch.setattr("code2video.flow.nodes.chat_json", fake_chat)
    settings = ai_settings.load()
    settings.providers["p"] = provider("http://unused/v1")
    ai_settings.save(settings)
    state.update({"topic": "t", "_types": {"idea": {"language": "vi", "minutes": 1}}})
    result = NODES["ai-script"](state, {"provider": "p", "skill": "whiteboard"}, None)
    assert "error" not in result and "HAY NOI THAT VUI" in seen["system"]
    with pytest.raises(ValueError, match="không còn"):
        NODES["skill"]({}, {"skill": "da-xoa"}, None)


# ---- lưu kết quả run ----

def test_execute_flow_job_persists_outputs_per_node(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "FLOWS_ROOT", tmp_path / "flows")
    flow = {"engine": "whiteboard", "start": "i", "nodes": {
        "i": {"type": "idea", "config": {"text": "Chủ đề"}},
        "s": {"type": "ai-script", "config": {"provider": "demo"}}},
        "edges": [{"from": "i", "to": "s"}]}
    job = SimpleNamespace(id="j1", params={"flow": flow, "flowId": "f1", "topic": "", "outputDir": str(tmp_path / "run")},
                          stage="", label="", result=None, progress=0.0, version=0, status="running", output_dir=None)
    queue = SimpleNamespace(_lock=threading.RLock(), _tts_lock=threading.Lock())
    execute_flow_job(job, queue)
    saved = store.read_run("f1")
    assert saved["status"] == "done" and saved["doneNodes"] == ["i", "s"]
    assert saved["outputs"]["i"]["topic"] == "Chủ đề" and saved["outputs"]["s"]["scenes"]
    assert job.result["outputs"]["s"]["scenes"] and saved["outputDir"] == str(tmp_path / "run")


def test_run_file_endpoint_blocks_escape(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "FLOWS_ROOT", tmp_path / "flows")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "a.png").write_bytes(b"png")
    (tmp_path / "secret.json").write_text("{}")
    store.write_flow("f1", {"name": "n"})
    store.write_run("f1", {"outputDir": str(run_dir)})
    assert studio.get_flow_run_file("f1", "a.png").path == (run_dir / "a.png").resolve()
    for bad in ("../secret.json", str(tmp_path / "secret.json"), "missing.png", "a.exe"):
        with pytest.raises(HTTPException) as err:
            studio.get_flow_run_file("f1", bad)
        assert err.value.status_code == 404


def test_user_and_template_flows_pass_new_rules():
    root = Path(__file__).resolve().parents[1] / "flows"
    paths = list(root.glob("*.flow.json")) + list((root / "templates").glob("*.flow.json"))
    assert paths
    for path in paths:
        assert validate_for_engine(json.loads(path.read_text(encoding="utf-8"))) == [], path.name


def test_skill_card_named_skill_reaches_ai_script_in_a_real_flow(local_settings, monkeypatch):
    """Regression: id card trùng khóa dữ liệu chung từng làm mất nội dung skill (KeyError 'content')."""
    from code2video.flow.flow import run_flow

    skill = uploads.save_skill_file("giong.md", b"PHONG CACH TRINH THAM")
    settings = ai_settings.load()
    settings.providers["p"] = provider("http://unused/v1")
    ai_settings.save(settings)
    seen = {}

    def fake_chat(provider_, messages, **kw):
        seen["system"] = messages[0]["content"]
        return {"scenes": [{"title": "t", "cues": [{"text": "x", "label": "l", "doodle": "key"}]}]}

    monkeypatch.setattr("code2video.flow.nodes.chat_json", fake_chat)
    flow = {"engine": "whiteboard", "start": "idea", "nodes": {
        "idea": {"type": "idea", "config": {"text": "Chủ đề"}},
        "skill": {"type": "skill", "config": {"skill": skill.id}},
        "script": {"type": "ai-script", "config": {"provider": "p"}}},
        "edges": [{"from": "idea", "to": "skill"}, {"from": "skill", "to": "script"}]}
    state = run_flow(flow, {}, NODES, None)
    assert "PHONG CACH TRINH THAM" in seen["system"] and state["script"]["scenes"]


def test_cards_with_custom_ids_still_find_their_inputs(tmp_path):
    """Card kéo từ thư viện có id tùy ý (ai_script, my_scenes...) vẫn nhận đúng đầu ra của card trước."""
    from code2video.flow.flow import run_flow

    flow = {"engine": "whiteboard", "start": "a", "nodes": {
        "a": {"type": "idea", "config": {"text": "Chủ đề bất kỳ"}},
        "ai_script": {"type": "ai-script", "config": {"provider": "demo"}},
        "my_scenes": {"type": "build-scenes", "config": {}}},
        "edges": [{"from": "a", "to": "ai_script"}, {"from": "ai_script", "to": "my_scenes"}]}
    state = run_flow(flow, {}, NODES, FlowContext(run_dir=tmp_path / "run"))
    assert state["my_scenes"]["images"] and Path(state["my_scenes"]["images"][0]).is_file()


def test_openrouter_lists_only_free_models_without_key(monkeypatch):
    from code2video import ai_client
    ai_client._ENTRY_CACHE.clear()
    seen = {}

    class Resp:
        status_code = 200

        def json(self):
            return {"data": [
                {"id": "a/paid", "pricing": {"prompt": "0.000001", "completion": "0.000002"}},
                {"id": "b/free-by-price", "pricing": {"prompt": "0", "completion": "0"}},
                {"id": "c/tagged:free", "pricing": {"prompt": "0.1", "completion": "0.1"}},
                {"id": "d/nopricing"},
            ]}

    def fake_get(url, headers=None, timeout=None):
        seen["url"], seen["auth"] = url, headers.get("Authorization")
        return Resp()

    monkeypatch.setattr("code2video.ai_client._get", fake_get)
    p = Provider(id="or", label="OR", baseUrl="https://openrouter.ai/api/v1", model="", apiKey="")
    assert list_models(p) == ["b/free-by-price", "c/tagged:free"]
    assert seen["url"].endswith("/models") and seen["auth"] is None
    monkeypatch.setattr("code2video.ai_client._get", lambda *a, **k: pytest.fail("phải dùng cache"))
    assert list_models(p) == ["b/free-by-price", "c/tagged:free"]
    ai_client._ENTRY_CACHE.clear()


def test_non_openrouter_still_requires_key():
    with pytest.raises(AiClientError, match="API key"):
        list_models(Provider(id="x", label="X", baseUrl="https://example.com/v1", model="", apiKey=""))


def test_main_repo_root_resolves_from_worktree(tmp_path):
    from code2video._env import main_repo_root

    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text(f"gitdir: {tmp_path}/main/.git/worktrees/wt\n", encoding="utf-8")
    assert main_repo_root(worktree) == tmp_path / "main"
    plain = tmp_path / "repo"
    (plain / ".git").mkdir(parents=True)
    assert main_repo_root(plain) == plain


def test_prepare_data_dir_migrates_without_overwriting(tmp_path):
    from code2video._env import prepare_data_dir

    code = tmp_path / "code"
    (code / "settings").mkdir(parents=True)
    (code / "settings" / "ai.json").write_text("cu", encoding="utf-8")
    (code / "flows").mkdir()
    (code / "flows" / "a.flow.json").write_text("flow-cu", encoding="utf-8")
    data = tmp_path / "data"
    prepare_data_dir(code, data)
    assert (data / "settings" / "ai.json").read_text(encoding="utf-8") == "cu"
    assert (data / "flows" / "a.flow.json").is_file() and (data / ".gitignore").read_text(encoding="utf-8") == "*\n"
    (data / "settings" / "ai.json").write_text("moi", encoding="utf-8")
    prepare_data_dir(code, data)
    assert (data / "settings" / "ai.json").read_text(encoding="utf-8") == "moi"


def test_retry_exhausted_reports_the_real_ai_error():
    from code2video.flow.flow import FlowError, run_flow

    flow = {"engine": "whiteboard", "start": "a", "nodes": {"a": {"type": "t"}},
            "edges": [{"from": "a", "to": "a", "condition": {"field": "a.error", "op": "exists"}, "maxLoop": 2}]}
    with pytest.raises(FlowError, match="401 key sai"):
        run_flow(flow, {}, {"t": lambda *a: {"error": "401 key sai"}})


def test_run_output_dir_keeps_only_latest_run(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "FLOWS_ROOT", tmp_path / "flows")
    first = store.run_output_dir("f1", "r1")
    (first / "x.png").write_bytes(b"x")
    second = store.run_output_dir("f1", "r2")
    assert second.is_dir() and not first.exists()
    store.delete_run("f1")
    assert not second.exists()


@pytest.mark.parametrize("engine,chain", [
    ("whiteboard", ["idea", "skill", "ai-script", "ai-image", "tts", "render", "merge"]),
    ("whiteboard", ["idea", "ai-script", "build-scenes", "tts", "render", "merge"]),
    ("hyperframes", ["idea", "skill", "ai-script", "tts", "ai-html", "render"]),
])
def test_step_chains_built_by_the_ui_are_valid(engine, chain):
    edges = []
    for i, t in enumerate(chain):
        if t.startswith("ai-"):
            edges.append({"from": t, "to": t, "condition": {"field": f"{t}.error", "op": "exists"}, "maxLoop": 2})
        if i < len(chain) - 1:
            edges.append({"from": t, "to": chain[i + 1]})
    flow = {"engine": engine, "start": chain[0], "nodes": {t: {"type": t, "config": {}} for t in chain}, "edges": edges}
    assert validate_for_engine(flow) == []


def _fake_models(monkeypatch, entries):
    class Resp:
        status_code = 200

        def json(self):
            return {"data": entries}

    monkeypatch.setattr("code2video.ai_client._get", lambda *a, **k: Resp())


def test_gemini_lists_only_free_tier_chat_models(monkeypatch):
    from code2video.ai_client import list_all_models

    _fake_models(monkeypatch, [{"id": "models/gemini-2.5-flash"}, {"id": "models/gemini-2.5-pro"},
                               {"id": "models/gemini-2.5-flash-preview-tts"}, {"id": "models/gemma-3-27b-it"},
                               {"id": "models/imagen-4.0-generate"}, {"id": "models/gemini-2.5-flash-image"}])
    p = Provider(id="g", label="G", baseUrl="https://generativelanguage.googleapis.com/v1beta/openai", model="", apiKey="k")
    result = list_all_models(p)
    assert result["models"] == ["gemma-3-27b-it", "gemini-2.5-flash"]  or result["models"] == sorted(["gemma-3-27b-it", "gemini-2.5-flash"])
    assert result["imageModels"] == ["gemini-2.5-flash-image", "imagen-4.0-generate"]  # model ảnh liệt kê đủ, kể cả tính phí


def test_openrouter_free_text_models_and_all_image_models(monkeypatch):
    from code2video import ai_client

    ai_client._ENTRY_CACHE.clear()
    free = {"prompt": "0", "completion": "0"}
    _fake_models(monkeypatch, [
        {"id": "a/text:free", "pricing": free, "architecture": {"output_modalities": ["text"]}},
        {"id": "b/img:free", "pricing": free, "architecture": {"output_modalities": ["image", "text"]}},
        {"id": "c/paid-img", "pricing": {"prompt": "1", "completion": "1"}, "architecture": {"output_modalities": ["image"]}}])
    p = Provider(id="or", label="OR", baseUrl="https://openrouter.ai/api/v1", model="", apiKey="")
    result = ai_client.list_all_models(p)
    assert result["models"] == ["a/text:free", "b/img:free"] and result["imageModels"] == ["b/img:free", "c/paid-img"]
    ai_client._ENTRY_CACHE.clear()


def test_groq_skips_audio_and_guard_models(monkeypatch):
    from code2video.ai_client import list_models

    _fake_models(monkeypatch, [{"id": "llama-3.3-70b-versatile"}, {"id": "whisper-large-v3"}, {"id": "llama-guard-4"}])
    assert list_models(Provider(id="q", label="Q", baseUrl="https://api.groq.com/openai/v1", model="", apiKey="k")) == ["llama-3.3-70b-versatile"]


def test_404_error_has_hint_and_is_fatal_but_429_is_not(server, monkeypatch):
    class R:
        def __init__(self, code):
            self.status_code, self.text = code, "x"

    from code2video.ai_client import _api_error

    gone = _api_error(R(404))
    assert gone.fatal and "Tải danh sách model" in str(gone)
    assert _api_error(R(401)).fatal and not _api_error(R(429)).fatal and not _api_error(R(500)).fatal


def test_fatal_ai_error_stops_flow_immediately_without_retries(monkeypatch):
    from code2video.flow.flow import FlowError, run_flow

    calls = []

    def fake_chat(*a, **k):
        calls.append(1)
        raise AiClientError("API trả về 404: model đã gỡ", 404)

    monkeypatch.setattr("code2video.flow.nodes.chat_json", fake_chat)
    settings = ai_settings.load()
    flow = {"engine": "whiteboard", "start": "i", "nodes": {
        "i": {"type": "idea", "config": {"text": "x"}},
        "s": {"type": "ai-script", "config": {"provider": "p"}}},
        "edges": [{"from": "i", "to": "s"}, {"from": "s", "to": "s", "condition": {"field": "s.error", "op": "exists"}, "maxLoop": 3}]}
    settings.providers["p"] = provider("http://unused/v1")
    ai_settings.save(settings)
    with pytest.raises(FlowError, match="404"):
        run_flow(flow, {}, NODES, None)
    assert len(calls) == 1


def test_skill_card_merges_up_to_four_skills(local_settings):
    ids = [uploads.save_skill_file(f"s{i}.md", f"NOI DUNG {i}".encode()).id for i in range(4)]
    out = NODES["skill"]({}, {"skills": ids[:2]}, None)
    content = out["_global"]["_skill"]["content"]
    assert "NOI DUNG 0" in content and "NOI DUNG 1" in content and out["skillIds"] == ids[:2]
    with pytest.raises(ValueError, match="tối đa 4"):
        NODES["skill"]({}, {"skills": ids + ["whiteboard"]}, None)
    with pytest.raises(ValueError, match="Chưa chọn"):
        NODES["skill"]({}, {"skills": []}, None)


def test_upload_limit_is_four_files(local_settings):
    for i in range(4):
        uploads.save_skill_file(f"s{i}.md", b"x")
    with pytest.raises(ValueError, match="tối đa"):
        uploads.save_skill_file("s5.md", b"x")
    uploads.delete_file("skills", "s0.md")
    uploads.save_skill_file("s5.md", b"x")


def test_rate_limit_waits_the_time_provider_asks_then_retries(monkeypatch):
    from code2video import ai_client

    class R:
        def __init__(self, code, text="", headers=None):
            self.status_code, self.text, self.headers = code, text, headers or {}

        def json(self):
            return {"choices": [{"message": {"content": '{"ok": 1}'}}]}

    replies = [R(429, "Rate limit. Please try again in 12.16s."), R(429, "", {"retry-after": "3"}), R(200)]
    waits = []
    monkeypatch.setattr(ai_client, "_post", lambda *a, **k: replies.pop(0))
    monkeypatch.setattr("time.sleep", waits.append)
    p = Provider(id="g", label="G", baseUrl="https://x/v1", model="m", apiKey="k")
    assert ai_client.chat_json(p, [{"role": "user", "content": "hi"}]) == {"ok": 1}
    assert waits == [pytest.approx(13.16), pytest.approx(4.0)]


def test_rate_limit_gives_up_after_three_tries_without_endless_waiting(monkeypatch):
    from code2video import ai_client

    class R:
        status_code, text, headers = 429, "slow down", {}

    monkeypatch.setattr(ai_client, "_post", lambda *a, **k: R())
    monkeypatch.setattr("time.sleep", lambda s: None)
    with pytest.raises(AiClientError, match="429") as err:
        ai_client.chat_json(Provider(id="g", label="G", baseUrl="https://x/v1", model="m", apiKey="k"), [])
    assert not err.value.fatal  # 429 là tạm thời, flow vẫn được thử lại theo vòng retry


def test_api_key_whitespace_is_stripped_on_save(local_settings):
    payload = {"providers": [{"id": "p", "baseUrl": "http://x/v1", "model": "m", "apiKey": "  abc123\n"}], "skills": []}
    asyncio.run(studio.put_ai_settings(studio._json_body(payload)))
    assert ai_settings.load().providers["p"].apiKey == "abc123"


def test_generate_script_requires_a_provider(local_settings):
    with pytest.raises(HTTPException) as err:
        asyncio.run(studio.generate_ai_script(studio._json_body({"topic": "x"})))
    assert err.value.status_code == 400 and "Chưa chọn provider" in err.value.detail


def test_non_chat_models_are_hidden_even_on_openrouter(monkeypatch):
    from code2video import ai_client

    ai_client._ENTRY_CACHE.clear()
    free = {"prompt": "0", "completion": "0"}
    _fake_models(monkeypatch, [{"id": "google/lyria-3:free", "pricing": free}, {"id": "nvidia/x-content-safety:free", "pricing": free},
                               {"id": "google/gemma-4:free", "pricing": free}])
    p = Provider(id="or", label="OR", baseUrl="https://openrouter.ai/api/v1", model="", apiKey="")
    assert ai_client.list_models(p) == ["google/gemma-4:free"]
    ai_client._ENTRY_CACHE.clear()







def test_groq_has_no_image_models_and_free_image_provider_is_gone(monkeypatch):
    from code2video import ai_client

    _fake_models(monkeypatch, [{"id": "llama-3.3-70b-versatile"}])
    p = Provider(id="q", label="Q", baseUrl="https://api.groq.com/openai/v1", model="", apiKey="k")
    assert ai_client.list_all_models(p)["imageModels"] == []
    assert not hasattr(ai_client, "generate_image_free")
    out = NODES["ai-image"]({"_types": {"ai-script": {"scenes": SCENES}}}, {"provider": "pollinations"}, FlowContext(run_dir=Path("unused")))
    assert "provider thật" in out["error"]  # id cũ không còn là nguồn đặc biệt, bị coi như provider không tồn tại


def test_overloaded_503_is_retried_with_backoff(monkeypatch):
    from code2video import ai_client

    class R:
        def __init__(self, code):
            self.status_code, self.text, self.headers = code, "high demand", {}

        def json(self):
            return {"choices": [{"message": {"content": '{"ok": 2}'}}]}

    replies, waits = [R(503), R(503), R(200)], []
    monkeypatch.setattr(ai_client, "_post", lambda *a, **k: replies.pop(0))
    monkeypatch.setattr("time.sleep", waits.append)
    p = Provider(id="g", label="G", baseUrl="https://x/v1", model="m", apiKey="k")
    assert ai_client.chat_json(p, []) == {"ok": 2} and waits == [4.0, 8.0]


def _hf_project(tmp_path, total_ms=8000):
    project = tmp_path / "project"
    project.mkdir()
    cues = [{"index": 1, "text": "Một chiếc chìa.", "startMs": 0, "endMs": 3000},
            {"index": 2, "text": "Một cánh cửa.", "startMs": 3000, "endMs": total_ms}]
    (project / "timeline.json").write_text(json.dumps({"durationMs": total_ms, "cues": cues}), encoding="utf-8")
    return project


def _hf_html(duration, extra=""):
    return (f'<div id="root" data-composition-id="x" data-width="1920" data-height="1080" data-start="0" data-duration="{duration}">'
            f'{extra}</div><script>window.__timelines={{}}</script>')


def _run_ai_html(monkeypatch, local_settings, tmp_path, files):
    seen = {}

    def fake_chat(provider_, messages, **kw):
        seen["user"] = json.loads(messages[1]["content"])
        seen["system"] = messages[0]["content"]
        return {"files": files}

    monkeypatch.setattr("code2video.flow.nodes.chat_json", fake_chat)
    settings = ai_settings.load()
    settings.providers["p"] = provider("http://unused/v1")
    ai_settings.save(settings)
    project = _hf_project(tmp_path)
    state = {"_types": {"ai-script": {"scenes": SCENES}, "tts": {"project": str(project)}}}
    out = NODES["ai-html"](state, {"provider": "p"}, FlowContext(run_dir=tmp_path / "r", engine="hyperframes"))
    return out, seen, project


def test_ai_html_rejects_references_to_files_it_did_not_create(local_settings, tmp_path, monkeypatch):
    html = _hf_html(8, '<img src="assets/a.svg"><img src="assets/missing.svg">')
    out, _, _ = _run_ai_html(monkeypatch, local_settings, tmp_path, {"index.html": html, "assets/a.svg": "<svg/>"})
    assert "assets/missing.svg" in out["error"] and "assets/a.svg" not in out["error"]


def test_ai_html_receives_real_cue_timings_from_the_voiceover(local_settings, tmp_path, monkeypatch):
    out, seen, project = _run_ai_html(monkeypatch, local_settings, tmp_path, {"index.html": _hf_html(8)})
    assert "error" not in out and (project / "index.html").is_file()
    cues = seen["user"]["scenes"][0]["cues"]
    assert seen["user"]["durationSeconds"] == 8.0
    assert [(c["startSec"], c["endSec"]) for c in cues] == [(0.0, 3.0), (3.0, 8.0)]
    assert "startSec" in seen["system"]


def test_ai_html_rejects_a_composition_whose_duration_ignores_the_voiceover(local_settings, tmp_path, monkeypatch):
    out, _, _ = _run_ai_html(monkeypatch, local_settings, tmp_path, {"index.html": _hf_html(20)})
    assert "20.0" in out["error"] and "8.0" in out["error"]
    (tmp_path / "again").mkdir()
    out, _, _ = _run_ai_html(monkeypatch, local_settings, tmp_path / "again", {"index.html": _hf_html(9.5)})  # lệch 1.5s: chấp nhận
    assert "error" not in out


def test_ai_html_requires_voiceover_step_first(tmp_path):
    with pytest.raises(ValueError, match="Giọng đọc phải chạy trước"):
        NODES["ai-html"]({"_types": {"ai-script": {"scenes": SCENES}}}, {"provider": "p"}, FlowContext(run_dir=tmp_path, engine="hyperframes"))


def test_hyperframes_tts_builds_project_with_real_timeline_before_html(tmp_path):
    state = {"_types": {"ai-script": {"scenes": SCENES}, "idea": {"language": "vi"}}}
    ctx = FlowContext(run_dir=tmp_path / "run", engine="hyperframes")
    out = NODES["tts"](state, {"dryRun": True}, ctx)
    project = Path(out["project"])
    timeline = json.loads((project / "timeline.json").read_text(encoding="utf-8"))
    assert out["_global"]["project"] == str(project) and len(timeline["cues"]) == 2
    assert (project / "voiceover.wav").is_file()
    srt = (project / "script.srt").read_text(encoding="utf-8")
    assert "Một chiếc chìa." in srt and "-->" in srt and out["durationSeconds"] == round(timeline["durationMs"] / 1000, 2)


def test_hyperframes_chain_runs_tts_then_html_then_render_order(tmp_path, monkeypatch):
    from code2video.flow.flow import run_flow

    order = []
    reg = {t: (lambda t_: lambda state, cfg, ctx: order.append(t_) or {})(t) for t in NODES}
    flow = {"engine": "hyperframes", "start": "i", "nodes": {
        "i": {"type": "idea"}, "s": {"type": "ai-script"}, "t": {"type": "tts"}, "h": {"type": "ai-html"}, "r": {"type": "render"}},
        "edges": [{"from": "i", "to": "s"}, {"from": "s", "to": "t"}, {"from": "t", "to": "h"}, {"from": "h", "to": "r"}]}
    assert validate_for_engine(flow) == []
    run_flow(flow, {}, reg, None)
    assert order == ["idea", "ai-script", "tts", "ai-html", "render"]
    old = {**flow, "edges": [{"from": "i", "to": "s"}, {"from": "s", "to": "h"}, {"from": "h", "to": "t"}, {"from": "t", "to": "r"}]}
    errors = validate_for_engine(old)
    assert any("AI dựng HTML" in e for e in errors)  # thứ tự cũ (HTML trước giọng đọc) bị từ chối
    wb = {"engine": "whiteboard", "start": "i", "nodes": {"i": {"type": "idea"}, "s": {"type": "ai-script"}, "b": {"type": "build-scenes"}, "t": {"type": "tts"}},
          "edges": [{"from": "i", "to": "s"}, {"from": "s", "to": "b"}, {"from": "b", "to": "t"}]}
    assert validate_for_engine(wb) == []  # Whiteboard giữ nguyên thứ tự


def test_hyperframes_render_muxes_voiceover_when_composition_has_no_audio_tag(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    (project / "index.html").write_text("<div></div>", encoding="utf-8")
    (project / "voiceover.wav").write_bytes(b"wav")
    calls = []

    def fake_render(proj, video, fps=None, quality=None):
        Path(video).write_bytes(b"silent")

    def fake_run(cmd, check=False, **kw):
        calls.append(cmd)
        Path(cmd[-1]).write_bytes(b"with-audio")

    monkeypatch.setattr("code2video.pipeline.render_hyperframes", fake_render)
    monkeypatch.setattr("code2video.pipeline.apply_format", lambda *a, **k: None)
    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("shutil.which", lambda name: "ffmpeg")
    out = NODES["render"]({"project": str(project)}, {"fps": 24}, FlowContext(run_dir=tmp_path / "r", engine="hyperframes"))
    video = Path(out["videos"][0])
    assert video.read_bytes() == b"with-audio" and "-map" in calls[0] and str(project / "voiceover.wav") in calls[0]
    assert not (project / "muxed.mp4").exists()
    # đã có <audio> trong HTML thì không ghép thêm
    (project / "index.html").write_text("<audio src='voiceover.wav'></audio>", encoding="utf-8")
    calls.clear()
    NODES["render"]({"project": str(project)}, {"fps": 24}, FlowContext(run_dir=tmp_path / "r", engine="hyperframes"))
    assert calls == []


def test_ai_html_rejects_inline_script_with_syntax_error(local_settings, tmp_path, monkeypatch):
    import shutil

    if shutil.which("node") is None:
        pytest.skip("cần node")
    bad = ('<div id="root" data-composition-id="x" data-duration="8"></div><script>'
           'const charId = 1; const charId = 2; window.__timelines = {};</script>')
    out, _, _ = _run_ai_html(monkeypatch, local_settings, tmp_path, {"index.html": bad})
    assert "lỗi cú pháp" in out["error"] and "charId" in out["error"]
    ok = '<div id="root" data-composition-id="x" data-duration="8"></div><script>const a = 1; window.__timelines = {};</script>'
    (tmp_path / "ok").mkdir()
    out, _, _ = _run_ai_html(monkeypatch, local_settings, tmp_path / "ok", {"index.html": ok})
    assert "error" not in out


def test_ai_html_retry_tells_the_model_what_went_wrong(local_settings, tmp_path, monkeypatch):
    seen = {}

    def fake_chat(provider_, messages, **kw):
        seen["user"] = json.loads(messages[1]["content"])
        return {"files": {"index.html": _hf_html(8)}}

    monkeypatch.setattr("code2video.flow.nodes.chat_json", fake_chat)
    settings = ai_settings.load()
    settings.providers["p"] = provider("http://unused/v1")
    ai_settings.save(settings)
    project = _hf_project(tmp_path)
    state = {"_types": {"ai-script": {"scenes": SCENES}, "tts": {"project": str(project)}, "ai-html": {"error": "thiếu assets/x.svg"}}}
    NODES["ai-html"](state, {"provider": "p"}, FlowContext(run_dir=tmp_path / "r", engine="hyperframes"))
    assert "thiếu assets/x.svg" in seen["user"]["lastAttemptError"]


def test_render_hyperframes_passes_fps_and_quality_flags(tmp_path, monkeypatch):
    from code2video import pipeline

    commands = []
    monkeypatch.setattr(pipeline.subprocess, "run", lambda cmd, **kw: commands.append(cmd))
    monkeypatch.setattr(pipeline.shutil, "which", lambda name: None)
    monkeypatch.delenv("HF_RENDER_QUALITY", raising=False)
    monkeypatch.delenv("HF_RENDER_FPS", raising=False)
    pipeline.render_hyperframes(tmp_path, tmp_path / "o.mp4", fps=60, quality="delivery")
    cmd = commands[0]
    assert cmd[cmd.index("--fps") + 1] == "60" and cmd[cmd.index("--quality") + 1] == "delivery"
    with pytest.raises(ValueError, match="Chất lượng"):
        pipeline.render_hyperframes(tmp_path, tmp_path / "o.mp4", quality="ultra")
    commands.clear()
    pipeline.render_hyperframes(tmp_path, tmp_path / "o.mp4")  # không chọn gì thì giữ mặc định của HyperFrames
    assert "--quality" not in commands[0] and "--fps" not in commands[0]


def test_whiteboard_fps_is_capped_at_60_and_studio_offers_higher_rates():
    from code2video.studio.jobs import _wb_fps

    assert _wb_fps({"fps": 120}) == 60 and _wb_fps({"fps": 24}) == 24 and _wb_fps({}) is None
    assert 120 in studio.get_config()["fpsOptions"]


def test_reencode_for_other_aspect_ratios_uses_near_lossless_settings(tmp_path, monkeypatch):
    from code2video import pipeline

    video = tmp_path / "v.mp4"
    video.write_bytes(b"x")
    commands = []
    monkeypatch.setattr(pipeline, "_video_size", lambda p: (1920, 1080))
    monkeypatch.setattr(pipeline.subprocess, "run", lambda cmd, **kw: (commands.append(cmd), (tmp_path / "v.fmt.mp4").write_bytes(b"y")))
    pipeline.apply_format(video, "9:16", "fit")
    cmd = commands[0]
    assert cmd[cmd.index("-crf") + 1] == "16" and cmd[cmd.index("-preset") + 1] == "slow"


# ---------- nhiều nhân vật ----------

class _VoiceSpyTTS:
    """TTS giả ghi lại giọng được dùng cho từng câu."""
    sample_rate = 24000

    def __init__(self):
        self.voice = None
        self.used = []

    def synthesize(self, text):
        import numpy as np

        self.used.append((self.voice, text))
        return np.ones(int(self.sample_rate * 0.6), dtype="float32") * 0.1


DIALOGUE = [{"title": "Cảnh 1", "cues": [
    {"text": "Chào bạn.", "doodle": "wave", "label": "Chào", "speaker": "An"},
    {"text": "Chào An nhé.", "doodle": "wave", "label": "Chào lại", "speaker": "Bình"},
    {"text": "Hôm nay học gì?", "doodle": "question", "label": "Học gì", "speaker": "An"}]}]


def test_clean_characters_strips_format_breaking_chars_and_limits_to_four():
    from code2video.ai_script import clean_characters

    assert clean_characters(["An", " Bình:]", "An", "", "[C]", "D", "E"]) == ["An", "Bình", "C", "D"]
    assert clean_characters(None) == [] and clean_characters(["  "]) == []


def test_script_prompt_and_parser_handle_speakers():
    from code2video.ai_script import demo_script, parse_script_payload, system_prompt

    assert "speaker" in system_prompt("x", "vi", ["An", "Bình"]) and "speaker" not in system_prompt("x", "vi", ["An"])
    payload = {"scenes": [{"title": "t", "cues": [
        {"text": "a", "speaker": "bình"}, {"text": "b", "speaker": "Lạ"}, {"text": "c"}]}]}
    cues = parse_script_payload(payload, ["An", "Bình"])["scenes"][0]["cues"]
    assert [c["speaker"] for c in cues] == ["Bình", "Bình", "Bình"]  # khác hoa thường vẫn khớp; thiếu/lạ giữ người trước
    assert "speaker" not in parse_script_payload(payload)["scenes"][0]["cues"][0]  # một người dẫn: không thêm trường
    demo = demo_script("chủ đề", "vi", 1, ["An", "Bình"])
    speakers = [c["speaker"] for s in demo["scenes"] for c in s["cues"]]
    assert speakers[:4] == ["An", "Bình", "An", "Bình"]


def test_scene_srt_uses_multi_speaker_format_that_the_voiceover_parser_reads(tmp_path):
    from code2video.script_parse import parse_script
    from code2video.whiteboard_assets import build_scene_folder

    items = [("wave", c["label"], c["text"]) for c in DIALOGUE[0]["cues"]]
    build_scene_folder(tmp_path / "s", "scene-01", "T", items, "vi", speakers=[c["speaker"] for c in DIALOGUE[0]["cues"]])
    lines, speakers = parse_script((tmp_path / "s" / "script.srt").read_text(encoding="utf-8"))
    assert speakers == ["An", "Bình"] and [l.speaker for l in lines] == ["An", "Bình", "An"]
    build_scene_folder(tmp_path / "p", "scene-01", "T", items, "vi")  # không speakers: SRT thường như cũ
    assert "[An]" not in (tmp_path / "p" / "script.srt").read_text(encoding="utf-8")


def test_whiteboard_tts_gives_each_character_their_own_voice(tmp_path, monkeypatch):
    spy = _VoiceSpyTTS()
    monkeypatch.setattr("code2video.flow.nodes._tts_for", lambda config, language: spy)
    state = {"_types": {"ai-script": {"scenes": DIALOGUE}, "idea": {"language": "vi"}}}
    ctx = FlowContext(run_dir=tmp_path / "run")
    state["_types"]["build-scenes"] = NODES["build-scenes"](state, {}, ctx)
    state["resources"] = state["_types"]["build-scenes"]["dirs"]
    NODES["tts"](state, {"voice": "Mặc định", "speakers": {"An": "Hải Đăng", "Bình": "Trúc Ly"}}, ctx)
    assert [v for v, _ in spy.used] == ["Hải Đăng", "Trúc Ly", "Hải Đăng"]


def test_hyperframes_tts_keeps_speakers_and_real_timings(tmp_path, monkeypatch):
    spy = _VoiceSpyTTS()
    monkeypatch.setattr("code2video.flow.nodes._tts_for", lambda config, language: spy)
    state = {"_types": {"ai-script": {"scenes": DIALOGUE}, "idea": {"language": "vi"}}}
    out = NODES["tts"](state, {"speakers": {"An": "Hải Đăng", "Bình": "Trúc Ly"}}, FlowContext(run_dir=tmp_path / "r", engine="hyperframes"))
    project = Path(out["project"])
    assert [v for v, _ in spy.used] == ["Hải Đăng", "Trúc Ly", "Hải Đăng"] and out["speakers"] == ["An", "Bình"]
    timeline = json.loads((project / "timeline.json").read_text(encoding="utf-8"))
    assert [c["speaker"] for c in timeline["cues"]] == ["An", "Bình", "An"]
    ends = [c["endMs"] for c in timeline["cues"]]
    assert ends == sorted(ends) and timeline["durationMs"] >= ends[-1]  # thời lượng thật, không ép vào ước lượng
    assert "[An]" not in (project / "script.srt").read_text(encoding="utf-8")  # script.srt cho AI HTML là SRT thường


def test_ai_script_node_asks_for_characters_and_returns_them(local_settings, monkeypatch):
    seen = {}

    def fake_chat(provider_, messages, **kw):
        seen["system"] = messages[0]["content"]
        return {"scenes": [{"title": "t", "cues": [{"text": "x", "label": "l", "doodle": "key", "speaker": "Bình"}]}]}

    monkeypatch.setattr("code2video.flow.nodes.chat_json", fake_chat)
    settings = ai_settings.load()
    settings.providers["p"] = provider("http://unused/v1")
    ai_settings.save(settings)
    state = {"topic": "t", "_types": {"idea": {"language": "vi", "minutes": 1}}}
    out = NODES["ai-script"](state, {"provider": "p", "characters": ["An", "Bình"]}, None)
    assert "An, Bình" in seen["system"] and out["scenes"][0]["cues"][0]["speaker"] == "Bình" and out["characters"] == ["An", "Bình"]
    offline = NODES["ai-script"](state, {"provider": "demo", "characters": ["An", "Bình"]}, None)
    assert {c["speaker"] for s in offline["scenes"] for c in s["cues"]} == {"An", "Bình"}


def test_dialogue_prompt_forces_turn_taking_between_all_characters():
    from code2video.ai_script import system_prompt, user_prompt

    system = system_prompt("x", "vi", ["An", "Bình"])
    assert "đổi lượt" in system and "MỖI cue" in system and "An, Bình" in system
    assert "An, Bình" in user_prompt("chủ đề", "vi", 1, ["An", "Bình"])
    assert "đối thoại" not in user_prompt("chủ đề", "vi", 1)
    assert "đối thoại" not in user_prompt("chủ đề", "vi", 1, ["An"])
