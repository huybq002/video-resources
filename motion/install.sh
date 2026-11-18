#!/usr/bin/env bash
# Make the hezb-motion engine ready: node modules (from the runner image when it has them) and the bundled page.
# Idempotent and fast on the runner (the image keeps /opt/hezb-motion/node_modules).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ ! -e "$HERE/node_modules" ]; then
  if [ -d /opt/hezb-motion/node_modules ]; then ln -s /opt/hezb-motion/node_modules "$HERE/node_modules"
  else (cd "$HERE" && npm ci --no-audit --no-fund --silent); fi
fi
(cd "$HERE" && node tools/bundle.mjs)
