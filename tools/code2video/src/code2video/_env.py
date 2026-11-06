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
