# Master Hat Registry

The Hats Team — Complete Role Catalog (section 4.1)

| # | Emoji | Hat Name | Run Mode | Trigger Conditions | Primary Focus |
|---|-------|----------|----------|--------------------|---------------|
| 1 | 🔴 | [Red Hat — Failure & Resilience](hats/01_red_hat.md) | Conditional | Error handling, retries, DB writes, shared state, async pipelines, concurrency | Cascade failures, race conditions, single points of failure, chaos readiness |
| 2 | ⚫ | [Black Hat — Security & Exploits](hats/02_black_hat.md) | **Always** | Every PR (mandatory baseline) | Prompt injection, credential leakage, privilege escalation, OWASP GenAI Top 10 |
| 3 | ⚪ | [White Hat — Efficiency & Resources](hats/03_white_hat.md) | Conditional | Loops, DB queries, LLM calls, large data processing, batch operations | Token waste reduction, compute budgeting, memory optimization |
| 4 | 🟡 | [Yellow Hat — Synergies & Integration](hats/04_yellow_hat.md) | Conditional | New features touching ≥2 services/components, API changes | Cross-component value, shared abstractions, dependency optimization |
| 5 | 🟢 | [Green Hat — Evolution & Extensibility](hats/05_green_hat.md) | Conditional | Architecture changes, new modules, public API changes | Versioning, deprecation, plugin architecture, future-proofing |
| 6 | 🔵 | [Blue Hat — Process & Specification](hats/06_blue_hat.md) | **Always** | Every PR (mandatory baseline) | Spec coverage, test completeness, commit hygiene, documentation |
| 7 | 🟣 | [Indigo Hat — Cross-Feature Architecture](hats/07_indigo_hat.md) | Conditional | PR modifies >2 modules, changes integration points | Macro-level DRY violations, duplicated pipelines, shared abstractions |
| 8 | 🩵 | [Cyan Hat — Innovation & Feasibility](hats/08_cyan_hat.md) | Conditional | Experimental patterns, new tech stacks, novel LLM usage | Technical feasibility, risk/ROI analysis, prototype validation |
| 9 | 🟪 | [Purple Hat — AI Safety & Alignment](hats/09_purple_hat.md) | **Always** | Every PR (mandatory baseline) | OWASP Agentic Top 10, bias detection, PII leakage, model alignment |
| 10 | 🟠 | [Orange Hat — DevOps & Automation](hats/10_orange_hat.md) | Conditional | Dockerfiles, CI YAML, deployment scripts, Terraform, Helm charts | Pipeline health, IaC quality, container security, deployment safety |
| 11 | 🪨 | [Silver Hat — Context & Token Optimization](hats/11_silver_hat.md) | Conditional | LLM prompt building, RAG pipelines, context window management | Token counting, context compression, hybrid retrieval optimization |
| 12 | 💎 | [Azure Hat — MCP & Protocol Integration](hats/12_azure_hat.md) | Conditional | Tool calls, function calling, MCP schema usage, A2A contracts | MCP contract validation, A2A schema enforcement, type safety |
| 13 | 🟤 | [Brown Hat — Data Governance & Privacy](hats/13_brown_hat.md) | Conditional | PII handling, user data storage, logging, data pipelines | GDPR/CCPA/HIPAA compliance, data minimization, audit logging |
| 14 | ⚙️ | [Gray Hat — Observability & Reliability](hats/14_gray_hat.md) | Conditional | Production services, long-running agents, SLA-bound endpoints | Distributed tracing, SLO/SLA monitoring, alerting, latency budgeting |
| 15 | ♿ | [Teal Hat — Accessibility & Inclusion](hats/15_teal_hat.md) | Conditional | UI changes, API responses, content generation, i18n/l10n | WCAG compliance, screen-reader compatibility, inclusive design |
| 16 | 🔗 | [Steel Hat — Supply Chain & Dependencies](hats/16_steel_hat.md) | Conditional | Dependency changes, lockfile updates, new package additions | SBOM generation, vulnerability scanning, license compliance |
| 17 | 🧪 | [Chartreuse Hat — Testing & Evaluation](hats/17_chartreuse_hat.md) | Conditional | Test additions/changes, evaluation pipelines, benchmark updates | Test coverage, RAGAS metrics, prompt evaluation, regression detection |
| 18 | ✨ | [Gold Hat — CoVE (Convergent Verification & Expert) — Final QA](hats/18_gold_hat.md) | **Always (Last)** | After all other hats complete | 14-dimension adversarial QA, merge-ready decision, severity adjudication |

> **Always hats** (2, 6, 9, 18) run on every PR. All other hats are **Conditional** and activate based on their trigger conditions.

---

Back to [README](README.md)
