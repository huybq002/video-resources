import httpx
import pytest

from code2video import ai_client
from code2video.ai_client import AiClientError, _extract_json, chat_json
from code2video.ai_settings import Provider


class FakeResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_extract_json_from_fenced_block():
    assert _extract_json('```json\n{"scenes": []}\n```') == {"scenes": []}
    assert _extract_json('Ghi chú trước {"a": 1} ghi chú sau') == {"a": 1}
    with pytest.raises(AiClientError):
        _extract_json("Không có json ở đây")


def test_chat_json_posts_openai_compatible(monkeypatch):
    calls = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        calls["url"] = url
        calls["json"] = json
        calls["headers"] = headers
        return FakeResponse(200, {"choices": [{"message": {"content": '{"scenes": []}'}}]})

    monkeypatch.setattr(ai_client, "_post", fake_post)
    provider = Provider(id="p", label="P", baseUrl="https://api.example.com/v1/", model="m", apiKey="k")
    result = chat_json(provider, [{"role": "user", "content": "xin chào"}])
    assert result == {"scenes": []}
    assert calls["url"] == "https://api.example.com/v1/chat/completions"
    assert calls["json"]["model"] == "m"
    assert calls["headers"]["Authorization"] == "Bearer k"


def test_chat_json_requires_api_key(monkeypatch):
    monkeypatch.setattr(
        ai_client, "_post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("không được gọi"))
    )
    provider = Provider(id="p", label="P", baseUrl="https://x", model="m", apiKey="")
    with pytest.raises(AiClientError, match="API key"):
        chat_json(provider, [{"role": "user", "content": "hi"}])


def test_chat_json_surfaces_http_error(monkeypatch):
    monkeypatch.setattr(ai_client, "_post", lambda *a, **k: FakeResponse(401, "unauthorized"))
    provider = Provider(id="p", label="P", baseUrl="https://x", model="m", apiKey="k")
    with pytest.raises(AiClientError, match="401"):
        chat_json(provider, [{"role": "user", "content": "hi"}])


def test_chat_json_requires_base_url_and_model(monkeypatch):
    monkeypatch.setattr(ai_client, "_post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("không được gọi")))
    provider = Provider(id="p", label="P", baseUrl="", model="", apiKey="k")
    with pytest.raises(AiClientError, match="baseUrl"):
        chat_json(provider, [{"role": "user", "content": "hi"}])


def test_chat_json_asks_for_json_mode_and_falls_back_when_unsupported(monkeypatch):
    sent = []

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.append(json)
        if "response_format" in json:
            return FakeResponse(400, "response_format is not supported by this model")
        return FakeResponse(200, {"choices": [{"message": {"content": '{"a": 1}'}}]})

    monkeypatch.setattr(ai_client, "_post", fake_post)
    p = Provider(id="p", label="P", baseUrl="https://x/v1", model="m", apiKey="k")
    assert chat_json(p, []) == {"a": 1}
    assert "response_format" in sent[0] and "response_format" not in sent[1]
