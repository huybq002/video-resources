from __future__ import annotations

import asyncio
import io
import json
import os
import re
import shutil
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .jobs import ARTIFACT_FILES, JobQueue, artifact_path
from ..tts import EDGE_VOICES
from ..whiteboard import whiteboard_root

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


@app.get("/api/fs/browse")
def browse_filesystem(path: str = "") -> dict:
    """Duyệt thư mục local cho ô chọn folder (tool chạy local, không cần upload)."""
    import os as _os
    import string as _string

    requested = (path or "").strip().strip('"')
    if not requested:
        drives = [f"{letter}:/" for letter in _string.ascii_uppercase if _os.path.exists(f"{letter}:\\")]
        return {"path": "", "parent": None, "dirs": drives, "drives": drives}
    current = Path(requested).expanduser()
    if not current.is_dir():
        raise HTTPException(status_code=400, detail=f"Đường dẫn không tồn tại: {current}")
    try:
        dirs = [
            str(entry) for entry in sorted(current.iterdir())
            if entry.is_dir() and not entry.name.startswith(".")
        ]
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=f"Không đọc được thư mục: {current}") from error
    parent = str(current.parent) if current.parent != current else None
    return {"path": str(current), "parent": parent, "dirs": dirs, "drives": []}


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
        "fpsOptions": [24, 30, 60],
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
    localFolder: str = Form(""),
) -> JSONResponse:
    if renderer not in ("hyperframes", "whiteboard"):
        raise HTTPException(status_code=400, detail="Video engine không hợp lệ.")
    if renderer == "whiteboard" and mode not in ("whiteboard-scenes", "whiteboard-folder", "preview-whiteboard"):
        raise HTTPException(status_code=400, detail="Whiteboard cần các scene được tải riêng.")
    if mode in ("whiteboard-scenes", "whiteboard-folder", "preview-whiteboard") and renderer != "whiteboard":
        raise HTTPException(status_code=400, detail="Scene riêng chỉ hỗ trợ engine Whiteboard.")

    def new_dir() -> tuple[str, Path]:
        rid = uuid.uuid4().hex[:12]
        run_dir = RUNS_ROOT / rid
        run_dir.mkdir(parents=True, exist_ok=True)
        return rid, run_dir

    if mode == "preview-whiteboard":
        if not isinstance(sceneImages, list) or not isinstance(sceneAnnotations, list) or not sceneImages or not sceneAnnotations:
            raise HTTPException(status_code=400, detail="Cần ảnh PNG và annotation để xem trước.")
        _, base = new_dir()
        image_path = base / Path(sceneImages[0].filename or "scene.png").name
        annotation_path = base / Path(sceneAnnotations[0].filename or "scene.annotation.json").name
        image_path.write_bytes(sceneImages[0].file.read())
        annotation_path.write_bytes(sceneAnnotations[0].file.read())
        job = queue.enqueue({
            "mode": "preview-whiteboard",
            "image": str(image_path),
            "annotation": str(annotation_path),
            "outputDir": str(base),
            "seconds": 10,
        })
        return _accepted([job])

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
                    "language": language,
                    "format": format,
                    "formatMode": formatMode,
                }, rid))
        jobs = queue.enqueue_many(job_entries)
        return _accepted(jobs)

    if mode == "whiteboard-folder":
        source_dir: Path | None = None
        if localFolder.strip():
            source_dir = Path(localFolder.strip()).expanduser()
            if not source_dir.is_dir():
                raise HTTPException(status_code=400, detail=f"Đường dẫn folder không tồn tại: {source_dir}")
        if not isinstance(files, list):
            files = []
        if not files and source_dir is None:
            raise HTTPException(status_code=400, detail="Chọn folder tải lên hoặc nhập đường dẫn folder trên máy.")
        from ..script_parse import parse_script

        _, base = new_dir()
        if source_dir is not None:
            shutil.copytree(source_dir, base, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
        else:
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
                "language": language,
                "format": format,
                "formatMode": formatMode,
            }, None))
        return _accepted(queue.enqueue_many(entries))

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
                    yield _sse("error", {"message": snap["error"]})
                    return
                yield _sse("stage", {
                    "stage": snap["stage"],
                    "progress": snap["progress"],
                    "label": snap["label"],
                    "queuePosition": snap["queuePosition"],
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

    from .._env import configure_cache
    configure_cache()
    host = os.environ.get("STUDIO_HOST", "127.0.0.1")
    port = int(os.environ.get("STUDIO_PORT", "7860"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
