#!/usr/bin/env python3
"""
🎩 Hats Team Runner — GitHub Actions Orchestrator

Implements the Conductor logic from the Hats Team Specification:
  - Hat selection based on diff triggers
  - Tiered-parallel execution via Ollama Cloud API
  - Gate engine (cost budget, security fast-path, timeout)
  - Consolidation and Gold Hat (CoVE) final adjudication
  - Structured JSON + Markdown report output

Usage:
  python hats_runner.py --diff <diff_text_or_file> [--hats black,blue,...] [--config hat_configs.yml]

Environment:
  OLLAMA_API_KEY   — Ollama Cloud API key (required)
  OLLAMA_BASE_URL  — API base URL (default: https://api.ollama.ai/v1)
"""

import argparse
import json
import os
import re
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR / "hat_configs.yml"

# ---------------------------------------------------------------------------
# Preflight health check — clear errors for missing configuration
# ---------------------------------------------------------------------------

def preflight_check() -> list[str]:
    """Check that required environment is configured.

    Returns a list of warning/error messages. Empty list = all good.
    """
    issues = []

    api_key = os.environ.get("OLLAMA_API_KEY", "").strip()
    if not api_key:
        issues.append(
            "❌ OLLAMA_API_KEY is not set.\n"
            "   → For GitHub Actions: Add it as a Repository Secret\n"
            "     (Settings → Secrets and variables → Actions → New repository secret)\n"
            "   → For local use: Copy .env.example to .env and fill in your key\n"
            "   → Get a key at: https://ollama.ai/cloud"
        )

    base_url = os.environ.get("OLLAMA_BASE_URL", "").strip()
    if not base_url:
        # Not an error — we have a default
        issues.append(
            "ℹ️  OLLAMA_BASE_URL not set — using default: https://api.ollama.ai/v1"
        )

    return issues


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config(config_path: str | Path) -> dict:
    """Load hat configuration from YAML file."""
    with open(config_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Hat selector — determines which hats to run based on diff content
# ---------------------------------------------------------------------------

def select_hats(config: dict, diff_text: str, requested_hats: list[str] | None = None) -> list[str]:
    """Select hats to run based on diff content triggers (per SPEC.md §6).

    Always-run hats (Black, Blue, Purple, Gold) are always included.
    Conditional hats activate when their trigger keywords appear in the diff.
    If requested_hats is provided, only those hats (plus always-run) are used.
    """
    hats_cfg = config["hats"]
    selected = []
    diff_lower = diff_text.lower()

    for hat_id, hat_def in hats_cfg.items():
        # Always-run hats are mandatory
        if hat_def.get("always_run"):
            selected.append(hat_id)
            continue

        # If caller requested specific hats, only include those
        if requested_hats and hat_id not in requested_hats:
            continue

        # Check trigger keywords against diff content
        triggers = hat_def.get("triggers", [])
        if any(trigger.lower() in diff_lower for trigger in triggers):
            selected.append(hat_id)

    # Gold/CoVE must always run last — ensure it's at the end
    if "gold" in selected:
        selected.remove("gold")
        selected.append("gold")

    return selected


# ---------------------------------------------------------------------------
# Cost estimation gate (G1)
# ---------------------------------------------------------------------------

def estimate_cost(config: dict, selected_hats: list[str], diff_tokens: int) -> tuple[float, bool]:
    """Estimate pipeline cost and check against budget gate.

    Returns (estimated_cost_usd, within_budget).
    """
    models_cfg = config["models"]
    hats_cfg = config["hats"]
    budget = config["gates"]["cost_budget"]["max_usd_per_pr"]

    total_cost = 0.0
    for hat_id in selected_hats:
        hat_def = hats_cfg[hat_id]
        model_name = hat_def["primary_model"]
        model_cfg = models_cfg.get(model_name, {})

        # Estimate: input = diff_tokens + ~500 (system prompt), output = max_tokens
        input_tokens = min(diff_tokens + 500, model_cfg.get("context_window", 128000))
        output_tokens = hat_def.get("max_tokens", 4096)

        input_cost = (input_tokens / 1_000_000) * model_cfg.get("input_cost_per_m", 0.20)
        output_cost = (output_tokens / 1_000_000) * model_cfg.get("output_cost_per_m", 0.80)
        total_cost += input_cost + output_cost

    return total_cost, total_cost <= budget


# ---------------------------------------------------------------------------
# Ollama Cloud API caller
# ---------------------------------------------------------------------------

def call_ollama(config: dict, model: str, system_prompt: str, user_prompt: str,
                temperature: float = 0.3, max_tokens: int = 4096,
                timeout: int = 120) -> dict:
    """Call the Ollama Cloud OpenAI-compatible chat completions endpoint."""
    api_cfg = config["api"]
    base_url = os.environ.get(
        api_cfg.get("base_url_env", "OLLAMA_BASE_URL"),
        api_cfg.get("default_base_url", "https://api.ollama.ai/v1"),
    )
    api_key = os.environ.get(
        api_cfg.get("api_key_env", "OLLAMA_API_KEY"), ""
    )

    if not api_key:
        return {
            "error": "OLLAMA_API_KEY not set",
            "model": model,
            "content": None,
            "usage": {"input": 0, "output": 0},
        }

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        choice = data.get("choices", [{}])[0]
        usage = data.get("usage", {})
        return {
            "error": None,
            "model": model,
            "content": choice.get("message", {}).get("content", ""),
            "usage": {
                "input": usage.get("prompt_tokens", 0),
                "output": usage.get("completion_tokens", 0),
            },
        }
    except requests.exceptions.Timeout:
        return {
            "error": f"Timeout after {timeout}s",
            "model": model,
            "content": None,
            "usage": {"input": 0, "output": 0},
        }
    except requests.exceptions.RequestException as exc:
        return {
            "error": str(exc),
            "model": model,
            "content": None,
            "usage": {"input": 0, "output": 0},
        }


# ---------------------------------------------------------------------------
# Single hat execution
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
      "recommendation": "<actionable fix>"
    }
  ],
  "summary": "<one-paragraph summary>",
  "confidence": <0.0-1.0>
}
"""


def run_hat(config: dict, hat_id: str, diff_text: str, context: str = "") -> dict:
    """Execute a single hat analysis against the diff.

    Returns the hat's structured report or an error report.
    """
    hats_cfg = config["hats"]
    hat_def = hats_cfg[hat_id]

    system_prompt = hat_def["persona"].strip() + "\n\n" + _FINDING_SCHEMA

    user_prompt = f"## Code Diff to Analyze\n\n```diff\n{diff_text}\n```"
    if context:
        user_prompt = f"## Additional Context\n\n{context}\n\n{user_prompt}"

    model = hat_def["primary_model"]
    temperature = hat_def.get("temperature", 0.3)
    max_tokens = hat_def.get("max_tokens", 4096)
    timeout = hat_def.get("timeout_seconds", 120)

    start = time.time()
    result = call_ollama(config, model, system_prompt, user_prompt,
                         temperature=temperature, max_tokens=max_tokens,
                         timeout=timeout)
    elapsed = time.time() - start

    # If primary fails, try fallback
    if result["error"] and hat_def.get("fallback_model"):
        fallback = hat_def["fallback_model"]
        result = call_ollama(config, fallback, system_prompt, user_prompt,
                             temperature=temperature, max_tokens=max_tokens,
                             timeout=timeout)
        elapsed = time.time() - start

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
    }

    if result["content"]:
        try:
            parsed = json.loads(result["content"])
            report["findings"] = parsed.get("findings", [])
            report["summary"] = parsed.get("summary", "")
            report["confidence"] = parsed.get("confidence", 0.0)
        except json.JSONDecodeError:
            # Model didn't return valid JSON — wrap the raw text as a single finding
            report["findings"] = [{
                "severity": "LOW",
                "title": "Unstructured response",
                "description": result["content"][:2000],
                "file": None,
                "line": None,
                "recommendation": "Review raw model output",
            }]
            report["summary"] = "Model returned unstructured response"

    return report


# ---------------------------------------------------------------------------
# Consolidator — merge all hat reports
# ---------------------------------------------------------------------------

def consolidate_reports(reports: list[dict]) -> dict:
    """Merge all hat reports into a single consolidated report.

    Aggregates findings from all hats and tallies severities.
    """
    all_findings = []
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    hat_summaries = []
    total_tokens = {"input": 0, "output": 0}
    total_cost = 0.0

    for report in reports:
        hat_summaries.append({
            "hat": report["hat_name"],
            "emoji": report["emoji"],
            "model": report["model_used"],
            "latency_s": report["latency_seconds"],
            "findings_count": len(report["findings"]),
            "error": report.get("error"),
        })

        total_tokens["input"] += report["token_usage"]["input"]
        total_tokens["output"] += report["token_usage"]["output"]

        for finding in report["findings"]:
            severity = finding.get("severity", "LOW").upper()
            if severity in severity_counts:
                severity_counts[severity] += 1

            finding_with_source = dict(finding)
            finding_with_source["source_hat"] = report["hat_name"]
            finding_with_source["source_emoji"] = report["emoji"]
            all_findings.append(finding_with_source)

    return {
        "hat_summaries": hat_summaries,
        "all_findings": all_findings,
        "severity_counts": severity_counts,
        "total_tokens": total_tokens,
        "hats_executed": len(reports),
        "hats_failed": sum(1 for r in reports if r.get("error")),
    }


# ---------------------------------------------------------------------------
# Risk score calculator (per CATALOG.md formula)
# ---------------------------------------------------------------------------

def compute_risk_score(config: dict, severity_counts: dict) -> tuple[int, str]:
    """Compute composite risk score and verdict per CATALOG.md formula.

    Returns (score, verdict) where verdict is ALLOW, ESCALATE, or QUARANTINE.
    """
    rs = config.get("risk_score", {})

    # Any CRITICAL → automatic QUARANTINE
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
                             selected_hats: list[str], config: dict) -> str:
    """Generate a Markdown summary report suitable for PR comments."""
    lines = []
    lines.append("# 🎩 Hats Team Review Report\n")

    # Verdict banner
    emoji_map = {"ALLOW": "✅", "ESCALATE": "⚠️", "QUARANTINE": "🚫"}
    lines.append(f"## {emoji_map.get(verdict, '❓')} Verdict: **{verdict}** (Risk Score: {risk_score}/100)\n")

    # Severity summary
    sc = consolidated["severity_counts"]
    lines.append("### Severity Summary\n")
    lines.append(f"| Severity | Count |")
    lines.append(f"|----------|-------|")
    lines.append(f"| 🔴 CRITICAL | {sc['CRITICAL']} |")
    lines.append(f"| 🟠 HIGH | {sc['HIGH']} |")
    lines.append(f"| 🟡 MEDIUM | {sc['MEDIUM']} |")
    lines.append(f"| 🟢 LOW | {sc['LOW']} |")
    lines.append("")

    # Hat execution summary
    lines.append("### Hat Execution Summary\n")
    lines.append("| Hat | Model | Latency | Findings | Status |")
    lines.append("|-----|-------|---------|----------|--------|")
    for hs in consolidated["hat_summaries"]:
        status = "❌ Error" if hs["error"] else "✅ OK"
        lines.append(
            f"| {hs['emoji']} {hs['hat']} | `{hs['model']}` | "
            f"{hs['latency_s']:.1f}s | {hs['findings_count']} | {status} |"
        )
    lines.append("")

    # Findings details
    if consolidated["all_findings"]:
        lines.append("### Findings\n")
        for i, finding in enumerate(consolidated["all_findings"], 1):
            sev = finding.get("severity", "LOW")
            sev_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(sev, "⚪")
            lines.append(f"#### {i}. {sev_emoji} [{sev}] {finding.get('title', 'Untitled')}")
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
    lines.append(f"- **Total Tokens:** {consolidated['total_tokens']['input'] + consolidated['total_tokens']['output']:,}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_pipeline(diff_text: str, config: dict, requested_hats: list[str] | None = None,
                 context: str = "", output_format: str = "both") -> dict:
    """Run the full Hats pipeline: select → estimate → execute → consolidate → adjudicate.

    Returns a dict with keys: verdict, risk_score, markdown, json_report, consolidated.
    """
    # Step 1: Select hats
    selected = select_hats(config, diff_text, requested_hats)
    print(f"🎩 Selected {len(selected)} hats: {', '.join(selected)}", file=sys.stderr)

    # Step 2: Cost estimation gate (G1)
    # Rough token estimate: ~4 chars per token
    diff_tokens = len(diff_text) // 4
    est_cost, within_budget = estimate_cost(config, selected, diff_tokens)
    print(f"💰 Estimated cost: ${est_cost:.4f} (budget: ${config['gates']['cost_budget']['max_usd_per_pr']}) "
          f"{'✅ PASS' if within_budget else '⚠️ OVER BUDGET'}", file=sys.stderr)

    if not within_budget:
        # Drop lowest-priority (Tier 4) conditional hats to fit budget
        always_hats = {h for h, d in config["hats"].items() if d.get("always_run")}
        selected = [h for h in selected if h in always_hats or
                    config["hats"][h].get("primary_model") != "nemotron-3-nano"]
        print(f"🎩 Trimmed to {len(selected)} hats after budget gate", file=sys.stderr)

    # Step 3: Execute hats (tiered parallel — per SPEC.md §6)
    # Separate Gold/CoVE (must run last) from the rest
    pre_gold = [h for h in selected if h != "gold"]
    max_workers = config["execution"]["max_concurrent_hats"]

    reports = []
    security_fast_path = False

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(run_hat, config, hat_id, diff_text, context): hat_id
                   for hat_id in pre_gold}

        for future in as_completed(futures):
            hat_id = futures[future]
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
                }
            reports.append(report)
            print(f"  {report['emoji']} {report['hat_name']}: "
                  f"{len(report['findings'])} findings, {report['latency_seconds']:.1f}s"
                  + (f" ⚠️ {report['error']}" if report['error'] else ""),
                  file=sys.stderr)

            # Security fast-path gate (G2) — per SPEC.md §7
            if config["gates"]["security_fast_path"]["enabled"]:
                for finding in report["findings"]:
                    if finding.get("severity", "").upper() == "CRITICAL":
                        security_fast_path = True
                        print("🚨 CRITICAL finding detected — security fast-path triggered",
                              file=sys.stderr)

    # Step 4: Run Gold/CoVE last (always)
    if "gold" in selected:
        # Build CoVE context from all prior reports
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
            "security_fast_path_triggered": security_fast_path,
        }, indent=2)

        gold_report = run_hat(config, "gold", diff_text, context=cove_context)
        reports.append(gold_report)
        print(f"  {gold_report['emoji']} {gold_report['hat_name']}: "
              f"{len(gold_report['findings'])} findings, {gold_report['latency_seconds']:.1f}s",
              file=sys.stderr)

    # Step 5: Consolidate
    consolidated = consolidate_reports(reports)

    # Step 6: Compute risk score and verdict
    risk_score, verdict = compute_risk_score(config, consolidated["severity_counts"])
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"🎩 VERDICT: {verdict} (Risk Score: {risk_score}/100)", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    # Step 7: Generate outputs
    markdown = generate_markdown_report(consolidated, risk_score, verdict, selected, config)

    json_report = {
        "verdict": verdict,
        "risk_score": risk_score,
        "severity_counts": consolidated["severity_counts"],
        "hats_executed": consolidated["hats_executed"],
        "hats_failed": consolidated["hats_failed"],
        "total_tokens": consolidated["total_tokens"],
        "hat_summaries": consolidated["hat_summaries"],
        "findings": consolidated["all_findings"],
        "security_fast_path_triggered": security_fast_path,
    }

    return {
        "verdict": verdict,
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
        description="🎩 Hats Team Runner — run the Hats review pipeline on a diff"
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

    args = parser.parse_args()

    # Preflight health check — fail fast with clear guidance
    issues = preflight_check()
    has_errors = any(msg.startswith("❌") for msg in issues)
    for msg in issues:
        print(msg, file=sys.stderr)
    if has_errors:
        print("\n🛑 Cannot proceed — fix the errors above and try again.", file=sys.stderr)
        print("   See FORK_SETUP.md for setup instructions.", file=sys.stderr)
        sys.exit(2)

    # Load config
    config = load_config(args.config)

    # Read diff
    if args.diff == "-":
        diff_text = sys.stdin.read()
    else:
        with open(args.diff, "r", encoding="utf-8") as fh:
            diff_text = fh.read()

    if not diff_text.strip():
        print("⚠️ Empty diff — nothing to review.", file=sys.stderr)
        sys.exit(0)

    # Parse requested hats
    requested_hats = None
    if args.hats:
        requested_hats = [h.strip() for h in args.hats.split(",")]

    # Run pipeline
    result = run_pipeline(diff_text, config, requested_hats=requested_hats,
                          context=args.context, output_format=args.output)

    # Output results
    if args.output in ("markdown", "both"):
        if args.markdown_file:
            with open(args.markdown_file, "w", encoding="utf-8") as fh:
                fh.write(result["markdown"])
        else:
            print(result["markdown"])

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
            fh.write(f"hats_executed={result['consolidated']['hats_executed']}\n")

    # Exit code: 0 for ALLOW, 1 for ESCALATE/QUARANTINE
    if result["verdict"] != "ALLOW":
        sys.exit(1)


if __name__ == "__main__":
    main()
