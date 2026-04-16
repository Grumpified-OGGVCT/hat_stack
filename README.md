# Hat Stack

**The Universal Agentic-AI Engineering Stack -- 18 Specialized Review Agents**

**Version:** 3.0 · **Status:** Production-Ready · **License:** [MIT](LICENSE)

Language-agnostic · Framework-agnostic · Domain-agnostic

---

## What Is Hat Stack?

Hat Stack is a **local-first agentic review system** that runs 18 specialized AI agents (each wearing a metaphorical "hat") against your code changes. Each hat provides a distinct review lens -- security, performance, accessibility, AI safety, and more -- producing a unified, adjudicated verdict.

**Local models, local machine.** Hat Stack runs on your machine using [Ollama](https://ollama.com). No cloud API keys required for the core experience. Cloud models are optional for heavier workloads.

> **Not every hat runs on every diff.** Only **4 hats are always-on** (Black, Blue, Purple, Gold). The remaining 14 activate when the diff matches their trigger conditions. A typical PR activates 4-8 hats.

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

---

## Local Model Pool

Hat Stack uses these local Ollama models by default (no cloud needed):

| Model | Size | Effective Params | Role |
|-------|------|------------------|------|
| `gemma4:e2b` | 7.2GB | 2.3B | Fast scanning: White, Blue, Silver, Teal |
| `gemma4:e4b` | 9.6GB | 4.5B | Security analysis: Black, Purple (local mode) |
| `qwen3.5:9b` | 6.1GB | 9B | Deep reasoning: Red, Brown (local mode) |

Pull all three for full local coverage:

```bash
ollama pull gemma4:e2b gemma4:e4b qwen3.5:9b
```

---

## Cloud Models (Optional)

For heavier workloads, Hat Stack supports Ollama Cloud models. Set `OLLAMA_API_KEY` to enable:

```bash
export OLLAMA_API_KEY="your-key-from-ollama-com"
# Get a key at: https://ollama.com/settings/keys
```

Cloud models (Tier 1-4) include: glm-5.1, kimi-k2.5, deepseek-v3.2, devstral-2, minimax-m2.7, nemotron-3-super, qwen3-coder, and more. See [`scripts/hat_configs.yml`](scripts/hat_configs.yml) for the full pool.

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

This is automatic. No configuration needed.

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

## The 18 Hats

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

Full specifications: [`CATALOG.md`](CATALOG.md) · Individual hat docs: [`hats/`](hats/)

---

## Verdicts

| Verdict | Meaning | Condition |
|---------|---------|-----------|
| **ALLOW** | Safe to merge | No CRITICAL findings; risk score <= 20 |
| **ESCALATE** | Requires human review | HIGH findings; risk score 21-60 |
| **QUARANTINE** | Cannot merge pending adjudication | CRITICAL finding; risk score > 60 |

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

Hat Stack also runs as GitHub Actions for CI/CD integration. See:

- [`FORK_SETUP.md`](FORK_SETUP.md) -- Fork and setup guide for GitHub Actions
- [`.github/workflows/`](.github/workflows/) -- Reusable workflows, dispatch handler, task runner
- `OLLAMA_API_KEY` -- Required as a Repository Secret for cloud models in CI

---

## Architecture

```
Layer 5: CLI / MCP Server / IDE Extension / CI/CD Trigger
Layer 4: Conductor -- Hat Selector, Gate Engine, Retry, State Manager, Consolidator, CoVE
Layer 3: 18 Hat Agents -- each with dedicated persona + model
Layer 2: MCP (Tool Integration) / A2A (Agent-to-Agent)
Layer 1: Ollama (Local + Cloud) / Vector Stores / Key-Value Stores
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [`FORK_SETUP.md`](FORK_SETUP.md) | GitHub Actions fork and setup guide |
| [`SPEC.md`](SPEC.md) | Primary specification -- orchestration, gates, retry, HITL, CI/CD |
| [`CATALOG.md`](CATALOG.md) | Master Hat Registry -- triggers, severity grading, risk scores |
| [`hats/`](hats/) | Individual hat specifications |
| [`scripts/hat_configs.yml`](scripts/hat_configs.yml) | Model pool and hat-to-model configuration |
| [`.env.example`](.env.example) | Environment variable template |

---

## Repository Layout

```
hat_stack/
  scripts/
    hats_runner.py           Review orchestrator (Conductor)
    hats_task_runner.py       Task orchestrator (generate, refactor, plan, etc.)
    hats_common.py            Shared library: call_ollama, retry, circuit breaker, concurrency
    hat_selector.py           Hat selection engine (keyword + AST + dependency)
    gates.py                  Gate engine (cost, security, consistency, timeout, decision)
    consolidator.py           Finding deduplication and conflict detection
    state.py                  Run state persistence and checkpoint resume
    hat_configs.yml           Model pool and hat configuration
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