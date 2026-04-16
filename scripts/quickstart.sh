#!/usr/bin/env bash
# Hat Stack Quick Start — pulls a model and runs a sample review
#
# Usage:
#   bash scripts/quickstart.sh          # Pull model + sample review
#   bash scripts/quickstart.sh --skip-pull  # Skip model pull (already have it)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/hat_configs.yml"

# Colors (disabled if not a terminal)
if [ -t 1 ]; then
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  CYAN='\033[0;36m'
  RED='\033[0;31m'
  NC='\033[0m'
else
  GREEN='' YELLOW='' CYAN='' RED='' NC=''
fi

echo -e "${CYAN}🎩 Hat Stack Quick Start${NC}"
echo ""

# Step 1: Check Python
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
  echo -e "${RED}Python 3 is required but not found.${NC}"
  echo "Install it from https://www.python.org/downloads/"
  exit 1
fi
PYTHON="${PYTHON:-python3}"
echo -e "${GREEN}✓${NC} Python found: $($PYTHON --version 2>&1 || echo "python")"

# Step 2: Install dependencies
if [ ! -d "$SCRIPT_DIR/__pycache__" ] || ! $PYTHON -c "import yaml, requests" 2>/dev/null; then
  echo -e "${YELLOW}Installing dependencies...${NC}"
  $PYTHON -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet 2>/dev/null || \
    $PYTHON -m pip install -r "$SCRIPT_DIR/requirements.txt"
fi
echo -e "${GREEN}✓${NC} Dependencies installed"

# Step 3: Check Ollama
if ! command -v ollama &>/dev/null; then
  echo ""
  echo -e "${YELLOW}Ollama is not installed.${NC}"
  echo "Install it from https://ollama.com/download"
  echo "Then run: bash scripts/quickstart.sh"
  exit 1
fi

if ! curl -s http://localhost:11434/api/version &>/dev/null; then
  echo -e "${YELLOW}Starting Ollama...${NC}"
  ollama serve &
  sleep 5
fi
echo -e "${GREEN}✓${NC} Ollama is running"

# Step 4: Pull minimum model
SKIP_PULL="${1:-}"
if [ "$SKIP_PULL" != "--skip-pull" ]; then
  echo ""
  echo -e "${CYAN}Pulling gemma4:e2b (7.2GB, the minimum model)...${NC}"
  echo "This is the only model you need to get started."
  echo ""
  ollama pull gemma4:e2b
fi
echo -e "${GREEN}✓${NC} Model ready: gemma4:e2b"

# Step 5: Create a sample diff
SAMPLE_DIFF=$(mktemp /tmp/hats-quickstart-XXXXXX.patch)
cat > "$SAMPLE_DIFF" <<'DIFF_EOF'
diff --git a/app/auth.py b/app/auth.py
--- a/app/auth.py
+++ b/app/auth.py
@@ -10,7 +10,7 @@
 import hashlib

 def authenticate(username, password):
-    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
+    query = "SELECT * FROM users WHERE username=%s AND password=%s"
     cursor.execute(query)
     user = cursor.fetchone()
     if user:
@@ -25,3 +25,8 @@
         return None

 def create_user(username, password):
+    if len(password) < 8:
+        raise ValueError("Password must be at least 8 characters")
+    hashed = hashlib.sha256(password.encode()).hexdigest()
+    cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
+    return {"username": username, "id": cursor.lastrowid}
DIFF_EOF

# Step 6: Run the review
echo ""
echo -e "${CYAN}Running a sample review with 3 hats...${NC}"
echo "  Diff: sample SQL injection fix + password validation"
echo "  Hats: black (security), blue (process), purple (AI safety)"
echo ""

$PYTHON "$SCRIPT_DIR/hats_runner.py" \
  --diff "$SAMPLE_DIFF" \
  --hats black,blue,purple \
  --config "$CONFIG" \
  --quiet \
  2>/dev/null || true

# Clean up
rm -f "$SAMPLE_DIFF"

echo ""
echo -e "${GREEN}Quick start complete!${NC}"
echo ""
echo "Next steps:"
echo "  • Run on your own code:  git diff main | python scripts/hats_runner.py --diff -"
echo "  • Add cloud models:      set OLLAMA_API_KEY or OPENROUTER_API_KEY"
echo "  • Schedule nightly runs: see README.md → Gremlin Overnight Daemon"
echo "  • Full model coverage:   ollama pull gemma4:e4b qwen3.5:9b"
echo ""
echo -e "See ${CYAN}README.md${NC} for full documentation."