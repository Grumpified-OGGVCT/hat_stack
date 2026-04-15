#!/usr/bin/env python3
"""
gates.py — Gate engine for Hat Stack pipeline.

Implements all 5 gates from SPEC §7:
  G1: Cost Budget Gate — estimate tokens, check budget, block or trim
  G2: Security Fast-Path Gate — after Black Hat completes, check for CRITICAL
  G3: Consistency Gate — detect contradictions between hat findings
  G4: Timeout Gate — per-hat timeout with graceful degradation
  G5: Final Decision Gate — CoVE verdict routing
"""

import sys
from typing import Any

from hats_common import estimate_cost


# ---------------------------------------------------------------------------
# G1: Cost Budget Gate (pre-execution)
# ---------------------------------------------------------------------------

def gate_cost_budget(config: dict, selected_hats: list[str], diff_tokens: int) -> dict:
    """Cost Budget Gate (G1) — SPEC §7.

    Estimates total pipeline cost and checks against budget.
    If over budget, trims hats by tier (remove Tier 4 first, then Tier 3, etc.)
    until within budget. Always-on hats cannot be trimmed.

    Returns dict with keys:
      within_budget: bool
      estimated_cost: float
      budget_limit: float
      trimmed_hats: list[str] — hats removed to fit budget
      selected_hats: list[str] — remaining hats after trimming
      verdict: "PASS" | "TRIMMED" | "BLOCKED"
    """
    budget = config["gates"]["cost_budget"]["max_usd_per_pr"]
    max_tokens = config["gates"]["cost_budget"].get("max_tokens_per_pr", 150000)
    models_cfg = config.get("models", {})
    hats_cfg = config["hats"]

    # Estimate with full selection
    est_cost, within_budget = estimate_cost(config, selected_hats, diff_tokens)

    result = {
        "estimated_cost": est_cost,
        "budget_limit": budget,
        "within_budget": within_budget,
        "trimmed_hats": [],
        "selected_hats": list(selected_hats),
        "verdict": "PASS",
    }

    if within_budget:
        return result

    # Over budget — trim by tier, starting from Tier 4
    always_hats = {h for h, d in hats_cfg.items() if d.get("always_run")}
    removable = [h for h in selected_hats if h not in always_hats and h != "gold"]

    # Group removable hats by tier
    hats_by_tier: dict[int, list[str]] = {}
    for hat_id in removable:
        model_name = hats_cfg[hat_id].get("primary_model", "")
        model_cfg = models_cfg.get(model_name, {})
        tier = model_cfg.get("tier", 4)
        hats_by_tier.setdefault(tier, []).append(hat_id)

    # Trim from highest tier down
    remaining = list(selected_hats)
    for tier in sorted(hats_by_tier.keys(), reverse=True):
        if est_cost <= budget:
            break
        for hat_id in hats_by_tier[tier]:
            if est_cost <= budget:
                break
            remaining.remove(hat_id)
            result["trimmed_hats"].append(hat_id)
            # Re-estimate without this hat
            est_cost, within_budget = estimate_cost(config, remaining, diff_tokens)

    result["estimated_cost"] = est_cost
    result["within_budget"] = within_budget
    result["selected_hats"] = remaining

    if est_cost <= budget:
        result["verdict"] = "TRIMMED"
    else:
        # Even after trimming all conditional hats, still over budget
        result["verdict"] = "BLOCKED"

    return result


# ---------------------------------------------------------------------------
# G2: Security Fast-Path Gate (mid-execution)
# ---------------------------------------------------------------------------

def gate_security_fast_path(config: dict, report: dict) -> dict:
    """Security Fast-Path Gate (G2) — SPEC §7.

    After Black Hat (or any hat) completes, check if any CRITICAL findings exist.
    If so, flag for early termination.

    Returns dict with keys:
      triggered: bool
      critical_findings: list[dict] — the CRITICAL findings that triggered the gate
      action: "continue" | "escalate"
    """
    gate_cfg = config.get("gates", {}).get("security_fast_path", {})
    if not gate_cfg.get("enabled", True):
        return {"triggered": False, "critical_findings": [], "action": "continue"}

    trigger_severity = gate_cfg.get("trigger_severity", "CRITICAL").upper()

    critical_findings = []
    for finding in report.get("findings", []):
        if finding.get("severity", "").upper() == trigger_severity:
            critical_findings.append(finding)

    triggered = len(critical_findings) > 0
    return {
        "triggered": triggered,
        "critical_findings": critical_findings,
        "action": "escalate" if triggered else "continue",
    }


# ---------------------------------------------------------------------------
# G3: Consistency Gate (post-consolidation)
# ---------------------------------------------------------------------------

# Mutually exclusive finding categories
_MUTUALLY_EXCLUSIVE = [
    {"add_feature", "remove_feature"},
    {"increase_logging", "decrease_logging"},
    {"add_test", "remove_test"},
    {"increase_security", "decrease_security"},
    {"optimize_speed", "optimize_size"},
]


def gate_consistency(consolidated_findings: list[dict]) -> dict:
    """Consistency Gate (G3) — SPEC §7.

    Detects contradictions between hat findings. Findings that contradict
    each other are tagged with `conflicted: true` for CoVE resolution.

    Returns dict with keys:
      contradictions: list[dict] — pairs of contradictory findings
      conflicted_finding_indices: set[int] — indices of conflicted findings
      verdict: "PASS" | "CONFLICTS_DETECTED"
    """
    contradictions = []
    conflicted_indices = set()

    for i, finding_a in enumerate(consolidated_findings):
        for j, finding_b in enumerate(consolidated_findings):
            if j <= i:
                continue

            # Same file, overlapping or same line range, different categories
            if _findings_contradict(finding_a, finding_b):
                contradictions.append({
                    "finding_a_index": i,
                    "finding_b_index": j,
                    "finding_a": finding_a,
                    "finding_b": finding_b,
                })
                conflicted_indices.add(i)
                conflicted_indices.add(j)

    return {
        "contradictions": contradictions,
        "conflicted_finding_indices": conflicted_indices,
        "verdict": "CONFLICTS_DETECTED" if contradictions else "PASS",
    }


def _findings_contradict(a: dict, b: dict) -> bool:
    """Check if two findings contradict each other.

    Two findings contradict if they:
    1. Reference the same file and overlapping line ranges
    2. Have mutually exclusive categories
    3. Have opposite severity levels for the same issue
    """
    # Same file check
    file_a = a.get("file") or ""
    file_b = b.get("file") or ""
    if not file_a or not file_b or file_a != file_b:
        return False

    # Overlapping line ranges
    line_a = a.get("line")
    line_b = b.get("line")
    if line_a is not None and line_b is not None:
        if abs(line_a - line_b) > 10:  # Not overlapping
            return False

    # Check categories
    cat_a = a.get("category", "").lower()
    cat_b = b.get("category", "").lower()
    for exclusive_set in _MUTUALLY_EXCLUSIVE:
        a_in = cat_a in exclusive_set
        b_in = cat_b in exclusive_set
        if a_in and b_in and cat_a != cat_b:
            return True

    # Opposite severity for same title
    title_a = (a.get("title") or "").lower()
    title_b = (b.get("title") or "").lower()
    if title_a and title_b and title_a == title_b:
        sev_a = a.get("severity", "LOW")
        sev_b = b.get("severity", "LOW")
        if (sev_a in ("CRITICAL", "HIGH") and sev_b in ("LOW", "MEDIUM")) or \
           (sev_b in ("CRITICAL", "HIGH") and sev_a in ("LOW", "MEDIUM")):
            return True

    return False


# ---------------------------------------------------------------------------
# G4: Timeout Gate (per-hat)
# ---------------------------------------------------------------------------

def gate_timeout(config: dict, hat_id: str, elapsed_seconds: float) -> dict:
    """Timeout Gate (G4) — SPEC §7.

    Checks if a hat has exceeded its timeout limit.
    Implements graceful degradation: record the timeout and mark the hat
    as timed out in the run state.

    Returns dict with keys:
      timed_out: bool
      hat_id: str
      timeout_limit: float
      elapsed: float
      action: "continue" | "degrade"
    """
    hats_cfg = config["hats"]
    hat_def = hats_cfg.get(hat_id, {})
    default_timeout = config.get("gates", {}).get("timeout", {}).get("default_per_hat_seconds", 120)
    timeout_limit = hat_def.get("timeout_seconds", default_timeout)

    timed_out = elapsed_seconds > timeout_limit
    return {
        "timed_out": timed_out,
        "hat_id": hat_id,
        "timeout_limit": timeout_limit,
        "elapsed": elapsed_seconds,
        "action": "degrade" if timed_out else "continue",
    }


# ---------------------------------------------------------------------------
# G5: Final Decision Gate (post-adjudication)
# ---------------------------------------------------------------------------

def gate_final_decision(verdict: str, risk_score: int, config: dict,
                        security_fast_path_triggered: bool = False) -> dict:
    """Final Decision Gate (G5) — SPEC §7.

    Routes CoVE output to the appropriate channel:
    - ALLOW: pipeline passes, PR can merge
    - ESCALATE: requires human review (HITL)
    - QUARANTINE: blocked, must be resolved before merge

    Returns dict with keys:
      verdict: "ALLOW" | "ESCALATE" | "QUARANTINE"
      risk_score: int
      action: str — human-readable action
      requires_human_review: bool
    """
    rs = config.get("risk_score", {})
    allow_threshold = rs.get("allow_threshold", 20)
    escalate_threshold = rs.get("escalate_threshold", 60)

    # Security fast-path always overrides to QUARANTINE
    if security_fast_path_triggered:
        return {
            "verdict": "QUARANTINE",
            "risk_score": risk_score,
            "action": "Security fast-path triggered — CRITICAL finding requires resolution",
            "requires_human_review": True,
        }

    if verdict == "ALLOW":
        action = "Pipeline passes — PR can merge"
        requires_hitl = False
    elif verdict == "ESCALATE":
        action = "Requires human review before merge"
        requires_hitl = True
    else:  # QUARANTINE
        action = "Blocked — must resolve issues before merge"
        requires_hitl = True

    return {
        "verdict": verdict,
        "risk_score": risk_score,
        "action": action,
        "requires_human_review": requires_hitl,
    }