#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE="${NUNKI_RSYNC_TARGET:-nunkichannels-vps@nunkistar}"
REMOTE_PATH="${NUNKI_RSYNC_PATH:-~/httpdocs/}"

python3 "$ROOT/scripts/build.py"
rsync -avz --delete --exclude '.DS_Store' "$ROOT/httpdocs/" "${REMOTE}:${REMOTE_PATH}"
