# hat_stack

**The Universal Agentic-AI Engineering Stack — Hats Team Specification**

Language-agnostic · Framework-agnostic · Domain-agnostic

---

## Overview

The Hats Team is a structured set of 18 AI-agent roles, each wearing a different "hat" that embodies a specific review lens. Together they provide comprehensive, adversarial quality assurance across every dimension of software engineering — from security and resilience to accessibility, supply-chain hygiene, and AI safety.

Every hat specifies:
- **Run Mode** — `Always` (mandatory on every PR) or `Conditional` (triggered by context)
- **Trigger Conditions** — the code patterns / file types that activate the hat
- **Primary Focus** — the quality dimension the hat owns

---

## Master Hat Registry

See [`CATALOG.md`](CATALOG.md) for the full table of all 18 hats.

---

## Individual Hat Specifications

| # | Hat | Spec |
|---|-----|------|
| 1 | 🔴 Red Hat — Failure & Resilience | [`hats/01_red_hat.md`](hats/01_red_hat.md) |
| 2 | ⚫ Black Hat — Security & Exploits | [`hats/02_black_hat.md`](hats/02_black_hat.md) |
| 3 | ⚪ White Hat — Efficiency & Resources | [`hats/03_white_hat.md`](hats/03_white_hat.md) |
| 4 | 🟡 Yellow Hat — Synergies & Integration | [`hats/04_yellow_hat.md`](hats/04_yellow_hat.md) |
| 5 | 🟢 Green Hat — Evolution & Extensibility | [`hats/05_green_hat.md`](hats/05_green_hat.md) |
| 6 | 🔵 Blue Hat — Process & Specification | [`hats/06_blue_hat.md`](hats/06_blue_hat.md) |
| 7 | 🟣 Indigo Hat — Cross-Feature Architecture | [`hats/07_indigo_hat.md`](hats/07_indigo_hat.md) |
| 8 | 🩵 Cyan Hat — Innovation & Feasibility | [`hats/08_cyan_hat.md`](hats/08_cyan_hat.md) |
| 9 | 🟪 Purple Hat — AI Safety & Alignment | [`hats/09_purple_hat.md`](hats/09_purple_hat.md) |
| 10 | 🟠 Orange Hat — DevOps & Automation | [`hats/10_orange_hat.md`](hats/10_orange_hat.md) |
| 11 | 🪨 Silver Hat — Context & Token Optimization | [`hats/11_silver_hat.md`](hats/11_silver_hat.md) |
| 12 | 💎 Azure Hat — MCP & Protocol Integration | [`hats/12_azure_hat.md`](hats/12_azure_hat.md) |
| 13 | 🟤 Brown Hat — Data Governance & Privacy | [`hats/13_brown_hat.md`](hats/13_brown_hat.md) |
| 14 | ⚙️ Gray Hat — Observability & Reliability | [`hats/14_gray_hat.md`](hats/14_gray_hat.md) |
| 15 | ♿ Teal Hat — Accessibility & Inclusion | [`hats/15_teal_hat.md`](hats/15_teal_hat.md) |
| 16 | 🔗 Steel Hat — Supply Chain & Dependencies | [`hats/16_steel_hat.md`](hats/16_steel_hat.md) |
| 17 | 🧪 Chartreuse Hat — Testing & Evaluation | [`hats/17_chartreuse_hat.md`](hats/17_chartreuse_hat.md) |
| 18 | ✨ Gold Hat — CoVE Final QA | [`hats/18_gold_hat.md`](hats/18_gold_hat.md) |

---

## Repository Layout

```
hat_stack/
├── README.md              ← This file — project overview & hat index
├── CATALOG.md             ← Master Hat Registry (full table)
├── SPEC.md                ← Primary specification entry point
└── hats/
    ├── 01_red_hat.md
    ├── 02_black_hat.md
    ├── ...
    └── 18_gold_hat.md
```

---

## License

See [LICENSE](LICENSE).

