"""Mở Code2Video Studio dạng ứng dụng desktop, không hiện cửa sổ console (double-click hoặc dùng shortcut)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from code2video.desktop import main  # noqa: E402

raise SystemExit(main())
