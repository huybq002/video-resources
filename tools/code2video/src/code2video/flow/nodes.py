"""Registry các node của flow; mỗi node: (state, config, ctx) -> dict (ghi đè state[id])."""
from __future__ import annotations

import json
import re
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from ..ai_client import AiClientError, chat_json, generate_image
from ..ai_script import clean_characters, demo_script, parse_script_payload, system_prompt, user_prompt
from ..ai_settings import load as load_ai_settings
from ..whiteboard_assets import build_scene_folder, estimate_dur_ms, fmt_time
from .conditions import MISSING, lookup

HTML_SYSTEM_PROMPT = (
    "Bạn dựng video HyperFrames 1920x1080 từ kịch bản. Trả về DUY NHẤT JSON "
    '{"files": {"index.html": "<html>", "assets/<tên>.svg": "<svg>"}}. '
    "index.html: root div#root có data-composition-id, data-width=1920, data-height=1080, data-start=0, "
    "data-duration=<tổng giây>; mọi phần tử có thời lượng là class=\"clip\" + data-start + data-duration (giây); "
    "GSAP timeline paused:true đăng ký window.__timelines[<id>]; không Date.now/Math.random/fetch/setTimeout/repeat:-1; "
    "mỗi cảnh có nền + nhân vật SVG + chuyển động; phụ đề ở 1/3 dưới; asset path assets/...; không thêm <audio>. "
    "Giọng đọc ĐÃ được thu sẵn: mỗi cue trong đầu vào có startSec/endSec thật. Phải dùng ĐÚNG các mốc này cho "
    "data-start, data-duration và thời điểm GSAP (hiện phụ đề/cảnh đúng lúc cue được đọc); tổng thời lượng "
    "data-duration của root phải bằng durationSeconds. Nếu cue có trường speaker (nhiều nhân vật): hiển thị tên "
    "nhân vật đang nói, dùng màu/vị trí riêng cho từng nhân vật."
)


@dataclass
class FlowContext:
    run_dir: Path
    engine: str = "whiteboard"
    tts_lock: object = field(default_factory=threading.Lock)
    max_render_workers: int = 3


def _ctx(ctx: object | None) -> FlowContext:
    if not isinstance(ctx, FlowContext):
        raise RuntimeError("Node cần FlowContext (thư mục chạy).")
    return ctx


def _of(state: dict, node_type: str) -> dict:
    """Đầu ra của card thuộc loại node_type (không phụ thuộc id card người dùng đặt)."""
    return (state.get("_types") or {}).get(node_type) or {}


def _need(state: dict, path: str, label: str):
    value = lookup(state, path)
    if value is MISSING or value in (None, "", []):
        raise ValueError(f"Thiếu dữ liệu '{label}' ({path}); node trước đó chưa chạy hoặc lỗi.")
    return value


def node_idea(state: dict, config: dict, ctx) -> dict:
    topic = str(config.get("text") or state.get("topic") or "").strip()
    if not topic:
        raise ValueError("Card Ý tưởng chưa có nội dung.")
    return {
        "topic": topic,
        "language": config.get("language") or "vi",
        "minutes": float(config.get("minutes") or 3),
        "_global": {"topic": topic},
    }


def node_skill(state: dict, config: dict, ctx) -> dict:
    """Gộp 1-4 skill (system prompt) cho các card AI phía sau, theo thứ tự đã chọn."""
    ids = list(config.get("skills") or ([config["skill"]] if config.get("skill") else []))
    if not ids:
        raise ValueError("Chưa chọn skill nào.")
    if len(ids) > 4:
        raise ValueError("Chỉ dùng tối đa 4 skill cùng lúc.")
    settings = load_ai_settings()
    chosen = []
    for sid in ids:
        skill = settings.skills.get(sid)
        if skill is None:
            raise ValueError(f"Skill '{sid}' không còn trong Settings (đã bị xóa?). Chọn hoặc tải lại skill.")
        chosen.append(skill)
    content = "\n\n".join(f"## {s.name}\n{s.content}" if len(chosen) > 1 else s.content for s in chosen)
    names = ", ".join(s.name for s in chosen)
    return {"skillIds": [s.id for s in chosen], "name": names, "chars": len(content),
            "_global": {"_skill": {"id": "+".join(s.id for s in chosen), "name": names, "content": content}}}


def node_ai_script(state: dict, config: dict, ctx) -> dict:
    """Lỗi model/JSON được ghi vào output.error (không ném) để dây điều kiện retry bắt được."""
    idea = _of(state, "idea")
    topic = str(state.get("topic") or "").strip()
    if not topic:
        raise ValueError("Thiếu topic; cần card Ý tưởng trước ai-script.")
    language = idea.get("language", "vi")
    minutes = float(idea.get("minutes", 3))
    provider_id = config.get("provider") or "demo"
    characters = clean_characters(config.get("characters"))
    try:
        if provider_id == "demo":
            payload = demo_script(topic, language, minutes, characters)
        else:
            settings = load_ai_settings()
            provider = settings.providers.get(provider_id)
            if provider is None:
                raise ValueError(f"Provider {provider_id} không tồn tại trong Settings.")
            upstream = state.get("_skill")  # card Skill phía trước được ưu tiên
            if upstream:
                base_content = upstream["content"]
            else:
                skill = settings.skills.get(config.get("skill") or "") or settings.skills.get("whiteboard")
                base_content = skill.content if skill else ""
            content = base_content + ("\n" + config["prompt"] if config.get("prompt") else "")
            payload = chat_json(provider, [
                {"role": "system", "content": system_prompt(content, language, characters)},
                {"role": "user", "content": user_prompt(topic, language, minutes, characters)},
            ])
        return {"scenes": parse_script_payload(payload, characters)["scenes"], "characters": characters}
    except AiClientError as error:
        if error.fatal:  # 4xx (key sai, model đã gỡ): thử lại vô ích, dừng ngay với lỗi thật
            raise
        return {"error": str(error)}
    except ValueError as error:
        return {"error": str(error)}


def _speakers(scene: dict) -> list[str] | None:
    """Danh sách người nói theo cue, hoặc None nếu kịch bản chỉ có một người dẫn."""
    names = [c.get("speaker", "") for c in scene["cues"]]
    return names if any(names) else None


def node_build_scenes(state: dict, config: dict, ctx) -> dict:
    ctx = _ctx(ctx)
    scenes = _need(state, "_types.ai-script.scenes", "kịch bản")
    language = _of(state, "idea").get("language", "vi")
    dirs, images = [], []
    for index, scene in enumerate(scenes, 1):
        sid = f"scene-{index:02d}"
        items = [(c["doodle"], c["label"], c["text"]) for c in scene["cues"]]
        build_scene_folder(ctx.run_dir / "scenes" / sid, sid, scene["title"], items, language, speakers=_speakers(scene))
        dirs.append(str(ctx.run_dir / "scenes" / sid))
        images.append(str(ctx.run_dir / "scenes" / sid / f"{sid}.png"))
    return {"dirs": dirs, "images": images, "_global": {"resources": dirs}}


IMAGE_STYLE = (
    "Hand-drawn whiteboard doodle illustration, black marker lines with red accents, plain off-white paper "
    "background, simple icons, no photographic realism, no watermark."
)


def _image_prompt(scene: dict, config: dict) -> str:
    n = len(scene["cues"])
    cols = 3 if n > 4 else (2 if n > 1 else 1)
    rows = -(-n // cols)
    panels = "; ".join(f"panel {i} (reading order): {c['label']} - {c['text']}" for i, c in enumerate(scene["cues"], 1))
    extra = (" " + config["prompt"]) if config.get("prompt") else ""
    return (f"{IMAGE_STYLE} 16:9 composition for the scene \"{scene['title']}\". Arrange exactly {n} separate "
            f"drawings in a {cols}x{rows} grid (columns x rows), evenly spaced with margins, left-to-right then "
            f"top-to-bottom, with a short label under each. {panels}.{extra}")


def node_ai_image(state: dict, config: dict, ctx) -> dict:
    """AI tự vẽ ảnh từng scene (không dùng bộ doodle của app); lỗi API ghi vào output.error để retry bằng dây điều kiện."""
    from io import BytesIO

    from PIL import Image

    ctx = _ctx(ctx)
    scenes = _need(state, "_types.ai-script.scenes", "kịch bản")
    language = _of(state, "idea").get("language", "vi")
    provider = load_ai_settings().providers.get(config.get("provider") or "")
    if provider is None:
        return {"error": f"Card AI tạo ảnh cần provider thật trong Settings (hiện: '{config.get('provider') or ''}')."}
    dirs, images = [], []
    try:
        for index, scene in enumerate(scenes, 1):
            sid = f"scene-{index:02d}"
            raw = generate_image(provider, _image_prompt(scene, config), size=str(config.get("size") or ""))
            try:
                picture = Image.open(BytesIO(raw))
                picture.load()
            except Exception as error:  # ảnh hỏng/không phải ảnh
                raise AiClientError(f"Dữ liệu ảnh scene {index} không đọc được ({error})") from error
            items = [("question", c["label"], c["text"]) for c in scene["cues"]]
            folder = ctx.run_dir / "scenes" / sid
            build_scene_folder(folder, sid, scene["title"], items, language, image=picture, speakers=_speakers(scene))
            dirs.append(str(folder))
            images.append(str(folder / f"{sid}.png"))
    except AiClientError as error:
        if error.fatal:
            raise
        return {"error": str(error)}
    return {"dirs": dirs, "images": images, "_global": {"resources": dirs}}


def _srt_from_scenes(scenes: list, language: str) -> tuple[str, int]:
    blocks, t, seq = [], 0, 1
    for scene in scenes:
        for cue in scene["cues"]:
            dur = estimate_dur_ms(cue["text"], language)
            blocks.append(f"{seq}\n{fmt_time(t)} --> {fmt_time(t + dur)}\n{cue['text']}\n")
            t += dur
            seq += 1
    return "\n".join(blocks), t


_SAFE_FILE = re.compile(r"^(index\.html|assets/[\w\-./]+)$")


def _timed_scenes(scenes: list, timeline: dict) -> list:
    """Gắn startSec/endSec thật (từ giọng đọc) vào từng cue của từng cảnh."""
    cues, i, timed = timeline["cues"], 0, []
    for scene in scenes:
        items = []
        for cue in scene["cues"]:
            real = cues[i] if i < len(cues) else cues[-1]
            items.append({**cue, "startSec": round(real["startMs"] / 1000, 2), "endSec": round(real["endMs"] / 1000, 2)})
            i += 1
        timed.append({"title": scene["title"], "cues": items})
    return timed


def _script_syntax_error(html: str) -> str | None:
    """Kiểm tra cú pháp các <script> nội tuyến bằng `node --check`: lỗi (vd khai báo trùng biến) làm trang không chạy,
    video render ra khung trống mà renderer vẫn báo thành công."""
    import subprocess
    import tempfile

    node = shutil.which("node")
    if node is None:
        return None
    for index, body in enumerate(re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", html, re.S | re.I), 1):
        if not body.strip():
            continue
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inline.js"
            path.write_text(body, encoding="utf-8")
            result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            detail = [line for line in result.stderr.splitlines() if "Error" in line]
            return f"Script #{index} trong index.html bị lỗi cú pháp: {(detail[-1] if detail else result.stderr.strip())[:200]}"
    return None


def _root_duration(html: str) -> float | None:
    for tag in re.findall(r"<[^>]*data-composition-id[^>]*>", html):
        match = re.search(r'data-duration="([\d.]+)"', tag)
        if match:
            return float(match.group(1))
    return None


def node_ai_html(state: dict, config: dict, ctx) -> dict:
    """LLM sinh index.html + assets vào project của bước Giọng đọc, theo mốc thời gian thật; lỗi hợp đồng ghi vào output.error."""
    ctx = _ctx(ctx)
    scenes = _need(state, "_types.ai-script.scenes", "kịch bản")
    project = Path(_need(state, "_types.tts.project", "project từ bước Giọng đọc (Giọng đọc phải chạy trước AI dựng HTML)"))
    timeline = json.loads((project / "timeline.json").read_text(encoding="utf-8"))
    total_seconds = round(timeline["durationMs"] / 1000, 2)
    provider_id = config.get("provider") or ""
    provider = load_ai_settings().providers.get(provider_id)
    if provider is None:
        return {"error": f"Card ai-html cần provider thật trong Settings (hiện: '{provider_id}')."}
    request = {"durationSeconds": total_seconds, "scenes": _timed_scenes(scenes, timeline)}
    previous = _of(state, "ai-html").get("error")
    if previous:  # vòng thử lại: cho AI biết lần trước sai ở đâu
        request["lastAttemptError"] = f"Bản trước bị từ chối: {previous}. Hãy sửa đúng lỗi này."
    try:
        payload = chat_json(provider, [
            {"role": "system", "content": HTML_SYSTEM_PROMPT + ("\n" + config["prompt"] if config.get("prompt") else "")},
            {"role": "user", "content": json.dumps(request, ensure_ascii=False)},
        ], timeout=300)
        files = payload.get("files")
        if not isinstance(files, dict) or "index.html" not in files:
            raise ValueError("Model không trả về files.index.html.")
        html = str(files["index.html"])
        if "data-composition-id" not in html or "__timelines" not in html:
            raise ValueError("index.html thiếu data-composition-id hoặc window.__timelines.")
        syntax = _script_syntax_error(html)
        if syntax:
            raise ValueError(syntax)
        duration = _root_duration(html)
        if duration is None or abs(duration - total_seconds) > 2.0:
            raise ValueError(f"data-duration của root là {duration}, phải khớp giọng đọc ({total_seconds} giây).")
        for name in files:
            if not _SAFE_FILE.match(name) or ".." in name:
                raise ValueError(f"Đường dẫn file không hợp lệ: {name}")
        missing = sorted(set(re.findall(r"assets/[\w\-./]+\.\w+", html)) - set(files))  # ảnh/svg HTML gọi tới nhưng AI không tạo
        if missing:
            raise ValueError("index.html tham chiếu file chưa được tạo: " + ", ".join(missing[:5]))
        for name, content in files.items():
            target = project / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(content), encoding="utf-8")
    except AiClientError as error:
        if error.fatal:  # 4xx (key sai, model đã gỡ): thử lại vô ích, dừng ngay với lỗi thật
            raise
        return {"error": str(error)}
    except ValueError as error:
        return {"error": str(error)}
    return {"dir": str(project), "_global": {"project": str(project)}}


def _tts_for(config: dict, language: str):
    from ..studio import engines
    from ..tts import VieNeuAdapter

    voice = config.get("voice") or None
    tts = engines.get_tts(bool(config.get("dryRun")), config.get("ttsMode", "v3turbo"), language, voice)
    if isinstance(tts, VieNeuAdapter):
        tts.voice = voice
    return tts


def _voice_map(config: dict) -> dict:
    """{tên nhân vật: giọng}; khóa "" là giọng mặc định cho người nói chưa gán giọng."""
    voices = {str(k): str(v) for k, v in (config.get("speakers") or {}).items() if v}
    if config.get("voice") and voices:
        voices[""] = str(config["voice"])
    return voices


def node_tts(state: dict, config: dict, ctx) -> dict:
    ctx = _ctx(ctx)
    language = _of(state, "idea").get("language", "vi")
    voices = _voice_map(config)
    done = []
    extra: dict = {}
    with ctx.tts_lock:
        tts = _tts_for(config, language)
        if ctx.engine == "whiteboard":
            from ..voiceover import build_whiteboard_from_script
            from ..whiteboard import apply_windows_to_annotations

            for folder in _need(state, "resources", "thư mục scene"):
                stats = build_whiteboard_from_script(
                    Path(folder), Path(folder) / "script.srt", tts, voices, language=language)
                apply_windows_to_annotations(Path(folder), stats["windows"])
                done.append(folder)
        else:
            extra = _tts_hyperframes(state, tts, ctx, voices, language)
            done.append(extra["project"])
    out = {"dirs": done, **extra}
    if "project" in extra:
        out["_global"] = {"project": extra["project"]}
    return out


def _tts_hyperframes(state: dict, tts, ctx: FlowContext, voices: dict | None = None, language: str = "vi") -> dict:
    """HyperFrames: đọc cả kịch bản trước (nhịp tự nhiên, nhiều giọng theo nhân vật) để có mốc thời gian thật."""
    from ..voiceover import build_whiteboard_from_script

    scenes = _need(state, "_types.ai-script.scenes", "kịch bản")
    project = ctx.run_dir / "project"
    project.mkdir(parents=True, exist_ok=True)
    cues = [cue for scene in scenes for cue in scene["cues"]]
    script = project / "script.txt"
    if any(c.get("speaker") for c in cues):  # định dạng đa nhân vật; mốc giả chỉ để đúng thứ tự, thời lượng thật do giọng đọc quyết định
        script.write_text("\n\n".join(f"[{c.get('speaker') or 'Người dẫn'}][{fmt_time(i * 1000)} --> {fmt_time(i * 1000 + 900)}]: {c['text']}"
                                       for i, c in enumerate(cues)), encoding="utf-8")
    else:
        script.write_text("\n".join(c["text"] for c in cues), encoding="utf-8")
    stats = build_whiteboard_from_script(project, script, tts, voices or {}, language=language)
    timeline = json.loads(Path(stats["timeline"]).read_text(encoding="utf-8"))
    real = timeline["cues"]
    blocks = [f"{i}\n{fmt_time(c['startMs'])} --> {fmt_time(c['endMs'])}\n{c['text']}\n" for i, c in enumerate(real, 1)]
    (project / "script.srt").write_text("\n".join(blocks), encoding="utf-8")
    return {"project": str(project), "durationSeconds": round(timeline["durationMs"] / 1000, 2), "cues": len(real),
            "speakers": stats.get("speakers", [])}


def _mux_voiceover(project: Path, video: Path) -> None:
    """Composition do AI viết không có thẻ <audio>, nên video render ra im lặng: ghép voiceover.wav vào video."""
    import subprocess

    voice = project / "voiceover.wav"
    html = project / "index.html"
    if not voice.is_file() or (html.is_file() and "<audio" in html.read_text(encoding="utf-8", errors="ignore")):
        return
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("Cần ffmpeg trong PATH để ghép giọng đọc vào video HyperFrames.")
    muxed = video.with_name("muxed.mp4")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-i", str(voice), "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-shortest", str(muxed)], check=True)
    muxed.replace(video)


def node_render(state: dict, config: dict, ctx) -> dict:
    ctx = _ctx(ctx)
    from ..pipeline import apply_format, render_hyperframes

    fps = config.get("fps")
    fmt, mode = config.get("format"), config.get("formatMode", "fit")
    if ctx.engine == "whiteboard":
        from ..whiteboard import render_whiteboard

        dirs = [Path(d) for d in _need(state, "resources", "thư mục scene")]

        def one(folder: Path) -> str:
            video = folder / "output.mp4"
            render_whiteboard(folder, video, fps=min(int(fps), 60) if fps else None, long_edge=int(config.get("longEdge") or 0) or None)
            apply_format(video, fmt, mode)
            return str(video)

        with ThreadPoolExecutor(max_workers=max(1, ctx.max_render_workers)) as pool:
            videos = list(pool.map(one, dirs))
    else:
        project = Path(_need(state, "project", "project HyperFrames"))
        video = project / "output.mp4"
        render_hyperframes(project, video, fps=fps, quality=config.get("quality") or None)
        _mux_voiceover(project, video)
        apply_format(video, fmt, mode)
        videos = [str(video)]
    out: dict = {"videos": videos}
    if len(videos) == 1:
        out["_global"] = {"video": videos[0]}
    return out


def node_merge(state: dict, config: dict, ctx) -> dict:
    ctx = _ctx(ctx)
    from ..pipeline import apply_format
    from ..whiteboard import merge_whiteboard_scenes

    videos = _need(state, "_types.render.videos", "video từng scene")
    out = ctx.run_dir / "output.mp4"
    if len(videos) == 1:
        shutil.copyfile(videos[0], out)
    else:
        merge_whiteboard_scenes([Path(v).parent for v in videos], out)
    apply_format(out, config.get("format"), config.get("formatMode", "fit"))
    return {"video": str(out), "_global": {"video": str(out)}}


NODES = {
    "idea": node_idea,
    "skill": node_skill,
    "ai-image": node_ai_image,
    "ai-script": node_ai_script,
    "build-scenes": node_build_scenes,
    "ai-html": node_ai_html,
    "tts": node_tts,
    "render": node_render,
    "merge": node_merge,
}
ENGINE_NODES = {
    "whiteboard": {"idea", "skill", "ai-script", "build-scenes", "ai-image", "tts", "render", "merge"},
    "hyperframes": {"idea", "skill", "ai-script", "ai-html", "tts", "render"},
}
