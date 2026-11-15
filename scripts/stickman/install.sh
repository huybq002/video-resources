#!/usr/bin/env bash
# Install the pinned stickman-video-director runtime (stickman/lock.json) into $STICKMAN_HOME
# (default /opt/stickman-director in the runner image, .cache/stickman-director elsewhere).
# Idempotent: does nothing when the pinned commit is already installed with its node_modules.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"   # python reads stickman/lock.json relative to the repo (portable paths)
PY=python3; "$PY" -c "print(1)" >/dev/null 2>&1 || PY=python
HOME_DIR="${STICKMAN_HOME:-$ROOT/.cache/stickman-director}"
REPO=$("$PY" -c "import json;print(json.load(open('stickman/lock.json'))['repo'])")
COMMIT=$("$PY" -c "import json;print(json.load(open('stickman/lock.json'))['commit'])")
SKILL=$("$PY" -c "import json;print(json.load(open('stickman/lock.json'))['skill_dir'])")
if [ -f "$HOME_DIR/.commit" ] && [ "$(cat "$HOME_DIR/.commit")" = "$COMMIT" ] && [ -d "$HOME_DIR/$SKILL/node_modules" ]; then
  echo "stickman runtime $COMMIT already installed at $HOME_DIR"; exit 0
fi
rm -rf "${HOME_DIR:?}"; mkdir -p "$HOME_DIR"
git -C "$HOME_DIR" init -q
git -C "$HOME_DIR" remote add origin "$REPO"
git -C "$HOME_DIR" config core.sparseCheckout true
"$PY" -c "import json;print('\n'.join(json.load(open('stickman/lock.json'))['sparse']))" > "$HOME_DIR/.git/info/sparse-checkout"
git -C "$HOME_DIR" fetch -q --depth 1 --filter=blob:none origin "$COMMIT"
git -C "$HOME_DIR" checkout -q FETCH_HEAD
test "$(git -C "$HOME_DIR" rev-parse HEAD)" = "$COMMIT"
(cd "$HOME_DIR/$SKILL" && npm ci --no-audit --no-fund --silent)
echo "$COMMIT" > "$HOME_DIR/.commit"
(cd "$HOME_DIR/$SKILL" && node scripts/autopilot.mjs doctor)
echo "stickman runtime $COMMIT installed at $HOME_DIR/$SKILL"
