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
| **`QUARANTINE`** | Hard block — cannot merge | Any CRITICAL finding from any hat; risk score > 60 |

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

## Documentation

| Document | Description |
|----------|-------------|
| [`README.md`](README.md) | This file — project overview, architecture, and quick reference |
| [`SPEC.md`](SPEC.md) | **Primary specification** — orchestration, gates, retry policies, HITL framework, CI/CD integration, security, deployment guide, and all appendices |
| [`CATALOG.md`](CATALOG.md) | **Master Hat Registry** — design philosophy, full hat table with triggers, severity grading, and composite risk score |
| [`hats/01_red_hat.md`](hats/01_red_hat.md) – [`hats/18_gold_hat.md`](hats/18_gold_hat.md) | Individual hat specifications with detailed assignments, severity grading, tools, and token budgets |
| [`hats/AGENTIC_AI_HATS_TEAM_STACK.md`](hats/AGENTIC_AI_HATS_TEAM_STACK.md) | **Complete Specification** (standalone) — the full 16-section specification including inline hat details, personas, orchestration, gates, and appendices |
| [`hats/HATS_TEAM_IMPLEMENTATION_GUIDE.md`](hats/HATS_TEAM_IMPLEMENTATION_GUIDE.md) | **Appendix E — Implementation Guide** — running the Hats Team on Ollama Cloud + n8n: LLM backend mapping, cost-optimized model selection, n8n workflow architecture, security box, self-improvement pipeline, and step-by-step deployment |
| [`hats/HATS_TEAM_CONCERNS_DISCUSSION.md`](hats/HATS_TEAM_CONCERNS_DISCUSSION.md) | **Appendix F — Addressing Concerns** — honest engagement with 17 real-world concerns including over-engineering, cost, latency, false positives, non-determinism, and "show me working code" |

---

## Repository Layout

```
hat_stack/
├── README.md                                  ← This file — project overview & navigation
├── CATALOG.md                                 ← Master Hat Registry (full table + design philosophy)
├── SPEC.md                                    ← Primary specification (16 sections + appendices)
├── LICENSE                                    ← MIT License
└── hats/
    ├── 01_red_hat.md                          ← Individual hat specifications
    ├── 02_black_hat.md
    ├── ...
    ├── 18_gold_hat.md
    ├── AGENTIC_AI_HATS_TEAM_STACK.md          ← Complete standalone specification
    ├── HATS_TEAM_IMPLEMENTATION_GUIDE.md      ← Appendix E: Ollama Cloud + n8n implementation
    └── HATS_TEAM_CONCERNS_DISCUSSION.md       ← Appendix F: Addressing concerns & FAQ
```

---

## License

MIT — See [LICENSE](LICENSE).

