# 🎩 Fork Setup Guide — Get Your Own Hat Stack Running in 5 Minutes

Welcome! This guide gets you from **fork** to **working Hats reviews** as fast as possible.

> **Your keys are YOUR keys.** The original repo owner's secrets are stored in their GitHub repository/organization secrets — they are never in the code. When you fork, you get the code and workflows, but **zero secrets**. You add your own.

---

## Quick Start (3 steps)

### Step 1: Fork the repo

Click **Fork** on [github.com/Grumpified-OGGVCT/hat_stack](https://github.com/Grumpified-OGGVCT/hat_stack).

### Step 2: Add your Ollama Cloud API key

In **your fork**, go to:

```
Settings → Secrets and variables → Actions → New repository secret
```

Add these secrets:

| Secret Name | Required? | Description |
|------------|-----------|-------------|
| `OLLAMA_API_KEY` | ✅ **Yes** | Your Ollama Cloud API key ([get one here](https://ollama.ai/cloud)) |
| `OLLAMA_BASE_URL` | ❌ No | API base URL (default: `https://api.ollama.ai/v1`) |
| `HAT_STACK_CALLBACK_TOKEN` | ❌ No | GitHub PAT for posting results to other repos' PRs (only needed for dispatch mode) |

That's it. **Two minutes, one secret.**

### Step 3: You're done

- **Self-review** runs automatically on every PR to your fork
- **Reusable workflow** is ready for your other repos to call
- **Dispatch handler** is ready for API-triggered reviews

---

## How Secrets Work (Why This Is Safe)

```
┌─────────────────────────────────────────────────────────────┐
│  ORIGINAL REPO (Grumpified-OGGVCT/hat_stack)                │
│                                                             │
│  Code: ✅ Public (MIT license)                              │
│  Secrets: 🔒 Owner's OLLAMA_API_KEY, etc.                  │
│           → Stored in GitHub Secrets                        │
│           → NEVER in code                                   │
│           → NOT included in forks                           │
│           → Cannot be read by anyone else                   │
├─────────────────────────────────────────────────────────────┤
│  YOUR FORK (you/hat_stack)                                  │
│                                                             │
│  Code: ✅ Same code, workflows, configs                     │
│  Secrets: 🔒 YOUR OLLAMA_API_KEY, etc.                     │
│           → You add them yourself (Step 2 above)            │
│           → Stored in YOUR GitHub Secrets                   │
│           → Cannot be read by the original owner            │
│           → Cannot be read by other forkers                 │
└─────────────────────────────────────────────────────────────┘
```

**Key facts:**
- GitHub Secrets are **encrypted at rest** and **never exposed in logs**
- Secrets are **not transferred** when you fork a repository
- Workflow files reference `${{ secrets.OLLAMA_API_KEY }}` — this resolves to **your fork's secret**, not anyone else's
- The Python runner reads `OLLAMA_API_KEY` from the environment — it never stores, logs, or transmits it

---

## Using Hat Stack from Your Other Projects

### Option A: Reusable Workflow (recommended)

In any of your other repos, create `.github/workflows/hats.yml`:

```yaml
name: "🎩 Hats Review"
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  get-diff:
    runs-on: ubuntu-latest
    outputs:
      diff_file: ${{ steps.diff.outputs.diff_file }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Generate diff
        id: diff
        run: |
          git diff origin/${{ github.base_ref }}...HEAD > /tmp/pr.diff
          echo "diff_file=/tmp/pr.diff" >> "$GITHUB_OUTPUT"
      - uses: actions/upload-artifact@v4
        with:
          name: pr-diff
          path: /tmp/pr.diff

  hats-review:
    needs: get-diff
    # Point this to YOUR fork:
    uses: YOUR_USERNAME/hat_stack/.github/workflows/hats-review.yml@main
    secrets:
      ollama_api_key: ${{ secrets.OLLAMA_API_KEY }}
```

> **Replace `YOUR_USERNAME`** with your GitHub username.

### Option B: Composite Action

Reference the action directly in any workflow step:

```yaml
- name: Run Hats Review
  uses: YOUR_USERNAME/hat_stack/.github/actions/run-hats@main
  with:
    diff_file: /tmp/pr.diff
  env:
    OLLAMA_API_KEY: ${{ secrets.OLLAMA_API_KEY }}
```

### Option C: Dispatch (API trigger)

Send a review request from anywhere — a CI agent, a script, a chatbot:

```bash
curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/YOUR_USERNAME/hat_stack/dispatches \
  -d '{
    "event_type": "run-hats",
    "client_payload": {
      "diff": "--- a/file.py\n+++ b/file.py\n@@ -1,3 +1,4 @@\n...",
      "callback_repo": "YOUR_USERNAME/other-project",
      "callback_pr": 42,
      "context": "Adding new authentication module"
    }
  }'
```

The Hats review runs in **your fork** of hat_stack, using **your API key**, and posts results back to the specified PR.

---

## Customizing Models

The default model assignments follow the [Implementation Guide](hats/HATS_TEAM_IMPLEMENTATION_GUIDE.md) §E2.2. To customize:

1. **Quick override**: Set environment variables in your GitHub Secrets:
   - `HATS_TIER1_MODEL=kimi-k2.5` (for security/safety/adjudication hats)
   - `HATS_TIER2_MODEL=minimax-m2.7` (for architectural reasoning hats)

2. **Full control**: Copy `scripts/hat_configs.yml` and modify model assignments per hat. Then set `config_override` in the reusable workflow call.

### Available Models (per the Implementation Guide)

| Model | Tier | Best For | Cost |
|-------|------|----------|------|
| `glm-5.1` | 1 | Security, safety, final adjudication | $0.40/$1.10 per M tokens |
| `kimi-k2.5` | 1 | Strong reasoning alternative | $0.42/$1.50 per M tokens |
| `deepseek-v3.1` | 2 | Long-context analysis (128K) | $0.10/$0.28 per M tokens |
| `minimax-m2.7` | 2 | Innovation/feasibility analysis | $0.30/$1.20 per M tokens |
| `nemotron-3-super` | 3 | Quality analysis, pattern matching | $0.25/$0.80 per M tokens |
| `qwen3-coder` | 3 | Code-specific reasoning | $0.20/$0.80 per M tokens |
| `nemotron-3-nano` | 4 | Ultra-fast deterministic checks | $0.08/$0.20 per M tokens |
| `ministral-3` | 4 | Ultra-cheap fast scanning | $0.05/$0.15 per M tokens |

---

## Local Development

For running Hats locally (not in GitHub Actions):

```bash
# 1. Clone your fork
git clone https://github.com/YOUR_USERNAME/hat_stack.git
cd hat_stack

# 2. Set up environment
cp .env.example .env
# Edit .env — add your OLLAMA_API_KEY

# 3. Install dependencies
pip install -r scripts/requirements.txt

# 4. Run on a diff file
python scripts/hats_runner.py --diff path/to/your.diff

# 5. Or pipe from git
git diff HEAD~1 | python scripts/hats_runner.py --diff -
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "OLLAMA_API_KEY not set" | Add the secret in Settings → Secrets → Actions |
| Workflow doesn't trigger | Make sure you're on `main` branch (or update the `@main` ref) |
| Dispatch doesn't work | The `GITHUB_TOKEN` you use to call the dispatch API needs `repo` scope |
| Callback comments don't appear | Add `HAT_STACK_CALLBACK_TOKEN` secret with `repo` scope |
| Models return errors | Verify your Ollama Cloud subscription includes the models you're using |

---

## Security Checklist

- [ ] `.env` is in `.gitignore` ✅ (already configured)
- [ ] No API keys in any committed file ✅ (all use `${{ secrets.* }}` or `os.environ`)
- [ ] Secrets are in GitHub Actions Secrets, not in code ✅
- [ ] Fork doesn't inherit original owner's secrets ✅ (GitHub design)
- [ ] Runner never logs or transmits API keys ✅

---

Back to [README](README.md) · Full spec: [SPEC.md](SPEC.md) · Implementation guide: [hats/HATS_TEAM_IMPLEMENTATION_GUIDE.md](hats/HATS_TEAM_IMPLEMENTATION_GUIDE.md)
