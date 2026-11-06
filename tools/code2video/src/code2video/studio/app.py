from __future__ import annotations

import asyncio
import io
import json
import os
import re
import shutil
import uuid
import zipfile
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .jobs import ARTIFACT_FILES, JobQueue, artifact_path
from .. import uploads
from .. import tools_config
from ..ai_client import AiClientError, chat_json, list_all_models, ping
from ..ai_script import demo_script, parse_script_payload, system_prompt, user_prompt
from ..ai_settings import Provider, Skill, load as load_ai_settings, save as save_ai_settings
from ..flow import rules as flow_rules
from ..flow import store as flow_store
from ..flow.runner import validate_for_engine
from ..tts import EDGE_VOICES
from ..whiteboard import whiteboard_root
from ..whiteboard_assets import DOODLES

STATIC_DIR = Path(__file__).parent / "static"
RUNS_ROOT = Path("build/ui-runs").resolve()

VOICE_PRESETS = {
    "v3turbo": [
        "Adam bựa", "Trúc Ly", "Thiện Minh", "Mai Anh", "Hải Đăng", "Thùy Dung",
        "Thiền Tâm Đức", "Ngọc Huyền", "Quang Sơn", "Ngọc Trân", "Minh Đức", "Phạm Tuyên",
        "Xuân Vĩnh", "Thanh Bình", "Ngọc Linh", "Đoan Trang", "Quỳnh Anh", "Quốc Tuấn",
        "Adam", "Thái Sơn", "Thục Đoan", "Minh Triết", "Mỹ Duyên", "Đức Trí", "Kim Thanh",
    ],
    "v3nano": [
        "Adam", "Ái Hân", "Mỹ Duyên", "Đức Trí", "Hữu Quân", "Xuân Tiên",
        "Mai Anh", "Trúc Ly", "Anh Khôi", "Minh Quân", "Mạnh Dũng",
    ],
}

queue = JobQueue()
app = FastAPI(title="Code2Video Studio")


def _read_script(script_text: str, script_file) -> tuple[str, str]:
    if script_file is not None and getattr(script_file, "size", 0):
        raw = script_file.file.read()
        text = raw.decode("utf-8-sig", errors="replace")
        suffix = Path(script_file.filename or "script.txt").suffix.lower() or ".txt"
        if suffix not in (".srt", ".txt"):
            suffix = ".srt" if "-->" in text else ".txt"
    else:
        text = (script_text or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Hãy nhập script hoặc tải file .srt/.txt.")
        suffix = ".srt" if "-->" in text else ".txt"
    text = re.sub(r"\r\n|\r", "\n", text)
    return text, suffix


def _safe_rel(name: str) -> str | None:
    """Trả về đường dẫn tương đối an toàn, hoặc None nếu có ý traversal/absolute."""
    cleaned = name.replace("\\", "/").lstrip("/")
    parts = [p for p in cleaned.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts) or not parts:
        return None
    return "/".join(parts)


def _write_tree(files, base_dir: Path, *, allow_without_index: bool = False) -> list[Path]:
    """Ghi cây upload giữ cấu trúc và tìm project roots."""
    entries: list[tuple[str, bytes]] = []
    for upload in files:
        rel = _safe_rel(upload.filename or "")
        if rel is None:
            raise HTTPException(status_code=400, detail=f"Đường dẫn file không hợp lệ: {upload.filename}")
        entries.append((rel, upload.file.read()))

    for rel, data in entries:
        target = (base_dir / rel).resolve()
        if not target.is_relative_to(base_dir.resolve()):
            raise HTTPException(status_code=400, detail=f"Đường dẫn ngoài project: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    roots = sorted(
        {(base_dir / rel).parent.resolve() for rel, _ in entries if rel.endswith("index.html")},
        key=lambda p: len(p.parts),
    )
    if not roots and allow_without_index:
        top_dirs = {rel.split("/", 1)[0] for rel, _ in entries}
        if len(top_dirs) == 1:
            candidate = (base_dir / next(iter(top_dirs))).resolve()
            if candidate.is_dir():
                roots = [candidate]
    kept: list[Path] = []
    for root in roots:
        if not any(root != other and root.is_relative_to(other) for other in kept):
            kept.append(root)
    return kept


def _assemble_files_project(html_file, timeline_file, asset_files, audio_file, run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "index.html").write_bytes(html_file.file.read())
    if timeline_file is not None and getattr(timeline_file, "size", 0):
        (run_dir / "timeline.json").write_bytes(timeline_file.file.read())
    if audio_file is not None and getattr(audio_file, "size", 0):
        ext = Path(audio_file.filename or "voiceover.wav").suffix or ".wav"
        (run_dir / f"voiceover{ext}").write_bytes(audio_file.file.read())
    for asset in asset_files:
        rel = _safe_rel(asset.filename or "")
        if rel is None:
            raise HTTPException(status_code=400, detail=f"Tên asset không hợp lệ: {asset.filename}")
        if not rel.startswith("assets/"):
            rel = "assets/" + rel.rsplit("/", 1)[-1]
        target = (run_dir / rel).resolve()
        if not target.is_relative_to(run_dir.resolve()):
            raise HTTPException(status_code=400, detail=f"Đường dẫn asset ngoài project: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(asset.file.read())


def _find_script(project_dir: Path) -> Path | None:
    for name in ("script.srt", "script.txt"):
        candidate = project_dir / name
        if candidate.is_file():
            return candidate
    for pattern in ("*.srt", "*.txt"):
        for candidate in sorted(project_dir.glob(pattern)):
            if candidate.is_file():
                return candidate
    return None


def _discover_whiteboard_scenes(base_dir: Path) -> list[dict]:
    """Tìm scene whiteboard trong cây upload: mỗi cặp <stem>.png + <stem>.annotation.json."""
    scenes: list[dict] = []
    for annotation in sorted(base_dir.rglob("*.annotation.json")):
        stem = annotation.name[: -len(".annotation.json")]
        scene_dir = annotation.parent
        image = scene_dir / f"{stem}.png"
        if not image.is_file():
            continue
        script = _find_script(scene_dir)
        scenes.append({"dir": scene_dir, "image": image, "annotation": annotation, "script": script})
    return scenes


def _accepted(jobs) -> JSONResponse:
    payload = {"jobIds": [job.id for job in jobs], "status": "queued"}
    if len(jobs) == 1:
        payload["jobId"] = jobs[0].id
    return JSONResponse(payload, status_code=202)


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


def _json_body(data: dict):
    """Helper test gọi route trực tiếp: mô phỏng request.json()."""

    class _Body:
        def __init__(self, payload):
            self._payload = payload

        async def json(self):
            return self._payload

    return _Body(data)


def _tools_payload() -> dict:
    values = tools_config.effective()
    root = whiteboard_root()
    ready = bool(root and (root / "scripts" / "render_stream_whiteboard.py").is_file() and (root / "scripts" / "merge_scenes.py").is_file())
    return {"values": values, "problems": tools_config.validate(values), "tools": tools_config.tools_present(),
            "saved": tools_config.load(), "whiteboardReady": ready}


@app.get("/api/tools")
def get_tools() -> dict:
    return _tools_payload()


@app.post("/api/tools")
async def put_tools(request: Request) -> dict:
    data = await request.json()
    values = {k: str(data.get(k) or "").strip() for k in tools_config.KEYS}
    problems = tools_config.validate(values)
    if problems:
        raise HTTPException(status_code=400, detail="; ".join(f"{k}: {v}" for k, v in problems.items()))
    tools_config.save(values)
    tools_config.clear_from_env(k for k, v in values.items() if not v)  # ô để trống = bỏ cấu hình đã lưu
    tools_config.apply_to_env(values)
    return _tools_payload()


@app.get("/api/ai/settings")
def get_ai_settings() -> dict:
    settings = load_ai_settings()
    return {
        "providers": [
            {**{k: v for k, v in asdict(p).items() if k != "apiKey"}, "hasKey": bool(p.apiKey)}
            for p in settings.providers.values()
        ],
        "skills": [asdict(s) for s in settings.skills.values()],
        "defaultProvider": settings.defaultProvider,
        "defaultSkill": settings.defaultSkill,
        "doodles": sorted(DOODLES),
    }


@app.post("/api/ai/settings")
async def put_ai_settings(request: Request) -> dict:
    data = await request.json()
    settings = load_ai_settings()
    old_keys = {pid: p.apiKey for pid, p in settings.providers.items()}
    raw_providers = data.get("providers")
    raw_skills = data.get("skills")
    if not isinstance(raw_providers, list) or not isinstance(raw_skills, list):
        raise HTTPException(status_code=400, detail="Settings cần mảng providers và skills.")
    settings.providers = {}
    for raw in raw_providers:
        if not isinstance(raw, dict) or not str(raw.get("id") or "").strip():
            raise HTTPException(status_code=400, detail="Mỗi provider cần id.")
        pid = str(raw["id"]).strip()
        base_url = str(raw.get("baseUrl") or "").strip()
        model = str(raw.get("model") or "").strip()
        api_key = str(raw.get("apiKey") or "").strip() or old_keys.get(pid, "")
        if api_key and (not base_url or not model):
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{pid}' đã có API key nhưng thiếu baseUrl hoặc model. Điền đủ hoặc xóa key.",
            )
        settings.providers[pid] = Provider(
            id=pid,
            label=str(raw.get("label") or pid),
            baseUrl=base_url,
            model=model,
            apiKey=api_key,
            imageModel=str(raw.get("imageModel") or "").strip(),
        )
    settings.skills = {}
    for raw in raw_skills:
        if not isinstance(raw, dict) or not raw.get("id"):
            raise HTTPException(status_code=400, detail="Mỗi skill cần id.")
        source = str(raw.get("source") or "")
        settings.skills[str(raw["id"])] = Skill(
            id=str(raw["id"]),
            name=str(raw.get("name") or raw["id"]),
            content=str(raw.get("content") or ""),
            source=source if source and (uploads.skills_dir() / source).is_file() else "",
        )
    settings.defaultProvider = str(data.get("defaultProvider") or next(iter(settings.providers), ""))
    settings.defaultSkill = str(data.get("defaultSkill") or next(iter(settings.skills), ""))
    save_ai_settings(settings)
    return {"saved": True}


def _provider_from_body(data: dict, *, need_model: bool) -> Provider:
    """Provider từ form Settings (chưa lưu); thiếu key thì dùng key đã lưu của cùng id."""
    pid = str(data.get("id") or "").strip()
    saved = load_ai_settings().providers.get(pid)
    api_key = str(data.get("apiKey") or "").strip() or (saved.apiKey if saved else "")
    return Provider(
        id=pid or "tmp",
        label=str(data.get("label") or pid or "provider"),
        baseUrl=str(data.get("baseUrl") or "").strip(),
        model=str(data.get("model") or "").strip(),
        apiKey=api_key,
        imageModel=str(data.get("imageModel") or "").strip(),
    )


@app.post("/api/ai/test")
async def test_ai_provider(request: Request) -> dict:
    """Gọi thử provider thật; luôn trả 200 với ok=true/false để UI hiện kết quả ngay trên dòng provider."""
    provider = _provider_from_body(await request.json(), need_model=True)
    try:
        result = await asyncio.to_thread(ping, provider)
    except AiClientError as error:
        return {"ok": False, "message": str(error)}
    return {"ok": True, **result}


@app.post("/api/ai/models")
async def list_ai_models(request: Request) -> dict:
    provider = _provider_from_body(await request.json(), need_model=False)
    try:
        return await asyncio.to_thread(list_all_models, provider)
    except AiClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/api/skills/upload")
async def upload_skill(file: UploadFile = File(...), name: str = Form("")) -> dict:
    data = await file.read()
    try:
        skill = uploads.save_skill_file(file.filename or "", data, name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"id": skill.id, "name": skill.name, "content": skill.content, "source": skill.source}


@app.get("/api/files")
def list_uploaded_files() -> dict:
    files = uploads.list_files()
    return {"files": files, "totalBytes": sum(f["size"] for f in files)}


@app.delete("/api/files/{kind}/{name}")
def delete_uploaded_file(kind: str, name: str) -> dict:
    try:
        removed = uploads.delete_file(kind, name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="File không tồn tại.") from error
    return {"deleted": True, "removedSkills": removed}


@app.post("/api/ai/generate-script")
async def generate_ai_script(request: Request) -> dict:
    data = await request.json()
    topic = str(data.get("topic") or "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Chưa nhập ý tưởng kịch bản.")
    language = str(data.get("language") or "vi")
    provider_id = str(data.get("providerId") or "").strip()
    if not provider_id:
        raise HTTPException(status_code=400, detail="Chưa chọn provider. Chọn Demo hoặc một provider đã có key và model ở Settings.")
    skill_id = str(data.get("skillId") or "")
    minutes = min(10.0, max(1.0, float(data.get("minutes") or 3)))

    settings = load_ai_settings()
    if provider_id == "demo":
        payload = demo_script(topic, language, minutes)
    else:
        provider = settings.providers.get(provider_id)
        if provider is None:
            raise HTTPException(status_code=400, detail=f"Provider {provider_id} không tồn tại.")
        skill = settings.skills.get(skill_id)
        fallback = settings.skills.get("whiteboard")
        content = skill.content if skill else (fallback.content if fallback else "")
        messages = [
            {"role": "system", "content": system_prompt(content, language)},
            {"role": "user", "content": user_prompt(topic, language, minutes)},
        ]
        try:
            payload = await asyncio.to_thread(chat_json, provider, messages)
        except AiClientError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
    try:
        validated = parse_script_payload(payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=f"Kịch bản AI không hợp lệ: {error}") from error
    return {"scenes": validated["scenes"], "providerId": provider_id}


def _flow_or_404(flow_id: str) -> dict:
    try:
        return flow_store.read_flow(flow_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=f"Không có flow {flow_id}.") from error


@app.get("/api/flow")
def list_flows() -> list[dict]:
    return flow_store.list_flows()


@app.post("/api/flow/from-template")
async def flow_from_template(request: Request) -> dict:
    data = await request.json()
    try:
        flow = flow_store.read_template(str(data.get("template") or ""))
        name = str(data.get("name") or flow.get("name") or "flow")
        flow_id = flow_store.unique_id(flow_store.slugify(name))
        flow = {**flow, "name": name}
        flow_store.write_flow(flow_id, flow)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Template không tồn tại.") from error
    return {**flow, "id": flow_id}


@app.get("/api/flow/rules")
def get_flow_rules() -> dict:
    return flow_rules.rules_payload()


@app.get("/api/flow/{flow_id}/last-run")
def get_flow_last_run(flow_id: str) -> dict:
    _flow_or_404(flow_id)
    return flow_store.read_run(flow_id) or {}


_RUN_FILE_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".wav", ".srt", ".json", ".txt", ".html"}


@app.get("/api/flow/{flow_id}/file")
def get_flow_run_file(flow_id: str, path: str):
    """Phục vụ file kết quả (ảnh/video/...) của lần chạy gần nhất, chỉ trong thư mục chạy đó."""
    run = flow_store.read_run(flow_id)
    if not run or not run.get("outputDir"):
        raise HTTPException(status_code=404, detail="Flow chưa có lần chạy nào.")
    base = Path(run["outputDir"]).resolve()
    target = Path(path)
    target = (target if target.is_absolute() else base / target).resolve()
    if not target.is_relative_to(base) or target.suffix.lower() not in _RUN_FILE_TYPES or not target.is_file():
        raise HTTPException(status_code=404, detail="Không có file này trong kết quả.")
    return FileResponse(target)


@app.get("/api/flow/{flow_id}")
def get_flow(flow_id: str) -> dict:
    return _flow_or_404(flow_id)


@app.put("/api/flow/{flow_id}")
async def put_flow(flow_id: str, request: Request) -> dict:
    flow = await request.json()
    if not isinstance(flow, dict):
        raise HTTPException(status_code=400, detail="Flow phải là object JSON.")
    errors = validate_for_engine(flow)
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))
    try:
        flow_store.write_flow(flow_id, flow)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"saved": True, "id": flow_id}


@app.delete("/api/flow/{flow_id}")
def delete_flow(flow_id: str) -> dict:
    _flow_or_404(flow_id)
    flow_store.delete_flow(flow_id)
    return {"deleted": True}


@app.post("/api/flow/run")
async def run_flow_job(request: Request) -> JSONResponse:
    data = await request.json()
    flow = _flow_or_404(str(data.get("flowId") or ""))
    errors = validate_for_engine(flow)
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))
    run_id = uuid.uuid4().hex[:12]
    run_dir = flow_store.run_output_dir(str(data.get("flowId")), run_id)
    job = queue.enqueue(
        {"mode": "flow", "flow": flow, "flowId": str(data.get("flowId")), "topic": str(data.get("topic") or "").strip(), "outputDir": str(run_dir)},
        job_id=run_id,
    )
    return _accepted([job])


@app.get("/api/config")
def get_config() -> dict:
    return {
        "voicePresets": VOICE_PRESETS,
        "defaultVoice": "Hải Đăng",
        "ttsModes": ["v3turbo", "v3nano", "remote"],
        "whisperModels": ["tiny", "base", "small", "medium", "large-v3"],
        "whisperDevices": ["cpu", "cuda"],
        "computeTypes": ["int8", "float16", "float32"],
        "hasFfprobe": shutil.which("ffprobe") is not None,
        "hasNode": shutil.which("node") is not None,
        "hasNpx": shutil.which("npx") is not None,
        "maxWorkers": 4,
        "workers": queue.worker_count,
        "fpsOptions": [24, 30, 48, 60, 120],
        "defaultFps": 60,
        "languages": [
            {"code": "vi", "label": "Tiếng Việt"},
            {"code": "en", "label": "English"},
            {"code": "ja", "label": "日本語"},
            {"code": "zh", "label": "中文"},
            {"code": "ko", "label": "한국어"},
        ],
        "defaultLanguage": "vi",
        "edgeVoices": EDGE_VOICES,
        "formats": [
            {"code": "16:9", "label": "YouTube 16:9 (1920×1080)"},
            {"code": "9:16", "label": "TikTok/Shorts 9:16 (1080×1920)"},
            {"code": "1:1", "label": "Vuông 1:1 (1080×1080)"},
            {"code": "4:5", "label": "Dọc 4:5 (1080×1350)"},
        ],
        "defaultFormat": "16:9",
        "hyperframesReady": bool(
            shutil.which("node") and shutil.which("npx") and shutil.which("ffprobe")
        ),
        "whiteboardReady": bool(
            whiteboard_root()
            and (whiteboard_root() / "scripts" / "render_stream_whiteboard.py").is_file()
            and (whiteboard_root() / "scripts" / "merge_scenes.py").is_file()
        ),
    }


@app.post("/api/settings")
def update_settings(workers: int = Form(3)) -> dict:
    return {"workers": queue.set_workers(workers)}


@app.post("/api/jobs", status_code=202)
async def create_job(
    mode: str = Form("script"),
    renderer: str = Form("hyperframes"),
    runMode: str = Form("queue"),
    sceneScripts: list[UploadFile] = File(default=[]),
    sceneImages: list[UploadFile] = File(default=[]),
    sceneAnnotations: list[UploadFile] = File(default=[]),
    scriptText: str = Form(""),
    scriptFile: UploadFile | None = File(None),
    scriptFiles: list[UploadFile] = File(default=[]),
    voice: str = Form("Hải Đăng"),
    ttsMode: str = Form("v3turbo"),
    refAudio: UploadFile | None = File(None),
    whisperModel: str = Form("small"),
    whisperDevice: str = Form("cpu"),
    computeType: str = Form("int8"),
    align: bool = Form(True),
    dryRun: bool = Form(True),
    renderMp4: bool = Form(False),
    fps: int | None = Form(None),
    hfQuality: str = Form(""),
    wbLongEdge: int = Form(0),
    language: str = Form("vi"),
    format: str = Form("16:9"),
    formatMode: str = Form("fit"),
    projectDir: str = Form(""),
    indexHtml: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    htmlFile: UploadFile | None = File(None),
    timelineFile: UploadFile | None = File(None),
    assetFiles: list[UploadFile] = File(default=[]),
    audioFile: UploadFile | None = File(None),
    makeVoiceover: bool = Form(False),
    voTtsMode: str = Form("v3turbo"),
    voVoice: str = Form(""),
    voRef: UploadFile | None = File(None),
    voDry: bool = Form(False),
    compScript: UploadFile | None = File(None),
    speakers: str = Form("{}"),
    autoMerge: bool = Form(False),
    scenes: str = Form("[]"),
) -> JSONResponse:
    if renderer not in ("hyperframes", "whiteboard"):
        raise HTTPException(status_code=400, detail="Video engine không hợp lệ.")
    if renderer == "whiteboard" and mode not in ("whiteboard-scenes", "whiteboard-folder", "ai-script"):
        raise HTTPException(status_code=400, detail="Whiteboard cần các scene được tải riêng.")
    if mode in ("whiteboard-scenes", "whiteboard-folder", "ai-script") and renderer != "whiteboard":
        raise HTTPException(status_code=400, detail="Scene riêng chỉ hỗ trợ engine Whiteboard.")

    def new_dir() -> tuple[str, Path]:
        rid = uuid.uuid4().hex[:12]
        run_dir = RUNS_ROOT / rid
        run_dir.mkdir(parents=True, exist_ok=True)
        return rid, run_dir

    def voice_params(dest: Path) -> dict:
        ref_path = None
        if voRef is not None and getattr(voRef, "size", 0):
            ext = Path(voRef.filename or "ref.wav").suffix or ".wav"
            ref_path = dest / f"ref_audio{ext}"
            ref_path.write_bytes(voRef.file.read())
        script_path = None
        if compScript is not None and getattr(compScript, "size", 0):
            text = re.sub(r"\r\n|\r", "\n", compScript.file.read().decode("utf-8-sig", errors="replace"))
            suffix = Path(compScript.filename or "script.srt").suffix.lower()
            if suffix not in (".srt", ".txt"):
                suffix = ".srt" if "-->" in text else ".txt"
            script_path = dest / f"script{suffix}"
            script_path.write_text(text, encoding="utf-8", newline="\n")
        return {
            "makeVoiceover": makeVoiceover,
            "voice": voVoice.strip() or None,
            "ttsMode": voTtsMode,
            "refAudio": str(ref_path) if ref_path else None,
            "dryRun": voDry,
            "scriptPath": str(script_path) if script_path else None,
            "speakers": speakers,
            "fps": fps,
            "hfQuality": hfQuality or None,
            "wbLongEdge": wbLongEdge or None,
            "language": language,
            "format": format,
            "formatMode": formatMode,
        }

    if mode == "whiteboard-scenes":
        if not sceneScripts or len(sceneScripts) != len(sceneImages) or len(sceneImages) != len(sceneAnnotations):
            raise HTTPException(status_code=400, detail="Mỗi scene cần đủ một script, một ảnh PNG và một annotation JSON.")
        from ..script_parse import parse_script

        validated_scenes = []
        for script_file, image_file, annotation_file in zip(sceneScripts, sceneImages, sceneAnnotations):
            image_name = Path(image_file.filename or "scene.png").name
            image_stem = Path(image_name).stem
            if Path(image_name).suffix.lower() != ".png":
                raise HTTPException(status_code=400, detail="Whiteboard scene image phải là PNG.")
            script_suffix = Path(script_file.filename or "script.srt").suffix.lower()
            if script_suffix not in (".srt", ".txt"):
                raise HTTPException(status_code=400, detail="Script scene phải là file .srt hoặc .txt.")
            if not all(getattr(upload, "size", 0) for upload in (script_file, image_file, annotation_file)):
                raise HTTPException(status_code=400, detail=f"Scene {image_name} có file rỗng.")
            try:
                script_text = script_file.file.read().decode("utf-8-sig")
                script_file.file.seek(0)
                if not parse_script(script_text)[0]:
                    raise ValueError("Script không có cue thoại.")
                annotation_data = json.loads(annotation_file.file.read().decode("utf-8-sig"))
                annotation_file.file.seek(0)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                raise HTTPException(status_code=400, detail=f"Script hoặc annotation không hợp lệ cho {image_name}.") from error
            if not isinstance(annotation_data, dict) or not annotation_data.get("elements"):
                raise HTTPException(status_code=400, detail=f"Annotation của {image_name} cần có elements.")
            validated_scenes.append((script_file, image_file, annotation_file, image_name, image_stem, script_suffix))

        ref_bytes = voRef.file.read() if voRef is not None and getattr(voRef, "size", 0) else None
        ref_ext = Path(voRef.filename or "ref.wav").suffix if ref_bytes is not None else ".wav"
        job_entries = []
        for script_file, image_file, annotation_file, image_name, image_stem, script_suffix in validated_scenes:
            rid, run_dir = new_dir()
            image_path = run_dir / image_name
            annotation_path = run_dir / f"{image_stem}.annotation.json"
            script_path = run_dir / f"script{script_suffix}"
            image_path.write_bytes(image_file.file.read())
            annotation_path.write_bytes(annotation_file.file.read())
            script_path.write_bytes(script_file.file.read())
            ref_path = None
            if ref_bytes is not None:
                ref_path = run_dir / f"ref_audio{ref_ext}"
                ref_path.write_bytes(ref_bytes)
            job_entries.append(({
                    "mode": "upload",
                    "renderer": "whiteboard",
                    "outputDir": str(run_dir),
                    "scriptPath": str(script_path),
                    "makeVoiceover": True,
                    "voice": voVoice.strip() or None,
                    "ttsMode": voTtsMode,
                    "refAudio": str(ref_path) if ref_path else None,
                    "dryRun": voDry,
                    "speakers": speakers,
                    "fps": fps,
            "hfQuality": hfQuality or None,
            "wbLongEdge": wbLongEdge or None,
                    "language": language,
                    "format": format,
                    "formatMode": formatMode,
                }, rid))
        jobs = queue.enqueue_many(job_entries)
        return _accepted(jobs)

    if mode == "whiteboard-folder":
        if not files:
            raise HTTPException(status_code=400, detail="Chưa chọn folder nào để tải lên.")
        from ..script_parse import parse_script

        _, base = new_dir()
        _write_tree(files, base)
        scenes = _discover_whiteboard_scenes(base)
        if not scenes:
            raise HTTPException(
                status_code=400,
                detail="Không tìm thấy scene nào. Mỗi scene cần <tên>.png + <tên>.annotation.json + script.srt.",
            )
        ref_bytes = voRef.file.read() if voRef is not None and getattr(voRef, "size", 0) else None
        ref_ext = Path(voRef.filename or "ref.wav").suffix if ref_bytes is not None else ".wav"
        entries = []
        for scene in scenes:
            name = scene["dir"].name
            if scene["script"] is None:
                raise HTTPException(status_code=400, detail=f"Scene {name} thiếu script .srt/.txt.")
            try:
                if not parse_script(scene["script"].read_text(encoding="utf-8-sig"))[0]:
                    raise ValueError("empty")
                annotation_data = json.loads(scene["annotation"].read_text(encoding="utf-8-sig"))
                if not isinstance(annotation_data, dict) or not annotation_data.get("elements"):
                    raise ValueError("no elements")
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as error:
                raise HTTPException(status_code=400, detail=f"Script/annotation không hợp lệ ở scene {name}.") from error
            ref_path = None
            if ref_bytes is not None:
                ref_path = scene["dir"] / f"ref_audio{ref_ext}"
                ref_path.write_bytes(ref_bytes)
            entries.append(({
                "mode": "upload",
                "renderer": "whiteboard",
                "outputDir": str(scene["dir"]),
                "scriptPath": str(scene["script"]),
                "makeVoiceover": True,
                "voice": voVoice.strip() or None,
                "ttsMode": voTtsMode,
                "refAudio": str(ref_path) if ref_path else None,
                "dryRun": voDry,
                "speakers": speakers,
                "fps": fps,
            "hfQuality": hfQuality or None,
            "wbLongEdge": wbLongEdge or None,
                "language": language,
                "format": format,
                "formatMode": formatMode,
            }, None))
        jobs = queue.enqueue_many(entries)
        return _enqueue_whiteboard_merge(entries, jobs, autoMerge, format, formatMode)

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
            "hfQuality": hfQuality or None,
            "wbLongEdge": wbLongEdge or None,
                "language": language,
                "format": format,
                "formatMode": formatMode,
            }, None))
        jobs = queue.enqueue_many(entries)
        return _enqueue_whiteboard_merge(entries, jobs, autoMerge, format, formatMode)

    if mode == "files":
        if htmlFile is None or not getattr(htmlFile, "size", 0):
            raise HTTPException(status_code=400, detail="Hãy tải lên index.html.")
        rid, run_dir = new_dir()
        _assemble_files_project(htmlFile, timelineFile, assetFiles, audioFile, run_dir)
        return _accepted([queue.enqueue({"mode": "files", "outputDir": str(run_dir), **voice_params(run_dir)}, job_id=rid)])

    if mode == "project":
        project = Path(projectDir.strip()).expanduser().resolve()
        if not project.is_dir():
            raise HTTPException(status_code=400, detail=f"Thư mục không tồn tại: {projectDir}")
        if not (project / "index.html").is_file():
            raise HTTPException(status_code=400, detail="Thư mục phải chứa index.html (composition HyperFrames).")
        return _accepted([queue.enqueue({"mode": "project", "outputDir": str(project), **voice_params(project)})])

    if mode == "html":
        html_src = (indexHtml or "").strip()
        if not html_src:
            raise HTTPException(status_code=400, detail="Hãy dán nội dung index.html.")
        rid, run_dir = new_dir()
        (run_dir / "index.html").write_text(html_src, encoding="utf-8", newline="\n")
        return _accepted([queue.enqueue({"mode": "html", "outputDir": str(run_dir), **voice_params(run_dir)}, job_id=rid)])

    if mode == "upload":
        if not files:
            raise HTTPException(status_code=400, detail="Chưa chọn folder/project nào để tải lên.")
        _, base = new_dir()
        is_whiteboard = renderer == "whiteboard"
        roots = _write_tree(files, base, allow_without_index=is_whiteboard)
        if not roots:
            detail = "Whiteboard chỉ nhận một folder project mỗi lần upload." if is_whiteboard else "Folder upload phải chứa index.html."
            raise HTTPException(status_code=400, detail=detail)
        if is_whiteboard and len(roots) > 1:
            raise HTTPException(status_code=400, detail="Whiteboard chỉ nhận một folder project mỗi lần upload.")

        def upload_params(root: Path) -> dict:
            params = {"mode": "upload", "renderer": renderer, "outputDir": str(root), **voice_params(root)}
            if not params.get("scriptPath"):
                found = _find_script(root)
                if found is not None:
                    params["scriptPath"] = str(found)
                    params["makeVoiceover"] = True
            if is_whiteboard and not params.get("scriptPath"):
                raise HTTPException(status_code=400, detail="Whiteboard cần file script .srt/.txt để tạo voiceover.")
            return params

        if runMode == "batch":
            return _accepted([queue.enqueue(upload_params(root)) for root in roots])
        if len(roots) > 1:
            raise HTTPException(status_code=400, detail="Folder có nhiều project — chọn chế độ Batch để render tất cả.")
        return _accepted([queue.enqueue(upload_params(roots[0]))])

    # --- mode == "script" ---
    sources: list[tuple[str, str]] = []
    for upload in scriptFiles:
        if not getattr(upload, "size", 0):
            continue
        text = re.sub(r"\r\n|\r", "\n", upload.file.read().decode("utf-8-sig", errors="replace"))
        suffix = Path(upload.filename or "script.txt").suffix.lower()
        if suffix not in (".srt", ".txt"):
            suffix = ".srt" if "-->" in text else ".txt"
        sources.append((text, suffix))
    if not sources:
        sources.append(_read_script(scriptText, scriptFile))

    ref_bytes = None
    if len(sources) == 1 and refAudio is not None and getattr(refAudio, "size", 0):
        ref_bytes = refAudio.file.read()

    jobs = []
    for text, suffix in sources:
        rid, run_dir = new_dir()
        script_path = run_dir / f"script{suffix}"
        script_path.write_text(text, encoding="utf-8", newline="\n")
        ref_audio_path = None
        if ref_bytes is not None:
            ref_audio_path = run_dir / "ref_audio.wav"
            ref_audio_path.write_bytes(ref_bytes)
        params = {
            "mode": "script",
            "scriptPath": str(script_path),
            "outputDir": str(run_dir),
            "voice": voice.strip() or None,
            "refAudio": str(ref_audio_path) if ref_audio_path else None,
            "ttsMode": ttsMode,
            "whisperModel": whisperModel,
            "whisperDevice": whisperDevice,
            "computeType": computeType,
            "align": align,
            "dryRun": dryRun,
            "renderMp4": renderMp4,
            "fps": fps,
            "hfQuality": hfQuality or None,
            "wbLongEdge": wbLongEdge or None,
            "language": language,
            "format": format,
            "formatMode": formatMode,
        }
        jobs.append(queue.enqueue(params, job_id=rid))
    return _accepted(jobs)


@app.post("/api/whiteboard/merge", status_code=202)
def merge_whiteboard_jobs(sceneJobIds: str = Form("[]"), format: str = Form("16:9"), formatMode: str = Form("fit")) -> JSONResponse:
    try:
        job_ids = json.loads(sceneJobIds)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=400, detail="Danh sách scene không hợp lệ.") from error
    if not isinstance(job_ids, list) or len(job_ids) < 2 or any(not isinstance(job_id, str) for job_id in job_ids):
        raise HTTPException(status_code=400, detail="Chọn ít nhất hai scene whiteboard đã render xong.")
    if len(set(job_ids)) != len(job_ids):
        raise HTTPException(status_code=400, detail="Danh sách scene bị trùng.")

    scene_dirs = []
    for job_id in job_ids:
        scene_job = queue.get(job_id)
        if (
            scene_job is None
            or scene_job.status != "done"
            or not scene_job.result
            or scene_job.result.get("renderer") != "whiteboard"
            or scene_job.output_dir is None
            or not (scene_job.output_dir / "output.mp4").is_file()
        ):
            raise HTTPException(status_code=400, detail=f"Scene {job_id} chưa render xong hoặc không phải whiteboard.")
        if not scene_job.output_dir.resolve().is_relative_to(RUNS_ROOT):
            raise HTTPException(status_code=400, detail=f"Scene {job_id} nằm ngoài thư mục job hợp lệ.")
        scene_dirs.append(str(scene_job.output_dir))

    merge_id = uuid.uuid4().hex[:12]
    output_dir = RUNS_ROOT / merge_id
    output_dir.mkdir(parents=True, exist_ok=True)
    job = queue.enqueue(
        {"mode": "merge-whiteboard", "outputDir": str(output_dir), "sceneDirs": scene_dirs,
         "format": format, "formatMode": formatMode},
        job_id=merge_id,
    )
    return _accepted([job])


@app.get("/api/whiteboard/download")
def download_whiteboard_scenes(jobIds: str) -> Response:
    try:
        ids = json.loads(jobIds)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=400, detail="Danh sách scene không hợp lệ.") from error
    if not isinstance(ids, list) or not ids or any(not isinstance(job_id, str) for job_id in ids):
        raise HTTPException(status_code=400, detail="Chọn ít nhất một scene để tải.")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for index, job_id in enumerate(ids, 1):
            job = queue.get(job_id)
            if (
                job is None
                or job.status != "done"
                or not job.result
                or job.result.get("renderer") != "whiteboard"
                or job.output_dir is None
            ):
                raise HTTPException(status_code=400, detail=f"Scene {job_id} chưa render xong.")
            video = job.output_dir / "output.mp4"
            if not video.is_file() or not job.output_dir.resolve().is_relative_to(RUNS_ROOT):
                raise HTTPException(status_code=400, detail=f"Thiếu video scene {job_id}.")
            name = job.result.get("sceneName") or job_id
            archive.write(video, f"{index:02d}-{name}.mp4")
    buffer.seek(0)
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="whiteboard-scenes.zip"'},
    )


@app.get("/api/jobs")
def list_jobs() -> list[dict]:
    return [queue.snapshot(job) for job in queue.list()]


@app.delete("/api/jobs")
def clear_jobs() -> dict:
    queue.clear()
    return {"cleared": True}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = queue.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")
    return queue.snapshot(job)


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str) -> StreamingResponse:
    job = queue.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")

    async def stream():
        last_version = -1
        while True:
            snap = queue.snapshot(job)
            if snap["version"] != last_version:
                last_version = snap["version"]
                if snap["status"] == "error":
                    yield _sse("error", {"message": snap["error"], "result": snap["result"]})
                    return
                yield _sse("stage", {
                    "stage": snap["stage"],
                    "progress": snap["progress"],
                    "label": snap["label"],
                    "queuePosition": snap["queuePosition"],
                    "result": snap["result"] if snap["stage"] == "flow" else None,
                })
                if snap["status"] == "done":
                    yield _sse("done", {"jobId": snap["jobId"], **(snap["result"] or {})})
                    return
            await asyncio.sleep(0.5)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/api/jobs/{job_id}/artifacts/{kind}")
def get_artifact(job_id: str, kind: str):
    job = queue.get(job_id)
    if job is None or kind not in ARTIFACT_FILES:
        raise HTTPException(status_code=404, detail="Không tìm thấy artifact.")
    path = artifact_path(job, kind)
    if path is None or not path.is_file() or not path.is_relative_to(RUNS_ROOT):
        raise HTTPException(status_code=404, detail="Artifact chưa sẵn sàng.")
    return FileResponse(path, filename=path.name)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


def main() -> None:
    import uvicorn

    from .._env import configure_cache, prepare_data_dir, startup_env
    configure_cache()
    startup_env()
    print(f"Dữ liệu  : {prepare_data_dir()}", flush=True)
    host = os.environ.get("STUDIO_HOST", "127.0.0.1")
    port = int(os.environ.get("STUDIO_PORT", "7860"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
