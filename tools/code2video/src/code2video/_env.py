from __future__ import annotations

import os
from pathlib import Path


def configure_cache() -> None:
    """Trỏ cache model HuggingFace vào repo (H:) thay vì C:, và tắt cảnh báo symlink Windows.

    Chỉ set khi chưa được cấu hình sẵn để không ghi đè chủ ý của người dùng.
    """
    project_root = Path(__file__).resolve().parents[2]
    cache = project_root / ".cache" / "huggingface"
    os.environ.setdefault("HF_HOME", str(cache))
    os.environ.setdefault("HF_HUB_CACHE", str(cache / "hub"))
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


CODE_ROOT = Path(__file__).resolve().parents[2]


def main_repo_root(code_root: Path = CODE_ROOT) -> Path:
    """Thư mục repo chính; trong git worktree, `.git` là file trỏ về <repo>/.git/worktrees/<tên>."""
    git = code_root / ".git"
    if git.is_file():
        text = git.read_text(encoding="utf-8").strip()
        if text.startswith("gitdir:"):
            gitdir = Path(text.split(":", 1)[1].strip())
            if gitdir.parent.name == "worktrees":
                return gitdir.parents[2]
    return code_root


def data_root() -> Path:
    """Nơi lưu settings, skill, flow, kết quả: cố định dù chạy từ repo chính hay worktree nào."""
    override = os.environ.get("STUDIO_DATA_DIR")
    return Path(override).resolve() if override else main_repo_root() / ".studio-data"


def prepare_data_dir(code_root: Path = CODE_ROOT, root: Path | None = None) -> Path:
    """Tạo thư mục dữ liệu (tự gitignore) và sao chép dữ liệu cũ nằm trong thư mục code nếu chưa có."""
    import shutil

    root = root or data_root()
    root.mkdir(parents=True, exist_ok=True)
    ignore = root / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n", encoding="utf-8")
    old_settings = code_root / "settings"
    if (old_settings / "ai.json").is_file() and not (root / "settings" / "ai.json").exists():
        shutil.copytree(old_settings, root / "settings", dirs_exist_ok=True)
    (root / "flows").mkdir(exist_ok=True)
    for old in (code_root / "flows").glob("*.flow.json"):
        if not (root / "flows" / old.name).exists():
            shutil.copy2(old, root / "flows" / old.name)
    return root


def load_dotenv(*files: Path) -> list[str]:
    """Nạp file .env (KEY=VALUE, bỏ dòng trống và #) mà không ghi đè biến đã có sẵn; trả về các khóa đã nạp."""
    loaded: list[str] = []
    for file in files:
        if not file.is_file():
            continue
        for line in file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key.replace("_", "").isalnum() and key not in os.environ:
                os.environ[key] = value
                loaded.append(key)
    return loaded


def startup_env() -> None:
    """Chuẩn bị môi trường khi mở app: .env (thư mục code, rồi repo chính) rồi cấu hình đường dẫn đã lưu trong Settings."""
    from . import tools_config

    load_dotenv(CODE_ROOT / ".env", main_repo_root() / ".env")
    tools_config.apply_to_env()
