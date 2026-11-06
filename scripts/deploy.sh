#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE="${NUNKI_RSYNC_TARGET:-nunkichannels-vps@nunkistar}"
REMOTE_PATH="${NUNKI_RSYNC_PATH:-~/httpdocs/}"

# Build: Python 3.13 + Pillow (`pip install -r "$ROOT/requirements.txt"`).
# Overschrijf met NUNKI_PYTHON=… als je een andere binary wilt.
PYTHON_CMD="${NUNKI_PYTHON:-python3.13}"
if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
	PYTHON_CMD="python3"
fi
"$PYTHON_CMD" "$ROOT/scripts/build.py"
rsync -avz --delete --exclude '.DS_Store' "$ROOT/httpdocs/" "${REMOTE}:${REMOTE_PATH}"
ssh "${REMOTE}" "find ${REMOTE_PATH} -type d -exec chmod 755 {} +; find ${REMOTE_PATH} -type f -exec chmod 644 {} +"
