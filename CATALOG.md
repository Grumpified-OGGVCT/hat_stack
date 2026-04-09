# Master Hat Registry

> **Full specification:** See [SPEC.md](SPEC.md) for the complete technical specification including orchestration architecture, gate system, retry policies, HITL framework, CI/CD integration, security stack, and deployment guide.

---

## Design Philosophy

The Hats Team is built on eight core tenets:

| # | Principle | Description |
|---|-----------|-------------|
| 1 | **Defense in Depth** | Every finding must be corroborated by at least two independent hats before escalating. No single hat may issue a final merge rejection alone; however, Black Hat may unilaterally place a change into **QUARANTINE** for a CRITICAL security finding, creating a temporary merge hold pending Gold Hat adjudication or an explicit policy/HITL decision. |
| 2 | **Cost Consciousness** | Every LLM call is metered. Hats use tiered model selection: cheap/fast models for scanning, premium models for final adjudication. A global token budget gate prevents runaway costs. |
| 3 | **Graceful Degradation** | If a hat times out or fails, the Conductor records the gap and proceeds. No single hat failure should block the pipeline. The **only** hat that may issue the final hard-block verdict in the default automated flow is the Gold Hat (CoVE), including confirmation, release, or rejection of any Black/Purple-initiated QUARANTINE. |
| 4 | **Stateful Checkpointing** | The entire orchestration graph is persisted at every node boundary. Any interrupted run can be resumed from the last successful checkpoint. |
| 5 | **Human Authority** | The system is advisory by default. Explicitly configured policies may auto-enforce outcomes (for example, retaining QUARANTINE or auto-rejecting PRs with confirmed CRITICAL security findings). HITL reviewers may override any automated recommendation or quarantine unless a mandatory compliance policy forbids release; absent such policy, the final non-human hard-block verdict remains Gold Hat's responsibility. |
| 6 | **Universal Applicability** | The hat taxonomy, gate logic, and orchestration patterns apply to any language, framework, or domain. Hat triggers are keyword- and AST-pattern-based, not language-specific. |
| 7 | **Interoperability First** | All inter-hat communication uses structured JSON schemas. Hats expose findings via MCP-compatible interfaces, enabling composition with external tools. |
| 8 | **Continuous Learning** | Hat effectiveness metrics (false-positive rate, coverage, latency) are tracked over time and fed back into persona prompt tuning. |

---

## Merge Decision Verdicts

| Verdict | Meaning | Condition |
|---------|---------|-----------|
| **`ALLOW`** | Safe to merge | No CRITICAL findings; composite risk score ≤ 20 |
| **`ESCALATE`** | Requires human review | One or more HIGH findings; risk score 21–60; or AI Act high-risk classification |
| **`QUARANTINE`** | Hard block — cannot merge | Any CRITICAL finding from any hat; risk score > 60 |

---

## Complete Hat Registry (Section 4.1)

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

> **Always hats** (⚫ #2, 🔵 #6, 🟪 #9, ✨ #18) run on every PR. All other hats are **Conditional** and activate based on their trigger conditions.

---

## Severity Grading

All hats use a consistent four-level severity scale:

| Severity | Definition | Required Action |
|----------|-----------|----------------|
| **CRITICAL** | Actively exploitable vulnerability or guaranteed production failure | Must be fixed before merge. Hard block. No exceptions. |
| **HIGH** | Significant risk under production conditions | Must be addressed before merge or explicitly accepted by Tier-2+ reviewer |
| **MEDIUM** | Best-practice deviation that could become HIGH/CRITICAL | Should be addressed; may be deferred to follow-up PR if documented |
| **LOW** | Minor improvement or best-practice suggestion | Informational. No action required for merge. |

---

## Composite Risk Score

The Gold Hat (CoVE) computes a composite risk score (0–100):

```
risk_score = min(100,
  CRITICAL_count × 20  (capped at 80) +
  HIGH_count × 5       (capped at 40) +
  MEDIUM_count × 1     (capped at 10) +
  LOW_count × 0.1      (capped at 5)
)
```

| Score Range | Verdict |
|-------------|---------|
| 0–20 | `ALLOW` |
| 21–60 | `ESCALATE` |
| 61–100 | `QUARANTINE` |
| Any CRITICAL | `QUARANTINE` (regardless of score) |

---

Back to [README](README.md) · Full spec: [SPEC.md](SPEC.md)
