# Runner image for the night job: everything installed once, pulled each night.
# Rebuilt by .github/workflows/build-image.yml when this file, requirements.txt,
# tools/code2video or the bg_renderer package files change.
FROM ubuntu:24.04

LABEL org.opencontainers.image.source="https://github.com/huybq002/video-resources"

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PUPPETEER_SKIP_DOWNLOAD=true \
    # GitHub container jobs override HOME (/github/home), so keep every cache at a fixed path.
    XDG_CACHE_HOME=/opt/cache \
    HF_HOME=/opt/cache/huggingface \
    HF_HUB_CACHE=/opt/cache/huggingface/hub \
    npm_config_cache=/opt/cache/npm \
    STUDIO_DATA_DIR=/tmp/studio-data \
    CHROME_PATH=/usr/local/bin/chrome-nosandbox \
    PUPPETEER_EXECUTABLE_PATH=/usr/local/bin/chrome-nosandbox

# System packages: git/curl/unzip are needed by claude-code-action; ffmpeg for media.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg git unzip zip sudo \
        python3 python3-pip python3-venv ffmpeg \
        fonts-liberation fonts-noto-core fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Node 22 (HyperFrames needs >= 22)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version

# Google Chrome + wrapper that adds --no-sandbox (required when running as root in a container)
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* \
    && printf '#!/bin/sh\nexec /opt/google/chrome/chrome --no-sandbox --disable-dev-shm-usage "$@"\n' > /usr/local/bin/chrome-nosandbox \
    && chmod +x /usr/local/bin/chrome-nosandbox

# GitHub CLI (publishes the Release with the bundle and video)
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /usr/share/keyrings/githubcli-archive-keyring.gpg     && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list     && apt-get update && apt-get install -y --no-install-recommends gh     && rm -rf /var/lib/apt/lists/*

RUN git config --system --add safe.directory '*'

# Python deps for the skills (edge-tts fallback, thumbnails, ...)
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# The tool (editable, fixed path) with TTS + alignment extras
COPY tools/code2video /opt/code2video
RUN pip install -e "/opt/code2video[tts,alignment]"

# HyperFrames CLI + warm the npx cache
RUN npm install -g hyperframes && (npx --yes hyperframes --help >/dev/null 2>&1 || true)

# Warm the bg_renderer npm cache (three, puppeteer-core)
COPY .claude/skills/code2video-resource-generator/scripts/bg_renderer/package.json /tmp/bg/package.json
RUN cd /tmp/bg && npm install --no-audit --no-fund && rm -rf /tmp/bg

# Download the models at build time so nights never download them.
# faster-whisper "small" (tool default) and VieNeu "v3turbo" (tool default).
RUN python3 -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8'); print('whisper ok')"
# VieNeu: the first load downloads the model, but onnxruntime then rejects it because the HuggingFace cache
# stores files as symlinks that point outside the model directory ("External data path escapes model directory").
# So: let it download (failure tolerated), replace every symlink with a real file, then load it again to verify.
RUN (python3 -c "from vieneu import Vieneu; Vieneu(mode='v3turbo')" || true)     && find /opt/cache/huggingface -type l | while read -r link; do target="$(readlink -f "$link")"; rm "$link"; cp "$target" "$link"; done     && python3 -c "from vieneu import Vieneu; Vieneu(mode='v3turbo'); print('vieneu ok')"

WORKDIR /github/workspace
