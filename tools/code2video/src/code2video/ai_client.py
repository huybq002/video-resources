"""Gọi model qua API chuẩn OpenAI-compatible (Gemini/Groq/OpenRouter/Other)."""
from __future__ import annotations

import json
import re

import httpx

from .ai_settings import Provider


class AiClientError(RuntimeError):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status

    @property
    def fatal(self) -> bool:
        """Lỗi 4xx (sai key, model đã gỡ...) thử lại vô ích; riêng 408/429 là tạm thời."""
        return self.status is not None and 400 <= self.status < 500 and self.status not in (408, 409, 425, 429)


def _api_error(response, what: str = "API") -> AiClientError:
    status = response.status_code
    message = f"{what} trả về {status}: {response.text[:300]}"
    if status == 404:
        message += " → Model có thể đã bị gỡ. Vào Settings, bấm “Tải danh sách model” rồi chọn lại model."
    elif status in (401, 403):
        message += " → Kiểm tra lại API key ở Settings."
    return AiClientError(message, status)


def _request(method: str, url: str, timeout: float, **kwargs) -> httpx.Response:
    """Ép IPv4 trước: Python thử IPv6 đầu tiên và có thể treo ~40 giây nếu mạng không có IPv6 (curl thì không).
    Nếu IPv4 không kết nối được thì thử lại bằng cấu hình mặc định (mạng chỉ có IPv6)."""
    try:
        with httpx.Client(timeout=timeout, transport=httpx.HTTPTransport(local_address="0.0.0.0")) as client:
            return client.request(method, url, **kwargs)
    except httpx.ConnectError:
        with httpx.Client(timeout=timeout) as client:
            return client.request(method, url, **kwargs)


def _get(url: str, *, timeout: float = 30.0, **kwargs) -> httpx.Response:
    return _request("GET", url, timeout, **kwargs)


def _post(url: str, *, timeout: float = 30.0, **kwargs) -> httpx.Response:
    return _request("POST", url, timeout, **kwargs)


def _retry_after(response) -> float:
    """Giây cần chờ khi bị giới hạn tốc độ: header Retry-After hoặc câu 'try again in 12.1s' trong lỗi."""
    import re

    header = response.headers.get("retry-after") if hasattr(response, "headers") else None
    try:
        if header:
            return float(header)
    except ValueError:
        pass
    match = re.search(r"try again in ([\d.]+)\s*(ms|s)", str(response.text), re.I)
    if match:
        value = float(match.group(1))
        return value / 1000 if match.group(2).lower() == "ms" else value
    return 8.0


def _post_retry(url: str, *, max_wait: float = 30.0, **kwargs) -> httpx.Response:
    """POST; gặp 429/503 thì chờ rồi thử lại (tối đa max_wait giây mỗi lần), tối đa 3 lần."""
    import time

    for attempt in range(3):
        response = _post(url, **kwargs)
        if response.status_code not in (429, 503) or attempt == 2:
            return response
        # 503 = máy chủ AI quá tải tạm thời: chờ vài giây rồi thử lại (429 thì chờ đúng số giây nhà cung cấp báo)
        wait = _retry_after(response) + 1.0 if response.status_code == 429 else 4.0 * (attempt + 1)
        time.sleep(min(wait, max_wait))
    return response


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
    if not provider.baseUrl or not provider.model:
        raise AiClientError(f"Provider {provider.label} chưa cấu hình baseUrl/model. Vào Settings để điền.")
    url = provider.baseUrl.rstrip("/") + "/chat/completions"
    payload = {"model": provider.model, "messages": messages, "temperature": 0.7}
    headers = {"Authorization": f"Bearer {provider.apiKey}", "Content-Type": "application/json"}
    try:
        # ép đầu ra là JSON hợp lệ (model nhỏ hay sinh JSON hỏng); provider không hỗ trợ thì thử lại không có
        response = _post_retry(url, json={**payload, "response_format": {"type": "json_object"}}, headers=headers, timeout=timeout)
        if response.status_code == 400 and "response_format" in response.text.lower():
            response = _post_retry(url, json=payload, headers=headers, timeout=timeout)
    except httpx.HTTPError as error:
        raise AiClientError(f"Không gọi được API ({error})") from error
    if response.status_code != 200:
        raise _api_error(response)
    body = response.json()
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise AiClientError(f"Response API không đúng dạng: {body}") from error
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return _extract_json(content)


def _headers(provider: Provider) -> dict:
    return {"Authorization": f"Bearer {provider.apiKey}", "Content-Type": "application/json"}


def _require(provider: Provider, *, need_model: bool = True) -> str:
    if not provider.apiKey:
        raise AiClientError(f"Provider {provider.label} chưa có API key. Vào Settings để nhập.")
    if not provider.baseUrl or (need_model and not provider.model):
        raise AiClientError(f"Provider {provider.label} chưa cấu hình baseUrl/model. Vào Settings để điền.")
    return provider.baseUrl.rstrip("/")


def _is_free(entry: dict) -> bool:
    """OpenRouter: model miễn phí khi có hậu tố ':free' hoặc giá prompt và completion đều bằng 0."""
    if str(entry.get("id", "")).endswith(":free"):
        return True
    pricing = entry.get("pricing") or {}
    try:
        return "prompt" in pricing and "completion" in pricing and all(float(pricing[k]) == 0 for k in ("prompt", "completion"))
    except (TypeError, ValueError):
        return False


_NOT_CHAT = ("whisper", "tts", "embed", "guard", "moderation", "image", "imagen", "veo", "lyria", "dall", "flux",
             "aqa", "live", "audio", "robotics", "orpheus", "transcribe", "safety", "lyria", "music")
_IMAGE_HINTS = ("image", "imagen", "dall", "flux")


def _provider_kind(base_url: str) -> str:
    if "openrouter.ai" in base_url:
        return "openrouter"
    if "groq.com" in base_url:
        return "groq"
    if "generativelanguage.googleapis.com" in base_url:
        return "gemini"
    return "other"


def _outputs(entry: dict) -> list[str]:
    return list((entry.get("architecture") or {}).get("output_modalities") or ["text"])


def _free_chat(kind: str, entry: dict) -> bool:
    """Model chữ miễn phí. OpenRouter: theo giá. Groq: free tier cho mọi model chat. Gemini: các dòng flash/gemma
    (free tier, suy luận theo tên vì API không trả giá). Provider khác: giữ nguyên."""
    name = str(entry["id"]).removeprefix("models/").lower()
    if any(w in name for w in _NOT_CHAT):
        return False
    if kind == "openrouter":
        return _is_free(entry) and "text" in _outputs(entry)
    if kind == "gemini":
        return ("flash" in name or "gemma" in name) and "pro" not in name
    return True


def _image_capable(kind: str, entry: dict) -> bool:
    """Model tạo ảnh (kể cả tính phí, vì ảnh chất lượng tốt hiếm khi miễn phí). Groq không có model ảnh."""
    name = str(entry["id"]).removeprefix("models/").lower()
    if kind == "openrouter":
        return "image" in _outputs(entry)
    if kind == "groq":
        return False
    return any(w in name for w in _IMAGE_HINTS)


_ENTRY_CACHE: dict[str, tuple[float, list[dict]]] = {}
ENTRY_CACHE_TTL = 600.0


def _fetch_entries(provider: Provider, timeout: float) -> list[dict]:
    import time

    kind = _provider_kind(provider.baseUrl)
    if kind == "openrouter":
        base = provider.baseUrl.rstrip("/")
        cached = _ENTRY_CACHE.get(base)
        if cached and time.monotonic() - cached[0] < ENTRY_CACHE_TTL:
            return cached[1]  # danh sách OpenRouter ~800 KB, tải chậm: nhớ 10 phút
    else:
        base = _require(provider, need_model=False)
    headers = _headers(provider) if provider.apiKey else {"Content-Type": "application/json"}
    try:
        response = _get(base + "/models", headers=headers, timeout=timeout)
    except httpx.HTTPError as error:
        raise AiClientError(f"Không gọi được API ({error})") from error
    if response.status_code != 200:
        raise _api_error(response)
    try:
        entries = response.json().get("data") or []
    except (ValueError, AttributeError) as error:
        raise AiClientError("Response /models không đúng dạng.") from error
    entries = [e for e in entries if isinstance(e, dict) and e.get("id")]
    if kind == "openrouter":
        _ENTRY_CACHE[base] = (time.monotonic(), entries)
    return entries


def list_all_models(provider: Provider, *, timeout: float = 120.0) -> dict:
    """GET {baseUrl}/models → {"models": chat miễn phí, "imageModels": mọi model tạo ảnh}, mỗi list sắp xếp A-Z.

    OpenRouter công khai danh sách (không cần key). Model chat chỉ lấy loại miễn phí; model ảnh lấy tất cả (có thể tính phí).
    """
    kind = _provider_kind(provider.baseUrl)
    entries = _fetch_entries(provider, timeout)
    ident = lambda e: str(e["id"]).removeprefix("models/")  # noqa: E731
    chat = sorted({ident(e) for e in entries if _free_chat(kind, e)})
    image = sorted({ident(e) for e in entries if _image_capable(kind, e)})
    if not chat and not image:
        raise AiClientError("Provider không trả về model miễn phí nào.")
    return {"models": chat, "imageModels": image}


def list_models(provider: Provider, *, timeout: float = 120.0) -> list[str]:
    return list_all_models(provider, timeout=timeout)["models"]


def ping(provider: Provider, *, timeout: float = 30.0) -> dict:
    """Gọi thử 1 câu rất ngắn để biết key/baseUrl/model có chạy thật không."""
    import time

    base = _require(provider)
    payload = {"model": provider.model, "messages": [{"role": "user", "content": "Trả lời đúng một từ: OK"}],
               "max_tokens": 16, "temperature": 0}
    started = time.monotonic()
    try:
        response = _post(base + "/chat/completions", json=payload, headers=_headers(provider), timeout=timeout)
    except httpx.HTTPError as error:
        raise AiClientError(f"Không gọi được API ({error})") from error
    if response.status_code != 200:
        raise _api_error(response)
    try:
        reply = response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise AiClientError("Response API không đúng dạng chat/completions.") from error
    if isinstance(reply, list):
        reply = "".join(part.get("text", "") for part in reply if isinstance(part, dict))
    return {"latencyMs": round((time.monotonic() - started) * 1000), "reply": str(reply or "").strip()[:80],
            "model": provider.model}


def generate_image(provider: Provider, prompt: str, *, size: str = "", timeout: float = 180.0) -> bytes:
    """POST {baseUrl}/images/generations (OpenAI-compatible) → bytes ảnh (b64_json hoặc url)."""
    import base64

    base = _require(provider, need_model=False)
    if not provider.imageModel:
        raise AiClientError(f"Provider {provider.label} chưa chọn model ảnh. Vào Settings → chọn 'Model ảnh'.")
    payload: dict = {"model": provider.imageModel, "prompt": prompt, "n": 1, "response_format": "b64_json"}
    if size:
        payload["size"] = size
    try:
        response = _post_retry(base + "/images/generations", json=payload, headers=_headers(provider), timeout=timeout)
    except httpx.HTTPError as error:
        raise AiClientError(f"Không gọi được API tạo ảnh ({error})") from error
    if response.status_code != 200:
        raise _api_error(response, "API ảnh")
    try:
        item = response.json()["data"][0]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise AiClientError("Response API ảnh không đúng dạng.") from error
    try:
        if item.get("b64_json"):
            return base64.b64decode(item["b64_json"])
        if item.get("url"):
            image = _get(item["url"], timeout=timeout)
            image.raise_for_status()
            return image.content
    except (httpx.HTTPError, ValueError) as error:
        raise AiClientError(f"Không tải được ảnh AI trả về ({error})") from error
    raise AiClientError("Response API ảnh không có b64_json hoặc url.")

