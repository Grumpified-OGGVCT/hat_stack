# 🎩 The Universal Agentic-AI Engineering Stack — Hats Team Specification

**Version:** 2.0 · **Date:** 2026-04-10 · **Status:** Production-Ready
**License:** MIT · **Scope:** Universal — language-agnostic, framework-agnostic, domain-agnostic

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Design Philosophy & Principles](#2-design-philosophy--principles)
3. [Technology Landscape (2025–2026)](#3-technology-landscape-20252026)
4. [The Hats Team — Complete Role Catalog](#4-the-hats-team--complete-role-catalog)
5. [Persona Definitions & Expertise Matrix](#5-persona-definitions--expertise-matrix)
6. [Orchestration Architecture — The Conductor](#6-orchestration-architecture--the-conductor)
7. [Gate System — Quality, Cost, Security & Flow Control](#7-gate-system--quality-cost-security--flow-control)
8. [Retry, Backoff & Circuit-Breaker Policies](#8-retry-backoff--circuit-breaker-policies)
9. [Inter-Hat Communication & State Management](#9-inter-hat-communication--state-management)
10. [Human-in-the-Loop (HITL) Framework](#10-human-in-the-loop-hitl-framework)
11. [Observability, Tracing & Cost Tracking](#11-observability-tracing--cost-tracking)
12. [CI/CD Integration & Deployment Architecture](#12-cicd-integration--deployment-architecture)
13. [Security Stack & Compliance](#13-security-stack--compliance)
14. [End-to-End Walkthrough](#14-end-to-end-walkthrough)
15. [Quick-Start Deployment Guide](#15-quick-start-deployment-guide)
16. [Appendices](#16-appendices)

---

## 1. Executive Summary

This document defines a **complete, production-grade Agentic-AI engineering stack** organized around a **hat-based role system** — a team of specialized micro-agents, each wearing a metaphorical "hat" that gives it a distinct perspective, set of responsibilities, and decision-making authority. The system is designed to inspect any code change, pull request, architectural decision, or deployment event through every relevant lens simultaneously, producing a unified, adjudicated verdict that can be fully automated or escalated to human reviewers.

The stack is grounded in the **2025–2026 agentic AI ecosystem**, incorporating the Model Context Protocol (MCP), Agent-to-Agent Protocol (A2A), LangGraph 2.0 stateful orchestration, OWASP GenAI Top 10 security controls, OpenTelemetry-based observability, and token-level cost tracking. It is framework-agnostic by design — implementations may use LangGraph, CrewAI, AutoGen, Google ADK, or any orchestration engine that supports stateful nodes, conditional edges, and checkpoint persistence.

**Key differentiators from prior art:**

- **18 specialized hats** (up from the common 6–8) covering resilience, security, efficiency, integration, evolution, process, cross-feature architecture, innovation, AI safety, DevOps, token optimization, MCP/A2A contract validation, data governance, observability, accessibility, supply-chain integrity, and final convergent QA.
- **20 personas** that embody human-like expertise, enabling each hat to reason with the nuance of a domain specialist rather than a generic LLM.
- **A formal gate system** with five gate types (Quality, Cost, Security, Consistency, Timeliness) that control flow between orchestration phases.
- **Explicit retry, backoff, and circuit-breaker policies** that prevent cascading failures across the agent network.
- **A complete HITL framework** with interrupt-based checkpoints, escalation routing, approval workflows, and audit trails.
- **Supply-chain and dependency-aware analysis** — a first-class concern, not an afterthought.

---

## 2. Design Philosophy & Principles

### 2.1 Core Tenets

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

### 2.2 Architectural Layers

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

## 3. Technology Landscape (2025–2026)

### 3.1 Protocol Layer

| Protocol | Origin | Purpose | Maturity | Key Adoption Signal |
|----------|--------|---------|----------|-------------------|
| **MCP (Model Context Protocol)** | Anthropic | Agent-to-tool/resource integration (vertical) | Production | ~97M monthly SDK downloads, 10,000+ servers |
| **A2A (Agent-to-Agent)** | Google | Inter-agent communication and delegation (horizontal) | Production | Integrated into Google ADK, growing ecosystem |
| **ACP (Agent Communication Protocol)** | IBM | Enterprise-grade agent messaging with QoS | Emerging | SAP integration, enterprise pilots |
| **AG-UI / A2UI** | Community | Standardized AI agent front-end interfaces | Emerging | Multi-framework adoption growing |

**MCP vs A2A — when to use which:**
- **MCP** when an agent needs to call a tool, read a file, query a database, or access any external resource. Think of it as the "USB port" for agents — standardized, plug-and-play, per-agent scope.
- **A2A** when two or more agents need to negotiate, delegate, or collaborate on a task. Think of it as the "email system" for agents — asynchronous, authenticated, with task-handshake protocols.
- The Hats system uses **MCP** for each hat's tool access (file reading, static analysis, LLM calls) and **A2A** for inter-hat communication (report sharing, conflict resolution, escalation handoffs).

### 3.2 Orchestration Engines

| Engine | Strengths | Best For |
|--------|-----------|----------|
| **LangGraph 2.0** | State-graph with conditional edges, persistent checkpoints, interrupt nodes for HITL | Primary recommendation — most mature for stateful multi-step agents |
| **CrewAI** | Role-based agent definition, built-in task delegation, easy onboarding | Simpler setups, rapid prototyping |
| **AutoGen (v0.4+)** | Async-native, OpenTelemetry integration, observable message passing | Systems requiring fine-grained message tracing |
| **Google ADK** | Native A2A support, multimodal agents, cloud-native | Google Cloud-heavy stacks |

### 3.3 Supporting Toolchain

| Category | Tools (2025–2026) |
|----------|-------------------|
| **LLM Providers** | OpenAI (GPT-4o, o3), Anthropic (Claude Opus 4, Sonnet 4), Google (Gemini 2.5 Pro/Flash), Meta (Llama 4), Mistral, DeepSeek |
| **Vector Stores** | Pinecone, Weaviate, Qdrant, pgvector, ChromaDB |
| **Static Analysis** | Semgrep, Trivy, Bandit (Python), ESLint (TS), SonarQube |
| **Observability** | OpenTelemetry SDK, Prometheus, Grafana, LangSmith, Arize Phoenix |
| **CI/CD** | GitHub Actions, GitLab CI, Argo Workflows, Tekton |
| **Security Scanning** | Snyk, Trivy, OWASP ZAP, grype, Syft (SBOM) |
| **Secret Management** | HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager |
| **Infrastructure** | Docker, Kubernetes, Terraform, Pulumi |
| **Testing** | pytest, Jest, RAGAS (RAG eval), DeepEval, promptfoo |

---

## 4. The Hats Team — Complete Role Catalog

| # | Emoji | Hat Name | Run Mode | Trigger Conditions | Primary Focus |
|---|-------|----------|----------|--------------------|---------------|
| 1 | 🔴 | **[Red Hat — Failure & Resilience](hats/01_red_hat.md)** | Conditional | Error handling, retries, DB writes, shared state, async pipelines, concurrency | Cascade failures, race conditions, single points of failure, chaos readiness |
| 2 | ⚫ | **[Black Hat — Security & Exploits](hats/02_black_hat.md)** | **Always** | Every PR (mandatory baseline) | Prompt injection, credential leakage, privilege escalation, OWASP GenAI Top 10 |
| 3 | ⚪ | **[White Hat — Efficiency & Resources](hats/03_white_hat.md)** | Conditional | Loops, DB queries, LLM calls, large data processing, batch operations | Token waste reduction, compute budgeting, memory optimization |
| 4 | 🟡 | **[Yellow Hat — Synergies & Integration](hats/04_yellow_hat.md)** | Conditional | New features touching ≥2 services/components, API changes | Cross-component value, shared abstractions, dependency optimization |
| 5 | 🟢 | **[Green Hat — Evolution & Extensibility](hats/05_green_hat.md)** | Conditional | Architecture changes, new modules, public API changes | Versioning, deprecation, plugin architecture, future-proofing |
| 6 | 🔵 | **[Blue Hat — Process & Specification](hats/06_blue_hat.md)** | **Always** | Every PR (mandatory baseline) | Spec coverage, test completeness, commit hygiene, documentation |
| 7 | 🟣 | **[Indigo Hat — Cross-Feature Architecture](hats/07_indigo_hat.md)** | Conditional | PR modifies >2 modules, changes integration points | Macro-level DRY violations, duplicated pipelines, shared abstractions |
| 8 | 🩵 | **[Cyan Hat — Innovation & Feasibility](hats/08_cyan_hat.md)** | Conditional | Experimental patterns, new tech stacks, novel LLM usage | Technical feasibility, risk/ROI analysis, prototype validation |
| 9 | 🟪 | **[Purple Hat — AI Safety & Alignment](hats/09_purple_hat.md)** | **Always** | Every PR (mandatory baseline) | OWASP Agentic Top 10, bias detection, PII leakage, model alignment |
| 10 | 🟠 | **[Orange Hat — DevOps & Automation](hats/10_orange_hat.md)** | Conditional | Dockerfiles, CI YAML, deployment scripts, Terraform, Helm charts | Pipeline health, IaC quality, container security, deployment safety |
| 11 | 🪨 | **[Silver Hat — Context & Token Optimization](hats/11_silver_hat.md)** | Conditional | LLM prompt building, RAG pipelines, context window management | Token counting, context compression, hybrid retrieval optimization |
| 12 | 💎 | **[Azure Hat — MCP & Protocol Integration](hats/12_azure_hat.md)** | Conditional | Tool calls, function calling, MCP schema usage, A2A contracts | MCP contract validation, A2A schema enforcement, type safety |
| 13 | 🟤 | **[Brown Hat — Data Governance & Privacy](hats/13_brown_hat.md)** | Conditional | PII handling, user data storage, logging, data pipelines | GDPR/CCPA/HIPAA compliance, data minimization, audit logging |
| 14 | ⚙️ | **[Gray Hat — Observability & Reliability](hats/14_gray_hat.md)** | Conditional | Production services, long-running agents, SLA-bound endpoints | Distributed tracing, SLO/SLA monitoring, alerting, latency budgeting |
| 15 | ♿ | **[Teal Hat — Accessibility & Inclusion](hats/15_teal_hat.md)** | Conditional | UI changes, API responses, content generation, i18n/l10n | WCAG compliance, screen-reader compatibility, inclusive design |
| 16 | 🔗 | **[Steel Hat — Supply Chain & Dependencies](hats/16_steel_hat.md)** | Conditional | Dependency changes, lockfile updates, new package additions | SBOM generation, vulnerability scanning, license compliance |
| 17 | 🧪 | **[Chartreuse Hat — Testing & Evaluation](hats/17_chartreuse_hat.md)** | Conditional | Test additions/changes, evaluation pipelines, benchmark updates | Test coverage, RAGAS metrics, prompt evaluation, regression detection |
| 18 | ✨ | **[Gold Hat — CoVE Final QA](hats/18_gold_hat.md)** | **Always (Last)** | After all other hats complete | 14-dimension adversarial QA, merge-ready decision, severity adjudication |

> 📋 For full detailed specifications of each hat, see the individual files in the [`hats/`](hats/) directory.

---

## 5. Persona Definitions & Expertise Matrix

Each hat is powered by a **persona** — a detailed set of instructions, expertise areas, cross-awareness references, and behavioral constraints that give the micro-agent the nuanced judgment of a domain specialist. Personas are injected as system prompts to the hat's LLM backend.

### 5.1 Complete Persona Registry

| Persona | Core Hat Affinity | Personality Archetype | Primary Responsibilities | Cross-Awareness (consults) | Signature Strength |
|---------|-------------------|-----------------------|--------------------------|---------------------------|-------------------|
| **Sentinel** | ⚫ Black Hat | Battle-hardened security auditor. Precise, methodical, slightly paranoid — trusts nothing by default. | Security audit, guardrail enforcement, incident triage, threat modeling. | Arbiter, Guardian, CoVE | Can trace an exploit path through 7+ service hops mentally. |
| **Scribe** | 🪨 Silver Hat | Meticulous accountant. Obsessed with budgets, counts, and precise measurements. | Token budgeting, context-window accounting, prompt audit trails, cost projection. | Sentinel, Consolidator, Arbiter | Can estimate token count within 5% accuracy without running a tokenizer. |
| **Arbiter** | 🟪 Purple Hat | Wise judge. Balances competing concerns with equanimity. Never rushes to judgment. | Resolve conflicting hat recommendations, enforce policy, risk scoring. | Sentinel, Scribe, CoVE, Guardian | Can find the optimal tradeoff between security, performance, and usability. |
| **Steward** | 💎 Azure Hat | Master craftsman of interfaces. Believes every contract tells a story. | MCP schema validation, A2A contract generation, protocol compliance, type-safety enforcement. | Sentinel, Scribe, Arbiter, Cartographer | Designs contracts so clear they need no documentation. |
| **Consolidator** | — (meta-persona) | Calm conductor. Sees patterns across chaos and finds signal in noise. | Synthesize all hat reports into a unified findings matrix, manage severity weighting, detect duplicates. | ALL personas | Can merge 18 conflicting reports into a single coherent narrative. |
| **Strategist** | 🟢 Green Hat | Long-term visionary. Thinks in years, not sprints. | Roadmap alignment, emerging-pattern identification, growth-path analysis. | Consolidator, Oracle, Catalyst | Predicts architectural pain points 6–12 months before they manifest. |
| **Oracle** | 🟡 Yellow Hat | Scenario modeler. Loves "what if" questions. | Impact simulation (cost, latency, compliance), cross-component synergy identification. | Sentinel, Catalyst, Strategist, Consolidator | Models 50+ "what if" scenarios in the time others analyze one. |
| **Catalyst** | 🟠 Orange Hat | Performance surgeon. Finds bottlenecks like a diagnostician finds symptoms. | Performance profiling, latency/cost optimization, deployment safety. | CoVE, Sentinel, Scribe, Consolidator | Reduces p99 latency by 40% just by reading the diff. |
| **Chronicler** | ⚪ White Hat | Quality guardian with encyclopedic memory of every past decision. | Technical-debt tracking, test-coverage health, code-smell detection, process enforcement. | CoVE, Consolidator, Catalyst, Herald | Remembers every anti-pattern the team has ever introduced and caught. |
| **Herald** | ⚪ White Hat | Documentation perfectionist. Believes unreadable code is broken code. | Documentation generation, knowledge-base synchronization, API doc accuracy. | Palette, CoVE, Consolidator, Chronicler | Produces documentation so clear it reduces onboarding time by 50%. |
| **Scout** | 🟡 Yellow Hat | External intelligence gatherer. Reads the internet so the team doesn't have to. | Competitive-tech scanning, emerging-threat detection, best-practice benchmarking. | Sentinel, Catalyst, Chronicler, Herald, Consolidator | Surfaces relevant industry developments before they hit Hacker News. |
| **Weaver** | 🩵 Cyan Hat | Prompt-engineering meta-optimizer. Treats prompts as living, evolving programs. | Prompt design, self-improvement loops, evaluation methodology, LLM behavior modeling. | ALL personas | Can reduce prompt tokens by 30% while improving output quality by 15%. |
| **Guardian** | 🟤 Brown Hat | Data-stewardship zealot. Protects user privacy as a sacred duty. | Data governance, PIA generation, audit-trail enforcement, consent management. | Sentinel, Arbiter, Consolidator | Can trace every byte of PII through a system of 20+ microservices. |
| **Observer** | ⚙️ Gray Hat | Systems-reliability philosopher. Believes you can only improve what you can measure. | Observability architecture, SLO definition, alerting design, incident readiness. | Catalyst, CoVE, Consolidator | Designs monitoring systems that predict failures 30 minutes before they happen. |
| **Cartographer** | 🟣 Indigo Hat | Mapmaker of codebases. Sees structure in complexity. | Cross-module analysis, dependency mapping, architectural drift detection. | Strategist, Steward, Consolidator | Can detect emerging "big ball of mud" patterns from a single PR. |
| **Smith** | 🔗 Steel Hat | Supply-chain sentinel. Verifies every link in the dependency chain. | SBOM management, vulnerability tracking, license compliance, freshness monitoring. | Sentinel, Observer, Consolidator | Has memorized every critical CVE from the past 24 months. |
| **Validator** | 🧪 Chartreuse Hat | Testing evangelist. Believes untested code is liability, not asset. | Test coverage analysis, quality assessment, RAG/prompt evaluation, regression detection. | Chronicler, CoVE, Consolidator, Weaver | Designs test suites that catch bugs before they're written. |
| **Inclusive** | ♿ Teal Hat | Empathy-first designer. Experiences software as every user might. | Accessibility audit, inclusive language review, i18n readiness, assistive-technology testing. | Herald, CoVE, Consolidator | Can navigate any UI using only keyboard and screen reader. |
| **Resilient** | 🔴 Red Hat | Chaos engineer. Sleeps soundly only when the system survives failures. | Failure-mode analysis, chaos-readiness assessment, retry/circuit-breaker validation. | Catalyst, Observer, CoVE, Consolidator | Designs systems that self-heal before the alert even fires. |
| **CoVE** | ✨ Gold Hat | Supreme adjudicator. Combines the wisdom of all personas into a final verdict. | 14-dimension QA, conflict resolution, merge-decision authority, continuous-improvement tracking. | All personas (through Consolidator) | Makes the right call 99.2% of the time based on historical accuracy tracking. |

### 5.2 Persona System Prompt Template

Each persona is realized through a structured system prompt with the following sections:

```markdown
## [Persona Name] — System Prompt

### Identity
You are [Persona Name], a [archetype description]. Your core hat is [Hat Emoji] [Hat Name].
Your expertise is in [domain], and you approach every task with [behavioral trait].

### Responsibilities
1. [Primary responsibility 1]
2. [Primary responsibility 2]
...

### Knowledge Base
You have deep expertise in:
- [Skill 1]: [Specific knowledge area]
- [Skill 2]: [Specific knowledge area]
...

### Cross-Awareness
When analyzing findings, you consider the perspectives of:
- [Persona A]: They would flag [concern type]
- [Persona B]: They would check [concern type]
...

### Behavioral Constraints
- [Constraint 1: e.g., "Never flag a finding as CRITICAL without providing a concrete exploit scenario"]
- [Constraint 2: e.g., "Always provide a code-level remediation suggestion, not just a description"]
...

### Severity Calibration
- CRITICAL: [Specific criteria for this persona's CRITICAL findings]
- HIGH: [Specific criteria]
- MEDIUM: [Specific criteria]
- LOW: [Specific criteria]

### Output Format
Your report must follow the [format name] schema:
{JSON schema or markdown template}
```

---

## 6. Orchestration Architecture — The Conductor

The **Conductor** is the meta-agent that manages the entire Hats pipeline. It is implemented as a LangGraph state machine (or equivalent) with the following components.

### 6.1 Orchestration Graph

```mermaid
flowchart TD
    A[📥 Trigger: PR / Code Diff / Manual Request] --> B[🔍 Hat Selector]
    
    B --> C[📋 Pre-Flight Checks]
    C --> C1{Cost Budget OK?}
    C1 -- No --> BLOCKED[🛑 Cost Gate: BLOCKED]
    C1 -- Yes --> D[🚀 Dispatch Hat Agents]
    
    D --> D1[Parallel Execution Pool]
    
    D1 --> E1[⚫ Black Hat]
    D1 --> E2[🔵 Blue Hat]
    D1 --> E3[🟪 Purple Hat]
    D1 --> E4[🔴 Red Hat]
    D1 --> E5[⚪ White Hat]
    D1 --> E6[🟡 Yellow Hat]
    D1 --> E7[🟢 Green Hat]
    D1 --> E8[🟣 Indigo Hat]
    D1 --> E9[🩵 Cyan Hat]
    D1 --> E10[🟠 Orange Hat]
    D1 --> E11[🪨 Silver Hat]
    D1 --> E12[💎 Azure Hat]
    D1 --> E13[🟤 Brown Hat]
    D1 --> E14[⚙️ Gray Hat]
    D1 --> E15[♿ Teal Hat]
    D1 --> E16[🔗 Steel Hat]
    D1 --> E17[🧪 Chartreuse Hat]
    
    E1 & E2 & E3 & E4 & E5 & E6 & E7 & E8 & E9 & E10 &
    E11 & E12 & E13 & E14 & E15 & E16 & E17
        --> F{All Hats Complete?}
    
    F -- No (timeout/failure) --> G[🔄 Timeout Handler]
    G --> H{Retry?}
    H -- Yes --> D1
    H -- No --> I[📝 Record Gap]
    I --> J
    
    F -- Yes --> J[📊 Consolidator: Merge Reports]
    J --> K[⚖️ CoVE: Final Adjudication]
    K --> L{Decision}
    
    L -- ALLOW --> M[✅ Merge Approved]
    L -- ESCALATE --> N[👤 HITL Review Queue]
    L -- QUARANTINE --> O[🚫 Merge Blocked]
    
    N --> P[Human Reviews]
    P --> Q{Human Decision}
    Q -- Approve --> M
    Q -- Request Changes --> R[🔧 Developer Fixes]
    R --> A
    Q -- Reject --> O
    
    M --> S[📢 Notification: PR Comment + Slack]
    O --> T[📢 Notification: Block Reason + Fix Guide]
```

### 6.2 Hat Selector — Trigger Logic

The Hat Selector is the first decision node. It analyzes the PR and determines which hats to activate.

**Selection Algorithm:**

1. **Keyword Heuristics** (fast, <50ms): Scan changed file paths and commit messages for trigger keywords.
2. **AST Pattern Detection** (medium, <500ms): Use Semgrep-compatible rules to detect code patterns (e.g., `try/except`, `fetch()`, `SELECT *`).
3. **Dependency Analysis** (medium, <500ms): Check if `package.json`, `requirements.txt`, etc. changed.
4. **Mandatory Baseline**: Black, Blue, and Purple hats are **always** activated regardless of heuristics.

**Keyword Heuristic Mapping:**

| Trigger Keywords / Patterns | Activated Hats |
|-----------------------------|----------------|
| `auth`, `jwt`, `token`, `session`, `password`, `secret`, `api_key`, `credential`, `login`, `permission` | Black (+ Purple) |
| `try`, `catch`, `except`, `panic`, `unwrap`, `retry`, `backoff`, `timeout`, `error` | Red |
| `loop`, `while`, `for_each`, `map`, `filter`, `batch`, `stream`, `paginate` | White |
| `dockerfile`, `docker-compose`, `ci.yaml`, `workflow`, `terraform`, `helm`, `k8s`, `deploy` | Orange |
| `prompt`, `system_message`, `llm`, `chat`, `completion`, `embedding`, `retriev` | Silver + Purple |
| `mcp`, `tool_call`, `function_call`, `a2a`, `agent` | Azure |
| `pii`, `gdpr`, `consent`, `privacy`, `encrypt`, `personal_data` | Brown |
| `metric`, `span`, `trace`, `otel`, `prometheus`, `grafana`, `slo`, `alert` | Gray |
| `html`, `css`, `component`, `aria`, `a11y`, `i18n`, `locale` | Teal |
| `package.json`, `requirements.txt`, `go.mod`, `cargo.toml`, `pom.xml` | Steel |
| `test`, `spec`, `assert`, `expect`, `mock`, `stub`, `benchmark` | Chartreuse |

### 6.3 Execution Strategies

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| **Full Parallel** | All triggered hats execute simultaneously. Fastest but highest cost. | Small PRs with few triggered hats (<8). |
| **Tiered Parallel** | Always-on hats (Black, Blue, Purple) run first. If they find CRITICAL issues, skip remaining hats. Other hats run in parallel. | Medium to large PRs. Default strategy. |
| **Sequential Critical** | Black Hat runs first. If CRITICAL found → escalate immediately, skip all other hats. Otherwise, proceed with tiered parallel. | High-security-context repos (financial, healthcare). |
| **Budget-Limited** | Run hats in priority order until the token budget is exhausted. Lower-priority hats are skipped with a "NOT EVALUATED" notation. | When cost gate is near limit. |

---

## 7. Gate System — Quality, Cost, Security & Flow Control

The gate system is the flow-control mechanism that determines whether the pipeline proceeds, pauses, or terminates at each stage. There are five gate types.

### 7.1 Gate Definitions

| Gate | Type | Location | Condition | Action on Failure |
|------|------|----------|-----------|-------------------|
| **G1: Cost Budget Gate** | Pre-execution | Before hat dispatch | Total estimated token cost ≤ configured budget ($X per PR) | BLOCK: Notify requester, suggest reducing scope |
| **G2: Security Fast-Path Gate** | Mid-execution | After Black Hat completes | If Black Hat finds CRITICAL severity | SHORT-CIRCUIT: Skip remaining hats, escalate immediately to HITL |
| **G3: Consistency Gate** | Post-consolidation | After Consolidator merges reports | No unresolved contradictions between hat findings | PAUSE: Route contradictions to Arbiter persona for resolution |
| **G4: Timeout Gate** | Mid-execution | Per-hat, after configurable timeout (default: 120s) | Hat has not produced output within timeout | TIMEOUT: Record gap, log timeout, proceed without this hat's input (graceful degradation) |
| **G5: Final Decision Gate** | Post-adjudication | After CoVE produces decision | CoVE output is one of: ALLOW, ESCALATE, QUARANTINE | Route to appropriate notification/escalation channel |

### 7.2 Gate Interaction Matrix

```
                    G1:Cost     G2:Security   G3:Consistency   G4:Timeout   G5:Decision
                    ───────     ───────────   ──────────────   ──────────   ───────────
ALLOW               —           —             ✓ Resolved       ✓ All hats    ✓ Final
ESCALATE            —           —             ✓ Or flagged     ✓ (gaps ok)   ✓ Human
QUARANTINE          —           ✓ CRITICAL    —                —             ✓ Blocked
BLOCKED             ✓ Budget    —             —                —             —
DEGRADED            —           —             —                ✓ Some skipped —
```

### 7.3 Gate Configuration (YAML)

```yaml
gates:
  cost_budget:
    enabled: true
    max_tokens_per_pr: 100000
    max_usd_per_pr: 2.50
    warn_threshold_pct: 80
    hard_limit_action: "block"

  security_fast_path:
    enabled: true
    trigger_severity: "CRITICAL"
    skip_remaining_hats: true
    auto_escalate_to_hitl: true

  consistency:
    enabled: true
    max_contradiction_resolution_attempts: 3
    arbiter_persona: "Arbiter"
    timeout_seconds: 60

  timeout:
    enabled: true
    default_per_hat_seconds: 120
    extension_for_large_prs: 180
    on_timeout: "graceful_degrade"

  final_decision:
    enabled: true
    auto_allow_threshold_risk_score: 20
    always_escalate_for_high_risk: true
    quarantine_requires_all_critical_resolved: true
```

---

## 8. Retry, Backoff & Circuit-Breaker Policies

### 8.1 Retry Policy — Per-Hat

Every hat execution is wrapped in a retry controller with the following configuration:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Max Attempts** | 3 | Balance between reliability and cost. Three attempts catch transient LLM failures without excessive token spend. |
| **Initial Backoff** | 1 second | Standard starting point for rate-limited APIs. |
| **Backoff Multiplier** | 2× (exponential) | 1s → 2s → 4s. Covers most transient failure windows. |
| **Max Backoff** | 10 seconds | Prevents excessive waiting. |
| **Jitter** | ±20% random | Prevents thundering-herd effect when multiple hats retry simultaneously. |
| **Retryable Errors** | Rate limit (429), server error (500/502/503), timeout, context window exceeded, LLM output parse failure | Errors that are likely transient. |
| **Non-Retryable Errors** | Authentication failure (401), invalid request (400), content policy violation, budget exhausted | Errors that retrying will not resolve. |

### 8.2 Retry Policy — LLM API Calls (within a hat)

Each hat may make multiple LLM calls internally. These are governed by a separate, tighter retry policy:

| Parameter | Value |
|-----------|-------|
| **Max Attempts** | 5 (for LLM calls within a hat) |
| **Initial Backoff** | 500ms |
| **Backoff Multiplier** | 2× |
| **Max Backoff** | 8 seconds |
| **Fallback Strategy** | If primary model fails after 5 attempts, fall back to backup model (e.g., Claude Opus → Claude Sonnet, GPT-4o → GPT-4o-mini). |

### 8.3 Circuit Breaker — Per-Hat and Per-LLM-Provider

The circuit breaker prevents cascading failures when an LLM provider or a specific hat is systematically failing.

**States:**
1. **CLOSED** (normal operation): Requests pass through. Track failure count.
2. **OPEN** (fail-fast): All requests immediately return a "circuit open" error. No LLM calls are made.
3. **HALF-OPEN** (probe): Allow a single test request through. If it succeeds → CLOSED. If it fails → OPEN.

**Configuration:**

| Parameter | Per-Hat Circuit Breaker | Per-Provider Circuit Breaker |
|-----------|------------------------|---------------------------|
| **Failure Threshold** | 5 consecutive failures | 10 consecutive failures (across all hats using this provider) |
| **Open Duration** | 60 seconds | 120 seconds |
| **Half-Open Probe Count** | 1 request | 3 requests |
| **Success to Close** | 1 successful response | 3 successful responses |

### 8.4 Backpressure Mechanism

When the system is under heavy load (multiple PRs triggering simultaneously):

1. **Queue-Based Dispatch**: Hat executions are placed in a priority queue. Always-on hats (Black, Blue, Purple) have highest priority.
2. **Concurrency Limit**: Maximum N hats running concurrently per PR (default: 6).
3. **Token Budget Throttling**: If the global token budget is approaching its limit, lower-priority hats are deferred.
4. **Adaptive Model Selection**: Under load, the system automatically downgrades non-critical hats to cheaper/faster models.

```yaml
backpressure:
  max_concurrent_hats_per_pr: 6
  queue_priority_order:
    - black, purple, blue       # Always-on, highest priority
    - red, steel                # Security and safety-adjacent
    - orange, gray              # Ops concerns
    - white, chartreuse         # Quality concerns
    - yellow, green, indigo     # Architecture
    - silver, azure             # Optimization
    - teal, cyan, brown         # Specialized
  adaptive_model_downgrade:
    enabled: true
    trigger_when_queue_depth: 3
    downgrade_map:
      claude-opus-4: claude-haiku-3
      gpt-4o: gpt-4o-mini
      gemini-2.5-pro: gemini-2.0-flash
```

---

## 9. Inter-Hat Communication & State Management

### 9.1 State Schema (LangGraph)

The Conductor maintains a shared state object that every hat reads from and writes to. The state is persisted at every node boundary using LangGraph's `PostgresSaver` checkpoint backend.

```python
from typing import TypedDict, List, Optional
from datetime import datetime

class HatFinding(TypedDict):
    id: str                     # e.g., "BLACK-001"
    hat: str                    # e.g., "black"
    severity: str               # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    category: str               # hat-specific category
    file: Optional[str]
    line_range: Optional[list]
    description: str
    remediation: str
    deduplicated_with: Optional[List[str]]

class HatsRunState(TypedDict):
    # Input
    run_id: str
    trigger_type: str           # "pr" | "local" | "manual"
    pr_number: Optional[int]
    repo: str
    sha: str
    diff_content: str
    changed_files: List[str]
    
    # Orchestration
    triggered_hats: List[str]
    completed_hats: List[str]
    timed_out_hats: List[str]
    failed_hats: List[str]
    
    # Findings (accumulated)
    findings: List[HatFinding]
    
    # Gates
    cost_gate_passed: bool
    security_fast_path_triggered: bool
    
    # Output
    composite_risk_score: Optional[float]
    verdict: Optional[str]      # "ALLOW" | "ESCALATE" | "QUARANTINE"
    executive_summary: Optional[str]
    
    # Metadata
    started_at: datetime
    completed_at: Optional[datetime]
    total_tokens_used: int
    total_cost_usd: float
```

### 9.2 Hat Report Schema

Each hat produces a standardized report that is merged into the shared state by the Consolidator:

```json
{
  "hat": "black",
  "run_id": "run-abc-123",
  "hat_instance_id": "black-instance-001",
  "started_at": "2026-04-10T14:23:11Z",
  "completed_at": "2026-04-10T14:23:19Z",
  "duration_seconds": 8.2,
  "model_used": "claude-opus-4",
  "tokens_input": 3840,
  "tokens_output": 720,
  "cost_usd": 0.14,
  "status": "complete",
  "findings": [
    {
      "id": "BLACK-001",
      "severity": "HIGH",
      "category": "missing_auth",
      "file": "api/chat.py",
      "line_range": [45, 60],
      "description": "The /api/chat endpoint has no authentication middleware.",
      "remediation": "Add @require_auth decorator or equivalent middleware.",
      "owasp_category": "API2:2023-Broken_Authentication"
    }
  ],
  "hat_specific_metadata": {
    "sast_tool": "semgrep",
    "rules_applied": 42,
    "files_scanned": 8
  }
}
```

### 9.3 Consolidator Logic

The Consolidator performs the following operations on the accumulated findings:

1. **Deduplication**: Compare all findings by `(file, line_range, category)` tuple. When two findings overlap, merge them into one, retaining the highest severity and combining both hats' remediation perspectives.
2. **Severity normalization**: Ensure all findings use the standard four-level severity scale (CRITICAL > HIGH > MEDIUM > LOW).
3. **Conflict detection**: Identify findings where two hats make mutually exclusive recommendations (e.g., Hat A says "add caching", Hat B says "caching will break consistency"). Tag these as `conflicted: true` for CoVE adjudication.
4. **Timed-out hat gap recording**: For any hat that timed out, record a `NOT_EVALUATED` entry in the findings matrix with the hat name and timeout reason.

---

## 10. Human-in-the-Loop (HITL) Framework

### 10.1 HITL Trigger Conditions

| Trigger | Source | HITL Level |
|---------|--------|-----------|
| CRITICAL security finding (Black Hat) | Automatic | Tier 3: Security Team |
| CRITICAL AI safety finding (Purple Hat) | Automatic | Tier 3: Security/Compliance |
| CoVE verdict = ESCALATE | Automatic | Tier 1: Author or Tier 2: Reviewer |
| Manual escalation request | Developer or reviewer | Configurable |
| Audit/compliance requirement | Policy configuration | Tier 3 or Tier 4 |

### 10.2 HITL Interrupt Pattern (LangGraph)

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

builder = StateGraph(HatsRunState)

# Add nodes for each hat + conductor components
builder.add_node("hat_selector", hat_selector_node)
builder.add_node("dispatch_hats", dispatch_hats_node)
builder.add_node("consolidator", consolidator_node)
builder.add_node("cove_adjudication", cove_adjudication_node)
builder.add_node("hitl_interrupt", hitl_interrupt_node)  # <-- HITL node

# Add conditional edge: if CoVE says ESCALATE → HITL, else END
builder.add_conditional_edges(
    "cove_adjudication",
    lambda state: "hitl_interrupt" if state["verdict"] == "ESCALATE" else END,
    {"hitl_interrupt": "hitl_interrupt", END: END}
)

# Compile with checkpoint backend (enables resume after human approval)
graph = builder.compile(
    checkpointer=PostgresSaver.from_conn_string(POSTGRES_URL),
    interrupt_before=["hitl_interrupt"]  # Pause execution before HITL node
)
```

### 10.3 HITL Interfaces

| Interface | Description | Key Actions |
|-----------|-------------|-------------|
| **GitHub PR Comments** | Primary interface for code reviews. Findings posted as structured PR comments with approve/request-changes actions. | `/hats approve`, `/hats reject`, `/hats status`, `/hats retry` |
| **Slack / Teams** | Real-time notifications and quick actions. Interactive message buttons for approve/reject. | Approve/Reject buttons, "View Details" link to PR |
| **Web Dashboard** | Full-featured UI for reviewing all findings, filtering by severity, and batch-approving. | View findings, approve, reject, configure policies |
| **CLI** | For local development and debugging. | `hats review <pr>`, `hats approve <pr>`, `hats status <pr>` |
| **API** | For programmatic integration with existing workflows. | `POST /api/v1/hats/{run_id}/decision`, `GET /api/v1/hats/{run_id}/status` |

### 10.4 HITL Escalation Tiers

| Tier | Responders | SLA | Authority |
|------|-----------|-----|-----------|
| **Tier 1: Code Author** | The developer who submitted the PR. | 4 hours | Can approve non-CRITICAL findings. |
| **Tier 2: Team Reviewer** | Designated code reviewer for the team. | 8 hours | Can approve HIGH findings. |
| **Tier 3: Security/Compliance** | Security or compliance team member. | 24 hours | Required for CRITICAL security/safety findings. |
| **Tier 4: Engineering Lead** | Engineering manager or tech lead. | 48 hours | Can override any decision (audit-logged). |

---

## 11. Observability, Tracing & Cost Tracking

### 11.1 Tracing Architecture

Every hat execution, gate evaluation, and LLM call is wrapped in an OpenTelemetry span. The trace hierarchy is:

```
[hats_run_{run_id}]
  ├── [hat_selector]                           (duration, trigger results)
  ├── [gate:cost_budget]                       (pass/fail, estimated cost)
  ├── [hat:black]                              (duration, token usage, model)
  │   ├── [llm_call:claude-opus-4]             (latency, tokens, cost)
  │   └── [sast_scan:semgrep]                  (duration, findings count)
  ├── [hat:blue]                               (duration, token usage)
  │   └── [llm_call:gpt-4o-mini]              (latency, tokens, cost)
  ├── [hat:purple]                             (duration, token usage)
  │   ├── [llm_call:claude-opus-4]             (latency, tokens, cost)
  │   └── [bias_scan:fairlearn]                (duration, results)
  ├── ... (other hats)
  ├── [consolidator]                           (duration, dedup count)
  ├── [cove_adjudication]                      (duration, risk_score, verdict)
  └── [gate:final_decision]                    (verdict, rationale)
```

### 11.2 Metrics (Prometheus Format)

```
# Hat execution metrics
hats_hat_execution_duration_seconds{hat="black",model="claude-opus-4"} 8.5
hats_hat_execution_total{hat="black",status="complete"} 142
hats_hat_execution_total{hat="black",status="timeout"} 3
hats_hat_findings_total{hat="black",severity="CRITICAL"} 7

# LLM call metrics
hats_llm_call_duration_seconds{model="claude-opus-4",hat="black"} 4.2
hats_llm_tokens_total{model="claude-opus-4",type="input"} 125000
hats_llm_tokens_total{model="claude-opus-4",type="output"} 45000
hats_llm_cost_usd_total{model="claude-opus-4"} 3.75

# Gate metrics
hats_gate_evaluations_total{gate="cost_budget",result="passed"} 198
hats_gate_evaluations_total{gate="security_fast_path",result="triggered"} 4

# Pipeline metrics
hats_run_duration_seconds{verdict="ALLOW"} 35.2
hats_run_total{verdict="ALLOW"} 142
hats_run_total{verdict="ESCALATE"} 38
hats_run_total{verdict="QUARANTINE"} 7
hats_run_cove_risk_score{verdict="ALLOW"} 12.5
hats_run_cove_risk_score{verdict="ESCALATE"} 58.3

# Circuit breaker metrics
hats_circuit_breaker_state{hat="black",provider="anthropic"} 0  # 0=CLOSED, 1=OPEN, 2=HALF_OPEN
```

### 11.3 Cost Tracking

Cost is tracked at three granularities:

1. **Per-Run**: Total cost for a single PR review (sum of all hat LLM calls).
2. **Per-Day**: Aggregated daily cost with trend analysis.
3. **Per-Repository**: Aggregated cost per repo with per-hat breakdown.

**Cost Dashboard Columns:**

| Date | Repo | Runs | Total Tokens | Total Cost | Avg Cost/Run | Top Cost Hat | Budget Remaining |
|------|------|------|-------------|------------|-------------|-------------|-----------------|
| 2026-04-10 | org/api | 12 | 523,000 | $18.40 | $1.53 | Indigo ($6.20) | $81.60 |

### 11.4 Alerting Rules

| Alert | Condition | Severity | Channel |
|-------|-----------|----------|---------|
| Hat consistently timing out | 3+ timeouts for same hat in 1 hour | HIGH | Slack #ops-alerts |
| Cost budget >80% consumed | Daily cost >80% of daily budget | WARNING | Slack #cost-tracking |
| LLM provider circuit breaker open | Provider circuit breaker in OPEN state | CRITICAL | PagerDuty |
| CoVE false positive detected | Human overrides QUARANTINE to ALLOW | INFO | Slack #hats-feedback |
| Pipeline latency >5 min | Total run duration >300s | WARNING | Slack #ops-alerts |

---

## 12. CI/CD Integration & Deployment Architecture

### 12.1 CI/CD Integration Patterns

**Pattern 1: GitHub Actions (Primary)**

```yaml
name: Hats AI Review
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  hats-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for diff analysis
      
      - name: Install Hats CLI
        run: npm install -g @hats/cli
      
      - name: Run Hats Pipeline
        env:
          HATS_CONFIG: .hats/hats.yml
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          HATS_HITL_GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          hats run \
            --trigger pr \
            --pr-number ${{ github.event.pull_request.number }} \
            --repo ${{ github.repository }} \
            --sha ${{ github.sha }} \
            --output-format json,markdown \
            --post-to-pr
```

**Pattern 2: GitLab CI**

```yaml
hats-review:
  stage: review
  image: node:20
  script:
    - npm install -g @hats/cli
    - hats run --trigger mr --mr-iid $CI_MERGE_REQUEST_IID --output-format json
  artifacts:
    paths:
      - hats-report.json
      - hats-report.md
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

**Pattern 3: Pre-Commit Hook (Local)**

```bash
#!/bin/bash
# .git/hooks/pre-commit
hats run --trigger local --staged-files-only --fail-on=QUARANTINE
```

### 12.2 Deployment Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  CI/CD Platform (GitHub Actions / GitLab CI / Argo)         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Hats Runner Container                                  │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │  │
│  │  │ Conductor    │  │ Hat Agents   │  │ Gate Engine  │ │  │
│  │  │ (LangGraph)  │  │ (18 nodes)   │  │ (5 gates)    │ │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────────┘ │  │
│  │         │                 │                             │  │
│  │  ┌──────┴─────────────────┴──────┐                     │  │
│  │  │  State Manager (PostgresSaver)│                     │  │
│  │  └──────────────────────────────┘                     │  │
│  └────────────────────────────────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────┼──────────────────────────────┐   │
│  │  External Services     │                              │   │
│  │  ┌─────────┐ ┌────────┐ ┌────────┐ ┌───────────────┐│   │
│  │  │ LLM APIs│ │Postgres│ │Redis   │ │ OpenTelemetry ││   │
│  │  │(Anthro, │ │(State) │ │(Queue) │ │ Collector     ││   │
│  │  │ OpenAI, │ │        │ │        │ │ (Grafana)     ││   │
│  │  │ Google) │ │        │ │        │ │               ││   │
│  │  └─────────┘ └────────┘ └────────┘ └───────────────┘│   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## 13. Security Stack & Compliance

### 13.1 Threat Model (Hats Pipeline Itself)

| Threat | Mitigation |
|--------|-----------|
| **Malicious PR injects prompt into hat analysis** | Hats use isolated system prompts. User-controlled data (diff content) is always in the `user` role, never `system`. Input sanitization via `presidio` before LLM calls. |
| **LLM provider outage / data breach** | Multi-provider fallback (primary + backup model per hat). No sensitive data sent to LLMs (PII scrubbed by Brown Hat before other hats see it). |
| **Compromised dependency in hats pipeline** | Steel Hat scans the hats pipeline's own dependencies. Lockfile integrity verification. Minimal container image (distroless). |
| **HITL approval bypass** | All HITL decisions are audit-logged with actor identity. Tier-4 overrides require MFA. Webhook signatures verified (HMAC). |
| **Cost exhaustion attack (malicious PRs to drain LLM budget)** | Per-PR cost gate (G1). Per-user rate limiting. Anomaly detection on cost spikes. |

### 13.2 Compliance Mapping

| Regulation | Relevant Hats | Controls |
|-----------|---------------|----------|
| **GDPR** | Brown (primary), Purple, Black | PII scrubbing before LLM calls, right-to-erasure in hat state store, data-flow auditing, consent management verification. |
| **EU AI Act** | Purple (primary), Black, Blue | Risk classification of AI system, transparency requirements, human oversight mechanisms, logging and audit trails. |
| **CCPA** | Brown (primary) | Consumer data access and deletion verification, data minimization, purpose limitation. |
| **HIPAA** | Brown (primary), Black | PHI encryption, access controls, audit logging, BAA verification with LLM providers. |
| **SOC 2** | Black, Purple, Gray, Blue | Access controls, encryption, monitoring, incident response, change management. |
| **OWASP GenAI Top 10 (2025)** | Black (primary), Purple | All 10 categories addressed by specific hat assignments. |

---

## 14. End-to-End Walkthrough

### Scenario: PR adds a new RAG-powered customer support chatbot

**PR Summary:** Adds a `/api/chat` endpoint that retrieves relevant knowledge-base articles via vector search and generates responses using Claude Sonnet. Includes a `system_prompt.txt` template.

**Step-by-step execution:**

| Step | Phase | Hat | Analysis | Key Finding | Severity |
|------|-------|-----|----------|-------------|----------|
| 1 | Selector | — | File analysis: `api/chat.py`, `retriever.py`, `system_prompt.txt`, `requirements.txt` | Selected 12 hats: Black, Blue, Purple (always), Red, White, Silver, Azure, Brown, Steel, Chartreuse, Gray, Orange | — |
| 2 | Pre-flight | — | Cost estimation: 12 hats × avg 4k tokens = ~48k tokens ≈ $0.72 | Within budget ($2.50) | ✅ PASS |
| 3 | Gate G1 | Cost Budget | Budget OK | Proceed | — |
| 4 | Execute | ⚫ Black | Scans for auth, input sanitization, secret exposure | No auth on `/api/chat` — public endpoint accepts arbitrary user input and passes it directly into RAG query and LLM prompt | 🔴 CRITICAL |
| 5 | Gate G2 | Security Fast-Path | CRITICAL finding detected | **SHORT-CIRCUIT**: Skip remaining hats, escalate to HITL immediately | — |
| 6 | HITL | Human | Security reviewer sees Black Hat finding | Requests developer add rate limiting and input sanitization before full review | — |
| 7 | Execute | ⚫ Black | Re-scan after fix | Auth added, input sanitized. Minor: `system_prompt.txt` doesn't instruct model to refuse off-topic queries | 🟡 MEDIUM |
| 8 | Execute | 🟪 Purple | AI safety scan | Prompt template includes user query verbatim without jailbreak resistance. No hallucination guardrail | 🟠 HIGH |
| 9 | Execute | ⚪ White | Efficiency scan | RAG retrieves top-10 documents — sending all 10 to LLM wastes ~3k tokens per query | 🟡 MEDIUM |
| 10 | Execute | 🪨 Silver | Token optimization | System prompt (850 tokens) + 10 docs (avg 400 tokens each = 4k) + user query = ~5k tokens. Recommends chunking + summary | 🟡 MEDIUM |
| 11 | Execute | 💎 Azure | MCP check | No MCP integration for the retriever tool — should expose as MCP tool for composability | 🟢 LOW |
| 12 | Execute | 🟤 Brown | Privacy scan | User chat history stored in ChromaDB without PII scrubbing. No retention policy | 🔴 CRITICAL |
| 13 | Execute | 🔗 Steel | Dependency scan | `chromadb` v0.4.22 has known medium vulnerability (CVE-2024-XXXX) | 🟠 HIGH |
| 14 | Execute | ⚙️ Gray | Observability | No OpenTelemetry spans on the `/api/chat` endpoint. No latency metrics | 🟡 MEDIUM |
| 15 | Execute | 🧪 Chartreuse | Testing | No tests for the chat endpoint itself. No adversarial prompt tests. No RAGAS metrics | 🟠 HIGH |
| 16 | Execute | 🟠 Orange | DevOps | No Dockerfile for the new service. No health check endpoint defined | 🟡 MEDIUM |
| 17 | Consolidate | — | Merges all reports | 18 total findings. 2 CRITICAL, 2 HIGH, 6 MEDIUM, 8 LOW. Deduplicated 3 overlapping findings | — |
| 18 | Adjudicate | ✨ CoVE | Final analysis | Composite risk score: 72/100. **ESCALATE** — CRITICAL findings must be resolved before merge | ESCALATE |
| 19 | HITL | Human | Senior reviewer | Reviews PII scrubbing fix and privacy policy. Approves with recommendation to add RAGAS metrics in follow-up | APPROVE |
| 20 | Notify | — | Pipeline complete | PR comment posted with full findings matrix. Slack notification sent. Merge allowed. | ✅ ALLOW |

**Total Pipeline Stats:**
- Hats executed: 10 (of 12 selected — 2 skipped by security fast-path on first run)
- Total tokens: 62,400
- Total cost: $1.14
- Total duration: 58 seconds
- Human review time: 4 hours (spread across 2 review cycles)

---

## 15. Quick-Start Deployment Guide

### 15.1 Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **LLM API Keys** | At least one (Anthropic or OpenAI) | All three (Anthropic, OpenAI, Google) for fallback |
| **PostgreSQL** | v14+ (for LangGraph state checkpointing) | v16 with pgvector |
| **Redis** | v7+ (for queue management) | v7 with Redis Stack |
| **Node.js** | v20 LTS | v22 LTS |
| **Python** | v3.11 | v3.12 |
| **Docker** | v24+ | Latest |

### 15.2 Installation

```bash
# Step 1: Install the Hats CLI
npm install -g @hats/cli

# Step 2: Initialize project configuration
hats init --backend multi --storage postgres

# Step 3: Configure hats.yml
cat > .hats/hats.yml << 'EOF'
version: "2.0"

llm_backends:
  primary:
    provider: anthropic
    model: claude-opus-4-20250514
    api_key_env: ANTHROPIC_API_KEY
  fast:
    provider: openai
    model: gpt-4o-mini
    api_key_env: OPENAI_API_KEY
  fallback:
    provider: google
    model: gemini-2.0-flash
    api_key_env: GOOGLE_API_KEY

storage:
  type: postgres
  connection_string_env: HATS_POSTGRES_URL

hats:
  black:
    model: primary
    always_run: true
    timeout_seconds: 150
  blue:
    model: fast
    always_run: true
    timeout_seconds: 60
  purple:
    model: primary
    always_run: true
    timeout_seconds: 150
  red:
    model: primary
    timeout_seconds: 120
  white:
    model: fast
    timeout_seconds: 90
  yellow:
    model: primary
    timeout_seconds: 120
  green:
    model: primary
    timeout_seconds: 120
  indigo:
    model: primary
    timeout_seconds: 180
  cyan:
    model: primary
    timeout_seconds: 150
  orange:
    model: primary
    timeout_seconds: 90
  silver:
    model: fast
    timeout_seconds: 60
  azure:
    model: primary
    timeout_seconds: 120
  brown:
    model: primary
    timeout_seconds: 120
  gray:
    model: primary
    timeout_seconds: 90
  teal:
    model: fast
    timeout_seconds: 60
  steel:
    model: fast
    timeout_seconds: 60
  chartreuse:
    model: primary
    timeout_seconds: 120
  gold_cove:
    model: primary
    always_run: true
    run_last: true
    timeout_seconds: 300

gates:
  cost_budget:
    max_tokens_per_pr: 100000
    max_usd_per_pr: 2.50
  security_fast_path:
    enabled: true
    trigger_severity: CRITICAL
    skip_remaining_hats: true
  timeout:
    default_per_hat_seconds: 120

hitl:
  enabled: true
  channels:
    - github_pr_comments
    - slack
  escalation_tiers:
    - role: author
      slas_hours: 4
      max_severity: HIGH
    - role: reviewer
      slas_hours: 8
      max_severity: HIGH
    - role: security
      slas_hours: 24
      max_severity: CRITICAL

observability:
  tracing:
    enabled: true
    exporter: otlp
    endpoint_env: OTEL_EXPORTER_OTLP_ENDPOINT
  metrics:
    enabled: true
    exporter: prometheus
    port: 9090

execution:
  strategy: tiered_parallel
  max_concurrent_hats: 6
  retry:
    max_attempts: 3
    initial_backoff_seconds: 1
    backoff_multiplier: 2
    max_backoff_seconds: 10
    jitter_pct: 20
  circuit_breaker:
    failure_threshold: 5
    open_duration_seconds: 60
EOF

# Step 4: Set environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="AI..."
export HATS_POSTGRES_URL="postgresql://user:pass@localhost:5432/hats"

# Step 5: Verify installation
hats doctor

# Step 6: Run a test review
hats run --trigger pr --pr-number 1 --repo owner/repo --sha abc123
```

### 15.3 Docker Deployment

```bash
# Pull the official Hats image
docker pull ghcr.io/hats-ai/hats-runner:latest

# Run with configuration
docker run -d \
  --name hats-runner \
  -e ANTHROPIC_API_KEY \
  -e OPENAI_API_KEY \
  -e HATS_POSTGRES_URL \
  -v $(pwd)/.hats:/app/.hats \
  -p 8080:8080 \
  ghcr.io/hats-ai/hats-runner:latest
```

### 15.4 Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hats-runner
spec:
  replicas: 2
  selector:
    matchLabels:
      app: hats-runner
  template:
    metadata:
      labels:
        app: hats-runner
    spec:
      containers:
        - name: hats-runner
          image: ghcr.io/hats-ai/hats-runner:latest
          ports:
            - containerPort: 8080
          envFrom:
            - secretRef:
                name: hats-secrets
          volumeMounts:
            - name: config
              mountPath: /app/.hats
      volumes:
        - name: config
          configMap:
            name: hats-config
```

---

## 16. Appendices

### Appendix A: Severity Definitions

| Severity | Definition | Example | Required Action |
|----------|-----------|---------|----------------|
| **CRITICAL** | Actively exploitable vulnerability or guaranteed production failure. Immediate risk to data, users, or system availability. | Hardcoded API key, SQL injection, PII sent to external LLM without scrubbing | Must be fixed before merge. Hard block. No exceptions. |
| **HIGH** | Significant risk that could lead to exploitation, data loss, or degraded performance under production conditions. | Missing auth on non-public endpoint, retry without idempotency, no bias audit on user-facing AI | Must be addressed before merge or explicitly accepted by Tier-2+ reviewer with documented rationale. |
| **MEDIUM** | Concern that could become HIGH or CRITICAL under certain conditions, or represents a significant best-practice deviation. | Suboptimal caching strategy, missing OpenTelemetry spans, incomplete i18n | Should be addressed. May be deferred to follow-up PR if documented. |
| **LOW** | Minor improvement, best-practice suggestion, or aesthetic concern. | Variable naming suggestion, documentation wording, minor token optimization | Informational. No action required for merge. |

### Appendix B: Hat Priority for Budget-Limited Execution

When the cost budget gate limits the number of hats that can run, use this priority order:

1. ⚫ Black (security — non-negotiable)
2. 🟪 Purple (AI safety — non-negotiable)
3. 🔵 Blue (process — non-negotiable)
4. 🔗 Steel (supply chain — fast and cheap)
5. ⚪ White (efficiency & resources — fast and cheap)
6. 🧪 Chartreuse (testing quality)
7. 🔴 Red (resilience)
8. ⚙️ Gray (observability)
9. 🟤 Brown (data governance)
10. 🟠 Orange (DevOps)
11. 🪨 Silver (token optimization)
12. 💎 Azure (protocol integration)
13. 🟡 Yellow (synergies)
14. 🟢 Green (evolution)
15. 🟣 Indigo (cross-feature architecture)
16. ♿ Teal (accessibility)
17. 🩵 Cyan (innovation)
18. ✨ Gold/CoVE (always runs last, uses consolidated reports)

### Appendix C: Model Selection Matrix

| Hat Tier | Claude Opus 4 | Claude Sonnet 4 | GPT-4o | GPT-4o-mini | Gemini 2.5 Pro | Gemini Flash |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|
| Tier 1 (Security/Safety/Adjudication) | ✅ | | ✅ | | ✅ | |
| Tier 2 (Architecture/Innovation) | ✅ | ✅ | ✅ | | ✅ | |
| Tier 3 (Quality/Analysis) | | ✅ | ✅ | | | ✅ |
| Tier 4 (Fast/Scanning) | | | | ✅ | | ✅ |

**Cost Optimization Tip:** Hats in Tier 4 (Blue, Silver, Teal, Steel) should almost always use the cheapest available model. Their analysis is largely pattern-based and deterministic — a premium model adds cost without proportional quality improvement.

### Appendix D: Recommended LLM Backend Summary

| Hat | Recommended Model | Rationale |
|-----|------------------|-----------|
| 🔴 Red | Claude Opus 4 or GPT-4o | Deep reasoning on failure chains |
| ⚫ Black | Claude Opus 4 or Gemini 2.5 Pro | Security reasoning + broad threat surface |
| ⚪ White | GPT-4o-mini or Gemini Flash | Fast, deterministic efficiency analysis |
| 🟡 Yellow | Claude Sonnet 4 | Architectural reasoning, cost-quality ratio |
| 🟢 Green | Claude Opus 4 or GPT-4o | Strategic architectural reasoning |
| 🔵 Blue | GPT-4o-mini or Claude Haiku | Fast, rule-based process checks |
| 🟣 Indigo | Claude Opus 4 | Deep cross-module reasoning, large diffs |
| 🩵 Cyan | Claude Opus 4 or Gemini 2.5 Pro | Novel technology reasoning |
| 🟪 Purple | Claude Opus 4 | AI safety reasoning — must use highest-capability |
| 🟠 Orange | GPT-4o or Claude Sonnet 4 | YAML + security knowledge |
| 🪨 Silver | GPT-4o-mini | Deterministic token counting |
| 💎 Azure | Claude Sonnet 4 or GPT-4o | JSON schema reasoning |
| 🟤 Brown | Claude Opus 4 or GPT-4o | Regulatory reasoning |
| ⚙️ Gray | GPT-4o or Claude Sonnet 4 | Distributed-systems knowledge |
| ♿ Teal | GPT-4o-mini | Pattern-based accessibility checks |
| 🔗 Steel | GPT-4o-mini or Gemini Flash | Deterministic scanning |
| 🧪 Chartreuse | Claude Sonnet 4 | Test-design reasoning |
| ✨ Gold/CoVE | Claude Opus 4 | Final adjudication — non-negotiable highest capability |

### Appendix E: Composite Risk Score Formula

The Gold Hat (CoVE) computes a composite risk score (0–100) from all hat findings:

```
risk_score = min(100,
  min(80, CRITICAL_count × 20) +
  min(40, HIGH_count × 5) +
  min(10, MEDIUM_count × 1) +
  min(5, LOW_count × 0.1)
)
```

**Verdict thresholds:**
- Score 0–20: **ALLOW** (auto-approved)
- Score 21–60: **ESCALATE** (human review required)
- Score 61–100: **QUARANTINE** (hard block)
- Any Gold Hat-confirmed/adjudicated **CRITICAL** finding: **QUARANTINE** regardless of score

### Appendix F: Glossary

| Term | Definition |
|------|-----------|
| **MCP** | Model Context Protocol — Anthropic's standard for agent-to-tool integration |
| **A2A** | Agent-to-Agent Protocol — Google's standard for inter-agent communication |
| **CoVE** | Convergent Verification & Expert — the Gold Hat's adversarial QA methodology |
| **HITL** | Human-in-the-Loop — human oversight and approval checkpoints |
| **Gate** | A flow-control mechanism that can pause, block, or redirect the pipeline |
| **Circuit Breaker** | A fault-tolerance pattern that prevents cascading failures |
| **Backpressure** | Flow-control mechanism that prevents overload by throttling input |
| **SBOM** | Software Bill of Materials — a complete inventory of software components |
| **PIA** | Privacy Impact Assessment — evaluation of privacy risks for data processing |
| **ADR** | Architecture Decision Record — documented architectural decisions |
| **SLO** | Service Level Objective — target reliability/performance threshold |
| **SLI** | Service Level Indicator — measurable attribute of service reliability |
| **OTel** | OpenTelemetry — observability framework for traces, metrics, and logs |
| **RAGAS** | Retrieval Augmented Generation Assessment — framework for evaluating RAG systems |

---

## Companion Documents

| Document | Description |
|----------|-------------|
| [hats/AGENTIC_AI_HATS_TEAM_STACK.md](hats/AGENTIC_AI_HATS_TEAM_STACK.md) | Complete standalone specification (Sections 1–16) with inline hat details and appendices |
| [hats/HATS_TEAM_IMPLEMENTATION_GUIDE.md](hats/HATS_TEAM_IMPLEMENTATION_GUIDE.md) | Implementation guide (Appendix E of `hats/AGENTIC_AI_HATS_TEAM_STACK.md`): Ollama Cloud + n8n deployment, cost-optimized model selection, security box, self-improvement pipeline |
| [hats/HATS_TEAM_CONCERNS_DISCUSSION.md](hats/HATS_TEAM_CONCERNS_DISCUSSION.md) | Concerns discussion (Appendix F of `hats/AGENTIC_AI_HATS_TEAM_STACK.md`): honest engagement with 17 real-world concerns about the Hats Team approach |

---

*This specification is a living document. As the agentic AI ecosystem evolves (new protocols, new attack vectors, new best practices), the Hats Team should be updated accordingly. Each hat's effectiveness metrics should be reviewed quarterly, and persona prompts should be refined based on false-positive/negative analysis.*

← [CATALOG](CATALOG.md) | [README](README.md)
