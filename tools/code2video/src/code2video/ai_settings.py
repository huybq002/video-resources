"""Cài đặt AI provider + skills cho Studio, lưu tại settings/ai.json (gitignored)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ._env import data_root

SETTINGS_FILE = data_root() / "settings" / "ai.json"
UPLOADS_ROOT = SETTINGS_FILE.parent / "uploads"

PRESET_PROVIDERS = {
    "gemini": {
        "label": "Google Gemini (free tier)",
        "baseUrl": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "",
    },
    "groq": {
        "label": "Groq (free)",
        "baseUrl": "https://api.groq.com/openai/v1",
        "model": "",
    },
    "openrouter": {
        "label": "OpenRouter (free models)",
        "baseUrl": "https://openrouter.ai/api/v1",
        "model": "",
    },
    "other": {
        "label": "Other (OpenAI-compatible)",
        "baseUrl": "",
        "model": "",
    },
}

DEFAULT_SKILL_CONTENT = (
    "Bạn là biên kịch video whiteboard (bảng trắng vẽ tay). Mỗi câu thoại ứng với MỘT hình vẽ đơn giản "
    "và một nhãn ngắn dưới hình. Câu thoại ngắn gọn, nói như dẫn chuyện video ngắn, không liệt kê khô khan. "
    "Duy trì mạch câu chuyện: mở đầu gây tò mò, thân bài triển khai, kết có kêu gọi hành động."
)


@dataclass
class Provider:
    id: str
    label: str
    baseUrl: str
    model: str
    apiKey: str = ""
    imageModel: str = ""


@dataclass
class Skill:
    id: str
    name: str
    content: str = ""
    source: str = ""  # tên file đã upload trong settings/uploads/skills


@dataclass
class AiSettings:
    providers: dict[str, Provider] = field(default_factory=dict)
    skills: dict[str, Skill] = field(default_factory=dict)
    defaultProvider: str = "gemini"
    defaultSkill: str = ""


def default_providers() -> dict[str, Provider]:
    return {
        pid: Provider(id=pid, label=cfg["label"], baseUrl=cfg["baseUrl"], model=cfg["model"])
        for pid, cfg in PRESET_PROVIDERS.items()
    }


def load() -> AiSettings:
    if not SETTINGS_FILE.is_file():
        return AiSettings(
            providers=default_providers(),
            skills={"whiteboard": Skill(id="whiteboard", name="Kịch bản whiteboard", content=DEFAULT_SKILL_CONTENT)},
            defaultSkill="whiteboard",
        )
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return AiSettings(
            providers=default_providers(),
            skills={"whiteboard": Skill(id="whiteboard", name="Kịch bản whiteboard", content=DEFAULT_SKILL_CONTENT)},
            defaultSkill="whiteboard",
        )
    providers = default_providers()
    for pid, raw in (data.get("providers") or {}).items():
        if isinstance(raw, dict):
            providers[pid] = Provider(id=pid, **{k: raw.get(k, "") for k in ("label", "baseUrl", "model", "apiKey", "imageModel")})
    skills = {
        sid: Skill(id=sid, name=raw.get("name", sid), content=raw.get("content", ""), source=raw.get("source", ""))
        for sid, raw in (data.get("skills") or {}).items()
        if isinstance(raw, dict)
    }
    if "whiteboard" not in skills:
        skills["whiteboard"] = Skill(id="whiteboard", name="Kịch bản whiteboard", content=DEFAULT_SKILL_CONTENT)
    return AiSettings(
        providers=providers,
        skills=skills,
        defaultProvider=data.get("defaultProvider") or "gemini",
        defaultSkill=data.get("defaultSkill") or "whiteboard",
    )


def save(settings: AiSettings) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_provider(settings: AiSettings, provider: Provider) -> AiSettings:
    settings.providers[provider.id] = provider
    return settings


def delete_provider(settings: AiSettings, provider_id: str) -> AiSettings:
    settings.providers.pop(provider_id, None)
    if settings.defaultProvider == provider_id:
        settings.defaultProvider = next(iter(settings.providers), "")
    return settings


def upsert_skill(settings: AiSettings, skill: Skill) -> AiSettings:
    settings.skills[skill.id] = skill
    return settings


def delete_skill(settings: AiSettings, skill_id: str) -> AiSettings:
    settings.skills.pop(skill_id, None)
    if settings.defaultSkill == skill_id:
        settings.defaultSkill = next(iter(settings.skills), "")
    return settings
