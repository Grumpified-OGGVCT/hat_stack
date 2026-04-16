# Hat Stack

**The Universal Agentic-AI Engineering Stack -- 26 Specialized Review Agents**

**Version:** 3.1 · **Status:** Production-Ready · **License:** [MIT](LICENSE)

Language-agnostic · Framework-agnostic · Domain-agnostic

---

## What Is Hat Stack?

Hat Stack is a **local-first agentic review system** that runs 26 specialized AI agents (each wearing a metaphorical "hat") against your code changes. Each hat provides a distinct review lens -- security, performance, accessibility, AI safety, compliance, cost, and more -- producing a unified, adjudicated verdict.

**Local models, local machine.** Hat Stack runs on your machine using [Ollama](https://ollama.com). No cloud API keys required for the core experience. Cloud models are optional for heavier workloads. **Local-only mode** is available for strict PII compliance.

**Multi-provider.** Route cloud models through Ollama Cloud, OpenRouter, or any OpenAI-compatible API. Cross-provider fallback keeps work flowing when your primary provider has issues.

> **Not every hat runs on every diff.** Only **5 hats are always-on** (Black, Blue, Purple, Coral, Gold). The remaining 21 activate when the diff matches their trigger conditions. A typical PR activates 5-9 hats.

---

## Quick Start

### 1. Install Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows -- download from https://ollama.com/download
```

### 2. Pull a model

```bash
ollama pull gemma4:e2b    # 7.2GB, fast, good for most hats
```

### 3. Clone and run

```bash
git clone https://github.com/Grumpified-OGGVCT/hat_stack.git
cd hat_stack

# Quick start: auto-checks, pulls model, runs sample review
bash scripts/quickstart.sh

# Or install manually:
pip install -r scripts/requirements.txt

# Review a diff file
python scripts/hats_runner.py --diff my-changes.patch

# Review from stdin
git diff main | python scripts/hats_runner.py --diff -

# Specify hats
python scripts/hats_runner.py --diff my-changes.patch --hats black,blue,purple
```

### 4. Done

You'll get a verdict: **ALLOW**, **ESCALATE**, or **QUARANTINE** with a full report.

### Large PR Workflow

For large diffs (hundreds of files), run the security-critical hats trio first, then expand if needed:

```bash
# Step 1: Fast security check (3 hats, ~2-5 min)
git diff main | python scripts/hats_runner.py --diff - --hats black,blue,purple

# Step 2: If risk score is low, run the full team on the remaining scope
git diff main | python scripts/hats_runner.py --diff -
```

### Quiet Mode (CI Pipelines)

Use `--quiet` to print only the verdict, risk score, and hat count:

```bash
python scripts/hats_runner.py --diff my.patch --quiet --json-file report.json
# Output: ALLOW risk=12/100 hats=5
#         report=report.json
```

---

## Local Model Pool

Hat Stack uses these local Ollama models by default (no cloud needed):

| Model | Size | Effective Params | Role |
|-------|------|------------------|------|
| `gemma4:e2b` | 7.2GB | 2.3B | Fast scanning: White, Blue, Silver, Teal |
| `gemma4:e4b` | 9.6GB | 4.5B | Security analysis: Black, Purple (local mode) |
| `qwen3.5:9b` | 6.1GB | 9B | Deep reasoning: Red, Brown (local mode) |

**You only need one model to start.** `gemma4:e2b` (7.2GB) covers the 4 always-on hats and most conditional ones. The other two add deeper analysis for security and data governance hats. Pull all three for full local coverage:

```bash
ollama pull gemma4:e2b gemma4:e4b qwen3.5:9b
```

---

## Multi-Provider LLM Routing

Hat Stack supports routing models to different LLM providers. The default setup uses Ollama Local and Ollama Cloud, but you can add OpenRouter or any OpenAI-compatible API.

### Configured Providers

| Provider | API Format | Auth | Default |
|----------|-----------|------|---------|
| `ollama_local` | Ollama `/api/chat` | None | Yes (local) |
| `ollama_cloud` | Ollama `/api/chat` | `OLLAMA_API_KEY` | Yes (cloud) |
| `openrouter` | OpenAI `/v1/chat/completions` | `OPENROUTER_API_KEY` | No |

### Adding OpenRouter

1. Get an API key from [openrouter.ai](https://openrouter.ai)
2. Set the environment variable:
   ```bash
   export OPENROUTER_API_KEY="sk-or-..."
   ```
3. In `scripts/hat_configs.yml`, set `openrouter.enabled: true`
4. OpenRouter model equivalents (e.g., `glm-5.1:openrouter`) are already configured

### Adding Other Providers (DeepInfra, Groq, Together AI)

Any OpenAI-compatible API can be added with config changes only -- no code changes needed:

1. Add a provider entry under `providers:` in `hat_configs.yml`:
   ```yaml
   providers:
     deepinfra:
       name: "DeepInfra"
       base_url_env: DEEPINFRA_BASE_URL
       default_base_url: "https://api.deepinfra.com/v1/openai"
       api_key_env: DEEPINFRA_API_KEY
       api_format: openai_compatible
       enabled: true
   ```
2. Add models with `provider: deepinfra` and `model_id: "deepseek-ai/DeepSeek-V3"`
3. Set the API key env var

### Cross-Provider Fallback

When `execution.fallback_across_providers: true` (default), if a model fails on one provider, the system tries equivalent-tier models on other available providers. This keeps work flowing even when your primary cloud provider has issues.

---

## Local-Only Mode

For strict PII compliance, enable local-only mode to ensure **no data ever leaves your machine**:

```yaml
# In scripts/hat_configs.yml
local_only:
  enabled: true
```

When enabled:
- All hats are forced to use local models
- Cloud model calls are blocked (return errors that trigger fallback to local)
- Dual-mode hats (Black, Purple, Brown) that would normally switch to local for sensitive content are already local
- The GitHub Actions / CI mode still works but will only use local models (requires self-hosted runners with Ollama)

**Note:** The default mode (hybrid cloud + local) still works as always. Local-only is opt-in. The original GitHub Actions CI mode using `OLLAMA_API_KEY` for cloud models continues to work unchanged.

---

## Cloud Models (Optional)

For heavier workloads, Hat Stack supports Ollama Cloud models. Set `OLLAMA_API_KEY` to enable:

```bash
export OLLAMA_API_KEY="your-key-from-ollama-com"
# Get a key at: https://ollama.com/settings/keys
```

Cloud models (Tier 1-4) include: glm-5.1, kimi-k2.5, deepseek-v3.2, devstral-2, minimax-m2.7, nemotron-3-super, qwen3-coder, and more. See [`scripts/hat_configs.yml`](scripts/hat_configs.yml) for the full pool.

---

## Gremlin Overnight Daemon

The Gremlin system is Hat Stack's autonomous overnight code scanner. It runs a 6-phase review loop across all your configured repos and produces a morning Herald digest.

### The 6 Phases

| Phase | Time | Hat | What |
|-------|------|-----|------|
| Catalog | 1 AM | Cyan | Crawl _universal_skills/ SKILL.md files, build searchable taxonomy |
| Review | 2 AM | Black | Scan recent git diffs for security issues |
| Propose | 3 AM | Gold | Synthesize findings into governance proposals |
| Analyze | 4 AM | Purple | Deep analysis of approved proposals |
| Herald | 5 AM | Blue | Compose cross-repo daily digest |
| Experiment | 6 AM | Green | Co-design candidate agents using skills taxonomy + idle budget |

### Multi-Repo Configuration

Add repos to monitor in `scripts/hat_configs.yml`:

```yaml
gremlins:
  repos:
    - path: "/path/to/your/repo1"
    - path: "/path/to/your/repo2"
    - path: "/path/to/your/repo3"
      skip_phases: ["herald"]    # Optional: skip specific phases
      enabled: true               # Optional: disable without removing
```

### Daemon CLI

```bash
# Start the daemon (foreground, schedule from config)
python scripts/gremlin_daemon.py --daemon --config scripts/hat_configs.yml

# Single check-and-run cycle (testing)
python scripts/gremlin_daemon.py --once

# Show schedule + repos without executing
python scripts/gremlin_daemon.py --dry-run

# Show status, next runs, per-repo stats
python scripts/gremlin_daemon.py --status

# Stop a running daemon
python scripts/gremlin_daemon.py --stop
```

### Schedule Configuration

The cron schedule is in `hat_configs.yml`:

```yaml
gremlins:
  overnight_schedule:
    catalog:    "0 1 * * *"     # 1 AM — Skills taxonomy crawl
    review:     "0 2 * * *"     # 2 AM daily
    propose:    "0 3 * * *"     # 3 AM daily
    analyze:    "0 4 * * *"     # 4 AM daily
    herald:     "0 5 * * *"     # 5 AM daily
    experiment: "0 6 * * *"     # 6 AM — Agent co-design
```

Supports standard 5-field cron syntax: `*`, ranges (`1-5`), steps (`*/15`), comma lists (`1,15,30`).

### Overnight Mode

During the overnight window, the daemon automatically switches to larger local models with extended timeouts:

```yaml
gremlins:
  overnight:
    enabled: true
    schedule_start: "01:00"
    schedule_end: "07:00"
    model_overrides:
      review: "qwen3.5:9b"
      analyze: "qwen3.5:9b"
      propose: "gemma3:12b"
    timeout_multiplier: 5
```

### Windows Scheduled Task

Install the daemon to start at logon:

```powershell
pwsh scripts/install-gremlin-daemon.ps1

# Check status
pwsh scripts/install-gremlin-daemon.ps1 -Status

# Uninstall
pwsh scripts/install-gremlin-daemon.ps1 -Uninstall
```

### Morning Workflow

1. Check `.gremlins/herald/social_log/YYYY-MM-DD-social_log.md` for the cross-repo digest
2. It lists findings per repo with section headers
3. Per-repo proposals in `.gremlins/repos/<name>/proposals/` -- approve or reject
4. `python scripts/gremlin_runner.py --status` shows a summary across all repos
5. The Herald digest is pushed to the OpenClaw bridge automatically

### Skills Configuration

The catalog phase crawls skill directories to build a searchable taxonomy. By default, Hat Stack looks for skills in `./skills` (relative to the project root). Set up the link:

```bash
# Option 1: Directory junction (Windows, no admin required)
powershell -Command "New-Item -ItemType Junction -Path skills -Target /path/to/_universal_skills"

# Option 2: Symlink (macOS/Linux)
ln -s /path/to/_universal_skills skills

# Option 3: Set environment variable
export HAT_STACK_SKILLS_DIR=/path/to/_universal_skills
```

The resolution order for skills directory:
1. `gremlins.experiment.skills_dir` in `hat_configs.yml` (supports relative paths)
2. `HAT_STACK_SKILLS_DIR` environment variable
3. `./skills` symlink/junction in the project root
4. `../_universal_skills` sibling directory (fallback)

The default config uses `./skills`:
```yaml
gremlins:
  experiment:
    skills_dir: "./skills"    # Relative to hat_stack root
```

### Governance

All proposals require human approval by default (`governance.require_human_approval: true`). Proposals follow a governance lifecycle:
- **PENDING_HUMAN** -- Created by Gremlins, awaiting your approval
- **APPROVED** -- You approved it, analysis will run
- **REJECTED** -- You rejected it, no further action
- **EXPIRED** -- Not approved within 48 hours, auto-expired

```bash
# Approve a proposal
python scripts/gremlin_runner.py --approve 001

# Reject a proposal
python scripts/gremlin_runner.py --reject 001 --reason "Too risky right now"
```

---

## MCP Server -- Use from Claude Code

Hat Stack exposes an MCP server so any MCP-compatible agent can call it:

```json
// In your project's .mcp.json or Claude Code settings
{
  "mcpServers": {
    "hat_stack": {
      "command": "node",
      "args": ["path/to/hat_stack/mcp/dist/index.js"]
    }
  }
}
```

**Available tools:**

| Tool | Description |
|------|-------------|
| `hats_review` | Run a review on a diff. Returns verdict, risk score, findings. |
| `hats_task` | Run a task (generate_code, analyze, plan, test, etc.) |
| `hats_list_models` | List available models and their hat assignments |
| `hats_check_status` | Check pipeline status for a run |
| `hats_get_config` | Get current hat_configs.yml |
| `hats_assemble_team` | Assemble a custom team for a specific task. Returns optimal hat+model lineup with execution plan. |

### hats_assemble_team Example

Tell it what you're working on and get the right team:

```
"I'm reviewing a PR that touches auth and database migrations"
```

Returns:
```
Team: Black [local: gemma4:e4b -- auth detected], Purple [local: gemma4:e4b -- PII detected],
      Indigo [cloud: devstral-2:123b-cloud -- multi-file], Blue [local: gemma4:e2b]
Execution: cloud group runs in parallel with local queue
Budget: ~8,500 tokens estimated
```

---

## Security Mode

When a diff contains credentials, API keys, or PII patterns, Hat Stack automatically switches dual-mode hats (Black, Purple, Brown) to **local models only** -- your sensitive code never leaves your machine.

This is automatic. No configuration needed. For full PII safety, enable **local-only mode** (see above).

---

## Task Mode -- Tell It to DO Things

Beyond review, Hat Stack can generate code, write docs, create plans, and build tests:

```bash
# Generate code
python scripts/hats_task_runner.py --task generate_code \
  --prompt "Build a FastAPI auth module with JWT"

# Write documentation
python scripts/hats_task_runner.py --task generate_docs \
  --prompt "Write API docs for /users endpoints"

# Create a plan
python scripts/hats_task_runner.py --task plan \
  --prompt "Plan migration from REST to GraphQL"

# Generate tests
python scripts/hats_task_runner.py --task test \
  --prompt "Write unit tests for auth.py"

# Deep analysis
python scripts/hats_task_runner.py --task analyze \
  --prompt "Security audit of payment processing"
```

---

## The 26 Hats

| # | Hat | Run Mode | Focus |
|---|-----|----------|-------|
| 1 | Red | Conditional | Failure & Resilience |
| 2 | Black | **Always** | Security & Exploits |
| 3 | White | Conditional | Efficiency & Resources |
| 4 | Yellow | Conditional | Synergies & Integration |
| 5 | Green | Conditional | Evolution & Extensibility |
| 6 | Blue | **Always** | Process & Specification |
| 7 | Indigo | Conditional | Cross-Feature Architecture |
| 8 | Cyan | Conditional | Innovation & Feasibility |
| 9 | Purple | **Always** | AI Safety & Alignment |
| 10 | Orange | Conditional | DevOps & Automation |
| 11 | Silver | Conditional | Context & Token Optimization |
| 12 | Azure | Conditional | MCP & Protocol Integration |
| 13 | Brown | Conditional | Data Governance & Privacy |
| 14 | Gray | Conditional | Observability & Reliability |
| 15 | Teal | Conditional | Accessibility & Inclusion |
| 16 | Steel | Conditional | Supply Chain & Dependencies |
| 17 | Chartreuse | Conditional | Testing & Evaluation |
| 18 | Gold | **Always (Last)** | CoVE Final QA |
| 19 | Coral | **Always** | Product & User Value |
| 20 | Maroon | Conditional | Compliance & Regulation |
| 21 | Amber | Conditional | Documentation Quality |
| 22 | Rose | Conditional | Performance Engineering |
| 23 | Sage | Conditional | Data Engineering |
| 24 | Lavender | Conditional | UX Research |
| 25 | Crimson | Conditional | Cost & Economics |
| 26 | Plum | Conditional | Integration Testing |

Full specifications: [`CATALOG.md`](CATALOG.md) · Individual hat docs: [`hats/`](hats/)

---

## Verdicts

| Verdict | Meaning | Condition |
|---------|---------|-----------|
| **ALLOW** | Safe to merge | No CRITICAL findings; risk score <= 20 |
| **ESCALATE** | Requires human review | HIGH findings; risk score 21-60 |
| **QUARANTINE** | Cannot merge pending adjudication | CRITICAL finding; risk score > 60 |

---

## When to Use Hat Stack

**Great fit:**

| Scenario | Why it fits |
|----------|-------------|
| Security-first teams that cannot send code to external APIs | Local-only mode + dual-mode hats keep secrets in-house |
| Mono-repo or multi-repo orgs wanting automated nightly governance | Gremlin daemon provides daily digests with human-gated proposals |
| Teams already using Ollama | No extra cost -- just pull the models you need (7.2GB minimum) |
| Hybrid cloud users who need fallback when a provider has outage | Multi-provider router with automatic tier fallback |

**Less ideal:**

| Scenario | Reason |
|----------|--------|
| Very small projects with cheap CI linters already in place | Hat Stack adds model download and per-hat inference time |
| Real-time PR feedback on massive PRs (hundreds of files) | Per-hat timeouts are 60-300s; consider splitting large PRs or raising `timeout_multiplier` |
| Repos with no diff semantics (binary assets, images) | Conditional hats won't activate on binary files; only the 4 always-on hats run |

### Benchmarks

Every run automatically logs timing data to `.hats/run_log.jsonl`. View accumulated benchmarks:

```bash
python scripts/hats_runner.py --benchmarks
```

This builds over time — the more you run Hat Stack, the more accurate the averages become. The table buckets diffs by size (<=200 lines, 200-2K, >2K) and shows average latency, hat count, token usage, and risk score per bucket.

---

## Resume from Checkpoint

Interrupted runs can be resumed:

```bash
# Original run saved to .hats/checkpoints/run-20260415-120000.json
python scripts/hats_runner.py --resume run-20260415-120000 --diff my-changes.patch
```

Only pending (not yet completed) hats will run.

---

## GitHub Actions (Optional)

Hat Stack also runs as GitHub Actions for CI/CD integration. This uses cloud models via `OLLAMA_API_KEY` as a Repository Secret. See:

- [`FORK_SETUP.md`](FORK_SETUP.md) -- Fork and setup guide for GitHub Actions
- [`.github/workflows/`](.github/workflows/) -- Reusable workflows, dispatch handler, task runner
- `OLLAMA_API_KEY` -- Required as a Repository Secret for cloud models in CI

**GitHub Actions mode works unchanged.** The hybrid cloud+local mode is the default. Local-only mode is opt-in. For CI with local-only, use self-hosted runners with Ollama installed.

---

## Environment Variables Reference

| Variable | Provider | Required | Description |
|----------|----------|----------|-------------|
| `OLLAMA_LOCAL_URL` | ollama_local | No | Local Ollama URL (default: `http://localhost:11434`) |
| `OLLAMA_CLOUD_URL` | ollama_cloud | No | Ollama Cloud URL (default: `https://ollama.com`) |
| `OLLAMA_API_KEY` | ollama_cloud | For cloud | Ollama Cloud API key |
| `OPENROUTER_API_KEY` | openrouter | For OpenRouter | OpenRouter API key |
| `OPENROUTER_BASE_URL` | openrouter | No | OpenRouter base URL (default: `https://openrouter.ai/api/v1`) |
| `DEEPINFRA_API_KEY` | deepinfra | For DeepInfra | DeepInfra API key |
| `GROQ_API_KEY` | groq | For Groq | Groq API key |
| `TOGETHER_API_KEY` | together | For Together AI | Together AI API key |
| `HAT_STACK_SKILLS_DIR` | skills | No | Override path to skills directory (catalog phase) |

---

## Architecture

```
Layer 5: CLI / MCP Server / IDE Extension / CI/CD Trigger / Gremlin Daemon
Layer 4: Conductor -- Hat Selector, Gate Engine, Retry, State Manager, Consolidator, CoVE
Layer 3: 26 Hat Agents -- each with dedicated persona + model
Layer 2: Provider Router -- Ollama / OpenRouter / DeepInfra / Groq / Together AI / ...
Layer 1: Ollama (Local + Cloud) / OpenAI-Compatible APIs / Vector Stores / Key-Value Stores
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [`FORK_SETUP.md`](FORK_SETUP.md) | GitHub Actions fork and setup guide |
| [`SPEC.md`](SPEC.md) | Primary specification -- orchestration, gates, retry, HITL, CI/CD |
| [`CATALOG.md`](CATALOG.md) | Master Hat Registry -- triggers, severity grading, risk scores |
| [`hats/`](hats/) | Individual hat specifications |
| [`scripts/hat_configs.yml`](scripts/hat_configs.yml) | Model pool, providers, and hat configuration |
| [`.env.example`](.env.example) | Environment variable template |

---

## Repository Layout

```
hat_stack/
  scripts/
    hats_runner.py           Review orchestrator (Conductor)
    hats_task_runner.py       Task orchestrator (generate, refactor, plan, etc.)
    hats_common.py            Shared library: multi-provider call_ollama, retry, circuit breaker
    provider_router.py        Multi-provider LLM routing (Ollama, OpenRouter, OpenAI-compatible)
    hat_selector.py           Hat selection engine (keyword + AST + dependency)
    gates.py                  Gate engine (cost, security, consistency, timeout, decision)
    consolidator.py           Finding deduplication and conflict detection
    state.py                  Run state persistence and checkpoint resume
    gremlin_runner.py         Multi-repo overnight Gremlin phase executor
    gremlin_daemon.py         Self-scheduling daemon with cron parser
    gremlin_memory.py         .gremlins/ directory management (per-repo storage)
    skills_crawler.py         Skills taxonomy builder (_universal_skills/ crawler)
    experiment_graph.py       Agent co-design state machine (BUILD→EVAL→SAFETY→PUBLISH→REPORT)
    herald_bridge.py          Push Herald digests to external channels
    hat_configs.yml           Model pool, providers, and hat configuration
    install-gremlin-daemon.ps1  Windows Scheduled Task installer
    tests/                    Unit and integration tests
  mcp/
    src/                      MCP server source (TypeScript)
    dist/                     Compiled MCP server
  hats/                       Individual hat specification documents
  .github/workflows/          GitHub Actions workflows (optional CI/CD mode)
```

---

## License

MIT -- See [LICENSE](LICENSE).