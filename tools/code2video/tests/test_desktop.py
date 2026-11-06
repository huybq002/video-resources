import socket

import httpx

from code2video import desktop


def test_pick_port_prefers_free_port_and_falls_back_when_busy():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
        busy.bind(("127.0.0.1", 0))
        taken = busy.getsockname()[1]
        chosen = desktop.pick_port(taken)  # cổng ưu tiên đang bị chiếm -> chọn cổng khác
        assert chosen != taken and chosen > 0
    free = desktop.pick_port(taken)  # đã giải phóng -> dùng đúng cổng ưu tiên
    assert free == taken


def test_server_starts_serves_the_web_ui_and_stops_cleanly():
    port = desktop.pick_port(0)
    server, thread = desktop.start_server(port)
    try:
        page = httpx.get(f"http://127.0.0.1:{port}/", trust_env=False, timeout=10)
        assert page.status_code == 200 and "Code2Video" in page.text
        assert httpx.get(f"http://127.0.0.1:{port}/api/flow/rules", trust_env=False, timeout=10).status_code == 200
    finally:
        desktop.stop_server(server, thread)
    assert not thread.is_alive()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        assert probe.connect_ex(("127.0.0.1", port)) != 0  # cổng đã đóng


def test_headless_launch_logs_to_file_instead_of_crashing(tmp_path, monkeypatch):
    import sys

    monkeypatch.setenv("STUDIO_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    log = desktop.redirect_streams_if_headless()
    try:
        assert log == tmp_path / "desktop.log" and sys.stdout is not None and sys.stderr is not None
        print("ghi vào log")
        sys.stdout.flush()
    finally:
        sys.stdout.close()
    assert "ghi vào log" in log.read_text(encoding="utf-8")


def test_console_launch_keeps_the_real_streams(monkeypatch):
    assert desktop.redirect_streams_if_headless() is None


def test_dotenv_loader_does_not_override_existing_env_and_ignores_comments(tmp_path, monkeypatch):
    from code2video._env import load_dotenv

    env = tmp_path / ".env"
    env.write_text('# ghi chú\nA_KEY=1\nB_KEY="hai"\nEXISTING=moi\nbad line\n', encoding="utf-8")
    monkeypatch.setenv("EXISTING", "cu")
    monkeypatch.delenv("A_KEY", raising=False)
    monkeypatch.delenv("B_KEY", raising=False)
    assert load_dotenv(env, tmp_path / "missing.env") == ["A_KEY", "B_KEY"]
    import os

    assert os.environ["A_KEY"] == "1" and os.environ["B_KEY"] == "hai" and os.environ["EXISTING"] == "cu"
    monkeypatch.delenv("A_KEY")
    monkeypatch.delenv("B_KEY")


def _fake_whiteboard(tmp_path):
    root = tmp_path / "wb"
    (root / "scripts").mkdir(parents=True)
    for name in ("render_stream_whiteboard.py", "merge_scenes.py"):
        (root / "scripts" / name).write_text("", encoding="utf-8")
    return root


def test_tool_paths_validate_save_and_apply_immediately(tmp_path, monkeypatch):
    import asyncio
    import os

    from fastapi import HTTPException

    from code2video.studio import app as studio

    monkeypatch.setenv("STUDIO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("WHITEBOARD_ROOT", raising=False)
    monkeypatch.delenv("WHITEBOARD_PYTHON", raising=False)

    class Body:
        def __init__(self, payload):
            self.payload = payload

        async def json(self):
            return self.payload

    with __import__("pytest").raises(HTTPException) as err:
        asyncio.run(studio.put_tools(Body({"WHITEBOARD_ROOT": str(tmp_path / "khong-co")})))
    assert err.value.status_code == 400 and "WHITEBOARD_ROOT" in err.value.detail
    with __import__("pytest").raises(HTTPException):  # thư mục có thật nhưng không phải whiteboard
        asyncio.run(studio.put_tools(Body({"WHITEBOARD_ROOT": str(tmp_path)})))
    root = _fake_whiteboard(tmp_path)
    result = asyncio.run(studio.put_tools(Body({"WHITEBOARD_ROOT": str(root), "WHITEBOARD_PYTHON": ""})))
    assert result["whiteboardReady"] is True and os.environ["WHITEBOARD_ROOT"] == str(root) and result["problems"] == {}
    assert studio.get_tools()["saved"] == {"WHITEBOARD_ROOT": str(root)}
    cleared = asyncio.run(studio.put_tools(Body({"WHITEBOARD_ROOT": "", "WHITEBOARD_PYTHON": ""})))  # để trống = bỏ cấu hình
    assert "WHITEBOARD_ROOT" not in os.environ and cleared["whiteboardReady"] is False and cleared["saved"] == {}
