#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FFMPEG_BIN="$ROOT/.tools/ffmpeg-local/usr/bin"
FFMPEG_LIB="$ROOT/.tools/ffmpeg-local/usr/lib/x86_64-linux-gnu"

if [ -x "$FFMPEG_BIN/ffprobe" ] && [ -d "$FFMPEG_LIB" ]; then
  PATH="$FFMPEG_BIN:$PATH"
  LD_LIBRARY_PATH="$FFMPEG_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export PATH LD_LIBRARY_PATH
fi

cd "$ROOT"
exec .venv/bin/python -m code2video.ui "$@"
