# AI Kịch bản — tích hợp model free vào Studio (Phase 1: Whiteboard) — Kế hoạch triển khai

**Mục tiêu:** Thêm tab "AI Kịch bản" vào Studio: người dùng chọn model free (Gemini/Groq/OpenRouter/Other + nhập API key), nhập ý tưởng → AI sinh kịch bản SRT + chọn doodle cho từng câu → người dùng duyệt/sửa → app tự dựng resource whiteboard rồi chạy đúng pipeline hiện có (TTS → render song song → auto-merge), vẫn giữ video từng scene.

**Ràng buộc quan trọng:** AI automation **không thay thế** upload thủ công. Các chế độ hiện có phải giữ nguyên hoạt động: whiteboard wtab **Folder** và **Thủ công**, HyperFrames **File lẻ** và **Folder**. Tab AI là **wtab thứ 3** nằm cạnh Folder/Thủ công, không sửa logic các nhánh cũ (chỉ tách helper merge dùng chung, hành vi y hệt).

**Kiến trúc:** Một store settings JSON (`settings/ai.json`, gitignored) giữ danh sách provider (baseUrl + model + apiKey) và skills (system prompt). Một client chuẩn **OpenAI-compatible** (`POST {baseUrl}/chat/completions`) — cả 4 provider đều tương thích chuẩn này nên chỉ cần 1 hàm gọi. Prompt sinh kịch bản trả về JSON `{scenes:[{title, cues:[{text, doodle, label}]}]}` được kiểm duyệt server-side. Thư viện doodle được tách từ `scripts/gen_whiteboard_mystery.py` thành module `code2video.whiteboard_assets` để cả generator CLI lẫn app đều dùng. Job mode mới `ai-script` dựng resource vào run dir rồi tái dùng nguyên nhánh folder (voice-derived pacing + auto-merge).

**Tech stack:** Python 3.12 + FastAPI (async JSON route) + httpx (gọi model) + Pillow (doodle) + JS thuần (UI). Không thêm framework mới.

---

## Bối cảnh cho người thực thi (đọc trước khi làm)

- Repo: `H:\Tool\code2video`, nhánh hiện tại `main`. **Bước 0 của mọi task: làm trên nhánh feature** (xem Bước 0).
- Chạy test: `cd /h/Tool/code2video && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest -q` (pytest đã pin `<9.0`).
- Chạy Studio: `cd /h/Tool/code2video && WHITEBOARD_ROOT="H:/Tool/video-generate/srt-whiteboard-animation" WHITEBOARD_PYTHON="H:/Tool/video-generate/srt-whiteboard-animation/.venv/Scripts/python.exe" STUDIO_PORT=7863 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m code2video.studio.app` — **server không auto-reload, sửa code phải restart**.
- UI tại http://127.0.0.1:7863/ (mở bằng browser để kiểm chứng; dùng MCP browser-use hoặc tự mở).
- Quy ước codebase: docstring tiếng Việt 1 dòng, không comment thừa, test trong `tests/`, form job nhận `Form(...)`, route trả `JSONResponse`/dict, lỗi tiếng Việt trong `detail`.
- `settings/` phải vào `.gitignore` (chứa API key).
- Server chạy song song tối đa 4 worker; TTS được tuần tự hóa bằng `self._tts_lock` (đã có).

## Bước 0: tạo nhánh feature

```bash
cd /h/Tool/code2video && git checkout -b feature/ai-script
```

---

## Cấu trúc file

| File | Trách nhiệm |
|---|---|
| `src/code2video/ai_settings.py` (mới) | Dataclass `Provider`/`Skill`, presets Gemini/Groq/OpenRouter/Other, load/save `settings/ai.json`, upsert/delete |
| `src/code2video/ai_client.py` (mới) | Gọi `POST {baseUrl}/chat/completions` (httpx), parse JSON từ output model, lỗi tiếng Việt |
| `src/code2video/ai_script.py` (mới) | Prompt hệ thống + user, kiểm duyệt payload JSON (doodle hợp lệ, 1-6 cue/scene), `demo_script()` không cần key |
| `src/code2video/whiteboard_assets.py` (mới) | Thư viện doodle (tách từ gen_whiteboard_mystery.py) + `draw_scene()` + `build_scene_folder()` |
| `scripts/gen_whiteboard_mystery.py`, `scripts/gen_whiteboard_mystery_i18n.py` (sửa) | Mỏng hóa: import từ `whiteboard_assets`, giữ nguyên dữ liệu SCENES/LOCALES |
| `src/code2video/studio/app.py` (sửa) | Route `/api/ai/settings` GET/POST, `/api/ai/generate-script` POST, mode `ai-script` trong `create_job`, helper `_enqueue_whiteboard_merge` |
| `src/code2video/studio/static/index.html` (sửa) | wtab "AI Kịch bản" + wbpanel ai (topic/provider/skill/review/settings) |
| `src/code2video/studio/static/studio.js` (sửa) | load/save settings, gọi generate-script, render review, `aiBuildForm()`, refactor `submitJob` → `sendForm` |
| `src/code2video/studio/static/studio.css` (sửa) | Style cho provider/skill/cue rows, details panel |
| `pyproject.toml`, `.gitignore` (sửa) | thêm `httpx>=0.27`; thêm `settings/` |
| `tests/test_ai_settings.py`, `tests/test_ai_client.py`, `tests/test_ai_script.py`, `tests/test_whiteboard_assets.py` (mới), `tests/test_studio_whiteboard.py` (sửa) | Test đơn vị + route |

---

## Task 1: Dependency httpx + module cài đặt AI (ai_settings)

**File:**
- Sửa: `pyproject.toml:10-17`, `.gitignore`
- Tạo: `src/code2video/ai_settings.py`
- Test: `tests/test_ai_settings.py`

- [ ] **Bước 1: Viết test thất bại**

`tests/test_ai_settings.py`:

```python
import json

from code2video import ai_settings


def test_defaults_have_presets_and_skill(monkeypatch, tmp_path):
    monkeypatch.setattr(ai_settings, "SETTINGS_FILE", tmp_path / "ai.json")
    settings = ai_settings.load()
    assert set(settings.providers) >= {"gemini", "groq", "openrouter", "other"}
    assert settings.providers["gemini"].baseUrl.startswith("https://")
    assert settings.providers["gemini"].model
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
    settings = ai_settings.load()  # fallback về default, không crash
    assert "gemini" in settings.providers
```

- [ ] **Bước 2: Chạy test, xác nhận fail**

```bash
cd /h/Tool/code2video && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_ai_settings.py -q
```
Kỳ vọng: FAIL — `ModuleNotFoundError: No module named 'code2video.ai_settings'`.

- [ ] **Bước 3: Thêm dependency + viết module**

`pyproject.toml` — sửa block dependencies thành:

```toml
dependencies = [
  "numpy>=1.24",
  "soundfile>=0.12",
  "fastapi>=0.110",
  "uvicorn>=0.27",
  "python-multipart>=0.0.9",
  "edge-tts>=7.0",
  "httpx>=0.27",
]
```

`.gitignore` — thêm dòng cuối:

```
settings/
```

`src/code2video/ai_settings.py`:

```python
"""Cài đặt AI provider + skills cho Studio, lưu tại settings/ai.json (gitignored)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

SETTINGS_FILE = Path(__file__).resolve().parents[2] / "settings" / "ai.json"

PRESET_PROVIDERS = {
    "gemini": {
        "label": "Google Gemini (free)",
        "baseUrl": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.0-flash",
    },
    "groq": {
        "label": "Groq (free)",
        "baseUrl": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
    },
    "openrouter": {
        "label": "OpenRouter (free models)",
        "baseUrl": "https://openrouter.ai/api/v1",
        "model": "deepseek/deepseek-chat-v3-0324:free",
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


@dataclass
class Skill:
    id: str
    name: str
    content: str = ""


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
        return load()  # file hỏng → dùng default (không ghi đè)
    providers = default_providers()
    for pid, raw in (data.get("providers") or {}).items():
        if isinstance(raw, dict):
            providers[pid] = Provider(id=pid, **{k: raw.get(k, "") for k in ("label", "baseUrl", "model", "apiKey")})
    skills = {
        sid: Skill(id=sid, name=raw.get("name", sid), content=raw.get("content", ""))
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
```

- [ ] **Bước 4: Cài dependency + chạy test**

```bash
cd /h/Tool/code2video && .venv/Scripts/python.exe -m pip install "httpx>=0.27" -q && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_ai_settings.py -q
```
Kỳ vọng: PASS (4 tests).

- [ ] **Bước 5: Commit**

```bash
cd /h/Tool/code2video && git add pyproject.toml .gitignore src/code2video/ai_settings.py tests/test_ai_settings.py && git commit -m "feat: ai settings store for free providers and skills"
```

---

## Task 2: Client gọi model chuẩn OpenAI-compatible (ai_client)

**File:**
- Tạo: `src/code2video/ai_client.py`
- Test: `tests/test_ai_client.py`

- [ ] **Bước 1: Viết test thất bại**

`tests/test_ai_client.py`:

```python
import httpx
import pytest

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

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = Provider(id="p", label="P", baseUrl="https://api.example.com/v1/", model="m", apiKey="k")
    result = chat_json(provider, [{"role": "user", "content": "xin chào"}])
    assert result == {"scenes": []}
    assert calls["url"] == "https://api.example.com/v1/chat/completions"
    assert calls["json"]["model"] == "m"
    assert calls["headers"]["Authorization"] == "Bearer k"


def test_chat_json_requires_api_key(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("không được gọi")))
    provider = Provider(id="p", label="P", baseUrl="https://x", model="m", apiKey="")
    with pytest.raises(AiClientError, match="API key"):
        chat_json(provider, [{"role": "user", "content": "hi"}])


def test_chat_json_surfaces_http_error(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse(401, "unauthorized"))
    provider = Provider(id="p", label="P", baseUrl="https://x", model="m", apiKey="k")
    with pytest.raises(AiClientError, match="401"):
        chat_json(provider, [{"role": "user", "content": "hi"}])
```

- [ ] **Bước 2: Chạy test, xác nhận fail**

```bash
cd /h/Tool/code2video && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_ai_client.py -q
```
Kỳ vọng: FAIL — `ModuleNotFoundError: No module named 'code2video.ai_client'`.

- [ ] **Bước 3: Viết module**

`src/code2video/ai_client.py`:

```python
"""Gọi model qua API chuẩn OpenAI-compatible (Gemini/Groq/OpenRouter/Other)."""
from __future__ import annotations

import json
import re

import httpx

from .ai_settings import Provider


class AiClientError(RuntimeError):
    pass


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise AiClientError(f"Model không trả về JSON: {text[:200]}")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as error:
        raise AiClientError(f"JSON từ model không hợp lệ: {error}") from error


def chat_json(provider: Provider, messages: list[dict], *, timeout: float = 120.0) -> dict:
    if not provider.apiKey:
        raise AiClientError(f"Provider {provider.label} chưa có API key. Vào Settings để nhập.")
    url = provider.baseUrl.rstrip("/") + "/chat/completions"
    payload = {"model": provider.model, "messages": messages, "temperature": 0.7}
    headers = {"Authorization": f"Bearer {provider.apiKey}", "Content-Type": "application/json"}
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=timeout)
    except httpx.HTTPError as error:
        raise AiClientError(f"Không gọi được API ({error})") from error
    if response.status_code != 200:
        raise AiClientError(f"API trả về {response.status_code}: {response.text[:300]}")
    body = response.json()
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise AiClientError(f"Response API không đúng dạng: {body}") from error
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return _extract_json(content)
```

- [ ] **Bước 4: Chạy test**

```bash
cd /h/Tool/code2video && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_ai_client.py -q
```
Kỳ vọng: PASS (4 tests).

- [ ] **Bước 5: Commit**

```bash
cd /h/Tool/code2video && git add src/code2video/ai_client.py tests/test_ai_client.py && git commit -m "feat: openai-compatible ai client with json extraction"
```

---

## Task 3: Tách thư viện doodle thành module (whiteboard_assets)

**File:**
- Tạo: `src/code2video/whiteboard_assets.py`
- Test: `tests/test_whiteboard_assets.py`

Nội dung module = phần "doodle + grid_slots + dur_ms + fmt + draw_scene" **copy nguyên văn** từ `scripts/gen_whiteboard_mystery.py` (dòng 1-238), cộng thêm `LOCALE_FONTS`, `locale_fonts()`, `estimate_dur_ms(text, language)`, `fit_font()`, `build_scene_folder()`. Cụ thể:

- [ ] **Bước 1: Viết test thất bại**

`tests/test_whiteboard_assets.py`:

```python
import json

from PIL import Image

from code2video.whiteboard_assets import DOODLES, build_scene_folder, draw_scene, locale_fonts


def test_locale_fonts_cover_languages():
    assert locale_fonts("vi")[0].endswith("segoeuib.ttf")
    assert "YuGoth" in locale_fonts("ja")[0]


def test_build_scene_folder_writes_png_annotation_srt(tmp_path):
    items = [
        ("door", "Cửa khóa", "Căn phòng bị khóa trái từ bên trong."),
        ("key", "Chìa khóa", "Nhưng chìa khóa vẫn nằm ở ổ bên trong."),
    ]
    result = build_scene_folder(tmp_path / "scene-01", "scene-01", "Mở đầu", items, "vi")

    image = Image.open(tmp_path / "scene-01" / "scene-01.png")
    assert image.size == (1920, 1080)

    annotation = json.loads((tmp_path / "scene-01" / "scene-01.annotation.json").read_text(encoding="utf-8"))
    assert annotation["sceneId"] == "scene-01"
    assert len(annotation["elements"]) == 2
    first = annotation["elements"][0]
    assert first["reveal"]["startMs"] == 0
    assert first["reveal"]["durationMs"] == max(700, first["reveal"]["durationMs"])
    assert annotation["sceneDurationMs"] == result["durationMs"] == sum(
        e["reveal"]["durationMs"] + 120 for e in annotation["elements"]
    )

    srt = (tmp_path / "scene-01" / "script.srt").read_text(encoding="utf-8")
    assert srt.count("-->") == 2
    assert "Căn phòng bị khóa" in srt


def test_draw_scene_contains_ink_and_paper(tmp_path):
    img = draw_scene("Tiêu đề", [("question", "Nhãn", "Sub")], *locale_fonts("vi"))
    assert img.size == (1920, 1080)
    pixels = list(img.getdata())
    paper = (247, 244, 234)
    ink = sum(1 for p in pixels if p != paper)
    assert ink > 2000  # có nét vẽ thật


def test_doodles_registry_has_expected_keys():
    assert {"mansion", "door", "window", "question", "arrow", "clock"}.issubset(DOODLES)
```

- [ ] **Bước 2: Chạy test, xác nhận fail**

```bash
cd /h/Tool/code2video && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_whiteboard_assets.py -q
```
Kỳ vọng: FAIL — `ModuleNotFoundError: No module named 'code2video.whiteboard_assets'`.

- [ ] **Bước 3: Viết module**

`src/code2video/whiteboard_assets.py` — sao chép **toàn bộ** hàm doodle (`d_mansion` … `d_wave`, dict `DOODLES`, `grid_slots`, `font`, `fmt_time`) từ `scripts/gen_whiteboard_mystery.py` rồi thêm các phần sau:

```python
"""Thư viện doodle + dựng folder scene whiteboard; dùng chung cho generator CLI và Studio AI."""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
INK = (38, 49, 46)
RED = (196, 81, 54)
BLUE = (58, 110, 165)
PAPER = (247, 244, 234)
GRID = (232, 228, 216)
FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"
FONT_REG = "C:/Windows/Fonts/segoeui.ttf"
LOCALE_FONTS = {
    "vi": (FONT_BOLD, FONT_REG),
    "en": (FONT_BOLD, FONT_REG),
    "ja": ("C:/Windows/Fonts/YuGothB.ttc", "C:/Windows/Fonts/YuGothM.ttc"),
    "zh": ("C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc"),
    "ko": ("C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"),
}
CPS = {"vi": 0.080, "en": 0.070, "ja": 0.155, "zh": 0.135, "ko": 0.150}

# ... (chép nguyên các hàm doodle d_* + DOODLES + grid_slots + font() từ gen_whiteboard_mystery.py)


def locale_fonts(language: str) -> tuple[str, str]:
    return LOCALE_FONTS.get(language, (FONT_BOLD, FONT_REG))


def estimate_dur_ms(text: str, language: str) -> int:
    return round(min(10.0, max(4.5, len(text) * CPS.get(language, 0.08) + 1.4)) * 1000)


def fmt_time(ms: int) -> str:
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, msr = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{msr:03d}"


def fit_font(path: str, text: str, size: int, max_width: int) -> ImageFont.FreeTypeFont:
    while size > 28:
        candidate = font(path, size)
        if candidate.getlength(text) <= max_width:
            return candidate
        size -= 4
    return font(path, 28)


def draw_scene(title: str, items: list, bold_path: str = FONT_BOLD, regular_path: str = FONT_REG) -> Image.Image:
    """items = [(kind, label, subtitle)]; vẽ tiêu đề + lưới + doodle + nhãn vào khung 1920x1080."""
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    for x in range(0, W, 64):
        d.line([(x, 0), (x, H)], fill=GRID, width=1)
    for y in range(0, H, 64):
        d.line([(0, y), (W, y)], fill=GRID, width=1)
    title_font = fit_font(bold_path, title, 64, W - 220)
    d.text((110, 90), title, font=title_font, fill=INK)
    d.line([(110, 190), (110 + int(title_font.getlength(title)), 190)], fill=RED, width=8)
    for (kind, label, _), slot in zip(items, grid_slots(len(items))):
        cx = slot["x"] + slot["width"] // 2
        cy = slot["y"] + slot["height"] // 2 - 18
        size = min(slot["width"], slot["height"]) * 0.32
        DOODLES.get(kind, DOODLES["question"])(d, cx, cy, size)
        label_font = font(regular_path, 34)
        if label_font.getlength(label) > slot["width"] - 28:
            label_font = font(regular_path, 26)
        d.text((slot["x"] + 14, slot["y"] + slot["height"] - 44), label, font=label_font, fill=RED)
    return img


def build_scene_folder(
    scene_dir: Path, scene_id: str, title: str, items: list, language: str
) -> dict:
    """Dựng <scene>.png + <scene>.annotation.json + script.srt cho một scene.

    items = [(kind, label, subtitle)]. Cửa sổ mỗi cue là ước lượng (dựa trên độ dài text);
    job thật sẽ ghi đè lại bằng độ dài giọng đọc thật (build_whiteboard_from_script).
    """
    bold_path, regular_path = locale_fonts(language)
    scene_dir = Path(scene_dir)
    scene_dir.mkdir(parents=True, exist_ok=True)
    draw_scene(title, items, bold_path, regular_path).save(scene_dir / f"{scene_id}.png", "PNG")
    slots = grid_slots(len(items))
    blocks, elements, t = [], [], 0
    for seq, ((kind, label, subtitle), slot) in enumerate(zip(items, slots), 1):
        dur = estimate_dur_ms(subtitle, language)
        blocks.append(f"{seq}\n{fmt_time(t)} --> {fmt_time(t + dur)}\n{subtitle}\n")
        pad = 14
        region = {"x": slot["x"] + pad, "y": slot["y"] + pad,
                  "width": slot["width"] - 2 * pad, "height": slot["height"] - 2 * pad}
        elements.append({
            "id": f"{scene_id}-el{seq}",
            "label": label,
            "sequence": seq,
            "narrativeRole": subtitle,
            "subtitle": subtitle,
            "type": kind,
            "region": region,
            "reveal": {
                "direction": "top_to_bottom",
                "startMs": t,
                "durationMs": max(700, dur - 120),
                "maskPaddingPx": 18,
                "protectedRegions": [],
            },
            "handPath": {
                "start": [region["x"] + region["width"] // 2, region["y"]],
                "end": [region["x"] + region["width"] // 2, region["y"] + region["height"]],
                "easing": "easeInOut",
            },
        })
        t += dur
    (scene_dir / "script.srt").write_text("\n".join(blocks), encoding="utf-8")
    (scene_dir / f"{scene_id}.annotation.json").write_text(json.dumps({
        "sceneId": scene_id,
        "canvas": {"width": W, "height": H},
        "storyBasis": title,
        "language": language,
        "sceneDurationMs": t,
        "elements": elements,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"sceneId": scene_id, "durationMs": t, "cues": len(items)}
```

> Lưu ý: `font()` cũ trong gen script không truyền `index`; để tải đúng face đầu của `.ttc` (Yu Gothic/msyh), hàm `font()` trong module mới phải là `ImageFont.truetype(path, size, index=0)` (đã kiểm chứng trước đây: YuGothB.ttc index 0 đúng glyph Nhật).

- [ ] **Bước 4: Chạy test**

```bash
cd /h/Tool/code2video && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_whiteboard_assets.py -q
```
Kỳ vọng: PASS (4 tests).

- [ ] **Bước 5: Commit**

```bash
cd /h/Tool/code2video && git add src/code2video/whiteboard_assets.py tests/test_whiteboard_assets.py && git commit -m "refactor: extract whiteboard doodle library into module"
```

---

## Task 4: Mỏng hóa 2 generator để dùng module chung

**File:**
- Sửa: `scripts/gen_whiteboard_mystery.py`, `scripts/gen_whiteboard_mystery_i18n.py`

- [ ] **Bước 1: Sửa `scripts/gen_whiteboard_mystery.py`**

Xóa toàn bộ phần đã chuyển vào module (constants, doodle functions, `DOODLES`, `grid_slots`, `dur_ms`, `fmt`, `draw_scene`) — giữ `OUT`, `SCENES`, `build()`. Thêm import đầu file:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from code2video.whiteboard_assets import draw_scene, grid_slots, locale_fonts, estimate_dur_ms, fmt_time
```

Trong `build()`: thay `draw_scene(title, items)` bằng `draw_scene(title, items, *locale_fonts("vi"))`; thay `dur_ms(subtitle)` bằng `estimate_dur_ms(subtitle, "vi")`; thay `fmt(t)` bằng `fmt_time(t)`.

- [ ] **Bước 2: Sửa `scripts/gen_whiteboard_mystery_i18n.py`**

Xóa phần doodle import cũ; đầu file thêm:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from code2video.whiteboard_assets import DOODLES, grid_slots, estimate_dur_ms, fmt_time, draw_scene
```

- Thay `dur_ms(subtitle, cfg["cps"])` bằng `estimate_dur_ms(subtitle, code)` và bỏ trường `cps` trong LOCALES (giữ font trong LOCALES: `"bold"`, `"regular"`).
- Thay `draw_scene(title, items, cfg)` bằng `draw_scene(title, items, cfg["bold"], cfg["regular"])` (sửa thân hàm `draw_scene` cục bộ của script i18n — xóa bản cục bộ này, dùng hàm của module).
- Trong `build_locale`: thay `fmt(...)` bằng `fmt_time(...)`; `sceneDurationMs` và reveal giữ nguyên công thức `max(700, dur - 120)` (khớp module).

- [ ] **Bước 3: Chạy cả 2 script, xác nhận output không đổi**

```bash
cd /h/Tool/code2video && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/gen_whiteboard_mystery.py > /dev/null && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/gen_whiteboard_mystery_i18n.py > /dev/null && git status --short examples/
```
Kỳ vọng: **không có file nào trong `examples/` bị đổi** (PNG + annotation + SRT tái sinh y hệt).

- [ ] **Bước 4: Chạy toàn bộ test suite**

```bash
cd /h/Tool/code2video && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest -q
```
Kỳ vọng: toàn bộ PASS (không regress).

- [ ] **Bước 5: Commit**

```bash
cd /h/Tool/code2video && git add scripts/gen_whiteboard_mystery.py scripts/gen_whiteboard_mystery_i18n.py && git commit -m "refactor: generators reuse whiteboard_assets module"
```

---

## Task 5: Prompt + kiểm duyệt kịch bản AI (ai_script)

**File:**
- Tạo: `src/code2video/ai_script.py`
- Test: `tests/test_ai_script.py`

- [ ] **Bước 1: Viết test thất bại**

`tests/test_ai_script.py`:

```python
import pytest

from code2video.ai_script import demo_script, parse_script_payload, system_prompt, user_prompt


VALID = {
    "scenes": [
        {"title": "Mở đầu", "cues": [
            {"text": "Câu thoại một về chủ đề.", "doodle": "door", "label": "Cánh cửa"},
            {"text": "Câu thoại hai.", "doodle": "key", "label": "Chìa khóa"},
        ]},
    ]
}


def test_parse_script_payload_valid():
    parsed = parse_script_payload(VALID)
    assert parsed["scenes"][0]["cues"][0]["doodle"] == "door"
    assert parsed["scenes"][0]["cues"][1]["label"] == "Chìa khóa"


def test_parse_script_payload_rejects_unknown_doodle():
    bad = {"scenes": [{"title": "T", "cues": [{"text": "x", "doodle": "rocket", "label": ""}]}]}
    with pytest.raises(ValueError, match="rocket"):
        parse_script_payload(bad)


def test_parse_script_payload_rejects_empty_and_too_many_cues():
    with pytest.raises(ValueError, match="scene"):
        parse_script_payload({"scenes": []})
    many = {"scenes": [{"title": "T", "cues": [{"text": f"c{i}", "doodle": "question", "label": ""} for i in range(7)]}]}
    with pytest.raises(ValueError, match="1-6"):
        parse_script_payload(many)


def test_prompts_contain_schema_and_doodles():
    system = system_prompt("Kỹ năng thử.", "vi")
    assert "scenes" in system and "doodle" in system
    assert "door" in system
    user = user_prompt("thói quen buổi sáng", "vi", 3)
    assert "thói quen buổi sáng" in user and "3" in user


def test_demo_script_needs_no_key_and_parses():
    payload = demo_script("thói quen buổi sáng", "vi", 2)
    parsed = parse_script_payload(payload)
    assert parsed["scenes"]
    assert all(c["doodle"] in ("question", "arrow", "clock", "like", "wave") for s in parsed["scenes"] for c in s["cues"])
```

- [ ] **Bước 2: Chạy test, xác nhận fail**

```bash
cd /h/Tool/code2video && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_ai_script.py -q
```
Kỳ vọng: FAIL — `ModuleNotFoundError: No module named 'code2video.ai_script'`.

- [ ] **Bước 3: Viết module**

`src/code2video/ai_script.py`:

```python
"""Prompt và kiểm duyệt kịch bản AI cho whiteboard engine."""
from __future__ import annotations

from .whiteboard_assets import DOODLES

MAX_CUES_PER_SCENE = 6

SCHEMA_NOTE = (
    'Trả về DUY NHẤT một object JSON, không kèm chú thích, đúng cấu trúc:\n'
    '{"scenes":[{"title":"<tiêu đề scene>","cues":[{"text":"<câu thoại>",'
    '"doodle":"<một trong các loại doodle ở trên>","label":"<nhãn ngắn dưới hình, tối đa 4 từ>"}]}]}\n'
    "Mỗi scene có từ 2 đến 6 cues; mỗi cue là 1-2 câu ngắn (8-25 từ)."
)


def system_prompt(skill_content: str, language: str) -> str:
    return f"{skill_content}\n\nDoodle khả dụng (chỉ chọn từ danh sách): {', '.join(sorted(DOODLES))}\n\n{SCHEMA_NOTE}\n"


def user_prompt(topic: str, language: str, minutes: float) -> str:
    cue_count = round(minutes * 60 / 4.5)
    return (
        f"Viết kịch bản video whiteboard bằng tiếng {language} về chủ đề: {topic}. "
        f"Tổng thời lượng khoảng {minutes} phút (khoảng {cue_count} cue thoại)."
    )


def parse_script_payload(payload: dict) -> dict:
    scenes = payload.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Kịch bản AI thiếu trường scenes.")
    result = []
    for scene_index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            raise ValueError(f"Scene {scene_index} không hợp lệ.")
        title = str(scene.get("title") or f"Phần {scene_index}").strip()
        cues = scene.get("cues")
        if not isinstance(cues, list) or not 1 <= len(cues) <= MAX_CUES_PER_SCENE:
            raise ValueError(f"Scene {title} cần 1-6 cue thoại.")
        parsed_cues = []
        for cue in cues:
            if not isinstance(cue, dict):
                raise ValueError(f"Scene {title} có cue không hợp lệ.")
            text = str(cue.get("text") or "").strip()
            doodle = str(cue.get("doodle") or "question").strip().lower()
            label = str(cue.get("label") or "").strip()
            if not text:
                raise ValueError(f"Scene {title} có cue thiếu text.")
            if doodle not in DOODLES:
                raise ValueError(f"Doodle không hợp lệ trong scene {title}: {doodle}")
            parsed_cues.append({"text": text, "doodle": doodle, "label": label or text[:40]})
        result.append({"title": title, "cues": parsed_cues})
    return {"scenes": result}


def demo_script(topic: str, language: str, minutes: float) -> dict:
    """Kịch bản mẫu không cần gọi model — dùng để test luồng offline và demo UI."""
    lines = [
        (f"Chào mừng bạn đến với video về {topic}.", "wave", "Chào mừng"),
        (f"Vì sao {topic} lại quan trọng với bạn?", "question", "Vì sao?"),
        (f"Thời điểm tốt nhất để bắt đầu là ngay bây giờ.", "clock", "Bắt đầu"),
        (f"Từng bước nhỏ mỗi ngày sẽ tạo ra thay đổi lớn.", "arrow", "Từng bước"),
        (f"Đừng quên áp dụng ngay điều vừa học hôm nay.", "like", "Áp dụng"),
        (f"Cảm ơn bạn đã theo dõi, hẹn gặp lại!", "wave", "Hẹn gặp lại"),
    ]
    cue_count = max(2, min(12, round(minutes * 60 / 4.5)))
    cues = [
        {"text": text, "doodle": doodle, "label": label}
        for text, doodle, label in lines[:cue_count]
    ]
    half = (len(cues) + 1) // 2
    return {"scenes": [
        {"title": "Mở đầu", "cues": cues[:half]},
        {"title": "Nội dung & kết", "cues": cues[half:]},
    ]}
```

- [ ] **Bước 4: Chạy test**

```bash
cd /h/Tool/code2video && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_ai_script.py -q
```
Kỳ vọng: PASS (5 tests).

- [ ] **Bước 5: Commit**

```bash
cd /h/Tool/code2video && git add src/code2video/ai_script.py tests/test_ai_script.py && git commit -m "feat: ai script prompt, validation and offline demo script"
```

---

## Task 6: Route settings + generate-script trong app

**File:**
- Sửa: `src/code2video/studio/app.py`
- Test: `tests/test_studio_whiteboard.py` (thêm 3 test)

- [ ] **Bước 1: Viết test thất bại**

Thêm vào `tests/test_studio_whiteboard.py`:

```python
import httpx

from code2video.studio import app as studio


async def test_ai_settings_roundtrip(monkeypatch, tmp_path):
    import code2video.ai_settings as ai_settings
    monkeypatch.setattr(ai_settings, "SETTINGS_FILE", tmp_path / "ai.json")

    result = studio.get_ai_settings()
    assert "gemini" in {p["id"] for p in result["providers"]}
    assert result["doodles"]

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


async def test_generate_script_demo_provider(monkeypatch, tmp_path):
    import code2video.ai_settings as ai_settings
    monkeypatch.setattr(ai_settings, "SETTINGS_FILE", tmp_path / "ai.json")
    result = asyncio.run(studio.generate_ai_script(studio._json_body({
        "topic": "thói quen buổi sáng", "language": "vi", "providerId": "demo", "skillId": "", "minutes": 2,
    })))
    assert result["providerId"] == "demo"
    assert len(result["scenes"]) == 2


async def test_generate_script_unknown_provider_400(monkeypatch, tmp_path):
    import code2video.ai_settings as ai_settings
    monkeypatch.setattr(ai_settings, "SETTINGS_FILE", tmp_path / "ai.json")
    with pytest.raises(HTTPException) as error:
        asyncio.run(studio.generate_ai_script(studio._json_body({
            "topic": "x", "language": "vi", "providerId": "khong-ton-tai", "skillId": "", "minutes": 2,
        })))
    assert "không tồn tại" in error.value.detail
```

> Lưu ý: pytest không có plugin asyncio — test phải là hàm sync gọi `asyncio.run(...)` (mẫu trên đặt tên `async def` chỉ để minh họa nội dung; khi viết file thật phải đổi thành `def` + bọc `asyncio.run`).

> `studio._json_body(...)` là helper mới (xem Bước 3) mô phỏng `await request.json()`.

- [ ] **Bước 2: Chạy test, xác nhận fail**

```bash
cd /h/Tool/code2video && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_studio_whiteboard.py -q
```
Kỳ vọng: FAIL — `AttributeError: module 'code2video.studio.app' has no attribute 'get_ai_settings'`.

- [ ] **Bước 3: Viết route**

Thêm import đầu `src/code2video/studio/app.py` (sau các import hiện có):

```python
from dataclasses import asdict
from fastapi import Request

from ..ai_client import AiClientError, chat_json
from ..ai_script import demo_script, parse_script_payload, system_prompt, user_prompt
from ..ai_settings import AiSettings, Provider, Skill, delete_provider, delete_skill, load, save
from ..whiteboard_assets import DOODLES
```

Thêm các hàm sau **trước** `create_job` (đặt sau `_accepted`):

```python
def _json_body(data: dict):
    """Helper test gọi route trực tiếp: mô phỏng request.json()."""

    class _Body:
        def __init__(self, payload):
            self._payload = payload

        async def json(self):
            return self._payload

    return _Body(data)


@app.get("/api/ai/settings")
def get_ai_settings() -> dict:
    settings = load()
    return {
        "providers": [asdict(p) for p in settings.providers.values()],
        "skills": [asdict(s) for s in settings.skills.values()],
        "defaultProvider": settings.defaultProvider,
        "defaultSkill": settings.defaultSkill,
        "doodles": sorted(DOODLES),
    }


@app.post("/api/ai/settings")
async def put_ai_settings(request: Request) -> dict:
    data = await request.json()
    settings = load()
    raw_providers = data.get("providers")
    raw_skills = data.get("skills")
    if not isinstance(raw_providers, list) or not isinstance(raw_skills, list):
        raise HTTPException(status_code=400, detail="Settings cần mảng providers và skills.")
    settings.providers = {}
    for raw in raw_providers:
        if not isinstance(raw, dict) or not raw.get("id") or not raw.get("baseUrl") or not raw.get("model"):
            raise HTTPException(status_code=400, detail="Mỗi provider cần id, baseUrl và model.")
        settings.providers[str(raw["id"])] = Provider(
            id=str(raw["id"]),
            label=str(raw.get("label") or raw["id"]),
            baseUrl=str(raw["baseUrl"]),
            model=str(raw["model"]),
            apiKey=str(raw.get("apiKey") or ""),
        )
    settings.skills = {}
    for raw in raw_skills:
        if not isinstance(raw, dict) or not raw.get("id"):
            raise HTTPException(status_code=400, detail="Mỗi skill cần id.")
        settings.skills[str(raw["id"])] = Skill(
            id=str(raw["id"]),
            name=str(raw.get("name") or raw["id"]),
            content=str(raw.get("content") or ""),
        )
    settings.defaultProvider = str(data.get("defaultProvider") or next(iter(settings.providers), ""))
    settings.defaultSkill = str(data.get("defaultSkill") or next(iter(settings.skills), ""))
    save(settings)
    return {"saved": True}


@app.post("/api/ai/generate-script")
async def generate_ai_script(request: Request) -> dict:
    data = await request.json()
    topic = str(data.get("topic") or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Chưa nhập ý tưởng kịch bản.")
    language = str(data.get("language") or "vi")
    provider_id = str(data.get("providerId") or "demo")
    skill_id = str(data.get("skillId") or "")
    minutes = min(10.0, max(1.0, float(data.get("minutes") or 3)))

    settings = load()
    if provider_id == "demo":
        payload = demo_script(topic, language, minutes)
    else:
        provider = settings.providers.get(provider_id)
        if provider is None:
            raise HTTPException(status_code=400, detail=f"Provider {provider_id} không tồn tại.")
        skill = settings.skills.get(skill_id)
        content = skill.content if skill else settings.skills.get("whiteboard").content
        messages = [
            {"role": "system", "content": system_prompt(content, language)},
            {"role": "user", "content": user_prompt(topic, language, minutes)},
        ]
        try:
            payload = chat_json(provider, messages)
        except AiClientError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
    try:
        validated = parse_script_payload(payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=f"Kịch bản AI không hợp lệ: {error}") from error
    return {"scenes": validated["scenes"], "providerId": provider_id}
```

- [ ] **Bước 4: Chạy test**

```bash
cd /h/Tool/code2video && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_studio_whiteboard.py -q
```
Kỳ vọng: PASS (toàn bộ file, gồm 3 test mới).

- [ ] **Bước 5: Commit**

```bash
cd /h/Tool/code2video && git add src/code2video/studio/app.py tests/test_studio_whiteboard.py && git commit -m "feat: ai settings and generate-script api routes"
```

---

## Task 7: Mode job `ai-script` — dựng resource rồi chạy pipeline folder

**File:**
- Sửa: `src/code2video/studio/app.py` (hàm `create_job` + helper merge)
- Test: `tests/test_studio_whiteboard.py` (thêm 1 test)

- [ ] **Bước 1: Viết test thất bại**

Thêm vào `tests/test_studio_whiteboard.py`:

```python
def test_ai_script_mode_builds_scenes_and_enqueues_merge(tmp_path):
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
```

- [ ] **Bước 2: Chạy test, xác nhận fail**

```bash
cd /h/Tool/code2video && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_studio_whiteboard.py::test_ai_script_mode_builds_scenes_and_enqueues_merge -q
```
Kỳ vọng: FAIL — lỗi 400 "Video engine không hợp lệ." hoặc "Whiteboard cần các scene được tải riêng." (mode `ai-script` chưa được nhận diện).

- [ ] **Bước 3: Sửa `create_job`**

a) Thêm param vào signature (sau `autoMerge`):

```python
    autoMerge: bool = Form(False),
    scenes: str = Form("[]"),
) -> JSONResponse:
```

b) Nới điều kiện renderer/mode ở đầu hàm (chấp nhận `ai-script` cho whiteboard):

```python
    if renderer not in ("hyperframes", "whiteboard"):
        raise HTTPException(status_code=400, detail="Video engine không hợp lệ.")
    if renderer == "whiteboard" and mode not in ("whiteboard-scenes", "whiteboard-folder", "ai-script"):
        raise HTTPException(status_code=400, detail="Whiteboard cần các scene được tải riêng.")
    if mode in ("whiteboard-scenes", "whiteboard-folder", "ai-script") and renderer != "whiteboard":
        raise HTTPException(status_code=400, detail="Scene riêng chỉ hỗ trợ engine Whiteboard.")
```

c) Tách helper merge (module-level, đặt trước `create_job`) — **đồng thời thay block merge hiện tại trong nhánh `whiteboard-folder` bằng lời gọi helper này**:

```python
def _enqueue_whiteboard_merge(entries, jobs, auto_merge: bool, format: str, format_mode: str) -> JSONResponse:
    if auto_merge and len(jobs) >= 2:
        merge_id = uuid.uuid4().hex[:12]
        merge_dir = RUNS_ROOT / merge_id
        merge_dir.mkdir(parents=True, exist_ok=True)
        merge_job = queue.enqueue(
            {
                "mode": "merge-whiteboard",
                "outputDir": str(merge_dir),
                "sceneDirs": [entry[0]["outputDir"] for entry in entries],
                "format": format,
                "formatMode": format_mode,
                "dependsOn": [job.id for job in jobs],
            },
            job_id=merge_id,
        )
        return _accepted(jobs + [merge_job])
    return _accepted(jobs)
```

Nhánh folder hiện tại (sau khi nạp `entries`): bỏ block `if autoMerge ...`, thay bằng:

```python
        jobs = queue.enqueue_many(entries)
        return _enqueue_whiteboard_merge(entries, jobs, autoMerge, format, formatMode)
```

d) Thêm nhánh mới **sau nhánh `whiteboard-folder`**, **trước nhánh `files`**:

```python
    if mode == "ai-script":
        try:
            scenes_raw = json.loads(scenes)
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=400, detail="Danh sách scene không hợp lệ.") from error
        try:
            validated = parse_script_payload({"scenes": scenes_raw})
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        from ..whiteboard_assets import build_scene_folder
        _, base = new_dir()
        entries = []
        for index, scene in enumerate(validated["scenes"], 1):
            sid = f"scene-{index:02d}"
            scene_dir = base / sid
            items = [(cue["doodle"], cue["label"], cue["text"]) for cue in scene["cues"]]
            build_scene_folder(scene_dir, sid, scene["title"], items, language)
            entries.append(({
                "mode": "upload",
                "renderer": "whiteboard",
                "outputDir": str(scene_dir),
                "scriptPath": str(scene_dir / "script.srt"),
                "makeVoiceover": True,
                "voice": voVoice.strip() or None,
                "ttsMode": voTtsMode,
                "dryRun": voDry,
                "speakers": speakers,
                "fps": fps,
                "language": language,
                "format": format,
                "formatMode": formatMode,
            }, None))
        jobs = queue.enqueue_many(entries)
        return _enqueue_whiteboard_merge(entries, jobs, autoMerge, format, formatMode)
```

- [ ] **Bước 4: Chạy test**

```bash
cd /h/Tool/code2video && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest -q
```
Kỳ vọng: toàn bộ PASS.

- [ ] **Bước 5: Commit**

```bash
cd /h/Tool/code2video && git add src/code2video/studio/app.py tests/test_studio_whiteboard.py && git commit -m "feat: ai-script job mode builds whiteboard scenes and merges"
```

---

## Task 8: UI — wtab AI Kịch bản + Settings (HTML/JS/CSS)

**File:**
- Sửa: `src/code2video/studio/static/index.html`, `studio.js`, `studio.css`

> Kiểm tra trước khi sửa: `grep -n "voTtsMode\|voVoice" src/code2video/studio/static/index.html` phải trả về 2 id (được dùng bởi `aiBuildForm`). Nếu thiếu thì thêm vào block voice có sẵn.

- [ ] **Bước 1: HTML — thêm wtab + wbpanel**

Trong `index.html`, ngay sau `<button class="wtab" data-wtab="manual">Thủ công</button>` thêm:

```html
            <button class="wtab" data-wbtab="ai">AI Kịch bản</button>
```

Ngay sau `</div>` đóng của `data-wbpanel="manual"` (trước `</div>` đóng `.mode-panel` whiteboard), thêm:

```html
          <div data-wbpanel="ai" hidden>
            <p class="note">AI viết kịch bản + chọn doodle theo ý tưởng của bạn. Chọn model free (Gemini/Groq/OpenRouter/Other) và nhập API key trong <b>Settings</b> bên dưới. Provider <b>Demo</b> chạy offline không cần key.</p>
            <label class="field"><span class="lbl">Ý tưởng / chủ đề</span>
              <textarea id="aiTopic" rows="3" placeholder="Ví dụ: 5 thói quen buổi sáng giúp làm việc hiệu quả hơn"></textarea></label>
            <div class="two">
              <label class="field"><span class="lbl">Thời lượng (phút)</span>
                <input id="aiMinutes" type="number" min="1" max="10" value="3"></label>
              <label class="field"><span class="lbl">Provider</span><select id="aiProvider"></select></label>
            </div>
            <label class="field"><span class="lbl">Skill (system prompt)</span><select id="aiSkill"></select></label>
            <button id="aiGenerate" class="primary" type="button">Sinh kịch bản (AI)</button>
            <div id="aiReview" class="whiteboard-scenes"></div>
            <button id="aiRender" class="primary" type="button" hidden>Tạo video từ kịch bản</button>
            <details class="ai-settings">
              <summary>Settings — AI provider &amp; skills</summary>
              <div id="aiProviders"></div>
              <button id="aiAddProvider" class="ghost add-scene" type="button">+ Thêm provider (Other)</button>
              <div id="aiSkills"></div>
              <button id="aiAddSkill" class="ghost add-scene" type="button">+ Thêm skill</button>
              <button id="aiSettingsSave" class="primary" type="button">Lưu settings</button>
            </details>
          </div>
```

- [ ] **Bước 2: JS — settings + generate + render**

Thêm vào cuối `studio.js`:

```js
// ── AI Kịch bản ──
let aiState = { providers: [], skills: [], doodles: [], defaultProvider: "", defaultSkill: "" };

async function loadAiSettings() {
  const res = await fetch("/api/ai/settings");
  if (!res.ok) throw new Error("Không đọc được ai settings");
  aiState = await res.json();
  $("aiProvider").innerHTML = `<option value="demo">Demo (offline, không cần key)</option>` +
    aiState.providers.map((p) => `<option value="${p.id}">${p.label}</option>`).join("");
  $("aiProvider").value = aiState.defaultProvider || "demo";
  $("aiSkill").innerHTML = aiState.skills.map((s) => `<option value="${s.id}">${s.name}</option>`).join("");
  $("aiSkill").value = aiState.defaultSkill || "";
  renderAiSettings();
}

function renderAiSettings() {
  $("aiProviders").innerHTML = aiState.providers.map((p) => `
    <div class="provider-row" data-id="${p.id}">
      <input class="ai-id" placeholder="id" value="${p.id}">
      <input class="ai-label" placeholder="Tên hiển thị" value="${p.label}">
      <input class="ai-base" placeholder="baseUrl (OpenAI-compatible)" value="${p.baseUrl}">
      <input class="ai-model" placeholder="model" value="${p.model}">
      <input class="ai-key" type="password" placeholder="API key / token" value="${p.apiKey}">
      <button class="ghost ai-del" type="button">Xóa</button>
    </div>`).join("");
  $("aiSkills").innerHTML = aiState.skills.map((s) => `
    <div class="skill-row" data-id="${s.id}">
      <input class="ai-skill-id" placeholder="id" value="${s.id}">
      <input class="ai-skill-name" placeholder="Tên skill" value="${s.name}">
      <textarea class="ai-skill-content" rows="3" placeholder="Nội dung system prompt">${s.content}</textarea>
      <button class="ghost ai-del" type="button">Xóa</button>
    </div>`).join("");
  document.querySelectorAll(".ai-del").forEach((btn) =>
    btn.addEventListener("click", () => btn.closest(".provider-row, .skill-row").remove()));
}

async function saveAiSettings() {
  const providers = [...document.querySelectorAll(".provider-row")].map((row) => ({
    id: row.querySelector(".ai-id").value,
    label: row.querySelector(".ai-label").value,
    baseUrl: row.querySelector(".ai-base").value,
    model: row.querySelector(".ai-model").value,
    apiKey: row.querySelector(".ai-key").value,
  }));
  const skills = [...document.querySelectorAll(".skill-row")].map((row) => ({
    id: row.querySelector(".ai-skill-id").value,
    name: row.querySelector(".ai-skill-name").value,
    content: row.querySelector(".ai-skill-content").value,
  }));
  const res = await fetch("/api/ai/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      providers, skills,
      defaultProvider: $("aiProvider").value,
      defaultSkill: $("aiSkill").value,
    }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
  await loadAiSettings();
}

async function generateScript() {
  $("aiGenerate").disabled = true;
  $("status").textContent = "AI đang viết kịch bản...";
  try {
    const res = await fetch("/api/ai/generate-script", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: $("aiTopic").value,
        language: $("language").value,
        providerId: $("aiProvider").value,
        skillId: $("aiSkill").value,
        minutes: Number($("aiMinutes").value) || 3,
      }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    const data = await res.json();
    renderAiReview(data.scenes);
    $("aiRender").hidden = false;
    $("status").textContent = `Kịch bản xong: ${data.scenes.length} scene. Duyệt/sửa rồi bấm "Tạo video".`;
  } catch (err) {
    $("status").textContent = "Lỗi: " + err.message;
  } finally {
    $("aiGenerate").disabled = false;
  }
}

function doodleOptions(selected) {
  return aiState.doodles.map((d) =>
    `<option value="${d}" ${d === selected ? "selected" : ""}>${d}</option>`).join("");
}

function renderAiReview(scenes) {
  $("aiReview").innerHTML = scenes.map((scene, sIndex) => `
    <div class="ai-scene">
      <input class="ai-scene-title" value="${scene.title}" data-scene="${sIndex}">
      ${scene.cues.map((cue, cIndex) => `
        <div class="cue-row" data-scene="${sIndex}" data-cue="${cIndex}">
          <select class="ai-cue-doodle">${doodleOptions(cue.doodle)}</select>
          <input class="ai-cue-label" placeholder="Nhãn dưới hình" value="${cue.label}">
          <textarea class="ai-cue-text grow" rows="2">${cue.text}</textarea>
        </div>`).join("")}
    </div>`).join("");
}

function collectAiScenes() {
  return [...document.querySelectorAll(".ai-scene")].map((scene) => ({
    title: scene.querySelector(".ai-scene-title").value,
    cues: [...scene.querySelectorAll(".cue-row")].map((row) => ({
      doodle: row.querySelector(".ai-cue-doodle").value,
      label: row.querySelector(".ai-cue-label").value,
      text: row.querySelector(".ai-cue-text").value,
    })),
  })).filter((s) => s.cues.length);
}

function aiBuildForm() {
  const scenes = collectAiScenes();
  if (!scenes.length) { $("status").textContent = "Chưa có kịch bản để render."; return null; }
  const fd = new FormData();
  fd.append("mode", "ai-script");
  fd.append("renderer", "whiteboard");
  fd.append("fps", $("fps").value);
  fd.append("language", $("language").value);
  fd.append("format", $("format").value);
  fd.append("formatMode", $("formatMode").value);
  fd.append("scenes", JSON.stringify(scenes));
  fd.append("voTtsMode", $("voTtsMode").value);
  fd.append("voVoice", $("voVoice").value.trim());
  fd.append("voDry", $("voDry").checked);
  fd.append("speakers", speakersJson());
  fd.append("autoMerge", true);
  const ref = $("voRef").files[0];
  if (ref) fd.append("voRef", ref);
  return fd;
}
```

Sửa `submitJob()` (dòng ~362) — tách phần gửi để tái dùng:

```js
async function sendForm(form) {
  $("run").disabled = true;
  $("status").textContent = "Đang gửi job...";
  try {
    const res = await fetch("/api/jobs", { method: "POST", body: form });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    const data = await res.json();
    const ids = data.jobIds || (data.jobId ? [data.jobId] : []);
    if (!ids.length) throw new Error("Không nhận được job.");
    follow(ids[0]);
    if (ids.length > 1) $("status").textContent = `Đã thêm ${ids.length} job vào hàng đợi.`;
    refreshQueue();
  } catch (err) {
    $("status").textContent = "Lỗi: " + err.message;
  } finally {
    $("run").disabled = false;
  }
}

async function submitJob() {
  const wbTab = $("wbTab").value;
  const form = wbTab === "ai" ? aiBuildForm() : buildForm();
  if (!form) return;
  await sendForm(form);
}
```

Thêm listener vào khối khởi tạo (gần các `addEventListener` khác, cuối vùng init):

```js
  $("aiGenerate").addEventListener("click", generateScript);
  $("aiRender").addEventListener("click", submitJob);
  $("aiSettingsSave").addEventListener("click", () => saveAiSettings().catch((e) => $("status").textContent = "Lỗi: " + e.message));
  $("aiAddProvider").addEventListener("click", () => {
    const row = document.createElement("div");
    row.className = "provider-row";
    row.innerHTML = `<input class="ai-id" placeholder="id" value="custom-${Date.now()}">
      <input class="ai-label" placeholder="Tên hiển thị">
      <input class="ai-base" placeholder="baseUrl (OpenAI-compatible)">
      <input class="ai-model" placeholder="model">
      <input class="ai-key" type="password" placeholder="API key / token">
      <button class="ghost ai-del" type="button">Xóa</button>`;
    row.querySelector(".ai-del").addEventListener("click", () => row.remove());
    $("aiProviders").appendChild(row);
  });
  $("aiAddSkill").addEventListener("click", () => {
    const row = document.createElement("div");
    row.className = "skill-row";
    row.innerHTML = `<input class="ai-skill-id" placeholder="id" value="skill-${Date.now()}">
      <input class="ai-skill-name" placeholder="Tên skill">
      <textarea class="ai-skill-content" rows="3" placeholder="Nội dung system prompt"></textarea>
      <button class="ghost ai-del" type="button">Xóa</button>`;
    row.querySelector(".ai-del").addEventListener("click", () => row.remove());
    $("aiSkills").appendChild(row);
  });
  loadAiSettings().catch((e) => $("status").textContent = "Lỗi settings: " + e.message);
```

Lưu ý: block `aiGenerate`/`aiRender`… nằm trong panel whiteboard luôn tồn tại trong DOM nên đăng ký listener 1 lần ở init là an toàn.

- [ ] **Bước 3: CSS**

Thêm vào cuối `studio.css`:

```css
.ai-settings { margin-top: 16px; border-top: 1px solid var(--line); padding-top: 10px; }
.ai-settings summary { cursor: pointer; color: var(--accent-2); font-size: .9rem; margin-bottom: 8px; }
.provider-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 8px 0; border-bottom: 1px dashed var(--line); align-items: center; }
.provider-row .ai-base { grid-column: 1 / -1; }
.skill-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 8px 0; border-bottom: 1px dashed var(--line); }
.skill-row .ai-skill-content { grid-column: 1 / -1; }
.ai-scene { border: 1px solid var(--line); border-radius: 8px; padding: 10px; margin-top: 10px; }
.ai-scene-title { width: 100%; margin-bottom: 8px; }
.cue-row { display: grid; grid-template-columns: 150px 1fr; gap: 8px; padding: 4px 0; }
.cue-row .grow { grid-column: 1 / -1; }
#aiReview { margin-top: 10px; }
```

- [ ] **Bước 4: Kiểm chứng bằng browser (bắt buộc)**

```bash
# restart server (Task 6/7 đã đổi app.py):
# dừng task server cũ rồi:
cd /h/Tool/code2video && WHITEBOARD_ROOT="H:/Tool/video-generate/srt-whiteboard-animation" WHITEBOARD_PYTHON="H:/Tool/video-generate/srt-whiteboard-animation/.venv/Scripts/python.exe" STUDIO_PORT=7863 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m code2video.studio.app
```
Mở http://127.0.0.1:7863/ → chọn engine **Whiteboard** → wtab **AI Kịch bản**:
1. Chọn provider **Demo**, nhập topic "5 thói quen buổi sáng", bấm **Sinh kịch bản** → review hiện 2 scene với doodle select.
2. Sửa 1 câu, bấm **Tạo video từ kịch bản** → hàng đợi hiện scene jobs + merge job; chờ `done`.
3. Chụp màn hình: (a) form AI đã điền, (b) review sau khi sinh, (c) hàng đợi done có video merge. Lưu vào `build/proof/`.
4. Settings: thêm provider Other (`https://openrouter.ai/api/v1` + model free + key), Lưu, F5 → select vẫn còn key.

Kỳ vọng: luồng offline chạy hết, video merge có file; console browser không lỗi.

- [ ] **Bước 5: Commit**

```bash
cd /h/Tool/code2video && git add src/code2video/studio/static/index.html src/code2video/studio/static/studio.js src/code2video/studio/static/studio.css && git commit -m "feat: ai script tab and settings panel in studio ui"
```

---

## Task 9: Kiểm thử E2E thật + docs + commit cuối

**File:**
- Sửa: `README.md` (thêm mục "AI Kịch bản")

- [ ] **Bước 1: E2E qua API (không cần browser)**

```bash
cd /h/Tool/code2video && curl -s -X POST http://127.0.0.1:7863/api/ai/generate-script -H "Content-Type: application/json" -d '{"topic":"vu an phong kin","language":"en","providerId":"demo","skillId":"","minutes":1}'
```
Kỳ vọng: JSON có `scenes` hợp lệ.

Sau đó tạo job (copy `scenes` từ output trên vào `-F`):

```bash
curl -s -X POST http://127.0.0.1:7863/api/jobs -F "mode=ai-script" -F "renderer=whiteboard" -F "language=en" -F "voDry=true" -F "autoMerge=true" -F 'scenes=<JSON scenes>' | tee /tmp/ai-jobs.json
```
Chờ các jobId trong output về `done` (poll `/api/jobs/{id}` mỗi 15s), rồi:

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 "$(cat /tmp/ai-merge-out.txt)"
```
Kỳ vọng: video merge tồn tại, có độ dài > 5s, 1920x1080@60; các scene dir vẫn còn `output.mp4`.

- [ ] **Bước 2: README**

Thêm mục sau phần whiteboard của `README.md`:

```markdown
## AI Kịch bản (whiteboard)

Tab **AI Kịch bản** (engine Whiteboard): nhập ý tưởng → AI sinh kịch bản SRT + chọn doodle
cho từng câu → duyệt/sửa → app dựng resource rồi chạy pipeline TTS + render + auto-merge.

- Provider mặc định: Google Gemini / Groq / OpenRouter (free tier) + **Other** cho mọi
  API chuẩn OpenAI-compatible. Nhập API key ở **Settings** trong tab (lưu tại
  `settings/ai.json`, đã gitignore).
- Provider **Demo** chạy offline không cần key (dùng test/demo).
- Skills: các system prompt tự thêm, chọn khi sinh kịch bản.
```

- [ ] **Bước 3: Chạy toàn bộ test suite lần cuối**

```bash
cd /h/Tool/code2video && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest -q
```
Kỳ vọng: toàn bộ PASS.

- [ ] **Bước 4: Commit cuối**

```bash
cd /h/Tool/code2video && git add README.md && git commit -m "docs: ai script tab usage"
```

---

## Phase 2 (kế hoạch riêng — viết sau khi Phase 1 merge)

- **AI cho engine HyperFrames**: sinh `index.html` + assets + script.srt từ ý tưởng, dùng `docs/claude-code-skill-brief.md` làm system prompt; asset ảnh (background/nhân vật) qua Pollinations/Cloudflare Workers AI nếu cần. Lý do tách: payload sinh HTML lớn hơn nhiều, cần bước duyệt HTML và chuẩn contract HyperFrames riêng.
- **Skill automation chaining**: chạy nhiều skill theo pipeline (viết kịch bản → duyệt → sinh asset → render) với hook người dùng duyệt giữa các bước.

## Tự kiểm tra (self-audit)

1. **Yêu cầu người dùng:**
   - Tích hợp API free (Gemini/Groq/OpenRouter/Other + key) → Task 1, 2, 6, 8 ✓
   - OpenRouter để tự thêm model → preset `openrouter` + row chỉnh sửa baseUrl/model/key ✓
   - Tích hợp vào 2 engine → Whiteboard Phase 1 (Task 5-8) ✓; HyperFrames → Phase 2 (đã khai báo) ✓
   - Add skills phục vụ automation → Task 1 (store) + Task 6 (route) + Task 8 (UI) ✓; chaining → Phase 2 ✓
   - Select model free + nhập key/token + Other custom → Task 1 presets + Task 8 UI ✓
2. **Không placeholder:** mọi bước đều có code/command cụ thể; không TBD/TODO.
3. **Nhất quán:** `Provider`/`Skill`/`AiSettings` dùng chung giữa ai_settings ↔ ai_client ↔ routes; `parse_script_payload` trả `{"scenes":[...]}` đúng dạng `build_scene_folder` tiêu thụ qua `(doodle, label, text)`; `_enqueue_whiteboard_merge` ký tên khớp 2 nhánh gọi.
4. **TDD:** mỗi task có test-thất-bại → implement → pass → commit.
5. **An toàn:** `settings/` gitignored (key không vào git); route validate id/baseUrl/model trước khi lưu; lỗi model trả 502 kèm detail tiếng Việt hiển thị được trong UI.
