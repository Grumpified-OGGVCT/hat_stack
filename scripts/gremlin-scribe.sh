#!/bin/bash
# gremlin-scribe.sh — Run overnight Gremlin review + proposal cycle
# Add to crontab: 0 2 * * * cd /path/to/hat_stack && bash scripts/gremlin-scribe.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

LOG_DIR=".gremlins"
mkdir -p "$LOG_DIR"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Gremlin Scribe starting..." >> "$LOG_DIR/overnight.log"

python scripts/gremlin_runner.py --all 2>&1 | tee -a "$LOG_DIR/overnight.log"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Gremlin Scribe complete." >> "$LOG_DIR/overnight.log"