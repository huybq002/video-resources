#!/usr/bin/env bash
# Chạy Code2Video Studio. Dùng: ./start.sh   (ghi đè bằng biến môi trường, ví dụ STUDIO_PORT=8000 ./start.sh)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# --- nạp .env (project, rồi repo gốc khi chạy từ worktree); không ghi đè biến đã export, không `source` để tránh chạy code ---
load_env() {
  local file line key val
  for file in "$@"; do
    [ -f "$file" ] || continue
    while IFS= read -r line || [ -n "$line" ]; do
      line="${line%$'\r'}"
      case "$line" in ''|\#*) continue ;; esac
      key="${line%%=*}"; val="${line#*=}"
      [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
      val="${val%\"}"; val="${val#\"}"
      if [ -z "${!key+x}" ]; then export "$key=$val"; fi
    done < "$file"
  done
}
MAIN_ROOT="$ROOT"
if common="$(git -C "$ROOT" rev-parse --git-common-dir 2>/dev/null)"; then
  MAIN_ROOT="$(cd "$ROOT" && cd "$(dirname "$common")" && pwd)"
fi
load_env "$ROOT/.env" "$MAIN_ROOT/.env"

# --- tìm Python trong venv: .venv của project, rồi .venv của repo gốc (khi chạy từ git worktree) ---
find_python() {
  local base candidates=()
  candidates+=("$ROOT/.venv")
  if common="$(git -C "$ROOT" rev-parse --git-common-dir 2>/dev/null)"; then
    candidates+=("$(cd "$ROOT" && cd "$(dirname "$common")" && pwd)/.venv")
  fi
  for base in "${candidates[@]}"; do
    for py in "$base/Scripts/python.exe" "$base/bin/python"; do
      if [ -x "$py" ]; then echo "$py"; return 0; fi
    done
  done
  command -v python3 || command -v python || true
}

PYTHON="${PYTHON:-$(find_python)}"
if [ -z "$PYTHON" ]; then
  echo "Không tìm thấy Python. Tạo venv: python -m venv .venv && .venv/Scripts/pip install -e ." >&2
  exit 1
fi

# --- cấu hình (có thể ghi đè từ bên ngoài) ---
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
export STUDIO_PORT="${STUDIO_PORT:-7863}"
export WHITEBOARD_ROOT="${WHITEBOARD_ROOT:-}"
export WHITEBOARD_PYTHON="${WHITEBOARD_PYTHON:-}"
if [ -z "$WHITEBOARD_ROOT" ]; then
  echo "[i] Chưa đặt WHITEBOARD_ROOT: sao chép .env.example thành .env và sửa đường dẫn." >&2
fi

URL="http://127.0.0.1:${STUDIO_PORT}/"

# --- dừng server Studio cũ (tiến trình python) đang giữ cổng; tiến trình khác thì giữ nguyên. Tắt bằng KILL_OLD=0 ---
free_port() {
  local port="$1" pid name
  if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -Command "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object { \$p = Get-Process -Id \$_.OwningProcess -ErrorAction SilentlyContinue; if (\$p -and \$p.ProcessName -like 'python*') { Stop-Process -Id \$p.Id -Force; Write-Output ('[i] Đã dừng server cũ (PID ' + \$p.Id + ') trên cổng $port') } elseif (\$p) { Write-Output ('[!] Cổng $port đang do ' + \$p.ProcessName + ' dùng, không dừng.') } }" 2>/dev/null | tr -d '\r' >&2 || true
  elif command -v lsof >/dev/null 2>&1; then
    for pid in $(lsof -ti "tcp:$port" -sTCP:LISTEN 2>/dev/null); do
      name="$(ps -p "$pid" -o comm= 2>/dev/null || true)"
      case "$name" in
        python*) kill "$pid" && echo "[i] Đã dừng server cũ (PID $pid) trên cổng $port" >&2 ;;
        *) echo "[!] Cổng $port đang do $name dùng, không dừng." >&2 ;;
      esac
    done
  fi
}
[ "${KILL_OLD:-1}" = "0" ] || free_port "$STUDIO_PORT"

# --- cảnh báo thiếu thành phần (không chặn chạy) ---
command -v ffmpeg >/dev/null 2>&1 || echo "[!] Thiếu ffmpeg trong PATH: Whiteboard sẽ không render/ghép được." >&2
[ -f "$WHITEBOARD_ROOT/scripts/render_stream_whiteboard.py" ] || echo "[!] WHITEBOARD_ROOT không hợp lệ ($WHITEBOARD_ROOT): chế độ Whiteboard chưa dùng được." >&2
command -v npx >/dev/null 2>&1 || echo "[!] Thiếu node/npx: chế độ HyperFrames chưa dùng được." >&2

echo "Python : $PYTHON"
echo "Studio : $URL   (Ctrl+C để dừng; sửa code phải chạy lại)"

# --- bản desktop: cửa sổ riêng (pywebview), không mở trình duyệt. Dùng: ./start.sh --desktop ---
if [ "${1:-}" = "--desktop" ]; then
  shift
  echo "Desktop: cửa sổ Code2Video Studio (cổng ${DESKTOP_PORT:-7870})"
  exec "$PYTHON" -m code2video.desktop "$@"
fi

# --- mở trình duyệt sau khi server lên (bỏ qua bằng NO_BROWSER=1) ---
if [ -z "${NO_BROWSER:-}" ]; then
  (
    for _ in $(seq 1 30); do
      if curl -fs -o /dev/null "$URL" 2>/dev/null; then
        if command -v cmd.exe >/dev/null 2>&1; then cmd.exe /c start "" "$URL" >/dev/null 2>&1
        elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1
        elif command -v open >/dev/null 2>&1; then open "$URL" >/dev/null 2>&1
        fi
        exit 0
      fi
      sleep 1
    done
  ) &
fi

exec "$PYTHON" -m code2video.studio.app
