"""Lưu/đọc flow JSON tại flows/<id>.flow.json và template tại flows/templates/."""
from __future__ import annotations

import json
import re
import shutil
import unicodedata
from pathlib import Path

from .._env import CODE_ROOT, data_root

FLOWS_ROOT = data_root() / "flows"
TEMPLATES_ROOT = CODE_ROOT / "flows" / "templates"  # template đi cùng code
_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def check_id(flow_id: str) -> str:
    if not _ID.match(flow_id or ""):
        raise ValueError("flow id chỉ gồm a-z, 0-9, '-' hoặc '_' (tối đa 64 ký tự).")
    return flow_id


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFD", name.lower().replace("đ", "d"))
    ascii_name = "".join(ch for ch in ascii_name if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")[:48]
    return slug or "flow"


def _path(flow_id: str) -> Path:
    return FLOWS_ROOT / f"{check_id(flow_id)}.flow.json"


def list_flows() -> list[dict]:
    items = []
    paths = sorted(FLOWS_ROOT.glob("*.flow.json")) if FLOWS_ROOT.is_dir() else []
    for path in paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        items.append({
            "id": path.name.removesuffix(".flow.json"),
            "name": data.get("name", path.stem),
            "engine": data.get("engine", ""),
        })
    return items


def read_flow(flow_id: str) -> dict:
    path = _path(flow_id)
    if not path.is_file():
        raise FileNotFoundError(flow_id)
    return json.loads(path.read_text(encoding="utf-8"))


def write_flow(flow_id: str, flow: dict) -> None:
    path = _path(flow_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**flow, "id": flow_id}, ensure_ascii=False, indent=2), encoding="utf-8")


def delete_flow(flow_id: str) -> None:
    path = _path(flow_id)
    if not path.is_file():
        raise FileNotFoundError(flow_id)
    path.unlink()
    delete_run(flow_id)


def read_template(template_id: str) -> dict:
    path = TEMPLATES_ROOT / f"{check_id(template_id)}.flow.json"
    if not path.is_file():
        raise FileNotFoundError(template_id)
    return json.loads(path.read_text(encoding="utf-8"))


def unique_id(base: str) -> str:
    candidate, n = base, 2
    while _path(candidate).exists():
        candidate, n = f"{base}-{n}", n + 1
    return candidate


def _run_path(flow_id: str) -> Path:
    return FLOWS_ROOT / ".runs" / f"{check_id(flow_id)}.json"


def write_run(flow_id: str, data: dict) -> None:
    """Lưu kết quả lần chạy gần nhất của flow (local) để mở lại vẫn thấy kết quả từng card."""
    path = _run_path(flow_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def read_run(flow_id: str) -> dict | None:
    path = _run_path(flow_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def run_output_dir(flow_id: str, run_id: str) -> Path:
    """Thư mục đầu ra của lần chạy mới; xóa đầu ra lần trước vì chỉ giữ kết quả gần nhất của mỗi flow."""
    base = FLOWS_ROOT / ".runs" / check_id(flow_id)
    if base.is_dir():
        shutil.rmtree(base, ignore_errors=True)
    path = base / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def delete_run(flow_id: str) -> None:
    path = _run_path(flow_id)
    if path.is_file():
        path.unlink()
    shutil.rmtree(FLOWS_ROOT / ".runs" / check_id(flow_id), ignore_errors=True)
