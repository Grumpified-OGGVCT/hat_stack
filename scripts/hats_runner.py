#!/usr/bin/env python3
"""
Hats Team Runner -- GitHub Actions Orchestrator

Implements the Conductor logic from the Hats Team Specification:
  - Hat selection based on diff triggers (via hat_selector.py)
  - Tiered-parallel execution via Ollama API (cloud pool + local queue)
  - Gate engine: cost budget (G1), security fast-path (G2), consistency (G3),
    timeout (G4), final decision (G5) (via gates.py)
  - Consolidation and deduplication (via consolidator.py)
  - Gold Hat (CoVE) final adjudication
  - Checkpoint persistence (via state.py)
  - Structured JSON + Markdown report output

Usage:
  python hats_runner.py --diff <diff_text_or_file> [--hats black,blue,...] [--config hat_configs.yml]

Environment:
  OLLAMA_API_KEY    -- Ollama Cloud API key (required for cloud models)
  OLLAMA_CLOUD_URL  -- Cloud API URL (default: https://ollama.com)
  OLLAMA_LOCAL_URL   -- Local Ollama URL (default: http://localhost:11434)
"""

import argparse
import json
import os
import sys
import time
import traceback
from concurrent.futures import as_completed
from pathlib import Path

# Shared modules
from hats_common import (
    load_config,
    call_ollama,
    detect_sensitive_mode,
    build_comparable_model_sequence,
    estimate_cost,
    truncate_to_context_window,
    preflight_check,
    try_model_chain,
    ConcurrencyCoordinator,
    RetryPolicy,
    DEFAULT_CONFIG,
)
from gates import (
    gate_cost_budget,
    gate_security_fast_path,
    gate_consistency,
    gate_timeout,
    gate_final_decision,
)
from consolidator import consolidate_findings, normalize_severity
from hat_selector import select_hats, _extract_changed_files
from state import (
    create_initial_state,
    save_checkpoint,
    load_checkpoint,
    update_state,
    finalize_state,
    get_pending_hats,
)


# ---------------------------------------------------------------------------
# Finding schema — forced JSON output structure
# ---------------------------------------------------------------------------

_FINDING_SCHEMA = """\
Respond with a JSON object with this exact schema:
{
  "hat": "<hat_name>",
  "findings": [
    {
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "title": "<short title>",
      "description": "<detailed description>",
      "file": "<file path if applicable>",
      "line": <line number if applicable or null>,
      "line_range": "<line range if applicable or null>",
      "category": "<finding category>",
      "recommendation": "<actionable fix>"
    }
  ],
  "summary": "<one-paragraph summary>",
  "confidence": <0.0-1.0>
}
"""


# ---------------------------------------------------------------------------
# Single hat execution — with model selection for sensitive mode
# ---------------------------------------------------------------------------

def run_hat(config: dict, hat_id: str, diff_text: str, context: str = "",
            sensitive_mode: bool = False, coordinator: ConcurrencyCoordinator | None = None) -> dict:
    """Execute a single hat analysis against the diff.

    Respects sensitive mode by switching dual-mode hats to local models.
    Uses the concurrency coordinator to enforce cloud/local parallelism limits.
    """
    hats_cfg = config["hats"]
    hat_def = hats_cfg[hat_id]

    # Determine which model to use
    if coordinator:
        model = coordinator.get_model_for_hat(config, hat_id, sensitive_mode)
        hat_type = coordinator.classify_hat(config, hat_id, sensitive_mode)
    else:
        model = hat_def["primary_model"]
        if sensitive_mode and hat_id in ("black", "purple", "brown"):
            model = hat_def.get("local_model", hat_def["primary_model"])
        hat_type = "local" if hat_def.get("local_only") else "cloud"

    system_prompt = hat_def["persona"].strip() + "\n\n" + _FINDING_SCHEMA
    user_prompt = f"## Code Diff to Analyze\n\n```diff\n{diff_text}\n```"
    if context:
        user_prompt = f"## Additional Context\n\n{context}\n\n{user_prompt}"

    temperature = hat_def.get("temperature", 0.3)
    max_tokens = hat_def.get("max_tokens", 4096)
    timeout = hat_def.get("timeout_seconds", 120)
    fallback = hat_def.get("fallback_model")

    # For local-only hats, use local fallback chain
    if hat_type == "local":
        fallback = hat_def.get("fallback_model") if hat_def.get("local_only") else hat_def.get("local_model")

    start = time.time()
    result = None

    if coordinator and hat_type == "local":
        # Acquire local model slot (only 1 local model at a time)
        with coordinator.local_queue:
            result = try_model_chain(config, model, fallback, system_prompt, user_prompt,
                                    temperature, max_tokens, timeout, hat_id)
    elif coordinator and hat_type == "cloud":
        # Cloud models run in the cloud pool (up to 4 parallel)
        result = try_model_chain(config, model, fallback, system_prompt, user_prompt,
                                temperature, max_tokens, timeout, hat_id)
    else:
        # No coordinator (legacy / simple mode)
        result = try_model_chain(config, model, fallback, system_prompt, user_prompt,
                                temperature, max_tokens, timeout, hat_id)

    elapsed = time.time() - start

    # Check timeout gate (G4)
    timeout_gate = gate_timeout(config, hat_id, elapsed)

    report = {
        "hat_id": hat_id,
        "hat_name": hat_def["name"],
        "emoji": hat_def["emoji"],
        "model_used": result["model"],
        "latency_seconds": round(elapsed, 2),
        "token_usage": result["usage"],
        "error": result["error"],
        "findings": [],
        "summary": "",
        "confidence": 0.0,
        "timed_out": timeout_gate["timed_out"],
    }

    if result["content"]:
        raw = result["content"].strip()
        # Strip markdown code fences if present (models sometimes wrap JSON in ```json ... ```)
        if raw.startswith("```"):
            lines = raw.split("\n")
            # Remove first line (```json or ```) and last line (```)
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            raw = "\n".join(lines).strip()
        try:
            parsed = json.loads(raw)
            report["findings"] = parsed.get("findings", [])
            report["summary"] = parsed.get("summary", "")
            report["confidence"] = parsed.get("confidence", 0.0)
        except json.JSONDecodeError:
            report["findings"] = [{
                "severity": "LOW",
                "title": "Unstructured response",
                "description": result["content"][:2000],
                "file": None,
                "line": None,
                "recommendation": "Review raw model output",
            }]
            report["summary"] = "Model returned unstructured response"

    if timeout_gate["timed_out"]:
        report["error"] = report.get("error") or f"Timeout after {timeout_gate['timeout_limit']}s"

    return report


# ---------------------------------------------------------------------------
# Risk score calculator (per CATALOG.md formula)
# ---------------------------------------------------------------------------

def compute_risk_score(config: dict, severity_counts: dict) -> tuple[int, str]:
    """Compute composite risk score and verdict per CATALOG.md formula.

    Returns (score, verdict) where verdict is ALLOW, ESCALATE, or QUARANTINE.
    """
    rs = config.get("risk_score", {})

    # Any CRITICAL -> automatic QUARANTINE
    if severity_counts.get("CRITICAL", 0) > 0:
        score = min(100,
            min(severity_counts["CRITICAL"] * rs.get("critical_weight", 20), rs.get("critical_cap", 80)) +
            min(severity_counts.get("HIGH", 0) * rs.get("high_weight", 5), rs.get("high_cap", 40)) +
            min(severity_counts.get("MEDIUM", 0) * rs.get("medium_weight", 1), rs.get("medium_cap", 10)) +
            int(min(severity_counts.get("LOW", 0) * rs.get("low_weight", 0.1), rs.get("low_cap", 5)))
        )
        return max(score, 61), "QUARANTINE"

    score = min(100,
        min(severity_counts.get("HIGH", 0) * rs.get("high_weight", 5), rs.get("high_cap", 40)) +
        min(severity_counts.get("MEDIUM", 0) * rs.get("medium_weight", 1), rs.get("medium_cap", 10)) +
        int(min(severity_counts.get("LOW", 0) * rs.get("low_weight", 0.1), rs.get("low_cap", 5)))
    )

    allow_threshold = rs.get("allow_threshold", 20)
    escalate_threshold = rs.get("escalate_threshold", 60)

    if score <= allow_threshold:
        return score, "ALLOW"
    elif score <= escalate_threshold:
        return score, "ESCALATE"
    else:
        return score, "QUARANTINE"


# ---------------------------------------------------------------------------
# Markdown report generator
# ---------------------------------------------------------------------------

def generate_markdown_report(consolidated: dict, risk_score: int, verdict: str,
                             selected_hats: list[str], config: dict,
                             sensitive_mode: bool = False) -> str:
    """Generate a Markdown summary report suitable for PR comments."""
    lines = []
    lines.append("# Hats Team Review Report\n")

    # Verdict banner
    emoji_map = {"ALLOW": "PASS", "ESCALATE": "WARN", "QUARANTINE": "BLOCK"}
    verdict_label = emoji_map.get(verdict, "UNKNOWN")
    lines.append(f"## Verdict: **{verdict}** (Risk Score: {risk_score}/100)\n")

    # Sensitive mode indicator
    if sensitive_mode:
        lines.append("> **Sensitive mode active** — credential/PII content detected. "
                     "Dual-mode hats used local models.\n")

    # Severity summary
    sc = consolidated["severity_counts"]
    lines.append("### Severity Summary\n")
    lines.append("| Severity | Count |")
    lines.append("|----------|-------|")
    lines.append(f"| CRITICAL | {sc.get('CRITICAL', 0)} |")
    lines.append(f"| HIGH | {sc.get('HIGH', 0)} |")
    lines.append(f"| MEDIUM | {sc.get('MEDIUM', 0)} |")
    lines.append(f"| LOW | {sc.get('LOW', 0)} |")
    if sc.get("INFO", 0) > 0:
        lines.append(f"| INFO | {sc['INFO']} |")
    lines.append("")

    # Dedup stats
    dedup = consolidated.get("dedup_stats", {})
    if dedup.get("removed_duplicates", 0) > 0:
        lines.append(f"> Deduplicated: {dedup['original_count']} findings -> "
                     f"{dedup['deduplicated_count']} (removed {dedup['removed_duplicates']} duplicates)\n")

    # Hat execution summary
    lines.append("### Hat Execution Summary\n")
    lines.append("| Hat | Model | Latency | Findings | Status |")
    lines.append("|-----|-------|---------|----------|--------|")
    for hs in consolidated["hat_summaries"]:
        status = "Error" if hs.get("error") else "OK"
        lines.append(
            f"| {hs['emoji']} {hs['hat']} | `{hs['model']}` | "
            f"{hs['latency_s']:.1f}s | {hs['findings_count']} | {status} |"
        )
    lines.append("")

    # Conflicts
    conflicts = consolidated.get("conflicts", [])
    if conflicts:
        lines.append("### Conflicts (flagged for CoVE resolution)\n")
        for conflict in conflicts:
            a = conflict.get("finding_a", {})
            b = conflict.get("finding_b", {})
            lines.append(f"- **{a.get('source_hat', '?')}** says: {a.get('title', '?')} "
                         f"vs **{b.get('source_hat', '?')}** says: {b.get('title', '?')}")
        lines.append("")

    # Not-evaluated hats
    not_eval = consolidated.get("not_evaluated_hats", [])
    if not_eval:
        lines.append(f"### Not Evaluated (timed out): {', '.join(not_eval)}\n")

    # Findings details
    if consolidated["all_findings"]:
        lines.append("### Findings\n")
        for i, finding in enumerate(consolidated["all_findings"], 1):
            sev = finding.get("severity", "LOW")
            conflict_marker = " [CONFLICT]" if finding.get("conflicted") else ""
            lines.append(f"#### {i}. [{sev}]{conflict_marker} {finding.get('title', 'Untitled')}")
            lines.append(f"**Source:** {finding.get('source_emoji', '')} {finding.get('source_hat', 'Unknown')}")
            if finding.get("file"):
                loc = f"`{finding['file']}`"
                if finding.get("line"):
                    loc += f" (line {finding['line']})"
                lines.append(f"**Location:** {loc}")
            lines.append(f"\n{finding.get('description', '')}\n")
            if finding.get("recommendation"):
                lines.append(f"**Recommendation:** {finding['recommendation']}\n")

    # Pipeline stats
    lines.append("### Pipeline Stats\n")
    lines.append(f"- **Hats Selected:** {len(selected_hats)}")
    lines.append(f"- **Hats Executed:** {consolidated['hats_executed']}")
    lines.append(f"- **Hats Failed:** {consolidated['hats_failed']}")
    total_tok = consolidated["total_tokens"]
    lines.append(f"- **Total Tokens:** {total_tok['input'] + total_tok['output']:,}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main orchestrator — the Conductor
# ---------------------------------------------------------------------------

def run_pipeline(diff_text: str, config: dict, requested_hats: list[str] | None = None,
                 context: str = "", output_format: str = "both",
                 run_id: str | None = None,
                 resumed_state: dict | None = None,
                 checkpoint_dir: str = ".hats/checkpoints") -> dict:
    """Run the full Hats pipeline:

    select -> G1 (cost budget) -> sensitive mode detect -> dispatch -> G2/G4 ->
    consolidate + G3 -> CoVE -> G5 -> output

    Implements the full Conductor flow with cloud/local concurrency orchestration.

    If resumed_state is provided, skips already-completed/failed/timed-out hats
    and only runs the pending ones from a checkpoint.
    """
    # Extract changed files from diff for dependency analysis
    changed_files = _extract_changed_files(diff_text)

    # Step 1: Select hats (4-layer algorithm via hat_selector.py)
    selected = select_hats(config, diff_text, requested_hats, changed_files)
    print(f"Selected {len(selected)} hats: {', '.join(selected)}", file=sys.stderr)

    # Step 2: Detect sensitive mode
    sensitive_mode = detect_sensitive_mode(diff_text, changed_files)
    if sensitive_mode:
        print("SENSITIVE MODE: credential/PII content detected. "
              "Dual-mode hats will use local models.", file=sys.stderr)

    # Step 3: Cost Budget Gate (G1) — block or trim, not silently continue
    diff_tokens = len(diff_text) // 4
    budget_result = gate_cost_budget(config, selected, diff_tokens)
    print(f"Cost estimate: ${budget_result['estimated_cost']:.4f} "
          f"(budget: ${budget_result['budget_limit']}) "
          f"{'PASS' if budget_result['verdict'] == 'PASS' else budget_result['verdict']}",
          file=sys.stderr)

    if budget_result["verdict"] == "BLOCKED":
        # Budget gate blocks — return error instead of silently trimming
        print("BUDGET GATE BLOCKED: Even after trimming all conditional hats, "
              "the pipeline exceeds budget.", file=sys.stderr)
        return {
            "verdict": "BLOCKED",
            "risk_score": 100,
            "error": "Budget gate blocked — pipeline cost exceeds budget even with only mandatory hats",
            "budget_result": budget_result,
            "markdown": "# Budget Gate Blocked\n\nThe pipeline cost exceeds the configured budget "
                        "even after trimming all conditional hats. Review the diff size or increase the budget.",
            "json_report": {
                "verdict": "BLOCKED",
                "risk_score": 100,
                "error": "Budget gate blocked",
                "budget_result": budget_result,
            },
            "consolidated": {},
        }

    if budget_result["verdict"] == "TRIMMED":
        selected = budget_result["selected_hats"]
        print(f"Budget gate trimmed to {len(selected)} hats. "
              f"Removed: {', '.join(budget_result['trimmed_hats'])}", file=sys.stderr)

    # Initialize run state (or resume from checkpoint)
    if resumed_state:
        state = resumed_state
        run_id = state["run_id"]
        # Only run hats that haven't completed/failed/timed out
        pending = get_pending_hats(state)
        # Filter selected to only pending hats, preserving order
        selected = [h for h in selected if h in pending]
        if not selected:
            print("Resume: all hats already completed. Nothing to run.", file=sys.stderr)
            # Re-consolidate existing findings and return
            existing_reports = state.get("findings", [])
            consolidated = consolidate_findings(
                [{"hat_id": f.get("source_hat", "?"), "findings": [f]} for f in existing_reports],
                timed_out_hats=state.get("timed_out_hats", [])
            )
            risk_score, verdict = compute_risk_score(config, consolidated["severity_counts"])
            markdown = generate_markdown_report(consolidated, risk_score, verdict or "ALLOW",
                                               state.get("triggered_hats", []), config,
                                               state.get("sensitive_mode", False))
            return {
                "verdict": state.get("verdict", verdict),
                "risk_score": state.get("risk_score", risk_score),
                "markdown": markdown,
                "json_report": {"verdict": state.get("verdict", verdict), "risk_score": risk_score},
                "consolidated": consolidated,
            }
        print(f"Resume: running {len(selected)} pending hats: {', '.join(selected)}", file=sys.stderr)
    else:
        if not run_id:
            run_id = time.strftime("run-%Y%m%d-%H%M%S", time.gmtime())
        state = create_initial_state(
            run_id=run_id,
            trigger_type="manual",
            diff_content=diff_text[:500],  # Don't store the full diff in state
            changed_files=changed_files,
            triggered_hats=selected,
            sensitive_mode=sensitive_mode,
        )
        update_state(state, gate={"gate_id": "G1", "passed": True, "details": budget_result})

    # Step 4: Set up concurrency coordinator
    exec_cfg = config.get("execution", {})
    max_cloud = exec_cfg.get("max_cloud_parallel", 4)
    if budget_result["verdict"] == "TRIMMED":
        max_cloud = exec_cfg.get("trio_mode_cloud", 3)  # Tight budget -> trio mode

    coordinator = ConcurrencyCoordinator(max_cloud=max_cloud)
    coordinator.start()

    # Step 5: Separate hats into cloud and local pools
    pre_gold = [h for h in selected if h != "gold"]
    cloud_hats = []
    local_hats = []
    for hat_id in pre_gold:
        hat_type = coordinator.classify_hat(config, hat_id, sensitive_mode)
        if hat_type == "local":
            local_hats.append(hat_id)
        else:
            cloud_hats.append(hat_id)

    print(f"Dispatching: {len(cloud_hats)} cloud hats (parallel), "
          f"{len(local_hats)} local hats (sequential)", file=sys.stderr)

    # Step 6: Execute hats with concurrency orchestration
    reports = []
    security_fast_path_triggered = False
    timed_out_hats = []

    # Run cloud hats in parallel via the cloud pool
    cloud_futures = {}
    for hat_id in cloud_hats:
        future = coordinator.cloud_pool.submit(
            run_hat, config, hat_id, diff_text, context, sensitive_mode, coordinator
        )
        cloud_futures[future] = hat_id

    # Run local hats sequentially via the local queue
    # (they'll acquire the lock inside run_hat)
    local_futures = {}
    for hat_id in local_hats:
        future = coordinator.cloud_pool.submit(
            run_hat, config, hat_id, diff_text, context, sensitive_mode, coordinator
        )
        local_futures[future] = hat_id

    # Collect all results
    all_futures = {**cloud_futures, **local_futures}
    for future in as_completed(all_futures):
        hat_id = all_futures[future]
        try:
            report = future.result()
        except Exception as exc:
            report = {
                "hat_id": hat_id,
                "hat_name": config["hats"][hat_id]["name"],
                "emoji": config["hats"][hat_id]["emoji"],
                "model_used": "N/A",
                "latency_seconds": 0,
                "token_usage": {"input": 0, "output": 0},
                "error": str(exc),
                "findings": [],
                "summary": "",
                "confidence": 0.0,
                "timed_out": False,
            }
        reports.append(report)

        # Update state
        if report.get("timed_out"):
            update_state(state, timed_out_hat=hat_id)
            timed_out_hats.append(hat_id)
        elif report.get("error"):
            update_state(state, failed_hat=hat_id)
        else:
            update_state(state, completed_hat=hat_id)

        print(f"  {report['emoji']} {report['hat_name']}: "
              f"{len(report['findings'])} findings, {report['latency_seconds']:.1f}s"
              + (f" ERROR: {report['error']}" if report['error'] else ""),
              file=sys.stderr)

        # Security fast-path gate (G2)
        g2_result = gate_security_fast_path(config, report)
        if g2_result["triggered"]:
            security_fast_path_triggered = True
            update_state(state, gate={"gate_id": "G2", "passed": False, "details": g2_result})
            print("CRITICAL finding detected -- security fast-path triggered",
                  file=sys.stderr)
            # Don't break — let running hats finish, but skip remaining unstarted ones

    coordinator.shutdown()

    # Step 7: Run Gold/CoVE last (always)
    if "gold" in selected:
        cove_context = json.dumps({
            "prior_hat_reports": [
                {
                    "hat": r["hat_name"],
                    "findings": r["findings"],
                    "summary": r["summary"],
                    "confidence": r["confidence"],
                }
                for r in reports
            ],
            "security_fast_path_triggered": security_fast_path_triggered,
            "sensitive_mode": sensitive_mode,
        }, indent=2)

        gold_report = run_hat(config, "gold", diff_text, context=cove_context,
                              sensitive_mode=False)
        reports.append(gold_report)
        update_state(state, completed_hat="gold")
        print(f"  {gold_report['emoji']} {gold_report['hat_name']}: "
              f"{len(gold_report['findings'])} findings, {gold_report['latency_seconds']:.1f}s",
              file=sys.stderr)

    # Step 8: Consolidate findings with deduplication (SPEC §9.3)
    consolidated = consolidate_findings(reports, timed_out_hats=timed_out_hats)

    # Step 9: Consistency Gate (G3)
    g3_result = gate_consistency(consolidated["all_findings"])
    update_state(state, gate={"gate_id": "G3", "passed": g3_result["verdict"] == "PASS",
                              "details": {"contradictions": len(g3_result["contradictions"])}})

    if g3_result["verdict"] == "CONFLICTS_DETECTED":
        print(f"Consistency gate: {len(g3_result['contradictions'])} contradictions detected "
              f"(flagged for CoVE resolution)", file=sys.stderr)

    # Step 10: Compute risk score and verdict
    risk_score, verdict = compute_risk_score(config, consolidated["severity_counts"])

    # Step 11: Final Decision Gate (G5)
    g5_result = gate_final_decision(verdict, risk_score, config,
                                    security_fast_path_triggered)
    update_state(state, verdict=g5_result["verdict"], risk_score=risk_score,
                 gate={"gate_id": "G5", "passed": g5_result["verdict"] == "ALLOW",
                       "details": g5_result})

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"VERDICT: {g5_result['verdict']} (Risk Score: {risk_score}/100)", file=sys.stderr)
    if g5_result["requires_human_review"]:
        print(f"ACTION: {g5_result['action']}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    # Finalize and save state
    finalize_state(state)
    save_checkpoint(state, checkpoint_dir)

    # Step 12: Generate outputs
    markdown = generate_markdown_report(consolidated, risk_score, g5_result["verdict"],
                                       selected, config, sensitive_mode)

    json_report = {
        "verdict": g5_result["verdict"],
        "risk_score": risk_score,
        "severity_counts": consolidated["severity_counts"],
        "hats_executed": consolidated["hats_executed"],
        "hats_failed": consolidated["hats_failed"],
        "total_tokens": consolidated["total_tokens"],
        "hat_summaries": consolidated["hat_summaries"],
        "findings": consolidated["all_findings"],
        "security_fast_path_triggered": security_fast_path_triggered,
        "sensitive_mode": sensitive_mode,
        "dedup_stats": consolidated.get("dedup_stats", {}),
        "conflicts": consolidated.get("conflicts", []),
        "not_evaluated_hats": consolidated.get("not_evaluated_hats", []),
    }

    return {
        "verdict": g5_result["verdict"],
        "risk_score": risk_score,
        "markdown": markdown,
        "json_report": json_report,
        "consolidated": consolidated,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Hats Team Runner -- run the Hats review pipeline on a diff"
    )
    parser.add_argument(
        "--diff", required=True,
        help="Path to diff file, or '-' to read from stdin"
    )
    parser.add_argument(
        "--config", default=str(DEFAULT_CONFIG),
        help="Path to hat_configs.yml (default: scripts/hat_configs.yml)"
    )
    parser.add_argument(
        "--hats", default=None,
        help="Comma-separated list of hat IDs to run (e.g., 'black,blue,purple'). "
             "Default: auto-select based on diff triggers."
    )
    parser.add_argument(
        "--context", default="",
        help="Additional context to include in hat prompts (e.g., PR description)"
    )
    parser.add_argument(
        "--output", choices=["json", "markdown", "both"], default="both",
        help="Output format (default: both)"
    )
    parser.add_argument(
        "--json-file", default=None,
        help="Path to write JSON report"
    )
    parser.add_argument(
        "--markdown-file", default=None,
        help="Path to write Markdown report"
    )
    parser.add_argument(
        "--run-id", default=None,
        help="Run ID for state tracking"
    )
    parser.add_argument(
        "--resume", default=None, metavar="RUN_ID",
        help="Resume a previous run from its checkpoint. Only pending hats will run."
    )
    parser.add_argument(
        "--checkpoint-dir", default=".hats/checkpoints",
        help="Directory for checkpoint files (default: .hats/checkpoints)"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Quiet mode: only print verdict, risk score, and report path. Useful for CI pipelines."
    )

    args = parser.parse_args()

    # Load config first (needed for preflight to know if cloud models are required)
    config = load_config(args.config)

    # Preflight health check
    requested_hat_ids = [h.strip() for h in args.hats.split(",")] if args.hats else None
    issues = preflight_check(config, requested_hats=requested_hat_ids)
    has_errors = any(msg.upper().startswith("ERROR:") for msg in issues)
    for msg in issues:
        print(msg, file=sys.stderr)
    if has_errors:
        print("\nCannot proceed -- fix the errors above and try again.", file=sys.stderr)
        print("See FORK_SETUP.md for setup instructions.", file=sys.stderr)
        sys.exit(2)

    # Read diff
    if args.diff == "-":
        diff_text = sys.stdin.read()
    else:
        with open(args.diff, "r", encoding="utf-8") as fh:
            diff_text = fh.read()

    if not diff_text.strip():
        print("Empty diff -- nothing to review.", file=sys.stderr)
        sys.exit(0)

    # Parse requested hats
    requested_hats = None
    if args.hats:
        requested_hats = [h.strip() for h in args.hats.split(",")]

    # Resume from checkpoint if requested
    resumed_state = None
    if args.resume:
        resumed_state = load_checkpoint(args.resume, args.checkpoint_dir)
        if not resumed_state:
            print(f"No checkpoint found for run_id: {args.resume}", file=sys.stderr)
            sys.exit(2)
        # Use the diff from the checkpoint if no new diff provided
        if args.diff == "-" and resumed_state.get("diff_content"):
            diff_text = resumed_state["diff_content"]
        print(f"Resuming run {args.resume} from checkpoint", file=sys.stderr)

    # Run pipeline
    result = run_pipeline(diff_text, config, requested_hats=requested_hats,
                          context=args.context, output_format=args.output,
                          run_id=args.run_id, resumed_state=resumed_state,
                          checkpoint_dir=args.checkpoint_dir)

    # Output results
    if args.quiet:
        # Quiet mode: only print verdict, risk score, and report path
        verdict = result["verdict"]
        risk = result["risk_score"]
        hats = result["consolidated"].get("hats_executed", 0)
        print(f"{verdict} risk={risk}/100 hats={hats}")
        if args.json_file:
            print(f"report={args.json_file}", file=sys.stderr)
        elif args.markdown_file:
            print(f"report={args.markdown_file}", file=sys.stderr)
    else:
        if args.output in ("markdown", "both"):
            if args.markdown_file:
                with open(args.markdown_file, "w", encoding="utf-8") as fh:
                    fh.write(result["markdown"])
            else:
                print(result["markdown"].encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace"))

        if args.output in ("json", "both"):
            json_str = json.dumps(result["json_report"], indent=2)
            if args.json_file:
                with open(args.json_file, "w", encoding="utf-8") as fh:
                    fh.write(json_str)
            elif args.output == "json":
                print(json_str)

    # Set GitHub Actions outputs if running in CI
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write(f"verdict={result['verdict']}\n")
            fh.write(f"risk_score={result['risk_score']}\n")
            fh.write(f"hats_executed={result['consolidated'].get('hats_executed', 0)}\n")

    # Exit code: 0 for ALLOW, 1 for ESCALATE/QUARANTINE/BLOCKED
    if result["verdict"] != "ALLOW":
        sys.exit(1)


if __name__ == "__main__":
    main()