"""Ứng dụng desktop: mở Studio trong cửa sổ riêng (pywebview) thay vì trình duyệt.

Dùng chung toàn bộ server FastAPI và giao diện với bản web (`code2video-studio`); không đổi gì ở bản web.
Chạy: `code2video-desktop` hoặc `python -m code2video.desktop` (cần `pip install -e ".[desktop]"`).
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time

TITLE = "Code2Video Studio"
DEFAULT_PORT = 7870  # khác cổng bản web (7863) để chạy song song được


def pick_port(preferred: int) -> int:
    """Cổng ưu tiên nếu còn trống, ngược lại để hệ điều hành chọn một cổng trống."""
    for candidate in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", candidate))
            except OSError:
                continue
            return sock.getsockname()[1]
    raise RuntimeError("Không tìm được cổng trống.")


def start_server(port: int):
    """Chạy uvicorn trong thread nền; trả về (server, thread) sau khi server sẵn sàng."""
    import uvicorn

    from .studio.app import app

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, name="studio-server", daemon=True)
    thread.start()
    deadline = time.monotonic() + 60
    while not server.started:
        if not thread.is_alive():
            raise RuntimeError("Server Studio không khởi động được (xem lỗi ở trên).")
        if time.monotonic() > deadline:
            raise RuntimeError("Server Studio khởi động quá 60 giây.")
        time.sleep(0.05)
    return server, thread


def stop_server(server, thread) -> None:
    server.should_exit = True
    thread.join(timeout=10)


def redirect_streams_if_headless() -> Path | None:
    """Mở bằng pythonw/shortcut thì không có console (stdout/stderr = None) và uvicorn sẽ lỗi: ghi log ra file thay thế."""
    if sys.stdout is not None and sys.stderr is not None:
        return None
    from ._env import data_root

    log = data_root() / "desktop.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    stream = open(log, "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or stream
    sys.stderr = sys.stderr or stream
    return log


def main(argv: list[str] | None = None) -> int:
    redirect_streams_if_headless()
    parser = argparse.ArgumentParser(description="Code2Video Studio (desktop)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("DESKTOP_PORT", DEFAULT_PORT)))
    parser.add_argument("--check", action="store_true", help="khởi động server rồi thoát, để kiểm tra môi trường")
    parser.add_argument("--debug", action="store_true", help="bật công cụ debug của cửa sổ")
    args = parser.parse_args(argv)

    from ._env import configure_cache, prepare_data_dir, startup_env

    configure_cache()
    startup_env()  # nạp .env + đường dẫn công cụ để mở bằng shortcut vẫn thấy Whiteboard, ffmpeg...
    print(f"Dữ liệu : {prepare_data_dir()}", flush=True)
    port = pick_port(args.port)
    server, thread = start_server(port)
    url = f"http://127.0.0.1:{port}/"
    print(f"Studio  : {url}", flush=True)
    try:
        if args.check:
            import webview  # noqa: F401  (chỉ kiểm tra có cài)

            print("OK: server chạy và pywebview đã sẵn sàng.", flush=True)
            return 0
        try:
            import webview
        except ImportError:
            print('Thiếu pywebview. Cài: pip install -e ".[desktop]"  (hoặc pip install pywebview)', file=sys.stderr)
            return 1
        webview.settings["ALLOW_DOWNLOADS"] = True  # nút tải video/zip trong giao diện
        webview.create_window(TITLE, url, width=1400, height=900, min_size=(1000, 650))
        webview.start(debug=args.debug)  # chặn tới khi đóng cửa sổ
        return 0
    finally:
        stop_server(server, thread)


if __name__ == "__main__":
    raise SystemExit(main())
