# 🎩 Appendix E — Implementation Guide: Running the Hats Team on Ollama Cloud + n8n

**Version:** 2.0 · **Date:** 2026-04-10
**Companion to:** [`AGENTIC_AI_HATS_TEAM_STACK.md`](./AGENTIC_AI_HATS_TEAM_STACK.md) (Sections 1–16)
**Source Documentation:**
- `Ollama_Cloud_Models_COMPLETE.docx` — Full 29-model inventory
- `Ollama_Cloud_Models_Comparison_Addendum.docx` — Benchmarks, pricing, decision matrix
- `AI_Agent_Best_Practices_Guide (2).docx` — Prompt patterns, security box, self-improvement
- `Ultimate_n8n_Workflows_Guide_2026.md` — n8n 2.16.0 workflows, nodes, scaling

---

## Table of Contents

1. [Architecture Overview: How the Three Layers Fit Together](#e1-architecture-overview)
2. [LLM Backend Mapping — Ollama Cloud Models for Every Hat](#e2-llm-backend-mapping)
3. [Cost-Optimized Model Selection Strategy](#e3-cost-optimized-model-selection)
4. [Persona System Prompts — Best Practices Integration](#e4-persona-system-prompts)
5. [The Conductor on n8n — Complete Workflow Architecture](#e5-the-conductor-on-n8n)
6. [Gate Engine — n8n Workflow Implementation](#e6-gate-engine-implementation)
7. [Retry, Circuit Breaker & Backpressure in n8n](#e7-retry-circuit-breaker-backpressure)
8. [HITL Framework — n8n Webhook + Notification Workflows](#e8-hitl-framework)
9. [Each Hat as an n8n Sub-Workflow](#e9-hat-sub-workflows)
10. [Consolidator & CoVE Adjudication Workflows](#e10-consolidator--cove)
11. [Observability — Metrics, Tracing & Cost Tracking in n8n](#e11-observability)
12. [Security Box — Deterministic Controls in n8n](#e12-security-box)
13. [Self-Improvement Pipeline — Continuous Tuning](#e13-self-improvement-pipeline)
14. [Complete Step-by-Step Deployment](#e14-step-by-step-deployment)
15. [Production Runbook & Troubleshooting](#e15-runbook--troubleshooting)

---

## E1. Architecture Overview: How the Three Layers Fit Together

The Hats Team specification (Sections 1–16 of the main document) defines **what** the system does — 18 hats, 5 gates, 16+ personas, retry policies, HITL tiers, observability. This appendix defines **how** to build it using your specific toolchain.

### The Three-Layer Stack

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 3 — ORCHESTRATION & AUTOMATION                              │
│  n8n 2.16.0 (Docker Compose + PostgreSQL + Redis Queue Mode)        │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Conductor    │  │ Hat Selector │  │ Gate Engine               │  │
│  │ (Main WF)    │  │ (Sub-WF)     │  │ (5 gates, If/Switch)     │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘  │
│         │                 │                       │                │
│  ┌──────┴─────────────────┴───────────────────────┴─────────────┐  │
│  │ 18 Hat Sub-Workflows (Execute Sub-Workflow nodes)             │  │
│  │ Black | Blue | Purple | Red | White | ... | Gold/CoVE        │  │
│  └──────────────────────────┬──────────────────────────────────┘  │
│                              │                                     │
│  ┌──────────────────────────┴──────────────────────────────────┐  │
│  │ HITL + Notifications + Error Trigger                        │  │
│  │ Slack | GitHub PR Comments | Email | n8n Error Trigger      │  │
│  └─────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 2 — LLM INFERENCE                                          │
│  Ollama Cloud (OpenAI-compatible API)                              │
│                                                                     │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────┐  │
│  │ GLM-5.1   │  │DeepSeek   │  │ Nemotron  │  │ Ministral 3   │  │
│  │ (Primary) │  │ V3.1      │  │ 3 Super   │  │ (Fast Tier)   │  │
│  └───────────┘  └───────────┘  └───────────┘  └───────────────┘  │
│                                                                     │
│  All 29 models available via OpenAI-compatible endpoint             │
│  Cost: $0.10–$1.20/M input · $0.28–$3.00/M output                 │
│  10–30x cheaper than Claude Opus 4.6 / GPT-5                       │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 1 — AGENT DESIGN PATTERNS                                   │
│  AI Agent Best Practices Guide                                     │
│                                                                     │
│  10 Prompt Patterns | Deterministic Security Box | Chain of       │
│  Verification | Confidence Thresholds | Self-Evaluation Loop |   │
│  Progressive Disclosure | Context Window Management                │
└─────────────────────────────────────────────────────────────────────┘
```

### Why This Combination Works

| Concern | Tool | How It Maps to the Hats Stack |
|---------|------|-------------------------------|
| **LLM Inference** | Ollama Cloud | Replaces the "multi-provider" abstraction. All 29 models use OpenAI-compatible API → one integration pattern. Cost 10–30× lower than Western providers. |
| **Orchestration** | n8n 2.16.0 | Replaces LangGraph as the stateful orchestration engine. Sub-workflows = hat nodes. If/Switch = gates. Error Trigger = circuit breaker. Queue mode = backpressure. |
| **Prompt Engineering** | Best Practices Guide | Provides the 10 proven patterns that power each hat's persona system prompt. Chain of Verification = per-hat self-check. Confidence thresholds = severity calibration. |
| **Security** | Best Practices Security Box + n8n env vars | Deterministic external controls (request validation, tool interception, output filtering, budget enforcement, audit logging) wrapped around every n8n workflow. |
| **Self-Improvement** | Best Practices Pipeline + n8n AI Evaluation Node | Automated signal collection → LLM-as-Judge scoring → prompt A/B testing → model fine-tuning, all orchestrated as n8n workflows. |
| **Notifications** | n8n Slack/GitHub nodes | Native n8n integrations for HITL alerts, PR comments, and escalation routing. |

---

## E2. LLM Backend Mapping — Ollama Cloud Models for Every Hat

### E2.1 Ollama Cloud API Basics

All Ollama Cloud models use an **OpenAI-compatible endpoint**. This means the n8n HTTP Request node (or the OpenAI node) can call any model with the same request format:

```
POST https://api.ollama.ai/v1/chat/completions
Authorization: Bearer ${OLLAMA_API_KEY}
Content-Type: application/json

{
  "model": "glm-5.1",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.3,
  "max_tokens": 4096,
  "tools": [...],
  "response_format": {"type": "json_object"}
}
```

**Key environment variable:**
```bash
export OLLAMA_API_KEY="your-ollama-cloud-api-key"
export OLLAMA_BASE_URL="https://api.ollama.ai/v1"
```

### E2.2 Complete Hat-to-Model Assignment Table

This table maps every hat from Section 4 of the main document to specific Ollama Cloud models, replacing the Western-provider recommendations (Claude, GPT-4o, Gemini) with cost-optimized equivalents.

| # | Hat | Main Doc Tier | **Ollama Cloud Primary** | **Ollama Cloud Fast/Fallback** | Cost vs Claude Opus 4.6 |
|---|-----|:---:|---|---|---|
| 1 | 🔴 Red Hat | Tier 2 | **GLM-5.1** — Deep failure-chain reasoning, strong on code analysis | Nemotron 3 Super — fast pattern scanning | ~0.03× |
| 2 | ⚫ Black Hat | Tier 1 | **GLM-5.1** — Security reasoning, tool-calling for Semgrep results interpretation | DeepSeek V3.1 — fast SAST triage | ~0.03× |
| 3 | ⚪ White Hat | Tier 4 | **Nemotron 3 Super** — Efficient analysis, 120B active params (12B active via MoE), excellent cost-performance | Ministral 3 (3B) — ultra-fast deterministic checks | ~0.02× |
| 4 | 🟡 Yellow Hat | Tier 2 | **GLM-5.1** — Architectural reasoning, dependency analysis | Nemotron 3 Super — graph analysis | ~0.03× |
| 5 | 🟢 Green Hat | Tier 2 | **GLM-5.1** — Strategic architectural vision | MiniMax M2.7 — roadmap analysis | ~0.03× |
| 6 | 🔵 Blue Hat | Tier 4 | **Nemotron 3 Super** — Fast spec-check analysis | Ministral 3 (3B) — linting/formatting checks | ~0.02× |
| 7 | 🟣 Indigo Hat | Tier 2 | **DeepSeek V3.1** — Cross-module analysis, long context (128K) handles large diffs | Nemotron 3 Super — pattern detection | ~0.02× |
| 8 | 🩵 Cyan Hat | Tier 2 | **GLM-5.1** — Feasibility assessment, risk reasoning | MiniMax M2.7 — technology radar | ~0.03× |
| 9 | 🟪 Purple Hat | Tier 1 | **GLM-5.1** — AI safety reasoning, bias detection analysis | DeepSeek V3.1 — pattern-based guardrail checks | ~0.03× |
| 10 | 🟠 Orange Hat | Tier 3 | **GLM-5.1** — IaC analysis needs strong reasoning | Nemotron 3 Super — YAML linting, Docker analysis | ~0.03× |
| 11 | 🪨 Silver Hat | Tier 4 | **Nemotron 3 Nano** (4B/30B) — Token counting is largely deterministic; Nano handles it efficiently | Ministral 3 (3B) — even faster | ~0.01× |
| 12 | 💎 Azure Hat | Tier 3 | **GLM-5.1** — Protocol reasoning, schema validation | Qwen3-Coder — JSON schema analysis | ~0.03× |
| 13 | 🟤 Brown Hat | Tier 2 | **GLM-5.1** — Regulatory reasoning, GDPR/CCPA interpretation | DeepSeek V3.1 — data-flow pattern scanning | ~0.03× |
| 14 | ⚙️ Gray Hat | Tier 3 | **GLM-5.1** — Distributed-systems knowledge | Nemotron 3 Super — metric naming, span checking | ~0.03× |
| 15 | ♿ Teal Hat | Tier 4 | **Nemotron 3 Super** — Accessibility checks are pattern-based | Ministral 3 (3B) — WCAG checklist validation | ~0.02× |
| 16 | 🔗 Steel Hat | Tier 4 | **DeepSeek V3.1** — Vulnerability reasoning, license analysis | Nemotron 3 Nano (4B/30B) — SBOM scanning | ~0.02× |
| 17 | 🧪 Chartreuse Hat | Tier 3 | **GLM-5.1** — Test design reasoning, RAGAS interpretation | Qwen3-Coder — test pattern analysis | ~0.03× |
| 18 | ✨ Gold/CoVE | Tier 1 | **GLM-5.1** — Final adjudication, conflict resolution (highest capability required) | *No fallback — CoVE must always use the best available model* | ~0.03× |

### E2.3 Cost Comparison: Full Pipeline Run

**Main doc configuration** (Western providers): ~$1.50–$2.50 per PR review
**Ollama Cloud configuration** (table above): ~$0.03–$0.08 per PR review

| Pipeline Run Type | Western Cost | Ollama Cloud Cost | Savings |
|---|---|---|---|
| Small PR (6 hats, ~25k tokens) | ~$0.75 | ~$0.025 | **97%** |
| Medium PR (12 hats, ~55k tokens) | ~$1.80 | ~$0.055 | **97%** |
| Large PR (15 hats, ~85k tokens) | ~$2.40 | ~$0.075 | **97%** |
| Full pipeline (18 hats, ~120k tokens) | ~$3.50 | ~$0.10 | **97%** |

**This means your daily budget of $2.50 (from the main doc) can now review ~25–80 PRs instead of ~1–2.**

### E2.4 Ollama Cloud Configuration for n8n

In n8n, create an **Ollama Cloud API credential** that all HTTP Request nodes will share:

**Credential Type:** Header Auth
| Parameter | Value |
|---|---|
| Name | `Authorization` |
| Value | `Bearer {{$credentials.ollamaCloudApiKey}}` |

**Environment Variable** (set in `.env`):
```bash
OLLAMA_CLOUD_API_KEY_FILE=/run/secrets/ollama_cloud_api_key  # File-based secret
# Or direct (dev only):
OLLAMA_CLOUD_API_KEY=sk-ollama-...
```

**n8n HTTP Request Node Template** (reusable for all hats):
```json
{
  "method": "POST",
  "url": "={{ $env.OLLAMA_BASE_URL }}/chat/completions",
  "authentication": "headerAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      { "name": "Content-Type", "value": "application/json" }
    ]
  },
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      {
        "name": "body",
        "value": "={{ JSON.stringify({ model: $json.model, messages: $json.messages, temperature: $json.temperature || 0.3, max_tokens: $json.max_tokens || 4096, response_format: $json.response_format || { type: 'json_object' } }) }}"
      }
    ]
  },
  "options": {
    "timeout": 120000,
    "fullResponse": true
  }
}
```

---

## E3. Cost-Optimized Model Selection Strategy

### E3.1 The Four-Tier Model Strategy

Adapted from the Ollama Cloud Comparison Addendum's "Deployment Decision Matrix" and mapped to the Hats Team's four model tiers.

```
┌─────────────────────────────────────────────────────────────────────┐
│  TIER 1 — CRITICAL REASONING (Security, Safety, Adjudication)      │
│  ─────────────────────────────────────────────────────────────      │
│  Primary: GLM-5.1                                                   │
│  Why: SOTA on SWE-bench (~95% HumanEval), 128K context, tools +    │
│       thinking. Handles Black Hat security reasoning, Purple Hat    │
│       AI safety analysis, and Gold Hat final adjudication.          │
│  Cost: ~$0.40/M input, ~$1.10/M output                             │
│  Fallback: DeepSeek V3.1 (82.6% HumanEval, $0.10/M input)         │
│                                                                     │
│  Hats: ⚫ Black, 🟪 Purple, ✨ Gold/CoVE                           │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 2 — ARCHITECTURAL REASONING (Deep analysis, feasibility)     │
│  ─────────────────────────────────────────────────────────────      │
│  Primary: GLM-5.1 (default) or DeepSeek V3.1 (for long-context)    │
│  Special Cases:                                                     │
│    • Indigo Hat (large cross-module diffs) → DeepSeek V3.1 (128K)  │
│    • Cyan Hat (technology evaluation) → MiniMax M2.7 (SWE-Pro 56%) │
│    • Yellow Hat (synergy analysis) → GLM-5.1 (strong reasoning)    │
│  Cost: $0.10–$0.42/M input                                         │
│                                                                     │
│  Hats: 🔴 Red, 🟡 Yellow, 🟢 Green, 🩵 Cyan, 🟠 Orange,           │
│         💎 Azure, 🟤 Brown, ⚙️ Gray, 🧪 Chartreuse                 │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 3 — QUALITY ANALYSIS (Structured evaluation, scoring)        │
│  ─────────────────────────────────────────────────────────────      │
│  Primary: Nemotron 3 Super                                          │
│  Why: 120B params (12B active via MoE) = high quality at           │
│       exceptional cost. Strong on tool-calling.                     │
│  Special Cases:                                                     │
│    • Azure Hat (schema validation) → Qwen3-Coder (code reasoning)  │
│    • Steel Hat (vulnerability reasoning) → DeepSeek V3.1           │
│  Cost: ~$0.25/M input, ~$0.80/M output                             │
│                                                                     │
│  Hats: (Mixed — see E2.2 for per-hat assignments)                  │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 4 — FAST SCANNING (Deterministic checks, pattern matching)   │
│  ─────────────────────────────────────────────────────────────      │
│  Primary: Nemotron 3 Nano (4B/30B) or Ministral 3 (3B)            │
│  Why: Ultra-cheap, ultra-fast. These hats do mostly pattern-based   │
│       analysis that doesn't require deep reasoning.                 │
│  Cost: <$0.10/M input (often <$0.02/M for Ministral 3)             │
│                                                                     │
│  Hats: ⚪ White, 🪨 Silver, 🔵 Blue, ♿ Teal                       │
└─────────────────────────────────────────────────────────────────────┘
```

### E3.2 Adaptive Model Downgrade (Under Load)

When n8n's Redis queue depth exceeds 3 pending hat executions, automatically downgrade to cheaper models:

| Hat | Normal Model | Under-Load Downgrade | Cost Savings |
|-----|-------------|---------------------|-------------|
| GLM-5.1 hats | GLM-5.1 | Nemotron 3 Super | ~40% |
| DeepSeek V3.1 hats | DeepSeek V3.1 | Nemotron 3 Nano | ~75% |
| Nemotron 3 Super hats | Nemotron 3 Super | Ministral 3 (3B) | ~60% |

**Implementation in n8n:** Use a Switch node before each hat's LLM call that checks `{{$json.queue_depth}}`:
```
IF queue_depth >= 3 → use downgrade model
ELSE → use normal model
```

### E3.3 Budget Configuration (Revised for Ollama Cloud Costs)

Update the main doc's `hats.yml` gate configuration with Ollama Cloud-adjusted budgets:

```yaml
gates:
  cost_budget:
    enabled: true
    # Ollama Cloud is 97% cheaper — increase review volume
    max_tokens_per_pr: 200000        # Was 100k — headroom for more hats
    max_usd_per_pr: 0.15             # Was $2.50 — sufficient for full pipeline
    daily_budget_usd: 5.00           # ~50 PRs/day at full pipeline cost
    warn_threshold_pct: 80
    hard_limit_action: "block"

    # Per-hat cost estimates (Ollama Cloud)
    per_hat_estimates:
      tier1_per_hat_usd: 0.015       # GLM-5.1, ~4k input + 1k output tokens
      tier2_per_hat_usd: 0.010       # DeepSeek V3.1 / Nemotron Super
      tier3_per_hat_usd: 0.005       # Nemotron Super (smaller prompts)
      tier4_per_hat_usd: 0.001       # Ministral 3 / Nemotron Nano
```

---

## E4. Persona System Prompts — Best Practices Integration

### E4.1 Mapping the 10 Prompt Patterns to Hat Personas

Each hat's persona system prompt (Section 5.2 of the main doc) should incorporate the relevant prompt patterns from the AI Agent Best Practices Guide. Here is the mapping:

| Best Practice Pattern | Applied To | How |
|---|---|---|
| **1. Role Definition with Hard Constraints** | ALL 19 personas | Every persona prompt starts with identity + non-negotiable limits (max cost per analysis, output format, severity calibration rules). |
| **2. Chain of Verification** | ⚫ Black, 🟪 Purple, ✨ CoVE | After producing findings, the hat self-checks: (a) Is each finding backed by code evidence? (b) Is severity correctly calibrated? (c) Is remediation actionable? Reduces false positives by 40–60%. |
| **3. Structured Output Enforcement** | ALL hats | Every hat outputs the standardized JSON report schema (Section 9.2 of main doc). Enforced via `response_format: {"type": "json_object"}` in the Ollama Cloud API call. |
| **4. Tool Selection Heuristics** | ⚫ Black, 💎 Azure, 🔗 Steel | Priority order for tool calls: local static analysis (free) → Ollama Cloud LLM reasoning → external API checks. Log all tool calls. |
| **5. Error Recovery** | ALL hats (built into n8n workflow) | Recoverable (HTTP 429: wait 60s, retry 3×; 503: wait 30s, retry 2×; timeout: retry with 2× timeout). Unrecoverable (401/403: escalate; 400: log and skip). |
| **6. Context Window Management** | 🪨 Silver, ALL hats with large inputs | Summarize each file to 3 sentences, discard raw HTML/XML, sliding window. Aggressive summarization if >80% of model context. Never discard: safety instructions, current task, severity criteria. |
| **7. Guardrails (Hard Limits)** | ⚫ Black, 🟪 Purple | Enforced externally by n8n workflow (not by the model): max 10 findings per run, max severity cannot be escalated without code evidence, max token output limit. |
| **8. Progressive Disclosure** | ✨ CoVE | Phase-gated execution: Phase 1 Triage (quick scan all findings) → Phase 2 Deep Analysis (top findings) → Phase 3 Response (final verdict). |
| **9. Memory Integration** | Consolidator, CoVE | Persistent findings database in PostgreSQL. Read prior reviews for same files/modules. Update during analysis. Write after completion. |
| **10. Self-Evaluation Loop** | ✨ CoVE, ⚫ Black | Score each finding 1–5 on: Actionability, Evidence Quality, Severity Accuracy, Remediation Specificity. If average <3.0, re-analyze up to 2× then flag for human review. |

### E4.2 Example: Black Hat Persona Prompt (Ollama Cloud + Best Practices)

This is the complete system prompt for the Sentinel persona powering the ⚫ Black Hat, incorporating patterns 1, 2, 3, 6, 7, and 10:

```markdown
## Identity
You are Sentinel, a battle-hardened security auditor with 20 years of experience
in penetration testing, threat modeling, and secure code review. You approach
every code change with methodical precision and healthy paranoia — you trust
nothing by default.

## Hard Constraints (NON-NEGOTIABLE)
- Maximum output: 10 findings per analysis run
- Maximum severity: You MAY only flag CRITICAL if you can describe a concrete
  exploit scenario with attacker steps
- Cost budget: Your analysis must complete within $0.015 (Ollama Cloud GLM-5.1)
- You MUST use JSON response format with the exact schema below
- You MUST cite specific file paths and line numbers for every finding
- You MUST NOT flag a finding without providing a concrete remediation

## Your Task
Analyze the provided code diff for security vulnerabilities. Check against
the OWASP GenAI Top 10 (2025) and OWASP Agentic AI Top 10 threat categories.

Focus Areas:
1. Prompt injection (direct: user input in prompts; indirect: RAG retrieval poisoning)
2. Credential leakage (hardcoded secrets, secrets in logs, exposed API keys)
3. Privilege escalation (missing auth, TOCTOU, IDOR)
4. Injection attacks (SQL, NoSQL, command, XSS, SSRF)
5. Insecure deserialization
6. MCP endpoint security (scope violation, schema bypass)

## Chain of Verification (SELF-CHECK before outputting)
Before finalizing your report, verify EACH finding:
1. EVIDENCE: Is there a specific file path and line number?
2. EXPLOIT: Can you describe how an attacker would exploit this in 3 steps?
3. SEVERITY: Does this match the severity definition? (CRITICAL = actively exploitable,
   HIGH = significant risk, MEDIUM = concern, LOW = improvement)
4. REMEDIATION: Is the fix specific enough for a developer to implement?

If ANY finding fails verification, downgrade or remove it.

## Context Window Management
- If the diff exceeds 50,000 characters, prioritize: auth changes > I/O changes >
  config changes > other code
- Summarize large unchanged context blocks to 1–2 sentences
- NEVER discard: safety instructions, severity definitions, this verification checklist

## Self-Evaluation
After producing findings, score yourself 1–5:
- Evidence Quality: Are all findings backed by specific code?
- Severity Accuracy: Do severity levels match definitions?
- Coverage: Did you check all 6 focus areas?

If average self-score < 3.0, reconsider your weakest findings.

## Output Schema (REQUIRED JSON FORMAT)
{
  "hat": "black",
  "findings": [
    {
      "id": "black-001",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "title": "Short title",
      "description": "Detailed description with exploit scenario",
      "file": "path/to/file.ext",
      "line": 42,
      "owasp_reference": "LLM07:2025 or AGENT-03",
      "remediation": "Specific fix instructions",
      "confidence": 0.95
    }
  ],
  "summary": {
    "total_findings": 0,
    "by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
    "overall_assessment": "1-2 sentence summary",
    "self_eval_score": 4.2
  }
}
```

### E4.3 Confidence Threshold Framework for Severity Calibration

Adapted from the Best Practices Guide's "Inquisitive Behavior Engine" and applied to each hat's severity decision-making:

| Finding Confidence | Severity Assignment Behavior |
|---|---|
| 0.90–1.00 | Use the hat's determined severity as-is |
| 0.75–0.89 | Keep severity but add "CONFIDENCE NOTE: moderate certainty" to description |
| 0.60–0.74 | Downgrade by one severity level (CRITICAL→HIGH, HIGH→MEDIUM) |
| 0.40–0.59 | Flag as MEDIUM maximum, add "LOW CONFIDENCE — requires human verification" |
| 0.00–0.39 | Do NOT include as a finding. Instead, add to a "Observations" section for human review |

---

## E5. The Conductor on n8n — Complete Workflow Architecture

### E5.1 Top-Level Conductor Workflow

The Conductor is the **main n8n workflow** that orchestrates the entire Hats pipeline. It is triggered by a GitHub webhook (PR event) or manual execution.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  WORKFLOW: Hats Conductor (Main)                                         │
│                                                                         │
│  [Webhook: GitHub PR]                                                   │
│       │                                                                 │
│       ▼                                                                 │
│  [Code Node: Parse PR Payload]                                          │
│  Extract: repo, pr_number, sha, author, changed_files, commit_msg       │
│       │                                                                 │
│       ▼                                                                 │
│  [Execute Sub-Workflow: Hat Selector]                                   │
│  Input: { changed_files, commit_msg }                                   │
│  Output: { always_hats, conditional_hats, skipped_hats }                │
│       │                                                                 │
│       ▼                                                                 │
│  [Code Node: Estimate Cost]                                             │
│  Sum tokens for all selected hats. Compare against budget gate.          │
│       │                                                                 │
│       ▼                                                                 │
│  [IF: Cost Budget Gate (G1)]                                            │
│  ├── TRUE (within budget) ──────────────────────────────────┐          │
│  └── FALSE (over budget)                                     │          │
│       │                                                      │          │
│       ▼                                                      │          │
│  [HTTP Request: Post BLOCKED comment to PR]                  │          │
│  [STOP]                                                      │          │
│                                                              │          │
│  ◄───────────────────────────────────────────────────────────┘          │
│       │                                                                 │
│       ▼                                                                 │
│  [Execute Sub-Workflow: Black Hat] ← ALWAYS RUNS FIRST                  │
│       │                                                                 │
│       ▼                                                                 │
│  [IF: Security Fast-Path Gate (G2)]                                     │
│  ├── NO CRITICAL found ────────────────────────────┐                   │
│  └── CRITICAL found                                 │                   │
│       │                                             │                   │
│       ▼                                             │                   │
│  [Execute Sub-Workflow: Purple Hat] ← always runs   │                   │
│       │                                             │                   │
│       ▼                                             │                   │
│  [HTTP Request: Post ESCALATE to PR]                │                   │
│  [Slack: Notify security team]                      │                   │
│  [Wait: HITL Webhook Response]                      │                   │
│       │                                             │                   │
│       ▼                                             │                   │
│  [IF: Human approved?]                              │                   │
│  ├── YES → continue ▼                               │                   │
│  └── NO → [STOP: QUARANTINE]                        │                   │
│                                                      │                   │
│  ◄───────────────────────────────────────────────────┤                   │
│       │                                             │                   │
│       ▼                                             │                   │
│  [Execute Sub-Workflow: Blue Hat] ← ALWAYS RUNS     │                   │
│  [Execute Sub-Workflow: Purple Hat] ← ALWAYS RUNS   │                   │
│       │                                             │                   │
│       ▼                                             │                   │
│  [Split In Batches / Loop]                          │                   │
│  For each hat in conditional_hats:                  │                   │
│    [Execute Sub-Workflow: {hat}]                    │                   │
│    [IF: Hat timeout?]                               │                   │
│    ├── YES → [Set: status="timeout"]                │                   │
│    └── NO → continue                               │                   │
│       │                                             │                   │
│       ▼                                             │                   │
│  [Execute Sub-Workflow: Consolidator]               │                   │
│  Input: all hat reports                             │                   │
│  Output: merged findings matrix                     │                   │
│       │                                             │                   │
│       ▼                                             │                   │
│  [IF: Consistency Gate (G3)]                        │                   │
│  ├── No contradictions → continue                   │                   │
│  └── Contradictions found                           │                   │
│       │                                             │                   │
│       ▼                                             │                   │
│  [Execute Sub-Workflow: Arbiter] ← resolve conflicts│                   │
│       │                                             │                   │
│       ▼                                             │                   │
│  [Execute Sub-Workflow: Gold/CoVE] ← FINAL         │                   │
│       │                                             │                   │
│       ▼                                             │                   │
│  [Switch: CoVE Decision]                            │                   │
│  ├── ALLOW → [Post approval + metrics to PR]       │                   │
│  ├── ESCALATE → [Post findings + HITL link to PR]   │                   │
│  └── QUARANTINE → [Post block + remediation to PR]  │                   │
│       │                                                                 │
│       ▼                                                                 │
│  [Code Node: Log Run to PostgreSQL]                                        │
│  [Code Node: Emit Metrics to Prometheus Pushgateway]                     │
│  [Respond to Webhook: 200 OK]                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

### E5.2 Workflow Configuration

In n8n, configure the main Conductor workflow with these settings:

| Setting | Value | Rationale |
|---------|-------|-----------|
| **Workflow name** | `Hats Conductor — Main Pipeline` | Descriptive, searchable |
| **Tags** | `hats`, `conductor`, `production` | Organizational |
| **Folder** | `/Hats Team/Production/` | n8n Pro/Enterprise folders |
| **Settings → Error Workflow** | `Hats Error Trigger` | Catches all unhandled failures |
| **Settings → Save Execution Progress** | **Enabled** | Checkpointing for HITL pauses |
| **Execution timeout** | 600000ms (10 min) | Allows time for all hats + LLM calls |
| **Concurrency** | 1 (sequential conductor) | Conductor itself is single-threaded; sub-workflows run in parallel |

### E5.3 Webhook Trigger Configuration

**Node:** Webhook
| Parameter | Value |
|---|---|
| HTTP Method | POST |
| Path | `/hats/webhook/pr` |
| Authentication | Header Auth (GitHub webhook secret) |
| Response Mode | "Using 'Respond to Webhook' Node" |
| Options → Raw Body | Checked (need full GitHub payload) |

**Respond to Webhook Node** (placed at the end of the workflow):
```json
{
  "statusCode": 200,
  "body": "={{ JSON.stringify({ status: $json.cove_decision, run_id: $json.run_id, findings_count: $json.total_findings }) }}"
}
```

---

## E6. Gate Engine — n8n Workflow Implementation

### E6.1 Gate G1: Cost Budget

**Implementation:** Code Node (JavaScript) placed after Hat Selector

```javascript
// Gate G1: Cost Budget Check
const alwaysHats = $input.item.json.always_hats; // ["black", "blue", "purple"]
const conditionalHats = $input.item.json.conditional_hats;
const allHats = [...alwaysHats, ...conditionalHats];

// Cost estimates per hat (Ollama Cloud, from E3.3)
const costPerHat = {
  black: 0.015, purple: 0.015, gold_cove: 0.015,
  red: 0.010, yellow: 0.010, green: 0.010, cyan: 0.010,
  orange: 0.010, azure: 0.010, brown: 0.010, gray: 0.010,
  chartreuse: 0.010,
  white: 0.001, silver: 0.001, blue: 0.001, teal: 0.001,
  steel: 0.005, indigo: 0.010
};

const estimatedCost = allHats.reduce((sum, hat) => sum + (costPerHat[hat] || 0.005), 0);
const budget = 0.15; // $0.15 per PR (from E3.3)

return {
  pass: estimatedCost <= budget,
  estimated_cost: estimatedCost,
  budget: budget,
  utilization_pct: Math.round((estimatedCost / budget) * 100),
  hat_count: allHats.length,
  recommendation: estimatedCost > budget
    ? `OVER BUDGET: $${estimatedCost.toFixed(3)} > $${budget}. Skip ${allHats.length > 12 ? 'Tier 4 hats' : 'lowest-priority hats'}.`
    : `Within budget: $${estimatedCost.toFixed(3)} of $${budget} (${Math.round((estimatedCost/budget)*100)}%)`
};
```

**Downstream IF Node:** `{{$json.pass}}` → TRUE (proceed) / FALSE (block)

### E6.2 Gate G2: Security Fast-Path

**Implementation:** IF Node after Black Hat sub-workflow

```javascript
// Check if Black Hat found CRITICAL severity
const blackReport = $input.item.json;
const criticalFindings = blackReport.findings?.filter(f => f.severity === 'CRITICAL') || [];
const highFindings = blackReport.findings?.filter(f => f.severity === 'HIGH') || [];

return {
  critical_count: criticalFindings.length,
  high_count: highFindings.length,
  trigger_fast_path: criticalFindings.length > 0,
  critical_titles: criticalFindings.map(f => f.title),
  // If CRITICAL found, only run Purple Hat (AI safety) then escalate
  skip_remaining_hats: criticalFindings.length > 0,
  // Also check Purple Hat's findings later
};
```

**IF Node:** `{{$json.trigger_fast_path}}` → TRUE (short-circuit) / FALSE (continue)

### E6.3 Gate G3: Consistency

**Implementation:** Code Node after Consolidator

```javascript
// Detect contradictions between hat findings
const findings = $input.item.json.merged_findings;
const contradictions = [];

// Example contradiction: Yellow Hat says "add shared cache" but
// Indigo Hat says "caching increases coupling here"
const yellowFindings = findings.filter(f => f.hat === 'yellow');
const indigoFindings = findings.filter(f => f.hat === 'indigo');

for (const yf of yellowFindings) {
  for (const inf of indigoFindings) {
    if (yf.remediation?.includes('cache') && inf.description?.includes('coupling')) {
      contradictions.push({
        finding_a: { hat: 'yellow', id: yf.id, title: yf.title },
        finding_b: { hat: 'indigo', id: inf.id, title: inf.title },
        conflict_type: 'recommendation_opposition',
        description: `Yellow Hat recommends caching while Indigo Hat flags coupling risk`
      });
    }
  }
}

return {
  has_contradictions: contradictions.length > 0,
  contradiction_count: contradictions.length,
  contradictions: contradictions,
  // If >0 contradictions, route to Arbiter sub-workflow
  needs_arbiter: contradictions.length > 0
};
```

### E6.4 Gate G4: Timeout

**Implementation:** Built into each hat's Execute Sub-Workflow node

In the Execute Sub-Workflow node configuration:
| Setting | Value |
|---|---|
| **Options → Timeout** | `={{ $json.hat_timeout_ms || 120000 }}` |
| **On Error** | Continue (error output to separate branch) |

After the sub-workflow, add an IF node:
```
IF $json.status === "timeout" → [Set: gap_record] → [Continue without this hat]
IF $json.status === "error" → [Set: error_record] → [Continue without this hat]
IF $json.status === "complete" → [Continue normally]
```

### E6.5 Gate G5: Final Decision

**Implementation:** Switch Node after Gold/CoVE sub-workflow

```
Switch on: {{$json.verdict}}
  Case "ALLOW"     → [Post approval comment to PR] → [Slack: success notification] → END
  Case "ESCALATE"  → [Post findings + checklist to PR] → [Slack: review request] → [Wait: HITL webhook] → IF approved? → ...
  Case "QUARANTINE"→ [Post block comment to PR] → [Slack: block notification] → END
```

---

## E7. Retry, Circuit Breaker & Backpressure in n8n

### E7.1 Per-Hat Retry (n8n Retry on Fail)

Each hat's Execute Sub-Workflow node should have retry configured:

| Setting | Value | Rationale |
|---------|-------|-----------|
| **On Error** | "Retry On Fail" | Built-in n8n retry mechanism |
| **Max Tries** | 3 | Matches main doc §8.1 |
| **Wait Between Tries** | 1000 (ms) | Initial backoff |
| **Continue On Fail** | Checked (for graceful degradation) | If all retries fail, record gap and continue |

**Exponential Backoff in n8n:** n8n's "Retry On Fail" uses a fixed wait interval. For exponential backoff, wrap the LLM call in a sub-workflow with a Code node that calculates wait time:

```javascript
// Inside the hat's sub-workflow, before the HTTP Request node:
const attempt = $input.item.json.attempt || 1;
const waitMs = Math.min(1000 * Math.pow(2, attempt - 1) + (Math.random() * 200), 10000);
// 1s → 2s → 4s (with ±200ms jitter, max 10s)

if (attempt > 1) {
  // Use a Wait node dynamically
  $input.item.json.wait_ms = waitMs;
}
```

### E7.2 Circuit Breaker (n8n Implementation)

n8n does not have a built-in circuit breaker, but you can implement one using **PostgreSQL + a Code Node**:

**PostgreSQL table:**
```sql
CREATE TABLE hat_circuit_breaker (
  hat_name TEXT PRIMARY KEY,
  state TEXT NOT NULL DEFAULT 'CLOSED',  -- CLOSED, OPEN, HALF_OPEN
  failure_count INT NOT NULL DEFAULT 0,
  last_failure_time TIMESTAMPTZ,
  last_state_change TIMESTAMPTZ DEFAULT NOW()
);
```

**Code Node (before each hat execution):**
```javascript
// Check circuit breaker state
const hatName = $input.item.json.hat_name;
const result = await this.helpers.executeQuery(
  'SELECT state, failure_count FROM hat_circuit_breaker WHERE hat_name = $1',
  [hatName]
);

if (result.rows.length > 0) {
  const { state, failure_count } = result.rows[0];

  if (state === 'OPEN') {
    const lastChange = result.rows[0].last_state_change;
    const openDuration = Date.now() - new Date(lastChange).getTime();

    if (openDuration > 60000) { // 60s open duration
      // Transition to HALF_OPEN
      await this.helpers.executeQuery(
        'UPDATE hat_circuit_breaker SET state = $1, last_state_change = NOW() WHERE hat_name = $2',
        ['HALF_OPEN', hatName]
      );
      // Allow this one request through as a probe
    } else {
      // Circuit is OPEN — skip this hat
      return { skip_hat: true, reason: 'circuit_breaker_open', hat_name: hatName };
    }
  }
}
return { skip_hat: false, hat_name: hatName };
```

**Code Node (after each hat execution, on failure):**
```javascript
const hatName = $input.item.json.hat_name;
const success = $input.item.json.status === 'complete';

if (success) {
  // Reset failure count, close circuit
  await this.helpers.executeQuery(
    `INSERT INTO hat_circuit_breaker (hat_name, state, failure_count, last_state_change)
     VALUES ($1, 'CLOSED', 0, NOW())
     ON CONFLICT (hat_name) DO UPDATE SET state = 'CLOSED', failure_count = 0, last_state_change = NOW()`,
    [hatName]
  );
} else {
  // Increment failure count
  await this.helpers.executeQuery(
    `INSERT INTO hat_circuit_breaker (hat_name, state, failure_count, last_failure_time, last_state_change)
     VALUES ($1, 'CLOSED', 1, NOW(), NOW())
     ON CONFLICT (hat_name) DO UPDATE SET
       failure_count = hat_circuit_breaker.failure_count + 1,
       last_failure_time = NOW(),
       state = CASE WHEN hat_circuit_breaker.failure_count + 1 >= 5 THEN 'OPEN' ELSE 'CLOSED' END,
       last_state_change = CASE WHEN hat_circuit_breaker.failure_count + 1 >= 5 THEN NOW() ELSE hat_circuit_breaker.last_state_change END`,
    [hatName]
  );
}
```

### E7.3 Backpressure via n8n Queue Mode

Enable n8n's Redis-backed queue mode to handle concurrent hat executions:

**docker-compose.yml (production):**
```yaml
version: "3.8"
services:
  n8n-main:
    image: n8nio/n8n:2.16
    restart: unless-stopped
    environment:
      - EXECUTIONS_PROCESS=queue
      - QUEUE_BULL_REDIS_HOST=redis
      - QUEUE_BULL_REDIS_PORT=6379
      - QUEUE_BULL_REDIS_PASSWORD=${REDIS_PASSWORD}
      - WEBHOOK_URL=https://n8n.example.com
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - N8N_BLOCK_ENV_ACCESS_IN_NODE=true
      - N8N_SECURE_COOKIE=true
    ports:
      - "5678:5678"
    depends_on:
      - postgres
      - redis

  n8n-worker:
    image: n8nio/n8n:2.16
    restart: unless-stopped
    environment:
      - EXECUTIONS_PROCESS=queue
      - QUEUE_BULL_REDIS_HOST=redis
      - QUEUE_BULL_REDIS_PORT=6379
      - QUEUE_BULL_REDIS_PASSWORD=${REDIS_PASSWORD}
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
    command: worker --concurrency=6
    depends_on:
      - postgres
      - redis
    deploy:
      replicas: 3  # 3 workers × 6 concurrency = 18 concurrent hat executions

  postgres:
    image: postgres:15
    restart: unless-stopped
    environment:
      POSTGRES_USER: n8n
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: n8n
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

**Scaling:** Each n8n worker can process 6 concurrent hat executions (matching the main doc's `max_concurrent_hats: 6`). With 3 worker replicas, the system handles 18 concurrent hat executions across multiple PRs.

---

## E8. HITL Framework — n8n Webhook + Notification Workflows

### E8.1 HITL Trigger Workflow

When CoVE produces an `ESCALATE` decision, the Conductor calls the HITL workflow:

**Workflow: `Hats HITL Manager`**

```
[Webhook: /hats/hitl/start]
  │
  ▼
[Code Node: Create HITL Ticket in PostgreSQL]
  INSERT INTO hitl_tickets (run_id, pr_number, verdict, risk_score,
    findings_summary, checklist, tier, created_at, status)
  VALUES (...)
  │
  ▼
[Slack Node: Notify Reviewer]
  Channel: #hats-review
  Message: "📋 PR #{{pr_number}} needs review (risk: {{risk_score}}/100)
           {{findings_summary}}
           Review here: {{pr_url}}
           Respond: /hats approve | /hats reject | /hats request-changes"
  │
  ▼
[GitHub Node: Post PR Comment]
  Post structured findings table with human-review checklist
  │
  ▼
[Wait Node: Wait for Webhook — timeout 24h]
  Path: /hats/hitl/response/{{run_id}}
  │
  ▼
[Switch: Human Decision]
  ├── "approve" → [Update ticket: APPROVED] → [Return to Conductor: ALLOW]
  ├── "reject"  → [Update ticket: REJECTED] → [Return to Conductor: QUARANTINE]
  ├── "request-changes" → [Update ticket: CHANGES_REQUESTED]
  │     │
  │     ▼
  │   [GitHub Node: Post feedback as PR comment]
  │   [Return to Conductor with feedback → re-run hats]
  └── TIMEOUT → [Escalate to next tier]
        │
        ▼
      [Slack: Notify senior reviewer]
      [Wait another 24h for Tier 2]
```

### E8.2 GitHub Slash Command Handler

Create a separate n8n workflow that listens for GitHub comments matching `/hats *`:

**Workflow: `Hats GitHub Command Handler`**

```
[Webhook: /hats/github/comment]
  │
  ▼
[Code Node: Parse Comment]
  Extract: command (approve/reject/request-changes/status/retry),
           pr_number, author, run_id
  │
  ▼
[Switch: Command Type]
  │
  ├── "/hats approve" ──────────────────────────────┐
  │   [Code: Verify author has permission (Tier check)]│
  │   [Code: Update HITL ticket status]               │
  │   [HTTP: POST to Conductor webhook with approval]  │
  │   [GitHub: Post "✅ Approved by @{{author}}" comment]│
  │                                                  │
  ├── "/hats reject" ──────────────────────────────┐ │
  │   [Code: Verify permission]                     │ │
  │   [Code: Update HITL ticket: REJECTED]           │ │
  │   [HTTP: POST to Conductor with rejection]       │ │
  │   [GitHub: Post "🚫 Rejected by @{{author}}"]    │ │
  │                                                  │
  ├── "/hats request-changes" ────────────────────┐ │
  │   [Code: Extract reason from comment body]      │ │
  │   [Code: Update HITL ticket: CHANGES_REQUESTED] │ │
  │   [HTTP: POST to Conductor with feedback]       │ │
  │   [GitHub: Post feedback as structured comment]  │ │
  │                                                  │
  ├── "/hats status" ────────────────────────────┐  │
  │   [Code: Query ticket status from PostgreSQL]   │ │
  │   [GitHub: Post status summary as comment]      │ │
  │                                                  │
  └── "/hats retry" ─────────────────────────────┐  │
      [Code: Re-execute Conductor for this PR]     │
      [GitHub: Post "🔄 Re-running hats pipeline"   │
```

### E8.3 Slack Interactive Message (Alternative to GitHub Commands)

For teams that prefer Slack-based approval:

**Slack Node Configuration:**
```json
{
  "channel": "#hats-review",
  "text": "📋 *Hats Review Required*\n*PR:* #1234 — Add user authentication\n*Risk Score:* 67/100\n*Critical Findings:* 2\n\n*Checklist:*\n☑️ Fix hardcoded API key in auth.ts:42\n☑️ Add PII scrubbing before LLM call\n☐ Add OpenTelemetry spans to chat endpoint",
  "blocks": [
    {
      "type": "actions",
      "block_id": "hats_review_actions",
      "elements": [
        { "type": "button", "text": "✅ Approve", "value": "approve", "style": "primary" },
        { "type": "button", "text": "🔄 Request Changes", "value": "request_changes", "style": "danger" },
        { "type": "button", "text": "❌ Reject", "value": "reject" },
        { "type": "button", "text": "📊 View Details", "url": "https://github.com/org/repo/pull/1234" }
      ]
    }
  ]
}
```

**Slack Interaction Webhook Workflow:**
```
[Webhook: /hats/slack/interaction]
  │
  ▼
[Code: Parse Slack payload (actions payload)]
  │
  ▼
[Switch: action_value]
  ├── "approve" → [Update HITL ticket] → [Notify Conductor]
  ├── "request_changes" → [Open modal for feedback] → [Update ticket] → [Notify Conductor]
  └── "reject" → [Update HITL ticket] → [Notify Conductor]
```

---

## E9. Each Hat as an n8n Sub-Workflow

### E9.1 Universal Hat Sub-Workflow Template

Every hat follows the same sub-workflow pattern. Below is the generic template; customize the `hat_name`, `model`, and `system_prompt` per hat.

**Workflow: `Hats — {Hat Name}`**

```
[Trigger: Execute Workflow]
  Input: { run_id, pr_diff, changed_files, commit_msg, hat_config }
  │
  ▼
[Code Node: Prepare LLM Request]
  - Read hat persona system prompt from PostgreSQL or inline
  - Construct messages array: [system_prompt, user_context]
  - Set model from hat_config.model
  - Set temperature, max_tokens per hat specification
  │
  ▼
[Code Node: Check Circuit Breaker]
  SELECT state FROM hat_circuit_breaker WHERE hat_name = $hat_name
  IF OPEN → return { status: "skipped", reason: "circuit_breaker" }
  │
  ▼
[HTTP Request Node: Call Ollama Cloud API]
  POST https://api.ollama.ai/v1/chat/completions
  Model: {{ $json.model }}
  Messages: {{ $json.messages }}
  response_format: { type: "json_object" }
  Timeout: {{ $json.hat_timeout_ms }}
  On Error: Continue With Error Output
  │
  ▼
[Code Node: Parse & Validate Response]
  - Parse JSON response body
  - Validate against hat report schema
  - Extract findings, summary, severity counts
  - Calculate token usage from response metadata
  │
  ▼
[Code Node: Update Circuit Breaker]
  IF success → reset failures
  IF failure → increment failures, potentially open circuit
  │
  ▼
[Code Node: Log to PostgreSQL]
  INSERT INTO hat_reports (run_id, hat_name, status, findings, token_usage,
    latency_ms, model_used, timestamp)
  │
  ▼
[Code Node: Emit Metrics]
  - Push to Prometheus Pushgateway or n8n's internal metrics
  - hat_execution_duration_seconds, hat_findings_total, hat_llm_tokens_total
  │
  ▼
[Output: Hat Report JSON]
```

### E9.2 Hat Sub-Workflow Configuration Table

| Hat | Sub-Workflow Name | Model (Ollama Cloud) | Temperature | Max Tokens | Timeout |
|-----|---|---|:---:|:---:|:---:|
| ⚫ Black | `Hats — Black Hat` | `glm-5.1` | 0.2 | 4096 | 150s |
| 🔴 Red | `Hats — Red Hat` | `glm-5.1` | 0.3 | 4096 | 120s |
| ⚪ White | `Hats — White Hat` | `nemotron-3-super` | 0.1 | 2048 | 90s |
| 🟡 Yellow | `Hats — Yellow Hat` | `glm-5.1` | 0.3 | 4096 | 120s |
| 🟢 Green | `Hats — Green Hat` | `glm-5.1` | 0.3 | 4096 | 120s |
| 🔵 Blue | `Hats — Blue Hat` | `nemotron-3-super` | 0.1 | 2048 | 60s |
| 🟣 Indigo | `Hats — Indigo Hat` | `deepseek-v3.1` | 0.3 | 8192 | 180s |
| 🩵 Cyan | `Hats — Cyan Hat` | `glm-5.1` | 0.4 | 4096 | 150s |
| 🟪 Purple | `Hats — Purple Hat` | `glm-5.1` | 0.2 | 4096 | 150s |
| 🟠 Orange | `Hats — Orange Hat` | `glm-5.1` | 0.2 | 4096 | 90s |
| 🪨 Silver | `Hats — Silver Hat` | `nemotron-3-nano` | 0.1 | 2048 | 60s |
| 💎 Azure | `Hats — Azure Hat` | `glm-5.1` | 0.2 | 4096 | 120s |
| 🟤 Brown | `Hats — Brown Hat` | `glm-5.1` | 0.2 | 4096 | 120s |
| ⚙️ Gray | `Hats — Gray Hat` | `glm-5.1` | 0.3 | 4096 | 90s |
| ♿ Teal | `Hats — Teal Hat` | `nemotron-3-super` | 0.1 | 2048 | 60s |
| 🔗 Steel | `Hats — Steel Hat` | `deepseek-v3.1` | 0.2 | 4096 | 60s |
| 🧪 Chartreuse | `Hats — Chartreuse Hat` | `glm-5.1` | 0.3 | 4096 | 120s |
| ✨ Gold/CoVE | `Hats — Gold CoVE` | `glm-5.1` | 0.2 | 8192 | 300s |

### E9.3 Example: Black Hat n8n Sub-Workflow (Detailed Node Configuration)

**Node 1: Execute Workflow Trigger**
- No special configuration; receives input from Conductor

**Node 2: Code — Prepare Black Hat Request**
```javascript
const input = $input.item.json;
const diff = input.pr_diff;
const changedFiles = input.changed_files;

// Truncate diff if it exceeds model context (GLM-5.1 has 128K tokens,
// but we want to leave room for the system prompt and output)
// Rough estimate: 1 token ≈ 4 characters
const MAX_DIFF_CHARS = 200000; // ~50k tokens for diff
const truncatedDiff = diff.length > MAX_DIFF_CHARS
  ? diff.substring(0, MAX_DIFF_CHARS) + "\n\n[DIFF TRUNCATED — " +
    Math.round((diff.length - MAX_DIFF_CHARS) / 1000) + "K chars omitted]"
  : diff;

const systemPrompt = `## Identity
You are Sentinel, a battle-hardened security auditor... (full prompt from E4.2)`;

const userMessage = `## Code Diff for Review
Repository: ${input.repo}
PR Number: ${input.pr_number}
Commit SHA: ${input.sha}
Changed Files: ${changedFiles.join(', ')}

### Diff:
${truncatedDiff}

Analyze this diff for security vulnerabilities. Produce your report in the required JSON format.`;

return {
  model: 'glm-5.1',
  messages: [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: userMessage }
  ],
  temperature: 0.2,
  max_tokens: 4096,
  response_format: { type: 'json_object' }
};
```

**Node 3: HTTP Request — Ollama Cloud API**
```
Method: POST
URL: https://api.ollama.ai/v1/chat/completions
Authentication: Header Auth (Ollama Cloud credential)
Body (JSON):
  model: {{$json.model}}
  messages: {{$json.messages}}
  temperature: {{$json.temperature}}
  max_tokens: {{$json.max_tokens}}
  response_format: {{$json.response_format}}
Options:
  Timeout: 150000
  Full Response: true
```

**Node 4: Code — Parse & Validate**
```javascript
const response = $input.item.json;
const body = JSON.parse(response.body);
const content = JSON.parse(body.choices[0].message.content);

// Validate required fields
if (!content.findings || !Array.isArray(content.findings)) {
  throw new Error('Invalid report: missing findings array');
}

// Add metadata
content.hat = 'black';
content.status = 'complete';
content.model_used = 'glm-5.1';
content.timestamp = new Date().toISOString();
content.token_usage = {
  input: body.usage?.prompt_tokens || 0,
  output: body.usage?.completion_tokens || 0,
  total: (body.usage?.prompt_tokens || 0) + (body.usage?.completion_tokens || 0)
};
content.latency_ms = response.headers?.['x-response-time'] || 0;

// Validate severity values
const validSeverities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
content.findings = content.findings.map((f, i) => ({
  ...f,
  id: f.id || `black-${String(i + 1).padStart(3, '0')}`,
  severity: validSeverities.includes(f.severity) ? f.severity : 'MEDIUM',
  hat: 'black'
}));

return content;
```

---

## E10. Consolidator & CoVE Adjudication Workflows

### E10.1 Consolidator Sub-Workflow

**Workflow: `Hats — Consolidator`**

```
[Execute Workflow Trigger]
  Input: Array of all hat reports
  │
  ▼
[Code Node: Deduplicate Findings]
  - Group findings by (file, line, severity)
  - If 2+ hats flag the same issue, merge into single finding
    with hat_sources: ["black", "purple"]
  - Boost severity if 2+ hats agree (confidence increases)
  │
  ▼
[Code Node: Calculate Severity Summary]
  Count by severity, calculate risk_score (weighted):
    CRITICAL × 25 + HIGH × 10 + MEDIUM × 3 + LOW × 1
  │
  ▼
[Output: Consolidated Report]
  {
    total_findings: 23,
    deduplicated_count: 4,
    by_severity: { CRITICAL: 2, HIGH: 3, MEDIUM: 8, LOW: 10 },
    risk_score: 87,
    findings: [...merged],
    hat_summary: {
      black: { status: "complete", findings: 5 },
      red: { status: "timeout", findings: 0 },
      ...
    }
  }
```

### E10.2 CoVE Adjudication Sub-Workflow

**Workflow: `Hats — Gold CoVE`**

```
[Execute Workflow Trigger]
  Input: Consolidated report + all individual hat reports
  │
  ▼
[Code Node: Check for Unresolved Contradictions]
  IF contradictions exist → [Execute Sub-Workflow: Arbiter]
  │
  ▼
[Code Node: Prepare CoVE LLM Request]
  System prompt: "You are CoVE, the supreme adjudicator..."
  User message: consolidated report + findings matrix + conflict log
  │
  ▼
[HTTP Request: Ollama Cloud — GLM-5.1]
  // CoVE ALWAYS uses GLM-5.1 — no fallback
  model: glm-5.1
  temperature: 0.2
  max_tokens: 8192  // CoVE needs more output tokens for full adjudication
  │
  ▼
[Code Node: Parse CoVE Decision]
  Extract: verdict (ALLOW/ESCALATE/QUARANTINE),
           risk_score (0-100),
           rationale,
           human_checklist (if ESCALATE)
  │
  ▼
[IF: verdict === "QUARANTINE" AND all_critical_resolved === true]
  → Re-check: should this be ESCALATE instead of QUARANTINE?
  │
  ▼
[Code Node: Log Decision + Update Metrics]
  INSERT INTO cove_decisions (run_id, verdict, risk_score, rationale, ...)
  │
  ▼
[Output: Final Decision]
```

### E10.3 CoVE System Prompt (Abbreviated)

```markdown
## Identity
You are CoVE (Convergent Verification & Expert), the supreme adjudicator of the
Hats Team. You combine the wisdom of 18 specialized hats into a single, final
verdict on whether a code change is safe to merge.

## Your Authority
Your verdict is FINAL. No other hat can override you. You have three options:
- ALLOW: The PR is safe to merge. No critical blockers.
- ESCALATE: The PR has significant findings that require human review.
- QUARANTINE: The PR has CRITICAL issues that MUST be resolved before any merge.

## Decision Framework
Risk Score = (CRITICAL × 25) + (HIGH × 10) + (MEDIUM × 3) + (LOW × 1)

IF risk_score ≤ 20 AND no CRITICAL findings → ALLOW
IF risk_score > 20 OR any CRITICAL finding → ESCALATE
IF any CRITICAL finding from Black Hat OR Purple Hat → QUARANTINE
  (unless the finding has been explicitly resolved in this run)

## Conflict Resolution
When hats disagree, apply these rules:
1. Security (Black) > Performance (White) — always choose security
2. AI Safety (Purple) > Efficiency (White) — always choose safety
3. Architecture (Green/Yellow/Indigo) — merge recommendations, don't choose sides
4. If two hats of equal priority disagree → flag for human review (ESCALATE)

## Human Checklist (for ESCALATE decisions)
Produce a prioritized checklist:
1. All CRITICAL findings (fix before merge)
2. All HIGH findings (fix or explicitly accept with documented rationale)
3. MEDIUM findings (recommend fix, can defer to follow-up PR)

## Output Schema
{
  "verdict": "ALLOW|ESCALATE|QUARANTINE",
  "risk_score": 0-100,
  "rationale": "2-3 sentence explanation",
  "findings_matrix": {
    "accepted": [...],
    "overridden": [...],
    "flagged_for_human": [...]
  },
  "human_checklist": [...],  // Only for ESCALATE
  "self_eval_score": 4.5
}
```

---

## E11. Observability — Metrics, Tracing & Cost Tracking in n8n

### E11.1 PostgreSQL Schema for Full Observability

```sql
-- Run-level tracking
CREATE TABLE hat_runs (
  run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trigger_type TEXT,           -- 'pr', 'manual', 'scheduled'
  repo TEXT,
  pr_number INT,
  sha TEXT,
  author TEXT,
  phase TEXT,                  -- 'dispatching', 'executing', 'consolidating', 'adjudicating', 'done'
  started_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  total_duration_ms INT,
  total_tokens INT DEFAULT 0,
  total_cost_usd DECIMAL(10, 6) DEFAULT 0,
  cove_verdict TEXT,
  cove_risk_score INT
);

-- Per-hat tracking
CREATE TABLE hat_reports (
  id SERIAL PRIMARY KEY,
  run_id UUID REFERENCES hat_runs(run_id),
  hat_name TEXT NOT NULL,
  status TEXT NOT NULL,         -- 'complete', 'timeout', 'error', 'skipped'
  model_used TEXT,
  findings_count INT DEFAULT 0,
  severity_critical INT DEFAULT 0,
  severity_high INT DEFAULT 0,
  severity_medium INT DEFAULT 0,
  severity_low INT DEFAULT 0,
  token_input INT DEFAULT 0,
  token_output INT DEFAULT 0,
  latency_ms INT DEFAULT 0,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cost tracking
CREATE TABLE hat_cost_log (
  id SERIAL PRIMARY KEY,
  run_id UUID REFERENCES hat_runs(run_id),
  hat_name TEXT,
  model TEXT,
  tokens_input INT,
  tokens_output INT,
  cost_usd DECIMAL(10, 6),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HITL tickets
CREATE TABLE hitl_tickets (
  id SERIAL PRIMARY KEY,
  run_id UUID REFERENCES hat_runs(run_id),
  pr_number INT,
  verdict TEXT,
  risk_score INT,
  tier INT DEFAULT 1,
  status TEXT DEFAULT 'pending',  -- 'pending', 'approved', 'rejected', 'changes_requested', 'expired'
  reviewer TEXT,
  feedback TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ,
  sla_deadline TIMESTAMPTZ        -- calculated based on tier
);

-- Circuit breaker state
CREATE TABLE hat_circuit_breaker (
  hat_name TEXT PRIMARY KEY,
  state TEXT NOT NULL DEFAULT 'CLOSED',
  failure_count INT NOT NULL DEFAULT 0,
  last_failure_time TIMESTAMPTZ,
  last_state_change TIMESTAMPTZ DEFAULT NOW()
);

-- Self-improvement metrics
CREATE TABLE hat_accuracy_log (
  id SERIAL PRIMARY KEY,
  run_id UUID REFERENCES hat_runs(run_id),
  hat_name TEXT,
  finding_id TEXT,
  severity TEXT,
  human_verdict TEXT,  -- 'confirmed', 'false_positive', 'adjusted'
  human_adjusted_severity TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### E11.2 n8n Metrics Dashboard Workflow

**Workflow: `Hats — Daily Metrics Report`** (Scheduled: daily at 9 AM)

```
[Cron Trigger: 0 9 * * *]
  │
  ▼
[PostgreSQL Node: Query Daily Stats]
  SELECT
    DATE(created_at) AS date,
    COUNT(DISTINCT run_id) AS total_runs,
    COUNT(CASE WHEN cove_verdict = 'ALLOW' THEN 1 END) AS allowed,
    COUNT(CASE WHEN cove_verdict = 'ESCALATE' THEN 1 END) AS escalated,
    COUNT(CASE WHEN cove_verdict = 'QUARANTINE' THEN 1 END) AS quarantined,
    AVG(total_duration_ms) AS avg_duration_ms,
    SUM(total_tokens) AS total_tokens,
    SUM(total_cost_usd) AS total_cost_usd,
    AVG(cove_risk_score) AS avg_risk_score
  FROM hat_runs
  WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'
  GROUP BY DATE(created_at)
  │
  ▼
[PostgreSQL Node: Query Per-Hat Stats]
  SELECT
    hat_name,
    COUNT(*) AS executions,
    AVG(latency_ms) AS avg_latency_ms,
    SUM(severity_critical) AS critical_findings,
    SUM(severity_high) AS high_findings,
    COUNT(CASE WHEN status = 'timeout' THEN 1 END) AS timeouts,
    COUNT(CASE WHEN status = 'error' THEN 1 END) AS errors
  FROM hat_reports
  WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'
  GROUP BY hat_name
  ORDER BY avg_latency_ms DESC
  │
  ▼
[Code Node: Format Markdown Report]
  Produce a structured markdown report with:
  - Daily summary table
  - Per-hat performance table
  - Top findings by severity
  - Cost breakdown
  - Recommendations
  │
  ▼
[Slack Node: Post to #hats-metrics]
  Post the formatted report
  │
  ▼
[Google Sheets Node: Append to Tracking Sheet]
  Append daily stats row for historical trending
```

### E11.3 Cost Tracking Per Hat (Ollama Cloud Pricing)

Implement a Code node in each hat sub-workflow that calculates actual cost:

```javascript
// Ollama Cloud pricing per model (from Comparison Addendum)
const pricing = {
  'glm-5.1':         { input_per_m: 0.40, output_per_m: 1.10 },
  'glm-5':           { input_per_m: 0.35, output_per_m: 1.00 },
  'deepseek-v3.1':   { input_per_m: 0.10, output_per_m: 0.28 },
  'deepseek-v3.2':   { input_per_m: 0.12, output_per_m: 0.35 },
  'nemotron-3-super':{ input_per_m: 0.25, output_per_m: 0.80 },
  'nemotron-3-nano': { input_per_m: 0.08, output_per_m: 0.20 },
  'minimax-m2.7':    { input_per_m: 0.30, output_per_m: 1.20 },
  'kimi-k2.5':       { input_per_m: 0.42, output_per_m: 1.50 },
  'qwen3-coder':     { input_per_m: 0.20, output_per_m: 0.80 },
  'ministral-3':     { input_per_m: 0.05, output_per_m: 0.15 },
  'gemini-3-flash-preview': { input_per_m: 0.15, output_per_m: 0.60 }
};

const model = $input.item.json.model_used;
const inputTokens = $input.item.json.token_usage.input;
const outputTokens = $input.item.json.token_usage.output;

const rates = pricing[model] || { input_per_m: 0.20, output_per_m: 0.80 };
const costUsd = (inputTokens / 1_000_000) * rates.input_per_m +
                (outputTokens / 1_000_000) * rates.output_per_m;

// Log to cost table
await this.helpers.executeQuery(
  `INSERT INTO hat_cost_log (run_id, hat_name, model, tokens_input, tokens_output, cost_usd)
   VALUES ($1, $2, $3, $4, $5, $6)`,
  [$input.item.json.run_id, $input.item.json.hat_name, model, inputTokens, outputTokens, costUsd]
);

return { ...$input.item.json, cost_usd: costUsd };
```

---

## E12. Security Box — Deterministic Controls in n8n

### E12.1 Mapping the Best Practices Security Box to n8n

The Best Practices Guide defines five enforcement mechanisms. Here is how each is implemented in n8n:

| Security Box Layer | Best Practice | n8n Implementation |
|---|---|---|
| **1. Request Validation** | Schema validation, length limits, content policy before reaching model | Code Node at the start of every hat sub-workflow: validate input schema, truncate oversized diffs, reject PRs with >500 changed files |
| **2. Tool Call Interception** | Whitelist validation, rate limiting, budget tracking | PostgreSQL-based budget tracker (E11.1 hat_cost_log table), n8n Rate Limit node (or custom Code Node), whitelist of allowed Ollama Cloud models |
| **3. Output Filtering** | Content moderation, PII detection, policy classifiers | Code Node after each LLM response: scan for PII patterns (email, SSN, API keys in output), reject reports containing leaked credentials |
| **4. Budget Enforcement** | Cumulative cost tracking with hard caps | Cost Budget Gate (G1) from E6.1, per-PR and daily limits stored in PostgreSQL |
| **5. Audit Logging** | Tamper-proof request/response logs | PostgreSQL hat_reports table (E11.1) + hat_cost_log + hitl_tickets. All operations logged with timestamps. |

### E12.2 n8n Security Configuration (docker-compose)

From the n8n Guide's production security checklist, applied to the Hats deployment:

```bash
# .env file for Hats n8n deployment
N8N_ENCRYPTION_KEY=$(openssl rand -base64 32)     # MANDATORY — loses all creds if rotated
N8N_BLOCK_ENV_ACCESS_IN_NODE=true                 # Prevent Code nodes from reading env vars
N8N_BLOCK_FILE_ACCESS_TO_N8N_FILES=true           # Default — block reading ~/.n8n
N8N_SECURE_COOKIE=true                            # HTTPS-only cookies
N8N_CONTENT_SECURITY_POLICY=default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://api.ollama.ai https://github.com
EXECUTIONS_PROCESS=queue                           # Required for production
QUEUE_BULL_REDIS_HOST=redis
QUEUE_BULL_REDIS_PORT=6379
QUEUE_BULL_REDIS_PASSWORD=${REDIS_PASSWORD}
WEBHOOK_URL=https://n8n.example.com               # Must match reverse proxy
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=postgres
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_USER=n8n
DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
```

### E12.3 PII Detection in Hat Reports

Add this Code Node after every hat's LLM response parsing:

```javascript
// PII Detection (inspired by presidio patterns from the Best Practices Guide)
const report = $input.item.json;
const text = JSON.stringify(report.findings);

// Regex-based PII detection (lightweight, no external dependency)
const piiPatterns = [
  { name: 'email', regex: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g },
  { name: 'api_key', regex: /(sk-[a-zA-Z0-9]{20,}|key-[a-zA-Z0-9]{20,}|pk_[a-zA-Z0-9]{20,})/g },
  { name: 'aws_key', regex: /AKIA[0-9A-Z]{16}/g },
  { name: 'github_token', regex: /(ghp_|gho_|ghu_|ghs_|ghr_)[a-zA-Z0-9]{36,}/g },
  { name: 'private_key', regex: /-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----/g },
  { name: 'jwt', regex: /eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}/g }
];

const detectedPii = [];
for (const pattern of piiPatterns) {
  const matches = text.match(pattern.regex);
  if (matches) {
    detectedPii.push({ type: pattern.name, count: matches.length });
    // Redact in report
    report.findings = JSON.parse(
      JSON.stringify(report.findings).replace(pattern.regex, '[REDACTED_' + pattern.name.toUpperCase() + ']')
    );
  }
}

if (detectedPii.length > 0) {
  report.pii_detected = detectedPii;
  report.pii_redacted = true;
  // Log PII detection event
  console.warn(`PII detected in ${report.hat} report: ${JSON.stringify(detectedPii)}`);
}

return report;
```

---

## E13. Self-Improvement Pipeline — Continuous Tuning

### E13.1 Mapping the Best Practices Self-Improvement Cycle

The Best Practices Guide defines a four-phase improvement cycle. Here is how it is implemented using n8n workflows + Ollama Cloud models:

```
┌─────────────────────────────────────────────────────────────────────┐
│  SELF-IMPROVEMENT PIPELINE (n8n Scheduled Workflows)               │
│                                                                     │
│  PHASE 1: SIGNAL COLLECTION (Continuous)                            │
│  ─────────────────────────────────────────                          │
│  Sources:                                                           │
│  • GitHub PR comments reacting to hat findings (👍/👎)              │
│  • Human HITL decisions (approve/reject/adjust severity)            │
│  • hat_accuracy_log table (from E11.1)                              │
│  • Hat execution metrics (latency, timeout rate, error rate)        │
│                                                                     │
│  Workflow: "Hats — Signal Collector" (runs every 6 hours)          │
│  [Cron: 0 */6 * * *]                                                │
│  → Query GitHub API for comment reactions                           │
│  → Query hat_accuracy_log for human verdicts                        │
│  → Query hat_reports for performance metrics                        │
│  → Aggregate into signal_summary table                              │
│                                                                     │
│  PHASE 2: AUTOMATED EVALUATION (Weekly)                             │
│  ─────────────────────────────────────                              │
│  Workflow: "Hats — Weekly Quality Eval" (runs every Monday 8 AM)   │
│  [Cron: 0 8 * * 1]                                                  │
│  → Query past week's hat reports                                    │
│  → Use n8n AI Evaluation Node (or Ollama Cloud call) to score:      │
│    - Finding Actionability (1-5)                                    │
│    - Evidence Quality (1-5)                                         │
│    - Severity Accuracy (1-5)                                        │
│    - False Positive Rate                                             │
│  → Compare evaluation model vs production model output              │
│  → Store scores in hat_eval_scores table                            │
│                                                                     │
│  PHASE 3: PROMPT TUNING (Bi-Weekly)                                │
│  ──────────────────────────────                                     │
│  Workflow: "Hats — Prompt Tuning Cycle" (runs every other Sunday)   │
│  [Cron: 0 8 * * 0] (every 2 weeks via manual trigger or toggle)    │
│  → Analyze eval scores for each hat                                 │
│  → Identify patterns in false positives/negatives                   │
│  → Generate hypothesis: "Adding [instruction X] will reduce FPR"   │
│  → Create variant B of persona system prompt                        │
│  → Store in hat_prompt_versions table                               │
│  → NOT auto-deployed — requires human review                       │
│                                                                     │
│  PHASE 4: DEPLOYMENT & VALIDATION (On human approval)              │
│  ───────────────────────────────────────────                        │
│  Workflow: "Hats — Deploy Prompt Update" (manual trigger)           │
│  → Human reviews prompt variant B                                   │
│  → Approved? → Update PostgreSQL persona_prompts table              │
│  → Next hat execution uses new prompt                               │
│  → Monitor for 1 week: compare false positive/negative rates       │
│  → If metrics improve → keep new prompt                             │
│  → If metrics degrade → rollback to previous version                │
└─────────────────────────────────────────────────────────────────────┘
```

### E13.2 n8n AI Evaluation Node for Hat Quality

n8n's built-in AI Evaluation node (from the Guide) can be used to score hat report quality:

```
[AI Agent Node: Hat Quality Evaluator]
  Model: Ollama Cloud → deepseek-v3.1 (cheaper for eval, separate from production)
  System Prompt: "You are an evaluation agent. Score the following hat report
    on four dimensions (1-5 each): Actionability, Evidence Quality, Severity
    Accuracy, Completeness. Output JSON with scores and reasoning."

  Test Cases: Loaded from hat_reports table (past week's reports)

  Output: {
    actionability: 4,
    evidence_quality: 3,
    severity_accuracy: 5,
    completeness: 4,
    overall: 4.0,
    reasoning: "Findings are well-evidenced but one HIGH finding lacked a
                specific remediation step..."
  }
```

### E13.3 Persona Prompt Versioning Table

```sql
CREATE TABLE hat_persona_prompts (
  id SERIAL PRIMARY KEY,
  hat_name TEXT NOT NULL,
  version INT NOT NULL DEFAULT 1,
  prompt TEXT NOT NULL,
  is_active BOOLEAN DEFAULT false,
  eval_score DECIMAL(3, 1),
  false_positive_rate DECIMAL(5, 4),
  false_negative_rate DECIMAL(5, 4),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  activated_at TIMESTAMPTZ,
  UNIQUE (hat_name, version)
);

-- Activate a new prompt version
UPDATE hat_persona_prompts SET is_active = false WHERE hat_name = 'black';
UPDATE hat_persona_prompts SET is_active = true, activated_at = NOW()
  WHERE hat_name = 'black' AND version = 3;
```

---

## E14. Complete Step-by-Step Deployment

### Phase 1: Infrastructure Setup (Day 1)

```bash
# 1. Create project directory
mkdir hats-team && cd hats-team

# 2. Create .env file
cat > .env << 'EOF'
# === Ollama Cloud ===
OLLAMA_CLOUD_API_KEY=sk-ollama-your-key-here
OLLAMA_BASE_URL=https://api.ollama.ai/v1

# === n8n ===
N8N_ENCRYPTION_KEY=$(openssl rand -base64 32)
N8N_BLOCK_ENV_ACCESS_IN_NODE=true
N8N_BLOCK_FILE_ACCESS_TO_N8N_FILES=true
N8N_SECURE_COOKIE=true
WEBHOOK_URL=https://n8n.yourdomain.com
EXECUTIONS_PROCESS=queue

# === PostgreSQL ===
POSTGRES_PASSWORD=$(openssl rand -base64 24)
DB_POSTGRESDB_HOST=postgres
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_USER=n8n
DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}

# === Redis ===
REDIS_PASSWORD=$(openssl rand -base64 24)
QUEUE_BULL_REDIS_HOST=redis
QUEUE_BULL_REDIS_PORT=6379
QUEUE_BULL_REDIS_PASSWORD=${REDIS_PASSWORD}

# === GitHub ===
GITHUB_WEBHOOK_SECRET=$(openssl rand -base64 32)
GITHUB_APP_ID=your-github-app-id
GITHUB_PRIVATE_KEY_PATH=/run/secrets/github_private_key

# === Slack (optional) ===
SLACK_BOT_TOKEN=xoxb-your-slack-token
SLACK_CHANNEL_HATS_REVIEW=#hats-review
SLACK_CHANNEL_HATS_METRICS=#hats-metrics
EOF
chmod 600 .env

# 3. Create docker-compose.yml (use the full version from E7.3)

# 4. Start infrastructure
docker compose up -d postgres redis
sleep 10  # Wait for databases to initialize

# 5. Start n8n
docker compose up -d n8n-main
sleep 5

# 6. Verify n8n is running
docker compose logs n8n-main | tail -20
# Should see: "Editor is now accessible via http://localhost:5678/"

# 7. Start workers
docker compose up -d n8n-worker
```

### Phase 2: Database Initialization (Day 1)

```bash
# Connect to PostgreSQL
docker exec -it hats-team-postgres-1 psql -U n8n -d n8n

# Run the schema from E11.1
\i /path/to/schema.sql
# Or paste the CREATE TABLE statements directly

# Verify tables
\dt
# Should show: hat_runs, hat_reports, hat_cost_log, hitl_tickets,
#              hat_circuit_breaker, hat_accuracy_log, hat_persona_prompts
```

### Phase 3: n8n Workflow Creation (Day 2–4)

Create workflows in this order (each depends on the previous):

| Day | Workflow | Section Reference | Action |
|-----|----------|-------------------|--------|
| 2 AM | `Hats — Black Hat` (sub-workflow) | E9.2, E9.3 | Create and test the most critical hat first |
| 2 AM | `Hats — Blue Hat` (sub-workflow) | E9.2 | Create the simplest always-on hat |
| 2 PM | `Hats — Purple Hat` (sub-workflow) | E9.2 | Create the AI safety hat |
| 2 PM | Test always-on hats manually | — | Execute each sub-workflow with a test diff |
| 3 AM | Remaining Tier 4 hats (White, Silver, Teal) | E9.2 | Fast to create (simple patterns) |
| 3 AM | Remaining Tier 3 hats (Orange, Gray, Steel, Chartreuse) | E9.2 | |
| 3 PM | Remaining Tier 2 hats (Red, Yellow, Green, Indigo, Cyan, Brown, Azure) | E9.2 | |
| 4 AM | `Hats — Consolidator` | E10.1 | |
| 4 AM | `Hats — Gold CoVE` | E10.2, E10.3 | Most important — test thoroughly |
| 4 PM | `Hats — Hat Selector` | E5.1 | The routing logic |
| 4 PM | `Hats Conductor — Main Pipeline` | E5.1, E6.x | Wire everything together |

### Phase 4: HITL & Notifications (Day 5)

| Day | Workflow | Section Reference |
|-----|----------|-------------------|
| 5 AM | `Hats HITL Manager` | E8.1 |
| 5 AM | `Hats GitHub Command Handler` | E8.2 |
| 5 PM | `Hats Slack Interaction Handler` | E8.3 |

### Phase 5: Observability & Self-Improvement (Day 6)

| Day | Workflow | Section Reference |
|-----|----------|-------------------|
| 6 AM | `Hats — Daily Metrics Report` | E11.2 |
| 6 AM | `Hats — Signal Collector` | E13.1 |
| 6 PM | `Hats — Weekly Quality Eval` | E13.1, E13.2 |
| 6 PM | `Hats Error Trigger` | n8n Guide §5 |

### Phase 6: GitHub Integration (Day 7)

```bash
# 1. Create GitHub App (or Personal Access Token) with:
#    - Read/write access to Pull Requests
#    - Read access to Code
#    - Read/write access to Commit Statuses

# 2. Configure GitHub webhook:
#    - Payload URL: https://n8n.yourdomain.com/webhook/hats/webhook/pr
#    - Content type: application/json
#    - Secret: (from GITHUB_WEBHOOK_SECRET in .env)
#    - Events: Pull requests (opened, synchronize, reopened)

# 3. Test with a real PR:
#    - Open a test PR
#    - Verify the Conductor workflow is triggered
#    - Check that hat reports are posted as PR comments
#    - Verify HITL flow works (if any findings)

# 4. Set up reverse proxy with TLS (NEVER expose port 5678 directly)
#    Recommended: Caddy (auto-TLS) or Nginx + Let's Encrypt
```

### Phase 7: Production Hardening (Day 8–10)

| Day | Task | Details |
|-----|------|---------|
| 8 | **Security audit** | Run the Security Box checks from E12 against your n8n instance. Verify env blocking, file blocking, encryption key. |
| 8 | **Backup verification** | Test PostgreSQL backup/restore. Test n8n credential export/import. |
| 9 | **Load testing** | Send 5 PRs simultaneously. Verify queue mode handles concurrent hat executions. Verify backpressure kicks in. |
| 9 | **Cost validation** | Run 10 test PRs. Verify actual Ollama Cloud costs match estimates from E3.3. Adjust budget gates if needed. |
| 10 | **Documentation & team onboarding** | Share this appendix with the team. Document any customizations. Set up Slack channels. Configure alerting. |

---

## E15. Production Runbook & Troubleshooting

### E15.1 Common Issues & Resolutions

| Symptom | Likely Cause | Resolution |
|---------|-------------|-----------|
| Hat sub-workflow returns "circuit breaker open" | LLM API has been failing for this hat | Check Ollama Cloud status. Check circuit breaker table: `SELECT * FROM hat_circuit_breaker WHERE state = 'OPEN'`. Reset with: `UPDATE hat_circuit_breaker SET state='CLOSED', failure_count=0 WHERE hat_name='...'` |
| Cost gate blocking all PRs | Daily budget exhausted | Check `hat_cost_log` for unusually expensive runs. Verify model pricing hasn't changed. Consider raising daily budget. |
| CoVE always says ESCALATE | Risk score threshold too aggressive | Lower `auto_allow_threshold_risk_score` in CoVE prompt. Review false positive findings in `hat_accuracy_log`. |
| n8n worker crashing | Out of memory (large diffs) | Increase Docker memory limit. Reduce `max_concurrent_hats`. Add diff truncation in hat sub-workflows. |
| GitHub webhook not triggering | Webhook secret mismatch | Verify `GITHUB_WEBHOOK_SECRET` matches GitHub App settings. Check n8n webhook logs. |
| Hat timeout on every run | Ollama Cloud latency spike | Check model availability. Switch to faster model (GLM-5.1 → Nemotron 3 Super). Increase timeout in hat config. |
| PII detected in hat report | Hat found a credential in the diff | This is expected behavior (the PII filter is working). Verify the credential is in the ORIGINAL code, not generated by the hat. |
| Slack notifications not sending | Bot token expired or missing permissions | Verify `SLACK_BOT_TOKEN`. Check Slack app has `chat:write` and `chat:write.public` scopes. |

### E15.2 Emergency Procedures

**Procedure: Emergency Pipeline Disable**
```bash
# If the Hats pipeline is causing issues (cost spike, incorrect blocks, etc.):
# 1. Disable the GitHub webhook in GitHub Settings → Developer Settings → Apps → [Your App] → Webhooks
# 2. Or: Deactivate the Conductor workflow in n8n UI (Shift+P to unpublish)
# 3. Existing in-flight executions will complete; no new ones will start
# 4. To re-enable: Re-publish workflow in n8n, re-enable webhook
```

**Procedure: Reset All Circuit Breakers**
```sql
UPDATE hat_circuit_breaker SET state = 'CLOSED', failure_count = 0, last_state_change = NOW();
```

**Procedure: Override a QUARANTINE Decision**
```bash
# Via GitHub PR comment:
/hats approve --force

# Or via n8n:
# 1. Open the HITL Manager workflow execution
# 2. Click "Execute Node" on the approval branch
# 3. The Conductor will receive the override and post ALLOW to the PR
```

**Procedure: Export Everything for Disaster Recovery**
```bash
# From the n8n Guide §15:
docker exec -it <n8n-container> n8n export:everything --all --output=/data/backup/hats_full_backup.json

# Also dump PostgreSQL:
docker exec hats-team-postgres-1 pg_dump -U n8n n8n > hats_postgres_backup.sql
```

### E15.3 Maintenance Schedule

Adapted from the n8n Guide's maintenance schedule (§17) and the Best Practices Guide's governance cadence:

| Task | Frequency | Owner | Workflow/Command |
|------|-----------|-------|-----------------|
| Review hat accuracy metrics | Weekly | Agent Owner | Hats — Weekly Quality Eval (n8n) |
| Update persona prompts | Bi-weekly | Prompt Engineer | Manual review + Hats — Deploy Prompt Update |
| Security audit (red team) | Weekly | Security Lead | Custom adversarial PR test suite |
| Review active n8n workflows | Monthly | ML Operations | n8n UI → check for deactivated/error workflows |
| Cost budget review | Monthly | Agent Owner | Query `hat_cost_log`, compare vs budget |
| n8n core upgrade | Monthly | ML Operations | `docker compose pull && docker compose up -d` |
| PostgreSQL backup test | Monthly | Platform Ops | Restore backup to test environment |
| Full governance review | Quarterly | Ethics Reviewer | Comprehensive audit: accuracy, bias, cost, security |
| Model re-evaluation | Quarterly | Agent Owner | Check Ollama Cloud for new models, re-run benchmarks |

### E15.4 Quick Reference: n8n CLI Commands for Hats

```bash
# Start the full stack
docker compose up -d

# Check worker status
docker compose ps
docker compose logs n8n-worker --tail=50

# Scale workers (increase concurrency)
docker compose up -d --scale n8n-worker=5

# Export all Hats workflows
docker exec -it <container> n8n export:workflow --all --output=/data/backup/hats_workflows.json

# Import workflows (disaster recovery)
docker exec -it <container> n8n import:workflow --input=/data/backup/hats_workflows.json

# Run diagnostics
docker exec -it <container> n8n doctor

# Manually trigger a hat run (testing)
docker exec -it <container> n8n execute --id=<conductor-workflow-id>

# Reset user (if locked out)
docker exec -it <container> n8n user-management:reset
```

---

*This appendix is a companion to the main Hats Team specification. Together, they provide everything needed to build, deploy, and operate a production-grade Agentic AI engineering review pipeline using Ollama Cloud models, n8n 2.16.0 orchestration, and the prompt engineering patterns from the AI Agent Best Practices Guide.*
