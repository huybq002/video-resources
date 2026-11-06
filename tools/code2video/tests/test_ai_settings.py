import json

from code2video import ai_settings


def test_defaults_have_presets_and_skill(monkeypatch, tmp_path):
    monkeypatch.setattr(ai_settings, "SETTINGS_FILE", tmp_path / "ai.json")
    settings = ai_settings.load()
    assert set(settings.providers) >= {"gemini", "groq", "openrouter", "other"}
    assert settings.providers["gemini"].baseUrl.startswith("https://")
    assert settings.providers["gemini"].model == ""  # model preset hay bị gỡ: bắt chọn từ danh sách tải về
    assert "whiteboard" in settings.skills
    assert settings.skills["whiteboard"].content


def test_save_and_load_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(ai_settings, "SETTINGS_FILE", tmp_path / "ai.json")
    settings = ai_settings.load()
    settings.providers["gemini"].apiKey = "secret-key"
    settings.defaultProvider = "openrouter"
    settings = ai_settings.upsert_skill(
        settings, ai_settings.Skill(id="custom", name="Kịch bản trinh thám", content="Luôn kết twist.")
    )
    ai_settings.save(settings)
    loaded = ai_settings.load()
    assert loaded.providers["gemini"].apiKey == "secret-key"
    assert loaded.defaultProvider == "openrouter"
    assert loaded.skills["custom"].content == "Luôn kết twist."


def test_delete_provider_and_skill(monkeypatch, tmp_path):
    monkeypatch.setattr(ai_settings, "SETTINGS_FILE", tmp_path / "ai.json")
    settings = ai_settings.load()
    settings = ai_settings.delete_provider(settings, "groq")
    settings = ai_settings.delete_skill(settings, "whiteboard")
    assert "groq" not in settings.providers
    assert "whiteboard" not in settings.skills


def test_settings_file_contains_no_plain_issue_on_partial_json(monkeypatch, tmp_path):
    path = tmp_path / "ai.json"
    path.write_text("{invalid json", encoding="utf-8")
    monkeypatch.setattr(ai_settings, "SETTINGS_FILE", path)
    settings = ai_settings.load()
    assert "gemini" in settings.providers
