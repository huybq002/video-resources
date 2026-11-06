"""Đường dẫn tới phần mềm bên ngoài (Whiteboard...), lưu local và áp dụng ngay không cần khởi động lại.

Ưu tiên: giá trị lưu trong Settings (tools.json) > biến môi trường/.env.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from ._env import data_root

KEYS = ("WHITEBOARD_ROOT", "WHITEBOARD_PYTHON")
_ROOT_FILES = ("scripts/render_stream_whiteboard.py", "scripts/merge_scenes.py")


def _file() -> Path:
    return data_root() / "settings" / "tools.json"


def load() -> dict[str, str]:
    try:
        data = json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {k: str(data[k]) for k in KEYS if isinstance(data.get(k), str) and data[k].strip()}


def validate(values: dict[str, str]) -> dict[str, str]:
    """Lỗi theo từng khóa (rỗng = hợp lệ). Giá trị rỗng nghĩa là bỏ cấu hình."""
    problems: dict[str, str] = {}
    root = str(values.get("WHITEBOARD_ROOT") or "").strip()
    if root:
        path = Path(root).expanduser()
        if not path.is_dir():
            problems["WHITEBOARD_ROOT"] = "Thư mục không tồn tại."
        else:
            missing = [f for f in _ROOT_FILES if not (path / f).is_file()]
            if missing:
                problems["WHITEBOARD_ROOT"] = "Không phải thư mục srt-whiteboard-animation (thiếu " + ", ".join(missing) + ")."
    python = str(values.get("WHITEBOARD_PYTHON") or "").strip()
    if python and not Path(python).expanduser().is_file():
        problems["WHITEBOARD_PYTHON"] = "Không tìm thấy file python này."
    return problems


def save(values: dict[str, str]) -> None:
    clean = {k: str(values.get(k) or "").strip() for k in KEYS}
    path = _file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({k: v for k, v in clean.items() if v}, ensure_ascii=False, indent=2), encoding="utf-8")


def apply_to_env(values: dict[str, str] | None = None) -> None:
    """Đưa cấu hình đã lưu vào os.environ (các module đọc os.environ mỗi lần gọi nên có hiệu lực ngay)."""
    saved = load() if values is None else {k: v for k, v in values.items() if v}
    for key in KEYS:
        if key in saved:
            os.environ[key] = saved[key]


def clear_from_env(keys) -> None:
    for key in keys:
        os.environ.pop(key, None)


def effective() -> dict[str, str]:
    return {k: os.environ.get(k, "") for k in KEYS}


def tools_present() -> dict[str, str | None]:
    return {name: shutil.which(name) for name in ("ffmpeg", "ffprobe", "node", "npx")}
