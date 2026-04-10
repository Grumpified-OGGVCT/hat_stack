# 🎩 hat_stack

**The Universal Agentic-AI Engineering Stack — Hats Team Specification**

**Version:** 2.0 · **Status:** Production-Ready · **License:** [MIT](LICENSE)

Language-agnostic · Framework-agnostic · Domain-agnostic

---

## What Is the Hats Team?

The Hats Team is a **complete, production-grade Agentic-AI engineering stack** organized around a hat-based role system — a team of **18 specialized micro-agents**, each wearing a metaphorical "hat" that gives it a distinct review lens, set of responsibilities, and decision-making authority.

The system inspects any code change, pull request, architectural decision, or deployment event through every relevant lens simultaneously, producing a unified, adjudicated verdict that can be fully automated or escalated to human reviewers.

> **Not every hat runs on every PR.** Only **4 hats are always-on** (⚫ Black, 🔵 Blue, 🟪 Purple, ✨ Gold). The remaining 14 are **conditional** — they activate only when the PR's changed files, commit messages, and AST patterns match their trigger conditions. A typical PR activates 4–8 hats, not 18.

---

## Key Differentiators

- **18 specialized hats** covering resilience, security, efficiency, integration, evolution, process, cross-feature architecture, innovation, AI safety, DevOps, token optimization, MCP/A2A contract validation, data governance, observability, accessibility, supply-chain integrity, and final convergent QA
- **20 personas** that embody human-like expertise, enabling each hat to reason with the nuance of a domain specialist rather than a generic LLM
- **A formal gate system** with five gate types (Quality, Cost, Security, Consistency, Timeliness) that control flow between orchestration phases
- **Explicit retry, backoff, and circuit-breaker policies** that prevent cascading failures across the agent network
- **A complete HITL framework** with interrupt-based checkpoints, escalation routing, approval workflows, and audit trails
- **Supply-chain and dependency-aware analysis** as a first-class concern, not an afterthought

---

## Design Philosophy

The system is built on eight core tenets:

| # | Principle | Summary |
|---|-----------|---------|
| 1 | **Defense in Depth** | Every finding corroborated by ≥2 hats before escalating. Black Hat may quarantine CRITICAL security findings pending Gold Hat adjudication. |
| 2 | **Cost Consciousness** | Tiered model selection: cheap/fast for scanning, premium for adjudication. Global token budget gate prevents runaway costs. |
| 3 | **Graceful Degradation** | No single hat failure blocks the pipeline. Only Gold Hat (CoVE) issues the final hard-block verdict. |
| 4 | **Stateful Checkpointing** | Orchestration graph persisted at every node boundary. Any interrupted run resumes from last checkpoint. |
| 5 | **Human Authority** | Advisory by default. HITL reviewers may override any automated recommendation. |
| 6 | **Universal Applicability** | Language-, framework-, and domain-agnostic. Triggers are keyword- and AST-pattern-based. |
| 7 | **Interoperability First** | Structured JSON schemas. MCP-compatible interfaces for external tool composition. |
| 8 | **Continuous Learning** | Hat effectiveness metrics tracked over time and fed back into persona prompt tuning. |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 5 — PRESENTATION & GATEWAY                                   │
│  CLI · Web UI · IDE Extension · CI/CD Trigger · API Endpoint        │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 4 — ORCHESTRATION (The Conductor)                            │
│  Hat Selector · Gate Engine · Retry Controller · State Manager       │
│  Consolidator · CoVE Final Adjudicator                               │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 3 — HAT AGENTS (Micro-Agents)                                │
│  18 specialized hat nodes, each with dedicated persona + tools       │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 2 — PROTOCOL LAYER                                           │
│  MCP (Tool Integration) · A2A (Agent-to-Agent) · AG-UI (Frontend)   │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 1 — INFRASTRUCTURE                                           │
│  LLM Providers · Vector Stores · Key-Value Stores · Message Queues  │
│  Observability (OTel) · Secret Management · Cost Tracking           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Merge Decision Verdicts

| Verdict | Meaning | Condition |
|---------|---------|-----------|
| **`ALLOW`** | Safe to merge | No CRITICAL findings; composite risk score ≤ 20 |
| **`ESCALATE`** | Requires human review | One or more HIGH findings; risk score 21–60; or AI Act high-risk classification |
| **`QUARANTINE`** | Temporary hold — cannot merge pending adjudication | Any CRITICAL finding triggers a quarantine hold pending Gold Hat adjudication; risk score > 60 |

---

## The 18 Hats — Complete Registry

> Full table with trigger conditions: [`CATALOG.md`](CATALOG.md) · Full technical specification: [`SPEC.md`](SPEC.md)

| # | Hat | Run Mode | Spec |
|---|-----|----------|------|
| 1 | 🔴 Red Hat — Failure & Resilience | Conditional | [`01_red_hat.md`](hats/01_red_hat.md) |
| 2 | ⚫ Black Hat — Security & Exploits | **Always** | [`02_black_hat.md`](hats/02_black_hat.md) |
| 3 | ⚪ White Hat — Efficiency & Resources | Conditional | [`03_white_hat.md`](hats/03_white_hat.md) |
| 4 | 🟡 Yellow Hat — Synergies & Integration | Conditional | [`04_yellow_hat.md`](hats/04_yellow_hat.md) |
| 5 | 🟢 Green Hat — Evolution & Extensibility | Conditional | [`05_green_hat.md`](hats/05_green_hat.md) |
| 6 | 🔵 Blue Hat — Process & Specification | **Always** | [`06_blue_hat.md`](hats/06_blue_hat.md) |
| 7 | 🟣 Indigo Hat — Cross-Feature Architecture | Conditional | [`07_indigo_hat.md`](hats/07_indigo_hat.md) |
| 8 | 🩵 Cyan Hat — Innovation & Feasibility | Conditional | [`08_cyan_hat.md`](hats/08_cyan_hat.md) |
| 9 | 🟪 Purple Hat — AI Safety & Alignment | **Always** | [`09_purple_hat.md`](hats/09_purple_hat.md) |
| 10 | 🟠 Orange Hat — DevOps & Automation | Conditional | [`10_orange_hat.md`](hats/10_orange_hat.md) |
| 11 | 🪨 Silver Hat — Context & Token Optimization | Conditional | [`11_silver_hat.md`](hats/11_silver_hat.md) |
| 12 | 💎 Azure Hat — MCP & Protocol Integration | Conditional | [`12_azure_hat.md`](hats/12_azure_hat.md) |
| 13 | 🟤 Brown Hat — Data Governance & Privacy | Conditional | [`13_brown_hat.md`](hats/13_brown_hat.md) |
| 14 | ⚙️ Gray Hat — Observability & Reliability | Conditional | [`14_gray_hat.md`](hats/14_gray_hat.md) |
| 15 | ♿ Teal Hat — Accessibility & Inclusion | Conditional | [`15_teal_hat.md`](hats/15_teal_hat.md) |
| 16 | 🔗 Steel Hat — Supply Chain & Dependencies | Conditional | [`16_steel_hat.md`](hats/16_steel_hat.md) |
| 17 | 🧪 Chartreuse Hat — Testing & Evaluation | Conditional | [`17_chartreuse_hat.md`](hats/17_chartreuse_hat.md) |
| 18 | ✨ Gold Hat — CoVE Final QA | **Always (Last)** | [`18_gold_hat.md`](hats/18_gold_hat.md) |

---

## Phased Adoption Path

You don't need to adopt all 18 hats at once. The recommended path:

| Phase | Hats | Coverage |
|-------|------|----------|
| **Week 1** | ⚫ Black, 🔵 Blue, 🟪 Purple | Mandatory baseline — security, process, AI safety |
| **Week 2** | + 🔴 Red, ⚪ White, 🔗 Steel | Add resilience, efficiency, supply-chain |
| **Week 3** | + 🟠 Orange, 🧪 Chartreuse, ⚙️ Gray | Add DevOps, testing, observability |
| **Week 4+** | Remaining hats as needed | Full catalog as your team's confidence grows |

---

## 🚀 Use It — GitHub Actions Integration

Hat Stack runs **in GitHub** as a tool your other projects can call. It does two things:

1. **Review** — Analyze PRs and diffs through 18 expert lenses
2. **Task** — Actually *do work*: generate code, write docs, create plans, build tests

### Quick Start: Fork & Go

1. **Fork** this repo
2. Add `OLLAMA_API_KEY` as a **Repository Secret** in your fork
3. Done — your fork's workflows are live

> **Your keys stay yours.** GitHub Secrets are encrypted, never in code, and never transferred to forks. See [`FORK_SETUP.md`](FORK_SETUP.md) for the full guide.

### Hook Up Your Other Projects (Review Mode)

**Option A — Reusable Workflow** (recommended):
```yaml
# In your other repo: .github/workflows/hats.yml
name: "🎩 Hats Review"
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  get-diff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Generate diff
        id: diff
        run: |
          git diff origin/${{ github.base_ref }}...HEAD > /tmp/pr.diff
      - uses: actions/upload-artifact@v4
        with:
          name: pr-diff
          path: /tmp/pr.diff

  hats-review:
    needs: get-diff
    uses: YOUR_USERNAME/hat_stack/.github/workflows/hats-review.yml@main
    with:
      diff_artifact: pr-diff
    secrets:
      ollama_api_key: ${{ secrets.OLLAMA_API_KEY }}
```

**Option B — Composite Action**:
```yaml
- uses: YOUR_USERNAME/hat_stack/.github/actions/run-hats@main
  with:
    diff_file: /tmp/pr.diff
  env:
    OLLAMA_API_KEY: ${{ secrets.OLLAMA_API_KEY }}
```

### 🤖 Task Mode — Tell It to DO Things (via `hat` CLI or GitHub CLI)

Install the `hat` CLI, then your local agent (Copilot, etc.) can dispatch real work:

```bash
# Install (one time)
cp scripts/hat /usr/local/bin/hat   # or add scripts/ to PATH
export HAT_STACK_REPO="YOUR_USERNAME/hat_stack"

# Generate code
hat task generate_code "Build a FastAPI auth module with JWT" \
  --repo myorg/app --pr 42 --category code --genre api --project auth-service

# Write documentation
hat task generate_docs "Write API docs for /users endpoints" --repo myorg/app --issue 10

# Create a plan
hat task plan "Plan migration from REST to GraphQL" --repo myorg/app

# Generate tests
hat task test "Write unit tests for auth.py" --repo myorg/app --pr 88

# Deep analysis
hat task analyze "Security audit of payment processing" --repo myorg/payments

# Review a diff
git diff main | hat review - --repo myorg/app --pr 123
```

Task runs now support a structured playground sandbox on the runner:

- Default workspace root: `/tmp/hats-playground`
- Layout: `<workspace>/<category>/<genre>/<project>/<run-id>/`
- Contents: generated files, `HATS_TASK_SUMMARY.md`, `hats_task_result.json`, `PLAYGROUND_MANIFEST.json`
- Persistence: both the run output and the full playground tree are uploaded as workflow artifacts

Or dispatch directly via `gh` CLI (what your Copilot agent would call):

```bash
gh api repos/YOUR_USERNAME/hat_stack/dispatches \
  -f event_type=run-task \
  -f client_payload='{"task":"generate_code","prompt":"Build auth module","callback_repo":"myorg/app","callback_pr":"42"}'
```

→ Full integration guide: [`FORK_SETUP.md`](FORK_SETUP.md)

---

## Documentation

| Document | Description |
|----------|-------------|
| [`README.md`](README.md) | This file — project overview, architecture, and quick reference |
| [`FORK_SETUP.md`](FORK_SETUP.md) | **Fork & Setup Guide** — get your own working Hat Stack in 5 minutes, secret management, integration patterns |
| [`SPEC.md`](SPEC.md) | **Primary specification** — orchestration, gates, retry policies, HITL framework, CI/CD integration, security, deployment guide, and all appendices |
| [`CATALOG.md`](CATALOG.md) | **Master Hat Registry** — design philosophy, full hat table with triggers, severity grading, and composite risk score |
| [`hats/01_red_hat.md`](hats/01_red_hat.md) – [`hats/18_gold_hat.md`](hats/18_gold_hat.md) | Individual hat specifications with detailed assignments, severity grading, tools, and token budgets |
| [`hats/AGENTIC_AI_HATS_TEAM_STACK.md`](hats/AGENTIC_AI_HATS_TEAM_STACK.md) | **Complete Specification** (standalone) — the full 16-section specification including inline hat details, personas, orchestration, gates, and appendices |
| [`hats/HATS_TEAM_IMPLEMENTATION_GUIDE.md`](hats/HATS_TEAM_IMPLEMENTATION_GUIDE.md) | **Implementation Guide** — running the Hats Team on Ollama Cloud + n8n: LLM backend mapping, cost-optimized model selection, n8n workflow architecture, security box, self-improvement pipeline, and step-by-step deployment |
| [`hats/HATS_TEAM_CONCERNS_DISCUSSION.md`](hats/HATS_TEAM_CONCERNS_DISCUSSION.md) | **Addressing Concerns** — honest engagement with 17 real-world concerns including over-engineering, cost, latency, false positives, non-determinism, and "show me working code" |

---

## Repository Layout

```
hat_stack/
├── README.md                                  ← This file — project overview & navigation
├── FORK_SETUP.md                              ← Fork & setup guide (start here for your own instance)
├── .env.example                               ← Environment template (copy to .env for local use)
├── CATALOG.md                                 ← Master Hat Registry (full table + design philosophy)
├── SPEC.md                                    ← Primary specification (16 sections + appendices)
├── LICENSE                                    ← MIT License
├── .github/
│   ├── workflows/
│   │   ├── hats-review.yml                    ← Reusable workflow (other repos call this for reviews)
│   │   ├── hats-dispatch.yml                  ← Dispatch handler (API-triggered reviews)
│   │   ├── hats-task.yml                      ← Task execution (generate code, docs, plans, etc.)
│   │   └── hats-self-review.yml               ← Self-review (reviews PRs to this repo)
│   └── actions/
│       └── run-hats/
│           └── action.yml                     ← Composite action (direct step in any workflow)
├── scripts/
│   ├── hat                                    ← CLI wrapper — dispatch tasks from terminal or agents
│   ├── hats_runner.py                         ← Review orchestrator (Conductor + all hat logic)
│   ├── hats_task_runner.py                    ← Task orchestrator (generate, refactor, plan, etc.)
│   ├── hat_configs.yml                        ← Hat-to-model mapping & configuration
│   └── requirements.txt                       ← Python dependencies
└── hats/
    ├── 01_red_hat.md                          ← Individual hat specifications
    ├── 02_black_hat.md
    ├── ...
    ├── 18_gold_hat.md
    ├── AGENTIC_AI_HATS_TEAM_STACK.md          ← Complete standalone specification
    ├── HATS_TEAM_IMPLEMENTATION_GUIDE.md      ← Implementation guide: Ollama Cloud + n8n
    └── HATS_TEAM_CONCERNS_DISCUSSION.md       ← Addressing concerns & FAQ
```

---

## License

MIT — See [LICENSE](LICENSE).
