#!/bin/bash
# gremlin-herald.sh — Run Herald phase + push to OpenClaw bridge
# Add to crontab: 0 5 * * * cd /path/to/hat_stack && bash scripts/gremlin-herald.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

LOG_DIR=".gremlins"
mkdir -p "$LOG_DIR"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Gremlin Herald starting..." >> "$LOG_DIR/overnight.log"

python scripts/gremlin_runner.py --phase herald 2>&1 | tee -a "$LOG_DIR/overnight.log"

# Push to OpenClaw bridge (if available)
if [ -f "scripts/herald_bridge.py" ]; then
    python scripts/herald_bridge.py 2>&1 >> "$LOG_DIR/overnight.log" || true
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Gremlin Herald complete." >> "$LOG_DIR/overnight.log"