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
- **16 personas** that embody human-like expertise, enabling each hat to reason with the nuance of a domain specialist rather than a generic LLM.
- **A formal gate system** with five gate types (Quality, Cost, Security, Consistency, Timeliness) that control flow between orchestration phases.
- **Explicit retry, backoff, and circuit-breaker policies** that prevent cascading failures across the agent network.
- **A complete HITL framework** with interrupt-based checkpoints, escalation routing, approval workflows, and audit trails.
- **Supply-chain and dependency-aware analysis** — a first-class concern, not an afterthought.

---

## 2. Design Philosophy & Principles

### 2.1 Core Tenets

| # | Principle | Description |
|---|-----------|-------------|
| 1 | **Defense in Depth** | Every finding must be corroborated by at least two independent hats before escalating. No single hat can block a merge alone (except Black Hat for CRITICAL security findings). |
| 2 | **Cost Consciousness** | Every LLM call is metered. Hats use tiered model selection: cheap/fast models for scanning, premium models for final adjudication. A global token budget gate prevents runaway costs. |
| 3 | **Graceful Degradation** | If a hat times out or fails, the Conductor records the gap and proceeds. No single hat failure should block the pipeline — only the Gold Hat (CoVE) can issue a hard block. |
| 4 | **Stateful Checkpointing** | The entire orchestration graph is persisted at every node boundary. Any interrupted run can be resumed from the last successful checkpoint. |
| 5 | **Human Authority** | The system is advisory by default. Only explicitly configured policies (e.g., "block all PRs with CRITICAL security findings") can auto-reject. All other decisions are recommendations. |
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

### 4.1 Master Hat Registry

| # | Emoji | Hat Name | Run Mode | Trigger Conditions | Primary Focus |
|---|-------|----------|----------|--------------------|---------------|
| 1 | 🔴 | **Red Hat — Failure & Resilience** | Conditional | Error handling, retries, DB writes, shared state, async pipelines, concurrency | Cascade failures, race conditions, single points of failure, chaos readiness |
| 2 | ⚫ | **Black Hat — Security & Exploits** | **Always** | Every PR (mandatory baseline) | Prompt injection, credential leakage, privilege escalation, OWASP GenAI Top 10 |
| 3 | ⚪ | **White Hat — Efficiency & Resources** | Conditional | Loops, DB queries, LLM calls, large data processing, batch operations | Token waste reduction, compute budgeting, memory optimization |
| 4 | 🟡 | **Yellow Hat — Synergies & Integration** | Conditional | New features touching ≥2 services/components, API changes | Cross-component value, shared abstractions, dependency optimization |
| 5 | 🟢 | **Green Hat — Evolution & Extensibility** | Conditional | Architecture changes, new modules, public API changes | Versioning, deprecation, plugin architecture, future-proofing |
| 6 | 🔵 | **Blue Hat — Process & Specification** | **Always** | Every PR (mandatory baseline) | Spec coverage, test completeness, commit hygiene, documentation |
| 7 | 🟣 | **Indigo Hat — Cross-Feature Architecture** | Conditional | PR modifies >2 modules, changes integration points | Macro-level DRY violations, duplicated pipelines, shared abstractions |
| 8 | 🩵 | **Cyan Hat — Innovation & Feasibility** | Conditional | Experimental patterns, new tech stacks, novel LLM usage | Technical feasibility, risk/ROI analysis, prototype validation |
| 9 | 🟪 | **Purple Hat — AI Safety & Alignment** | **Always** | Every PR (mandatory baseline) | OWASP Agentic Top 10, bias detection, PII leakage, model alignment |
| 10 | 🟠 | **Orange Hat — DevOps & Automation** | Conditional | Dockerfiles, CI YAML, deployment scripts, Terraform, Helm charts | Pipeline health, IaC quality, container security, deployment safety |
| 11 | 🪨 | **Silver Hat — Context & Token Optimization** | Conditional | LLM prompt building, RAG pipelines, context window management | Token counting, context compression, hybrid retrieval optimization |
| 12 | 💎 | **Azure Hat — MCP & Protocol Integration** | Conditional | Tool calls, function calling, MCP schema usage, A2A contracts | MCP contract validation, A2A schema enforcement, type safety |
| 13 | 🟤 | **Brown Hat — Data Governance & Privacy** | Conditional | PII handling, user data storage, logging, data pipelines | GDPR/CCPA/HIPAA compliance, data minimization, audit logging |
| 14 | ⚙️ | **Gray Hat — Observability & Reliability** | Conditional | Production services, long-running agents, SLA-bound endpoints | Distributed tracing, SLO/SLA monitoring, alerting, latency budgeting |
| 15 | ♿ | **Teal Hat — Accessibility & Inclusion** | Conditional | UI changes, API responses, content generation, i18n/l10n | WCAG compliance, screen-reader compatibility, inclusive design |
| 16 | 🔗 | **Steel Hat — Supply Chain & Dependencies** | Conditional | Dependency changes, lockfile updates, new package additions | SBOM generation, vulnerability scanning, license compliance |
| 17 | 🧪 | **Chartreuse Hat — Testing & Evaluation** | Conditional | Test additions/changes, evaluation pipelines, benchmark updates | Test coverage, RAGAS metrics, prompt evaluation, regression detection |
| 18 | ✨ | **Gold Hat — CoVE (Convergent Verification & Expert) — Final QA** | **Always (Last)** | After all other hats complete | 14-dimension adversarial QA, merge-ready decision, severity adjudication |

### 4.2 Detailed Hat Specifications

---

#### 🔴 Red Hat — Failure & Resilience

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | Code touches error-handling blocks (`try/catch`, `except`, `panic!`, `unwrap`), retry logic (`retry`, `backoff`, `circuit_breaker`), database writes, shared mutable state, async pipelines, concurrency primitives (`Mutex`, `Lock`, `Semaphore`, `Channel`), or external service calls with failure potential |
| **Focus Area** | Identify cascade failures, race conditions, deadlocks, single points of failure, missing graceful degradation, and inadequate retry strategies. Ensure the system fails safely and recovers automatically. |
| **Core Assignments** | 1. Scan for all error-handling patterns and verify they follow the project's error taxonomy (no swallowed errors, no bare `except:`). 2. Analyze retry logic: are exponential backoffs configured? Are idempotency keys used for retried operations? Are retry budgets (max attempts, max elapsed time) defined? 3. Check shared state access patterns for race conditions and deadlocks. 4. Validate that circuit breakers exist at service boundaries and are configured with appropriate thresholds (failure count, timeout, half-open probe interval). 5. Simulate failure injection mentally (or via chaos-toolkit): what happens when each external dependency fails? 6. Verify that database writes within retry loops are idempotent or use upsert patterns. 7. Check for proper timeout configuration on all network calls (connection timeout, read timeout, overall timeout). 8. Assess whether the system degrades gracefully under partial failure (e.g., returning cached data when the primary source is down). |
| **Severity Grading** | CRITICAL: Missing error handling on financial/irreversible operations. HIGH: Swallowed errors, missing retries on external calls. MEDIUM: Suboptimal retry configuration, missing circuit breakers. LOW: Timeout tuning suggestions, logging improvements. |
| **Output Format** | Structured JSON report with categorized findings, plus a resilience-score (0–100) and a prioritized remediation list. |
| **Required Skills / Tools** | Static analysis (Semgrep rules for error-handling patterns), chaos engineering concepts (Chaos Monkey, Litmus), language-specific concurrency analysis tools (Go race detector, Python threading audit), `retry` library best practices, circuit-breaker pattern knowledge, LangGraph state-recovery patterns. |
| **Recommended LLM Backend** | Claude Opus 4 (deep reasoning on failure chains) or GPT-4o for broad coverage. |
| **Approximate Token Budget** | 2,000–4,000 input tokens (diff + context) · 500–1,000 output tokens (report) |

---

#### ⚫ Black Hat — Security & Exploits

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | **Every PR** — this hat runs unconditionally as a mandatory security baseline. Additional focus when code touches authentication, authorization, I/O, network calls, configuration, environment variables, secrets, tool-call interfaces, or MCP endpoints. |
| **Focus Area** | Detect prompt injection (direct and indirect), credential leakage, privilege escalation, insecure deserialization, SSRF, injection attacks (SQL, NoSQL, command, XSS), OWASP GenAI Top 10 (2025 edition), OWASP Agentic Top 10 threats, and supply-chain vulnerabilities. |
| **Core Assignments** | 1. Run SAST scanning (Semgrep, Bandit, ESLint security rules) on all changed files. 2. Execute prompt-injection tests against every LLM call site: direct injection via user input, indirect injection via retrieved documents (RAG poisoning), and injection via tool-call responses. 3. Verify MCP endpoint least-privilege: does each tool expose only the minimum necessary capabilities? Are input schemas enforced? 4. Check for credential leakage: hardcoded secrets, secrets in logs, exposed API keys in error messages. 5. Validate authentication and authorization logic: are all endpoints protected? Is role-based access control (RBAC) enforced? Are there TOCTOU (time-of-check-time-of-use) vulnerabilities? 6. Scan for insecure dependencies using lockfile analysis (Syft/grype). 7. Verify that user-supplied data is sanitized before being included in LLM prompts, system prompts, or tool-call arguments. 8. Check for SSRF vulnerabilities in any URL-fetching or API-calling code. 9. Verify that MCP sandbox boundaries are enforced (no filesystem escape, no network access beyond declared scope). |
| **Severity Grading** | CRITICAL: Active exploitable vulnerability, credential leakage, prompt injection with confirmed bypass. HIGH: Missing auth on sensitive endpoint, insecure deserialization. MEDIUM: Missing input validation, weak CORS policy. LOW: Best-practice improvements, defensive coding suggestions. |
| **Output Format** | OWASP-aligned vulnerability report with CVE references where applicable, exploit scenario descriptions, and concrete remediation code patches. |
| **Required Skills / Tools** | OWASP GenAI Top 10 (2025), OWASP Agentic AI Top 10, Semgrep, Trivy, Bandit, grype/Syft (SBOM), `llama-guard` (prompt injection), `presidio` (PII detection), MCP security model knowledge, pen-testing methodology, threat modeling (STRIDE/DREAD). |
| **Recommended LLM Backend** | Claude Opus 4 (security reasoning) or Gemini 2.5 Pro (broad threat surface analysis). Use a fast model (GPT-4o-mini or Gemini Flash) for initial SAST triage, then escalate to premium for confirmed findings. |
| **Approximate Token Budget** | 3,000–8,000 input tokens · 1,000–3,000 output tokens (due to detailed exploit descriptions) |
| **Special Authority** | Black Hat is the **only hat** (besides Gold Hat/CoVE) that can issue a **hard block** on CRITICAL findings. When Black Hat flags CRITICAL, the Conductor immediately escalates to HITL regardless of other hat results. |

---

#### ⚪ White Hat — Efficiency & Resources

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | Code includes loops over large datasets, database queries, LLM API calls, batch processing, streaming pipelines, caching logic, or memory-intensive operations. |
| **Focus Area** | Reduce token waste, optimize compute budgets, minimize memory bloat, improve query performance, and identify unnecessary redundancy in data processing pipelines. |
| **Core Assignments** | 1. Perform token-budget analysis: calculate prompt sizes for all LLM calls, compare against model context windows, identify truncation risks. 2. Estimate database query costs: analyze `WHERE` clauses, `JOIN` patterns, index usage, and projected row counts. 3. Identify opportunities for batch processing (combining multiple API calls into one), streaming (processing data in chunks rather than loading all into memory), and lazy evaluation. 4. Check caching strategies: is stale data possible? Are cache invalidation boundaries correct? Is the cache hit rate likely to be acceptable? 5. Analyze memory allocation patterns: are large objects held longer than necessary? Are there memory leaks in long-running agent loops? 6. Suggest algorithmic improvements: O(n²) to O(n log n), redundant sorting, unnecessary string concatenation. 7. Evaluate whether a cheaper LLM model could produce acceptable results for the given task (cost-quality tradeoff analysis). |
| **Severity Grading** | CRITICAL: LLM call will exceed context window (guaranteed failure). HIGH: O(n²) algorithm on production data, unbounded memory growth. MEDIUM: Missing batch optimization, suboptimal query. LOW: Minor efficiency suggestions, micro-optimizations. |
| **Output Format** | Resource consumption report with before/after estimates, cost projection (tokens × price per model), and prioritized optimization list with estimated impact. |
| **Required Skills / Tools** | LangSmith cost tracking, `tiktoken` / `tokenizer` libraries, database profiling (`EXPLAIN ANALYZE`, `pg_stat_statements`), memory profiling (Python `memory_profiler`, Node.js `heapdump`), algorithm complexity analysis. |
| **Recommended LLM Backend** | GPT-4o-mini or Gemini Flash (fast, cheap — this hat's analysis is largely deterministic). |
| **Approximate Token Budget** | 1,500–3,000 input tokens · 400–800 output tokens |

---

#### 🟡 Yellow Hat — Synergies & Integration

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | New feature or change touches two or more services, components, modules, or bounded contexts. Triggered by cross-boundary API calls, shared database tables, event-bus messages, or configuration changes affecting multiple services. |
| **Focus Area** | Discover hidden cross-component synergies, identify reusable APIs or shared infrastructure, find opportunities for consolidation, and flag integration anti-patterns (circular dependencies, tight coupling, distributed monolith smell). |
| **Core Assignments** | 1. Build a dependency graph of all components touched by the PR, including transitive dependencies. 2. Identify potential shared caches, event buses, or message queues that could reduce direct coupling. 3. Highlight "10× improvement" opportunities: shared authentication middleware, unified error-handling patterns, common data-access layers. 4. Detect circular dependencies between modules and suggest breakage strategies (interface extraction, event-driven decoupling). 5. Evaluate whether the integration follows established patterns (API gateway, service mesh, event sourcing) or introduces ad-hoc coupling. 6. Propose A2A integration patterns if multiple agents/services need to coordinate (task delegation, result aggregation). |
| **Severity Grading** | CRITICAL: Circular dependency that will cause deployment deadlock. HIGH: Distributed monolith pattern emerging. MEDIUM: Missed consolidation opportunity. LOW: Architectural suggestion for future consideration. |
| **Output Format** | Dependency graph visualization (Mermaid), integration health report, and opportunity matrix. |
| **Required Skills / Tools** | Graph analysis (`networkx`, `madge` for JS), GraphQL schema introspection, service-mesh analysis (Istio/Linkerd), LangGraph multi-agent graph design, A2A protocol patterns. |
| **Recommended LLM Backend** | Claude Sonnet 4 (architectural reasoning with good cost-quality ratio). |
| **Approximate Token Budget** | 2,000–5,000 input tokens · 600–1,200 output tokens |

---

#### 🟢 Green Hat — Evolution & Extensibility

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | Core architecture changes, new module additions, public API surface changes, schema migrations, or introduction of new abstractions/interfaces. |
| **Focus Area** | Ensure the change is future-proof: versioning policies are correct, deprecation notices are in place, extension points exist, and the architecture accommodates planned growth. |
| **Core Assignments** | 1. Verify API versioning policy: are breaking changes properly versioned? Are deprecated endpoints scheduled for removal with documented timelines? 2. Check for extension points: can new behavior be added without modifying existing code (plugin hooks, strategy patterns, event listeners)? 3. Validate schema migration strategy: are backward-compatible migrations used? Is rollback possible? 4. Assess the "growth path": if the feature needs to scale 10× or 100×, will the current architecture support it, or will it need fundamental redesign? 5. Verify OpenAPI spec accuracy: does the API documentation match the actual implementation? 6. Check that new abstractions are appropriately generic (not over-engineered for a single use case) and appropriately specific (not so generic they're unusable). |
| **Severity Grading** | CRITICAL: Breaking API change without version bump. HIGH: Schema migration without rollback plan. MEDIUM: Missing extension points for predictable growth. LOW: Documentation gaps, naming suggestions. |
| **Output Format** | Evolution roadmap with risk assessment, extensibility score (0–100), and specific recommendations for each growth dimension. |
| **Required Skills / Tools** | Semantic-release tooling, OpenAPI spec diff tools (`oasdiff`), schema migration analysis, design-pattern expertise (SOLID, GoF patterns), LangChain tool-registry patterns. |
| **Recommended LLM Backend** | Claude Opus 4 or GPT-4o (strategic architectural reasoning). |
| **Approximate Token Budget** | 2,000–4,000 input tokens · 500–1,000 output tokens |

---

#### 🔵 Blue Hat — Process & Specification

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | **Every PR** — runs unconditionally as a mandatory process baseline. |
| **Focus Area** | Ensure internal consistency between code and design documents, verify test completeness, enforce commit-message schema, and validate that the change follows established engineering processes. |
| **Core Assignments** | 1. Compare code changes against design documents, ADRs (Architecture Decision Records), and spec files (OpenAPI, JSON Schema, Protobuf definitions). 2. Flag missing unit tests, integration tests, and edge-case coverage. Calculate test coverage delta. 3. Enforce commit-message conventions (Conventional Commits, project-specific schemas). 4. Verify that PR description accurately describes the change, includes testing instructions, and references relevant issues. 5. Check that required reviews (security review, performance review, design review) have been completed or are not applicable. 6. Validate that changelog/release-notes entries exist for user-facing changes. 7. Ensure that new code follows established coding standards (linting, formatting, naming conventions). |
| **Severity Grading** | CRITICAL: Code contradicts approved ADR or design spec. HIGH: No tests for changed logic, missing required reviews. MEDIUM: Commit message non-conformant, documentation drift. LOW: Style/naming suggestions. |
| **Output Format** | Compliance report with pass/fail for each process gate, coverage delta table, and discrepancy list between code and documentation. |
| **Required Skills / Tools** | `markdown-lint`, `commitlint`, `conventional-commits` parser, `pytest-cov` / `jest --coverage`, `oasdiff`, ADR parsing, CI configuration analysis. |
| **Recommended LLM Backend** | GPT-4o-mini or Claude Haiku (fast, deterministic checks — most of this hat's work is rule-based). |
| **Approximate Token Budget** | 2,000–6,000 input tokens · 300–600 output tokens |

---

#### 🟣 Indigo Hat — Cross-Feature Architecture

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | PR modifies more than two modules, changes integration points between bounded contexts, introduces shared libraries, or modifies cross-cutting concerns (logging, metrics, error handling). |
| **Focus Area** | Detect macro-level architectural issues: DRY violations across modules, duplicated pipelines, inconsistent patterns between teams, and emerging "big ball of mud" anti-patterns. |
| **Core Assignments** | 1. Perform cross-module similarity analysis: identify duplicated logic, near-duplicated patterns, and inconsistent implementations of the same concept across different modules. 2. Map the "architectural seam" — where does the change cross module boundaries, and are those boundaries properly defined? 3. Identify shared abstractions that should be extracted into common libraries. 4. Detect "architectural drift": is the codebase moving away from the documented architecture? 5. Evaluate whether the change introduces unnecessary coupling between modules that were previously independent. 6. Check that cross-cutting concerns (authentication, logging, error handling, metrics) are applied consistently across all affected modules. |
| **Severity Grading** | CRITICAL: Architectural drift that violates a documented constraint. HIGH: Large-scale code duplication across modules. MEDIUM: Inconsistent cross-cutting concern application. LOW: Architectural improvement suggestions. |
| **Output Format** | Cross-module analysis report with similarity heat map, dependency matrix, and concrete refactoring proposals. |
| **Required Skills / Tools** | SonarQube multi-module analysis, clone detection tools (`jscpd`, `PMD CPD`), architecture fitness functions, LangGraph macro-graph analysis, module boundary analysis. |
| **Recommended LLM Backend** | Claude Opus 4 (deep cross-module reasoning). |
| **Approximate Token Budget** | 5,000–15,000 input tokens (large diffs) · 800–2,000 output tokens |

---

#### 🩵 Cyan Hat — Innovation & Feasibility

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | Introduction of experimental patterns, new technology stack components, novel LLM usage patterns, prototype code, or "POC" markers in commits/PRs. |
| **Focus Area** | Validate technical feasibility, assess risk and ROI, benchmark performance and cost, and determine whether the innovation is production-ready or needs further development. |
| **Core Assignments** | 1. Conduct a rapid feasibility assessment: does the proposed approach have known limitations, unsupported edge cases, or maturity concerns? 2. Benchmark latency, throughput, and cost against the project's SLOs and budget constraints. 3. Identify "unknown unknowns" — areas where the new technology's behavior under production load is not well documented. 4. Evaluate the vendor/dependency risk: is the new technology backed by a stable organization? Is the community active? Are there known breaking changes between versions? 5. Produce a "feasibility memo" with a go/no-go recommendation and a risk register. 6. Suggest an incremental adoption path if the innovation is deemed high-risk (feature flags, canary deployment, shadow mode). |
| **Severity Grading** | CRITICAL: Known critical issue with the new technology that will cause production failure. HIGH: Significant performance or cost risk under production load. MEDIUM: Maturity concerns, limited community support. LOW: Documentation gaps, minor integration friction. |
| **Output Format** | Feasibility memo with risk matrix, performance benchmarks, cost projection, and adoption roadmap. |
| **Required Skills / Tools** | Cloud sandbox environments (GitHub Codespaces, Gitpod), performance profiling (`py-instrument`, `criterion`), cost estimation (provider pricing APIs), technology radar methodology, competitive analysis. |
| **Recommended LLM Backend** | Claude Opus 4 or Gemini 2.5 Pro (deep reasoning on novel technologies). |
| **Approximate Token Budget** | 2,000–4,000 input tokens · 800–1,500 output tokens |

---

#### 🟪 Purple Hat — AI Safety & Alignment

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | **Every PR** — runs unconditionally as a mandatory AI safety baseline. Additional depth when code manipulates prompts, uses epistemic modifiers (confidence scores, uncertainty quantification), processes personal data through LLMs, or introduces new model integrations. |
| **Focus Area** | OWASP Agentic AI Top 10 (goal manipulation, excessive agency, tool misuse, information integrity), bias detection, fairness assessment, PII leakage through LLM outputs, model alignment verification, hallucination risk, and EU AI Act compliance classification. |
| **Core Assignments** | 1. Scan all prompts for jailbreak-vulnerable patterns: does user input directly reach the model without sanitization? Are system prompts structured to resist manipulation? 2. Run bias-detection analysis on training data, retrieval results, and model outputs (using `fairlearn`, `AI Fairness 360`). 3. Verify PII handling: are prompts scrubbed of personal data before being sent to external LLM providers? Do outputs accidentally leak training data? 4. Assess hallucination risk: for factual claims in outputs, are grounding sources referenced? Is a confidence threshold enforced? 5. Check AI Act classification: does the change affect a high-risk AI system (biometrics, critical infrastructure, employment decisions)? If so, verify required documentation and human oversight mechanisms. 6. Validate that LLM outputs used for automated decisions include explainability traces. 7. Test for "excessive agency" — can the agent take actions beyond its intended scope without human approval? 8. Verify "tool misuse" guards — can the agent be tricked into using tools for unintended purposes? |
| **Severity Grading** | CRITICAL: Confirmed jailbreak path, bias causing discriminatory outcomes, PII leakage to external parties. HIGH: Missing PII scrubbing, no hallucination guardrails, excessive agency without HITL. MEDIUM: Missing bias audit, inadequate explainability. LOW: Documentation improvements, best-practice suggestions. |
| **Output Format** | AI safety report with OWASP Agentic mapping, bias audit summary, PII exposure assessment, and compliance checklist (EU AI Act, GDPR, CCPA). |
| **Required Skills / Tools** | `llama-guard` (prompt injection detection), `fairlearn` / `AI Fairness 360` (bias), `presidio` (PII detection), `neMo Guardrails`, RAGAS faithfulness metrics, EU AI Act classification framework. |
| **Recommended LLM Backend** | Claude Opus 4 (safety reasoning) — this hat must use the most capable model available for accurate threat assessment. |
| **Approximate Token Budget** | 3,000–8,000 input tokens · 1,000–2,500 output tokens |
| **Special Authority** | Purple Hat findings at CRITICAL or HIGH severity trigger an immediate HITL escalation, similar to Black Hat. AI safety findings cannot be overridden by other hats. |

---

#### 🟠 Orange Hat — DevOps & Automation

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | Changes to Dockerfiles, CI/CD YAML (GitHub Actions, GitLab CI, Argo), deployment scripts, Terraform/Helm/Pulumi configurations, Kubernetes manifests, or infrastructure-as-code files. |
| **Focus Area** | Verify CI/CD pipeline health, infrastructure-as-code quality, container security, deployment safety, and operational readiness. |
| **Core Assignments** | 1. Lint CI/CD configuration files for errors, deprecated actions, and security issues. 2. Test pipeline dry-run: do all steps have proper dependencies? Are secrets properly referenced (not hardcoded)? 3. Analyze Docker layer caching: can build times be improved? Are multi-stage builds used? Is the final image minimal (distroless/alpine)? 4. Check for secret exposure: environment variables in Dockerfiles, secrets in CI logs, exposed ports in Terraform. 5. Validate Terraform/Pulumi configuration: are resources properly tagged? Is state management secure? Are drift-detection policies in place? 6. Verify deployment strategies: is blue-green or canary deployment configured? Are rollback procedures documented? 7. Check that health checks, readiness probes, and liveness probes are configured for all services. |
| **Severity Grading** | CRITICAL: Secret in Docker image, exposed credentials in CI logs. HIGH: Missing health checks, no rollback procedure. MEDIUM: Suboptimal Docker layering, missing resource limits. LOW: Tagging improvements, naming conventions. |
| **Output Format** | DevOps health report with pipeline analysis, container security scan results, and IaC compliance checklist. |
| **Required Skills / Tools** | GitHub Actions linter (`actionlint`), Trivy Docker scanner, `hadolint` (Dockerfile linter), `tflint` / `checkov` (Terraform), `helm lint`, Kubernetes manifest validators, Argo Workflows API. |
| **Recommended LLM Backend** | GPT-4o or Claude Sonnet 4 (needs both YAML understanding and security knowledge). |
| **Approximate Token Budget** | 2,000–5,000 input tokens · 500–1,000 output tokens |

---

#### 🪨 Silver Hat — Context & Token Optimization

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | Any LLM prompt construction, prompt template changes, RAG pipeline modifications, context window management code, or changes to retrieval/chunking strategies. |
| **Focus Area** | Keep token usage within model limits, optimize context compression, recommend hybrid retrieval strategies, and ensure prompt engineering follows best practices for cost-efficiency and output quality. |
| **Core Assignments** | 1. Compute precise token counts for all prompts using the target model's tokenizer (`tiktoken` for OpenAI, `claude-tokenizer` for Anthropic). 2. Identify context-window overflow risks: if the sum of system prompt + retrieved context + user input exceeds the model's limit, flag immediately. 3. Suggest summarization or compression strategies for large contexts: extractive summarization, semantic chunking, or "lost-in-the-middle" mitigation (critical information placement). 4. Recommend hybrid retrieval (vector + BM25 + knowledge-graph) when pure vector search may miss relevant documents. 5. Evaluate prompt structure: is the system prompt well-organized? Are instructions clear and unambiguous? Is few-shot prompting used effectively? 6. Analyze RAG pipeline: are chunk sizes appropriate? Is overlap configured? Are reranking strategies in place? 7. Calculate the "cost per query" for the RAG pipeline and compare against project budget. |
| **Severity Grading** | CRITICAL: Prompt will exceed context window (guaranteed truncation or failure). HIGH: RAG retrieval returning irrelevant documents, missing reranking. MEDIUM: Suboptimal chunk size, no hybrid retrieval. LOW: Prompt phrasing improvements, minor token savings. |
| **Output Format** | Token analysis report with per-component breakdown, compression ratio estimates, and cost-per-query projection. |
| **Required Skills / Tools** | `tiktoken`, `anthropic` tokenizer, LlamaIndex chunking strategies, hybrid retriever patterns (LangChain), BM25 integration, RAGAS retrieval metrics. |
| **Recommended LLM Backend** | GPT-4o-mini (fast and cheap — token counting is largely deterministic). |
| **Approximate Token Budget** | 1,500–3,000 input tokens · 400–800 output tokens |

---

#### 💎 Azure Hat — MCP & Protocol Integration

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | Any tool-call definitions, function-calling schemas, MCP server/client code, A2A agent endpoints, or API contract changes. |
| **Focus Area** | Validate MCP contracts (request/response schemas, tool capabilities, resource URIs), enforce A2A inter-agent contracts, verify type safety, and ensure protocol compliance. |
| **Core Assignments** | 1. Verify MCP request/response schemas: do all tool definitions have valid JSON schemas? Are required fields marked? Are default values specified? 2. Check MCP server registration: is the server properly configured? Are capabilities (tools, resources, prompts) correctly declared? 3. Validate A2A contracts: are task-handshake protocols implemented? Are cancellation and reassignment signals handled? 4. Enforce type safety across protocol boundaries: are type coercions documented? Are there potential data loss conversions? 5. Auto-generate A2A contracts for downstream agents based on the current tool definitions. 6. Verify that MCP sandbox boundaries are respected: tools cannot access resources outside their declared scope. 7. Check protocol versioning: are breaking changes properly versioned? Are backward-compatible fallbacks implemented? |
| **Severity Grading** | CRITICAL: Schema mismatch that will cause runtime failure at protocol boundary. HIGH: Missing A2A contract, type coercion data loss. MEDIUM: Incomplete schema, missing version negotiation. LOW: Documentation improvements, naming conventions. |
| **Output Format** | Protocol compliance report with schema validation results, contract diff, and type-safety analysis. |
| **Required Skills / Tools** | MCP SDK (Anthropic `mcp` package), A2A client libraries (`google-adk`), JSON Schema validation (`ajv`), OpenAPI specification tools, Protocol Buffers / gRPC reflection. |
| **Recommended LLM Backend** | Claude Sonnet 4 or GPT-4o (needs JSON schema reasoning and protocol understanding). |
| **Approximate Token Budget** | 2,000–6,000 input tokens · 600–1,200 output tokens |

---

#### 🟤 Brown Hat — Data Governance & Privacy

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | Code reads or writes personally identifiable information (PII), logs user data, stores data in databases or file systems, processes cookies/session data, or handles data exports/deletions. |
| **Focus Area** | Enforce GDPR, CCPA, HIPAA (where applicable), and general data-privacy best practices. Ensure data minimization, purpose limitation, consent management, and right-to-erasure compliance. |
| **Core Assignments** | 1. Perform data-flow analysis: trace how PII enters, transforms, is stored, and exits the system. Flag any unexpected data flows. 2. Verify PII field encryption at rest and in transit. 3. Check that consent management is properly implemented: is consent collected before data collection? Can consent be withdrawn? 4. Validate right-to-erasure implementation: can all user data be completely deleted on request? Are there backup copies that might persist? 5. Audit logging: are data access events logged? Is the log retention policy compliant? 6. Generate a privacy impact assessment (PIA) summary for the change. 7. Check for data minimization: is only the minimum necessary data collected and retained? 8. Verify that data shared with third-party LLM providers is scrubbed of PII (via `presidio` or equivalent). |
| **Severity Grading** | CRITICAL: PII stored in plaintext, data shared with external LLM without PII scrubbing, missing encryption. HIGH: Incomplete right-to-erasure, no consent management. MEDIUM: Missing audit logging, suboptimal data retention. LOW: Documentation improvements, privacy policy wording suggestions. |
| **Output Format** | Data governance report with data-flow diagram, PIA summary, compliance checklist (GDPR/CCPA/HIPAA), and remediation priorities. |
| **Required Skills / Tools** | `presidio` (PII detection), `pydantic-settings` (configuration), `privacy-engine` (data anonymization), data cataloging tools (Amundsen, DataHub), GDPR/CCPA regulatory knowledge, encryption library expertise. |
| **Recommended LLM Backend** | Claude Opus 4 (regulatory reasoning) or GPT-4o. |
| **Approximate Token Budget** | 2,000–5,000 input tokens · 600–1,500 output tokens |

---

#### ⚙️ Gray Hat — Observability & Reliability

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | Production-bound service code, long-running agent processes, SLA-bound API endpoints, or any code that will run in a monitored environment. |
| **Focus Area** | End-to-end distributed tracing, latency budgeting, error-rate alerting, SLO/SLA compliance, dashboard creation, and incident-response readiness. |
| **Core Assignments** | 1. Verify OpenTelemetry instrumentation: are spans created for all significant operations? Are trace contexts propagated across service boundaries? 2. Define or validate SLOs: latency (p50, p95, p99), error rate, availability. Check that alerting thresholds are aligned with SLOs (error-budget-based alerting). 3. Check structured logging: are logs in a parseable format (JSON)? Do they include correlation IDs (trace IDs)? Are sensitive fields excluded? 4. Verify metric exports: are custom metrics (business-level, not just infrastructure) exposed via Prometheus format? 5. Create dashboard specifications: what are the key indicators that should be visible for this service? 6. Assess incident-response readiness: are runbooks documented? Are escalation paths clear? 7. Check for "silent failure" patterns: operations that can fail without being logged, traced, or alerted. |
| **Severity Grading** | CRITICAL: Missing instrumentation on critical path with SLA commitment. HIGH: No error alerting, missing trace propagation. MEDIUM: Incomplete logging, missing custom metrics. LOW: Dashboard suggestions, metric naming improvements. |
| **Output Format** | Observability gap analysis, SLO recommendation, dashboard specification (Grafana JSON or equivalent), and alerting rule proposals. |
| **Required Skills / Tools** | OpenTelemetry SDK (traces, metrics, logs), Prometheus + Grafana, Alertmanager, LangSmith tracing, distributed-systems monitoring patterns, SLO/SLI/SLA methodology. |
| **Recommended LLM Backend** | GPT-4o or Claude Sonnet 4 (needs distributed-systems knowledge). |
| **Approximate Token Budget** | 2,000–4,000 input tokens · 500–1,200 output tokens |

---

#### ♿ Teal Hat — Accessibility & Inclusion

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | UI changes (HTML, CSS, component libraries), API response format changes, content generation, i18n/l10n additions, or any user-facing text changes. |
| **Focus Area** | WCAG 2.2 AA compliance, screen-reader compatibility, keyboard navigation, color contrast, inclusive language, and internationalization readiness. |
| **Core Assignments** | 1. Check color contrast ratios for all new/changed UI elements against WCAG 2.2 AA standards (4.5:1 for normal text, 3:1 for large text). 2. Verify keyboard navigability: can all interactive elements be reached and activated via keyboard alone? 3. Check ARIA labels and roles: are they present, accurate, and not redundant with visible labels? 4. Assess screen-reader compatibility: does the content flow make sense when linearized? Are dynamic updates announced? 5. Review inclusive language: are there terms that could be exclusionary? Are gender-neutral options provided where applicable? 6. Verify i18n readiness: are strings externalized? Are date/number/currency formats locale-aware? Are text expansion ratios considered for non-Latin scripts? 7. Check that LLM-generated content includes alt-text for images, captions for media, and appropriate reading levels. |
| **Severity Grading** | CRITICAL: UI completely inaccessible to assistive technology (missing ARIA on custom widgets). HIGH: Missing keyboard navigation, insufficient color contrast. MEDIUM: Incomplete i18n, minor ARIA issues. LOW: Language suggestions, documentation improvements. |
| **Output Format** | WCAG compliance report with per-criterion pass/fail, screen-reader test results, and i18n readiness assessment. |
| **Required Skills / Tools** | Axe / Lighthouse accessibility audit, `pa11y`, WCAG 2.2 specification, i18n frameworks (`react-intl`, `vue-i18n`), screen-reader simulation (`voiceover`, `nvda`). |
| **Recommended LLM Backend** | GPT-4o-mini (accessibility checks are largely pattern-based). |
| **Approximate Token Budget** | 1,000–3,000 input tokens · 300–800 output tokens |

---

#### 🔗 Steel Hat — Supply Chain & Dependencies

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | Changes to `package.json`, `requirements.txt`, `go.mod`, `Cargo.toml`, `pom.xml`, lockfile updates, or addition of any new external dependency. |
| **Focus Area** | Software Bill of Materials (SBOM) integrity, known vulnerability scanning, license compliance, dependency freshness, and supply-chain attack surface. |
| **Core Assignments** | 1. Generate or update SBOM for the changed dependencies (using Syft). 2. Run vulnerability scanning (using Grype, Snyk, or Trivy) against all dependencies. 3. Check license compliance: are all dependency licenses compatible with the project's license? Are there `GPL`/`AGPL` dependencies in a proprietary project? 4. Verify dependency freshness: are any dependencies unmaintained (no commits in 12+ months)? Are known end-of-life packages still in use? 5. Check for typosquatting: are package names one character away from popular packages? 6. Verify lockfile integrity: does the lockfile match the manifest? Are integrity hashes (SHASUM, SRI) present and correct? 7. Assess transitive dependency risk: do any new dependencies introduce deep dependency trees with known vulnerabilities? |
| **Severity Grading** | CRITICAL: Known critical vulnerability (CVSS ≥9.0) in direct dependency, license violation. HIGH: Known high vulnerability (CVSS 7.0–8.9), typosquatting indicator. MEDIUM: Stale dependency, missing lockfile integrity. LOW: License documentation improvements, dependency update suggestions. |
| **Output Format** | SBOM, vulnerability scan report, license matrix, and dependency health dashboard data. |
| **Required Skills / Tools** | Syft (SBOM generation), Grype (vulnerability scanning), Trivy, `npm audit` / `pip audit` / `cargo audit`, FOSSA or `licensee` (license detection), `dep-tree` (transitive analysis). |
| **Recommended LLM Backend** | GPT-4o-mini or Gemini Flash (mostly deterministic scanning). |
| **Approximate Token Budget** | 1,000–3,000 input tokens · 400–800 output tokens |

---

#### 🧪 Chartreuse Hat — Testing & Evaluation

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | Test additions or modifications, evaluation pipeline changes, benchmark updates, assertion changes, or any modification to testing infrastructure (fixtures, mocks, test utilities). |
| **Focus Area** | Test coverage adequacy, test quality (flaky tests, assertion specificity), RAG evaluation metrics, prompt evaluation methodology, regression detection, and benchmark validity. |
| **Core Assignments** | 1. Calculate test coverage delta: what is the net change in line/branch/function coverage? Are uncovered paths justified? 2. Identify flaky test indicators: non-deterministic assertions, time-dependent tests, tests that depend on execution order. 3. Verify assertion quality: are assertions specific (checking exact values) rather than generic (checking "not null")? Are edge cases covered? 4. For RAG systems: verify that RAGAS metrics (faithfulness, answer_relevancy, context_precision, context_recall) are measured and tracked. 5. For prompt-based systems: verify that `promptfoo` or equivalent evaluation is configured with adversarial test cases. 6. Check that benchmark baselines are documented and that regression thresholds are enforced in CI. 7. Verify that mocks and fixtures accurately represent production data shapes and edge cases. |
| **Severity Grading** | CRITICAL: Critical path with 0% test coverage, removed test without replacement. HIGH: Known flaky test not quarantined, missing RAG evaluation. MEDIUM: Weak assertions, missing edge-case tests. LOW: Benchmark improvements, test organization suggestions. |
| **Output Format** | Test quality report with coverage delta, flaky test assessment, RAGAS metric summary, and regression risk score. |
| **Required Skills / Tools** | `pytest-cov`, `jest --coverage`, RAGAS (RAG evaluation), `promptfoo` (prompt eval), `mutation-testing` tools, `flaky` test detection, benchmarking frameworks. |
| **Recommended LLM Backend** | Claude Sonnet 4 (needs test-design reasoning). |
| **Approximate Token Budget** | 2,000–5,000 input tokens · 500–1,200 output tokens |

---

#### ✨ Gold Hat — CoVE (Convergent Verification & Expert) — Final QA

| Attribute | Detail |
|-----------|--------|
| **Auto-Select When** | **Always runs last**, after all other triggered hats have produced their reports. This hat never runs concurrently with others — it is the terminal node in the orchestration graph. |
| **Focus Area** | 14-dimension adversarial QA: functional correctness, security, AI safety, performance/efficiency, accessibility, i18n, infrastructure readiness, supply-chain integrity, data governance, observability coverage, architectural coherence, test adequacy, documentation completeness, and regulatory compliance. Produce the final merge-ready decision. |
| **Core Assignments** | 1. Aggregate all hat reports into a unified findings matrix. 2. Deduplicate overlapping findings (e.g., both Black Hat and Purple Hat flag the same prompt injection risk). 3. Resolve conflicts between hats (e.g., Yellow Hat recommends shared cache, but Indigo Hat says it would increase coupling — CoVE adjudicates). 4. Prioritize all findings by severity (CRITICAL > HIGH > MEDIUM > LOW) and by blast radius (number of users/systems affected). 5. Produce the final **Merge Decision**: `ALLOW` (no blockers), `ESCALATE` (requires human review), or `QUARANTINE` (hard block until critical issues are resolved). 6. Generate an executive summary suitable for PR comments, Slack notifications, or management dashboards. 7. For `ESCALATE` decisions, produce a structured checklist for the human reviewer: exactly what to verify, which files to check, and what the automated system could not determine. 8. Track decision accuracy over time (did `ALLOW` decisions lead to incidents? did `QUARANTINE` decisions have false positives?) for continuous improvement. |
| **Severity Grading** | This hat does not grade severity — it consumes severity grades from all other hats and produces a composite risk score (0–100). |
| **Output Format** | Final adjudication report with: composite risk score, findings matrix, conflict resolution log, merge decision with rationale, and human-review checklist (if applicable). |
| **Required Skills / Tools** | Policy engine (OPA/Rego), multi-objective decision theory, severity-weighted scoring algorithm, LangGraph decision-engine node, release-gate UI integration. |
| **Recommended LLM Backend** | Claude Opus 4 (must use the highest-capability model — this is the final arbiter and its reasoning quality directly determines system effectiveness). |
| **Approximate Token Budget** | 8,000–25,000 input tokens (all hat reports) · 2,000–4,000 output tokens (comprehensive adjudication) |
| **Special Authority** | Gold Hat/CoVE has **absolute final authority** on the merge decision. Its verdict cannot be overridden by any other hat. If it outputs `QUARANTINE`, the PR is blocked until all CRITICAL findings are resolved and a re-run confirms resolution. |

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

**Keyword Heuristic Mapping (excerpt):**

| Trigger Keywords / Patterns | Activated Hats |
|----------------------------|----------------|
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
| **G3: Consistency Gate** | Post-consolidation | After Consolidator merges reports | No unresolved contradictions between hat findings (e.g., one hat says "add caching" and another says "caching will break consistency") | PAUSE: Route contradictions to Arbiter persona for resolution |
| **G4: Timeout Gate** | Mid-execution | Per-hat, after configurable timeout (default: 120s per hat) | Hat has not produced output within timeout | TIMEOUT: Record gap, log timeout, proceed without this hat's input (graceful degradation) |
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
    on_timeout: "graceful_degrade"  # or "fail_hard"

  final_decision:
    enabled: true
    auto_allow_threshold_risk_score: 20  # risk score ≤20 → auto-ALLOW
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
| **Backoff Multiplier** | 2× (exponential) | 1s → 2s → 4s. Covers most transient failure windows (rate limits, temporary API issues). |
| **Max Backoff** | 10 seconds | Prevents excessive waiting. If three attempts with 1s+2s+4s backoff all fail, the issue is likely not transient. |
| **Jitter** | ±20% random | Prevents thundering-herd effect when multiple hats retry simultaneously after a shared API outage. |
| **Retryable Errors** | Rate limit (429), server error (500/502/503), timeout, context window exceeded, LLM output parse failure | Errors that are likely transient or can be resolved with a slightly different request. |
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
| **Metrics Emitted** | `hat.{name}.circuit_breaker.state`, `hat.{name}.circuit_breaker.failure_count` | `provider.{name}.circuit_breaker.state` |

### 8.4 Backpressure Mechanism

When the system is under heavy load (multiple PRs triggering simultaneously):

1. **Queue-Based Dispatch**: Hat executions are placed in a priority queue. Always-on hats (Black, Blue, Purple) have highest priority.
2. **Concurrency Limit**: Maximum N hats running concurrently per PR (default: 6, configurable based on LLM provider rate limits).
3. **Token Budget Throttling**: If the global token budget is approaching its limit, lower-priority hats are deferred to the next available budget window.
4. **Adaptive Model Selection**: Under load, the system automatically downgrades non-critical hats to cheaper/faster models (e.g., Claude Opus → Claude Haiku for Silver Hat).

```yaml
backpressure:
  max_concurrent_hats_per_pr: 6
  queue_priority_order:
    - black, purple, blue  # Always-on, highest priority
    - red, steel            # Security and safety-adjacent
    - orange, gray          # Ops concerns
    - white, chartreuse     # Quality concerns
    - yellow, green, indigo # Architecture
    - silver, azure         # Optimization
    - teal, cyan, brown     # Specialized
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

### 9.1 State Schema

The orchestration state is a single JSON object that is persisted at every node boundary via LangGraph's `PostgresSaver` (or equivalent checkpoint store).

```jsonc
{
  "run_id": "uuid-v4",
  "trigger": { "type": "pr", "pr_number": 1234, "repo": "org/repo", "sha": "abc123...", "author": "dev@example.com" },
  "phase": "dispatching | executing | consolidating | adjudicating | done",
  "hat_selector_results": {
    "always": ["black", "blue", "purple"],
    "conditional": ["red", "white", "orange", "silver"],
    "skipped": { "green": { "reason": "budget_exhausted" } }
  },
  "hat_reports": {
    "black": { "status": "complete", "findings": [...], "severity_summary": {...}, "token_usage": 5230, "latency_ms": 8500 },
    "red": { "status": "timeout", "error": "LLM provider timeout after 120s", "token_usage": 2100 },
    // ...
  },
  "gate_results": {
    "cost_budget": { "passed": true, "estimated_cost_usd": 1.82 },
    "security_fast_path": { "passed": false, "triggered_by": "black", "critical_count": 1 },
    "consistency": { "passed": true, "contradictions_resolved": 2 },
    "timeout": { "passed": true, "hats_timed_out": ["red"] },
    "final_decision": { "passed": true, "decision": "ESCALATE" }
  },
  "consolidated_report": { "total_findings": 23, "by_severity": {...}, "deduplicated": 4 },
  "cove_decision": {
    "verdict": "ESCALATE",
    "risk_score": 67,
    "rationale": "...",
    "human_checklist": [...]
  },
  "metadata": {
    "total_token_usage": 45230,
    "total_cost_usd": 1.47,
    "total_duration_ms": 45000,
    "checkpoint_sequence": 12
  }
}
```

### 9.2 Report Schema (Per-Hat)

Each hat produces a standardized report:

```jsonc
{
  "hat": "black",
  "run_id": "uuid-v4",
  "timestamp": "2026-04-10T14:30:00Z",
  "status": "complete | timeout | error | skipped",
  "model_used": "claude-opus-4-20250514",
  "token_usage": { "input": 5230, "output": 1800, "total": 7030 },
  "latency_ms": 8500,
  "findings": [
    {
      "id": "black-001",
      "severity": "CRITICAL",
      "title": "Hardcoded API key in auth middleware",
      "description": "File `src/auth/middleware.ts:42` contains a hardcoded API key `sk-...` that is logged on every request.",
      "file": "src/auth/middleware.ts",
      "line": 42,
      "remediation": "Move to environment variable: `process.env.AUTH_API_KEY`. Add to secret management (Vault).",
      "owasp_reference": "LLM07:2025",
      "cve_references": [],
      "confidence": 0.98
    }
  ],
  "summary": {
    "total_findings": 5,
    "by_severity": { "CRITICAL": 1, "HIGH": 2, "MEDIUM": 1, "LOW": 1 },
    "overall_assessment": "Security posture is severely compromised due to hardcoded credentials and missing input sanitization."
  }
}
```

### 9.3 Communication Patterns

| Pattern | Description | Protocol |
|---------|-------------|----------|
| **Report Publication** | Each hat publishes its report to the shared state store. | Direct state update (no protocol needed — same process). |
| **Cross-Hat Consultation** | A hat can request input from another hat's persona (e.g., Black Hat asks Purple Hat's perspective on a prompt-injection finding). | A2A task delegation with 60s timeout. |
| **Conflict Resolution** | When two hats produce contradictory recommendations, the Arbiter persona is invoked. | A2A task delegation to Arbiter, which reads both reports and produces a resolution. |
| **Emergency Broadcast** | Black Hat or Purple Hat can broadcast a CRITICAL finding that immediately alerts all running hats. | In-process event bus (for same-process hats) or A2A notification (for distributed hats). |

---

## 10. Human-in-the-Loop (HITL) Framework

### 10.1 HITL Trigger Conditions

| Condition | Action |
|-----------|--------|
| Black Hat finds CRITICAL severity | Immediate escalation. Pipeline pauses. |
| Purple Hat finds CRITICAL or HIGH severity | Immediate escalation. Pipeline pauses. |
| CoVE decision is `ESCALATE` | Standard escalation. Human has 24h to review (configurable). |
| CoVE decision is `QUARANTINE` | Block notification. Human must explicitly override to unblock. |
| Contradiction gate (G3) cannot be auto-resolved | Escalate to Arbiter persona → if still unresolved, escalate to human. |
| Cost gate (G1) exceeded by >50% | Notify requester for approval to proceed at higher cost. |

### 10.2 HITL Interaction Flow

```mermaid
sequenceDiagram
    participant C as Conductor
    participant COVE as Gold Hat (CoVE)
    participant HITL as HITL Gateway
    participant H as Human Reviewer
    participant G as GitHub/Slack

    C->>COVE: Consolidated reports
    COVE->>C: Decision: ESCALATE (risk_score: 67)
    C->>HITL: Create escalation ticket
    HITL->>G: Post PR comment with checklist
    HITL->>G: Send Slack DM to reviewer
    G->>H: Human sees notification
    
    alt Human Approves
        H->>G: Comment "/hats approve"
        G->>HITL: Webhook: approved
        HITL->>C: Resume pipeline → ALLOW
        C->>G: Post approval comment, enable merge
    else Human Requests Changes
        H->>G: Comment "/hats request-changes Fix X and Y"
        G->>HITL: Webhook: request-changes
        HITL->>C: Resume pipeline with feedback
        C->>G: Post feedback, await new commit
    else Human Rejects
        H->>G: Comment "/hats reject"
        G->>HITL: Webhook: rejected
        HITL->>C: QUARANTINE
        C->>G: Post rejection with rationale
    else Timeout (24h default)
        HITL->>C: Auto-ESCALATE to senior reviewer
    end
```

### 10.3 HITL Interfaces

| Interface | Description | Commands |
|-----------|-------------|----------|
| **GitHub PR Comments** | Primary interface. Reviewers interact via slash commands. | `/hats approve`, `/hats reject`, `/hats request-changes [reason]`, `/hats status`, `/hats retry` |
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
  │   └── [sast_scan:semgrep]                 (duration, findings count)
  ├── [hat:blue]                               (duration, token usage)
  │   └── [llm_call:gpt-4o-mini]              (latency, tokens, cost)
  ├── [hat:purple]                             (duration, token usage)
  │   ├── [llm_call:claude-opus-4]             (latency, tokens, cost)
  │   └── [bias_scan:fairlearn]               (duration, results)
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
hats_run_duration_seconds{verdict="ESCALATE"} 42.1
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
| CoVE false positive detected | Human overrides QUARANTINE to ALLOW | INFO | Slack #hats-feedback (for tuning) |
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
| **Cost exhaustion attack (malicious PRs to drain LLM budget)** | Per-pr cost gate (G1). Per-user rate limiting. Anomaly detection on cost spikes. |

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
| 1 | Selector | — | File analysis: `api/chat.py`, `retriever.py`, `system_prompt.txt`, `requirements.txt` (new: `chromadb`, `anthropic`) | Selected 12 hats: Black, Blue, Purple (always), Red, White, Silver, Azure, Brown, Steel, Chartreuse, Gray, Orange | — |
| 2 | Pre-flight | — | Cost estimation: 12 hats × avg 4k tokens = ~48k tokens ≈ $0.72 | Within budget ($2.50) | ✅ PASS |
| 3 | Gate G1 | Cost Budget | Budget OK | Proceed | — |
| 4 | Execute | ⚫ Black | Scans for auth, input sanitization, secret exposure | No auth on `/api/chat` — public endpoint accepts arbitrary user input and passes it directly into RAG query and LLM prompt | 🔴 CRITICAL |
| 5 | Gate G2 | Security Fast-Path | CRITICAL finding detected | **SHORT-CIRCUIT**: Skip remaining hats, escalate to HITL immediately | — |
| 6 | HITL | Human | Security reviewer sees Black Hat finding | Requests developer add rate limiting and input sanitization before full review | — |
| 7 | Execute | ⚫ Black | Re-scan after fix | Auth added, input sanitized. Minor: `system_prompt.txt` doesn't instruct model to refuse off-topic queries | 🟡 MEDIUM |
| 8 | Execute | 🟪 Purple | AI safety scan | Prompt template includes user query verbatim without system-level jailbreak resistance. No hallucination guardrail — model could invent information not in knowledge base | 🟠 HIGH |
| 9 | Execute | ⚪ White | Efficiency scan | RAG retrieves top-10 documents — sending all 10 to LLM wastes ~3k tokens per query. Recommend top-5 + reranking | 🟡 MEDIUM |
| 10 | Execute | 🪨 Silver | Token optimization | System prompt (850 tokens) + 10 docs (avg 400 tokens each = 4k) + user query = ~5k tokens. Claude Sonnet limit is 200k — OK, but costly. Recommends chunking + summary | 🟡 MEDIUM |
| 11 | Execute | 💎 Azure | MCP check | No MCP integration for the retriever tool — should expose as MCP tool for composability | 🟢 LOW |
| 12 | Execute | 🟤 Brown | Privacy scan | User chat history stored in ChromaDB without PII scrubbing. Chat logs may contain names, emails, account numbers. No retention policy | 🔴 CRITICAL |
| 13 | Execute | 🔗 Steel | Dependency scan | `chromadb` v0.4.22 has known medium vulnerability (CVE-2024-XXXX). `anthropic` SDK is latest. | 🟠 HIGH |
| 14 | Execute | ⚙️ Gray | Observability | No OpenTelemetry spans on the `/api/chat` endpoint. No latency metrics. No trace ID propagation to LLM provider | 🟡 MEDIUM |
| 15 | Execute | 🧪 Chartreuse | Testing | Unit tests exist for retriever (coverage 78%) but no tests for the chat endpoint itself. No adversarial prompt tests. No RAGAS metrics configured | 🟠 HIGH |
| 16 | Execute | 🟠 Orange | DevOps | No Dockerfile for the new service. No health check endpoint defined | 🟡 MEDIUM |
| 17 | Consolidate | — | Merges all reports | 18 total findings. 2 CRITICAL, 2 HIGH, 6 MEDIUM, 8 LOW. Deduplicated 3 overlapping findings | — |
| 18 | Adjudicate | ✨ CoVE | Final analysis | Composite risk score: 72/100. Decision: **ESCALATE** — CRITICAL findings (missing PII scrubbing, incomplete privacy handling) must be resolved before merge | ESCALATE |
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
5. ⚪ White (process quality — fast and cheap)
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

### Appendix D: Glossary

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

*This specification is a living document. As the agentic AI ecosystem evolves (new protocols, new attack vectors, new best practices), the Hats team should be updated accordingly. Each hat's effectiveness metrics should be reviewed quarterly, and persona prompts should be refined based on false-positive/negative analysis.*
