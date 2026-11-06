"""Lưu trữ file người dùng upload (skill) tại settings/uploads — hoàn toàn local, có thể liệt kê và xóa."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path

from . import ai_settings

MAX_SKILL_BYTES = 200 * 1024
MAX_SKILL_FILES = 4
SKILL_EXTENSIONS = {".md", ".markdown", ".txt"}
_SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,79}$")


def skills_dir() -> Path:
    return ai_settings.UPLOADS_ROOT / "skills"


def slugify(name: str) -> str:
    text = unicodedata.normalize("NFD", name.lower().replace("đ", "d"))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:48] or "skill"


def save_skill_file(filename: str, data: bytes, display_name: str = "") -> ai_settings.Skill:
    """Lưu file skill vào uploads và đăng ký skill (id duy nhất) vào ai.json."""
    ext = Path(filename or "").suffix.lower()
    if ext not in SKILL_EXTENSIONS:
        raise ValueError("Chỉ nhận file .md, .markdown hoặc .txt.")
    if not data:
        raise ValueError("File rỗng.")
    if len(data) > MAX_SKILL_BYTES:
        raise ValueError(f"File quá lớn (tối đa {MAX_SKILL_BYTES // 1024} KB).")
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("File phải mã hóa UTF-8.") from error
    if not content.strip():
        raise ValueError("File chỉ chứa khoảng trắng.")
    existing = [p for p in skills_dir().glob("*") if p.is_file()] if skills_dir().is_dir() else []
    if len(existing) >= MAX_SKILL_FILES:
        raise ValueError(f"Đã có {MAX_SKILL_FILES} skill upload (tối đa). Xóa bớt ở Settings → Tệp đã tải lên.")
    settings = ai_settings.load()
    stem = slugify(Path(filename).stem)
    skill_id, n = stem, 2
    while skill_id in settings.skills or (skills_dir() / f"{skill_id}{ext}").exists():
        skill_id, n = f"{stem}-{n}", n + 1
    skills_dir().mkdir(parents=True, exist_ok=True)
    stored = f"{skill_id}{ext}"
    (skills_dir() / stored).write_bytes(data)
    skill = ai_settings.Skill(
        id=skill_id, name=(display_name.strip() or Path(filename).stem), content=content, source=stored)
    settings.skills[skill_id] = skill
    ai_settings.save(settings)
    return skill


def list_files() -> list[dict]:
    """Danh sách file đã upload + skill đang dùng chúng."""
    settings = ai_settings.load()
    users: dict[str, list[str]] = {}
    for skill in settings.skills.values():
        if skill.source:
            users.setdefault(skill.source, []).append(skill.name)
    items = []
    root = skills_dir()
    for path in sorted(root.glob("*")) if root.is_dir() else []:
        if not path.is_file():
            continue
        stat = path.stat()
        items.append({
            "kind": "skills",
            "name": path.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "usedBy": users.get(path.name, []),
        })
    return items


def delete_file(kind: str, name: str) -> list[str]:
    """Xóa file upload; skill gắn với file cũng bị gỡ khỏi settings. Trả về id skill đã gỡ."""
    if kind != "skills" or not _SAFE_NAME.match(name or ""):
        raise ValueError("Tên file hoặc loại file không hợp lệ.")
    path = skills_dir() / name
    if not path.is_file():
        raise FileNotFoundError(name)
    path.unlink()
    settings = ai_settings.load()
    removed = [sid for sid, skill in settings.skills.items() if skill.source == name]
    for sid in removed:
        ai_settings.delete_skill(settings, sid)
    if removed:
        ai_settings.save(settings)
    return removed
