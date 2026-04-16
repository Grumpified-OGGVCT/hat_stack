#!/usr/bin/env python3
"""
gremlin_runner.py -- Multi-repo overnight Gremlin orchestrator for Hat Stack.

Four-phase overnight loop using hat-based execution:
  Phase 1 (2 AM): Review Queue -- Black Hat scans recent git diffs per repo
  Phase 2 (3 AM): Proposals -- Gold Hat synthesizes findings into governance proposals
  Phase 3 (4 AM): Deep Analysis -- Purple Hat (or dynamically selected hat) analyzes APPROVED proposals
  Phase 4 (5 AM): Herald Summary -- Blue Hat composes cross-repo daily digest

Each phase uses the hat's persona, model chain with fallback, and sensitive mode detection.
Overnight mode upgrades to larger local models with extended timeouts.

Multi-repo: Scans all repos configured in hat_configs.yml gremlins.repos.
Per-repo findings go to .gremlins/repos/<name>/, cross-repo Herald to .gremlins/herald/.

Usage:
  python scripts/gremlin_runner.py --all
  python scripts/gremlin_runner.py --phase review
  python scripts/gremlin_runner.py --repo GrumpRolled --phase review
  python scripts/gremlin_runner.py --repos-only
  python scripts/gremlin_runner.py --overnight --status
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from hats_common import (
    load_config,
    call_ollama,
    detect_sensitive_mode,
    try_model_chain,
    is_overnight_mode,
    get_overnight_timeout,
    resolve_gremlin_model,
    send_wake_on_lan,
    DEFAULT_CONFIG,
    preflight_check,
)
from gremlin_memory import (
    init_gremlin_memory,
    init_gremlin_memory_global,
    list_repos,
    write_ledger_entry,
    read_ledger,
    read_ledger_all_repos,
    create_proposal,
    list_proposals,
    list_proposals_all_repos,
    expire_stale_proposals,
    write_herald,
    read_herald,
    GREMLIN_SIGNOFF,
)
from moltbook_auth import (
    verify_moltbook_identity,
    extract_moltbook_identity,
    format_agent_identity,
)
from hat_selector import select_hats
from gates import gate_governance

__all__ = [
    "phase_review", "phase_propose", "phase_analyze", "phase_herald",
    "show_status", "_resolve_phase_hat",
]

SCRIPT_DIR = Path(__file__).resolve().parent

# JSON output format for gremlin findings
_GREMLIN_FINDING_SCHEMA = """\
Respond with a JSON object:
{"findings": [{"severity": "HIGH|MEDIUM|LOW", "title": "...", "description": "...", "file": "...", "recommendation": "..."}], "summary": "..."}

Sign off with: -- Gremlin Legion
"""

# JSON output format for proposals
_GREMLIN_PROPOSAL_SCHEMA = """\
Respond with a JSON object:
{"proposals": [{"title": "...", "description": "...", "proposed_action": "...", "priority": "HIGH|MEDIUM|LOW"}]}

Only propose actions for findings that are HIGH or CRITICAL severity.
Low and MEDIUM findings should be logged but not proposed.

Sign off with: -- Gremlin Legion
"""

# JSON output format for analysis
_GREMLIN_ANALYSIS_SCHEMA = """\
Respond with a JSON object:
{"analysis": "...", "action_plan": [{"step": 1, "action": "..."}], "risks": ["..."], "estimated_effort": "LOW|MEDIUM|HIGH"}

Sign off with: -- Gremlin Legion
"""

# JSON output format for herald digest
_GREMLIN_HERALD_SCHEMA = """\
Respond with a JSON object:
{"headline": "...", "digest": "...", "action_items": ["..."]}

Sign off with: -- Gremlin Legion
"""


def _resolve_phase_hat(config: dict, phase: str) -> str:
    """Resolve which hat a gremlin phase uses."""
    phase_to_hat = config.get("gremlins", {}).get("phase_to_hat", {})
    default_map = {"review": "black", "propose": "gold", "analyze": "purple", "herald": "blue"}
    return phase_to_hat.get(phase, default_map.get(phase, "blue"))


def _get_hat_config(config: dict, hat_id: str) -> dict:
    """Get hat definition from config, with fallback."""
    return config.get("hats", {}).get(hat_id, {})


def _get_configured_repos(config: dict) -> list[dict]:
    """Get the list of configured repos from config.

    Returns list of dicts with 'path' and optional 'enabled', 'skip_phases'.
    Filters out disabled repos.
    """
    repos_cfg = config.get("gremlins", {}).get("repos", [])
    enabled = []
    for repo in repos_cfg:
        if not repo.get("enabled", True):
            continue
        repo_path = repo.get("path", "")
        if not repo_path:
            continue
        if not Path(repo_path).exists():
            print(f"  WARNING: repo path does not exist: {repo_path}", file=sys.stderr)
            continue
        enabled.append(repo)
    return enabled


def _repo_name_from_path(repo_path: str) -> str:
    """Extract repo name from its path (last directory component)."""
    return Path(repo_path).name


# ---------------------------------------------------------------------------
# Phase 1: Review Queue (Black Hat) -- multi-repo
# ---------------------------------------------------------------------------

def phase_review(config: dict, gremlins_root: Path, since: str = "24 hours ago") -> dict:
    """Black Hat scans recent git diffs for each configured repo."""
    hat_id = _resolve_phase_hat(config, "review")
    hat_def = _get_hat_config(config, hat_id)

    repos = _get_configured_repos(config)
    if not repos:
        return {"phase": "review", "status": "skipped", "reason": "No repos configured"}

    repo_results = []
    total_findings = 0

    for repo_cfg in repos:
        repo_path = repo_cfg["path"]
        repo_name = _repo_name_from_path(repo_path)

        # Skip if this repo is excluded from review
        skip_phases = repo_cfg.get("skip_phases", [])
        if "review" in skip_phases:
            continue

        # Initialize per-repo memory
        repo_dir = init_gremlin_memory(gremlins_root.parent, repo_name=repo_name)

        # Get recent diffs from THIS repo
        since_arg = since if since != "all" else "1970-01-01"
        try:
            result = subprocess.run(
                ["git", "log", f"--since={since_arg}", "--oneline"],
                capture_output=True, text=True, timeout=10,
                cwd=repo_path,
            )
            recent_commits = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            recent_commits = ""

        if not recent_commits:
            repo_results.append({"repo": repo_name, "status": "skipped", "reason": "No commits in last 24h"})
            continue

        # Get the diff for recent changes — dynamically determine diff range
        try:
            # Count total commits to pick a valid base
            count_result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                capture_output=True, text=True, timeout=10,
                cwd=repo_path,
            )
            total_commits = int(count_result.stdout.strip()) if count_result.returncode == 0 else 0
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            total_commits = 0

        try:
            if total_commits <= 1:
                # Only one commit — diff against empty tree
                result = subprocess.run(
                    ["git", "diff", "--root", "HEAD"],
                    capture_output=True, text=True, timeout=10,
                    cwd=repo_path,
                )
            else:
                # Use up to 5 commits back, but never beyond the first commit
                depth = min(5, total_commits - 1)
                result = subprocess.run(
                    ["git", "diff", f"HEAD~{depth}..HEAD"],
                    capture_output=True, text=True, timeout=10,
                    cwd=repo_path,
                )
            recent_diff = result.stdout.strip()[:8000]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            recent_diff = ""

        if not recent_diff:
            repo_results.append({"repo": repo_name, "status": "skipped", "reason": "No diff content"})
            continue

        # Sensitive mode detection
        sensitive_mode = detect_sensitive_mode(recent_diff)
        if sensitive_mode:
            print(f"  [{repo_name}] SENSITIVE MODE: credential/PII content detected", file=sys.stderr)

        # Resolve model
        model = resolve_gremlin_model(config, "review", hat_id)
        if sensitive_mode and hat_id in ("black", "purple", "brown"):
            model = hat_def.get("local_model", model)

        fallback = hat_def.get("fallback_model")
        if sensitive_mode:
            fallback = hat_def.get("local_model", fallback)

        persona = hat_def.get("persona", "You are a security-focused code reviewer.").strip()
        system_prompt = persona + "\n\n" + _GREMLIN_FINDING_SCHEMA

        user_prompt = (
            f"## Repo: {repo_name}\n\n"
            f"## Recent Commits (last 24h)\n```\n{recent_commits}\n```\n\n"
            f"## Recent Diff\n```diff\n{recent_diff}\n```\n\n"
            "Review these changes and identify security issues, bugs, and quality concerns."
        )

        base_timeout = hat_def.get("timeout_seconds", 300)
        timeout = get_overnight_timeout(config, base_timeout)

        result = try_model_chain(
            config, model, fallback, system_prompt, user_prompt,
            temperature=hat_def.get("temperature", 0.2),
            max_tokens=hat_def.get("max_tokens", 4096),
            timeout=timeout,
            hat_id=f"gremlin_{hat_id}",
        )

        if result["error"]:
            repo_results.append({"repo": repo_name, "status": "error", "error": result["error"]})
            continue

        content = result["content"] or ""
        try:
            parsed = json.loads(content)
            summary = parsed.get("summary", "Review completed")
            findings = parsed.get("findings", [])
        except json.JSONDecodeError:
            summary = "Review completed (raw output)"
            findings = []

        # Write findings to per-repo ledger
        finding_lines = [f"**Repo:** {repo_name}\n**Summary:** {summary}\n"]
        for f in findings:
            sev = f.get("severity", "LOW")
            title = f.get("title", "Unknown")
            desc = f.get("description", "")
            rec = f.get("recommendation", "")
            finding_lines.append(f"- **[{sev}]** {title}: {desc}")
            if rec:
                finding_lines.append(f"  - Recommendation: {rec}")

        write_ledger_entry(
            repo_dir, "findings", f"{repo_name} Overnight Review",
            "\n".join(finding_lines), author=hat_id,
        )

        total_findings += len(findings)
        repo_results.append({
            "repo": repo_name,
            "status": "completed",
            "model": result["model"],
            "findings_count": len(findings),
            "summary": summary,
        })

    return {
        "phase": "review",
        "status": "completed" if repo_results else "skipped",
        "hat": hat_id,
        "repos_scanned": len([r for r in repo_results if r["status"] == "completed"]),
        "total_findings": total_findings,
        "repo_results": repo_results,
        "overnight_mode": is_overnight_mode(config),
    }


# ---------------------------------------------------------------------------
# Phase 2: Proposals (Gold Hat) -- reads across repos
# ---------------------------------------------------------------------------

def phase_propose(config: dict, gremlins_root: Path) -> dict:
    """Gold Hat synthesizes findings into governance proposals per repo."""
    hat_id = _resolve_phase_hat(config, "propose")
    hat_def = _get_hat_config(config, hat_id)

    governance_cfg = config.get("gremlins", {}).get("governance", {})
    max_proposals = governance_cfg.get("max_active_proposals", 10)
    ttl = governance_cfg.get("proposal_ttl_hours", 48)

    # Expire stale proposals across all repos
    for repo_info in list_repos(gremlins_root):
        expire_stale_proposals(Path(repo_info["path"]), ttl_hours=ttl)

    # Read recent findings from ALL repos
    all_findings = read_ledger_all_repos(gremlins_root, category="findings")
    if not all_findings:
        return {"phase": "propose", "status": "skipped", "reason": "No findings to propose on"}

    # Check total active proposals across repos
    all_pending = list_proposals_all_repos(gremlins_root, status="PENDING_HUMAN")
    if len(all_pending) >= max_proposals:
        return {
            "phase": "propose", "status": "skipped",
            "reason": f"Max active proposals reached ({max_proposals})",
        }

    # Build context from findings (last 5 per repo, capped)
    findings_by_repo = {}
    for entry in all_findings:
        repo = entry.get("repo", "unknown")
        findings_by_repo.setdefault(repo, []).append(entry)
    findings_text = ""
    for repo_name, entries in findings_by_repo.items():
        findings_text += f"## Repo: {repo_name}\n\n"
        for entry in entries[-3:]:
            findings_text += f"### {entry['title']}\n{entry['content'][:1500]}\n\n"

    model = resolve_gremlin_model(config, "propose", hat_id)
    fallback = hat_def.get("fallback_model")

    persona = hat_def.get("persona", "You are a synthesis and proposal specialist.").strip()
    system_prompt = persona + "\n\n" + _GREMLIN_PROPOSAL_SCHEMA

    user_prompt = (
        f"## Recent Findings (across {len(findings_by_repo)} repos)\n\n{findings_text}\n\n"
        "Based on these findings, create governance proposals for issues that need "
        "human-approved action. Focus on HIGH and CRITICAL findings only."
    )

    base_timeout = hat_def.get("timeout_seconds", 300)
    timeout = get_overnight_timeout(config, base_timeout)

    result = try_model_chain(
        config, model, fallback, system_prompt, user_prompt,
        temperature=hat_def.get("temperature", 0.3),
        max_tokens=hat_def.get("max_tokens", 4096),
        timeout=timeout,
        hat_id=f"gremlin_{hat_id}",
    )

    if result["error"]:
        return {"phase": "propose", "status": "error", "error": result["error"], "model": result["model"]}

    content = result["content"] or ""
    try:
        parsed = json.loads(content)
        raw_proposals = parsed.get("proposals", [])
    except json.JSONDecodeError:
        raw_proposals = []

    # Create proposals in the repo where the first finding was found
    created = []
    slots_left = max_proposals - len(all_pending)
    for prop in raw_proposals[:slots_left]:
        # Find the repo dir for the first repo that has findings
        repo_name = list(findings_by_repo.keys())[0] if findings_by_repo else "unknown"
        repo_dir = init_gremlin_memory(gremlins_root.parent, repo_name=repo_name)
        proposal = create_proposal(
            repo_dir,
            title=prop.get("title", "Untitled proposal"),
            description=prop.get("description", ""),
            proposed_action=prop.get("proposed_action", ""),
            author=hat_id,
        )
        created.append(proposal)

    return {
        "phase": "propose",
        "status": "completed",
        "hat": hat_id,
        "model": result["model"],
        "proposals_created": len(created),
        "overnight_mode": is_overnight_mode(config),
    }


# ---------------------------------------------------------------------------
# Phase 3: Deep Analysis (Purple Hat / dynamic) -- across repos
# ---------------------------------------------------------------------------

def phase_analyze(config: dict, gremlins_root: Path) -> dict:
    """Purple Hat (or dynamically selected hat) analyzes APPROVED proposals across repos."""
    default_hat_id = _resolve_phase_hat(config, "analyze")

    # Get approved proposals from all repos
    all_approved = list_proposals_all_repos(gremlins_root, status="APPROVED")
    if not all_approved:
        return {"phase": "analyze", "status": "skipped", "reason": "No approved proposals"}

    results = []
    for proposal in all_approved:
        # Check governance gate
        gate_result = gate_governance(proposal, config)
        if not gate_result["allowed"]:
            results.append({"proposal_id": proposal["id"], "skipped": True, "reason": gate_result["reason"]})
            continue

        # Dynamic hat selection
        proposal_text = f"{proposal['title']} {proposal.get('description', '')} {proposal.get('proposed_action', '')}"
        suggested_hats = select_hats(config, proposal_text)
        hat_id = default_hat_id
        for h in suggested_hats:
            hat_def_candidate = _get_hat_config(config, h)
            if not hat_def_candidate.get("always_run", False) and h != "gold":
                hat_id = h
                break

        hat_def = _get_hat_config(config, hat_id)

        # Sensitive mode
        proposal_content = proposal.get("description", "") + proposal.get("proposed_action", "")
        sensitive_mode = detect_sensitive_mode(proposal_content)

        model = resolve_gremlin_model(config, "analyze", hat_id)
        if sensitive_mode and hat_id in ("black", "purple", "brown"):
            model = hat_def.get("local_model", model)

        fallback = hat_def.get("fallback_model")
        if sensitive_mode:
            fallback = hat_def.get("local_model", fallback)

        persona = hat_def.get("persona", "You are a deep analysis specialist.").strip()
        system_prompt = persona + "\n\n" + _GREMLIN_ANALYSIS_SCHEMA

        repo_label = proposal.get("repo", "")
        user_prompt = (
            f"## Proposal: {proposal['title']}\n\n"
            f"**Repo:** {repo_label}\n\n"
            f"**Description:** {proposal.get('description', '')}\n\n"
            f"**Proposed Action:** {proposal.get('proposed_action', '')}\n\n"
            "Provide a deep analysis and implementation plan for this proposal."
        )

        base_timeout = hat_def.get("timeout_seconds", 300)
        timeout = get_overnight_timeout(config, base_timeout)

        result = try_model_chain(
            config, model, fallback, system_prompt, user_prompt,
            temperature=hat_def.get("temperature", 0.3),
            max_tokens=hat_def.get("max_tokens", 4096),
            timeout=timeout,
            hat_id=f"gremlin_{hat_id}",
        )

        if result["error"]:
            results.append({"proposal_id": proposal["id"], "error": result["error"]})
            continue

        content = result["content"] or ""
        try:
            parsed = json.loads(content)
            analysis_text = f"**Analysis:** {parsed.get('analysis', '')}\n\n"
            for step in parsed.get("action_plan", []):
                analysis_text += f"{step.get('step', '')}. {step.get('action', '')}\n"
            for risk in parsed.get("risks", []):
                analysis_text += f"- Risk: {risk}\n"
            effort = parsed.get("estimated_effort", "UNKNOWN")
            analysis_text += f"\n**Estimated Effort:** {effort}"
        except json.JSONDecodeError:
            analysis_text = content

        # Write analysis to the repo's directory
        repo_name = proposal.get("repo", "unknown")
        repo_dir = init_gremlin_memory(gremlins_root.parent, repo_name=repo_name)
        write_ledger_entry(
            repo_dir, "reviews", f"Analysis: {proposal['title']}",
            analysis_text, author=hat_id,
        )

        results.append({
            "proposal_id": proposal["id"],
            "repo": repo_name,
            "hat": hat_id,
            "model": result["model"],
            "status": "analyzed",
        })

    return {
        "phase": "analyze",
        "status": "completed",
        "hat": default_hat_id,
        "proposals_analyzed": len([r for r in results if r.get("status") == "analyzed"]),
        "overnight_mode": is_overnight_mode(config),
    }


# ---------------------------------------------------------------------------
# Phase 4: Herald Summary (Blue Hat) -- cross-repo digest
# ---------------------------------------------------------------------------

def phase_herald(config: dict, gremlins_root: Path) -> dict:
    """Blue Hat composes a cross-repo daily digest."""
    hat_id = _resolve_phase_hat(config, "herald")
    hat_def = _get_hat_config(config, hat_id)

    herald_cfg = config.get("gremlins", {}).get("herald", {})
    max_posts = herald_cfg.get("max_daily_posts", 3)

    # Write to global herald directory
    herald_dir = gremlins_root / "herald"

    # Check if we've already posted today
    today = time.strftime("%Y-%m-%d", time.gmtime())
    existing = read_herald(herald_dir, since=today)
    if len(existing) >= max_posts:
        return {"phase": "herald", "status": "skipped", "reason": f"Max daily posts reached ({max_posts})"}

    # Gather recent activity from ALL repos
    all_findings = read_ledger_all_repos(gremlins_root, category="findings", since=today)
    all_proposals = list_proposals_all_repos(gremlins_root, status="PENDING_HUMAN")
    all_reviews = read_ledger_all_repos(gremlins_root, category="reviews", since=today)

    if not all_findings and not all_proposals and not all_reviews:
        return {"phase": "herald", "status": "skipped", "reason": "No activity to report"}

    # Group by repo for the digest
    repos_seen = set()
    for item in all_findings + all_reviews:
        repos_seen.add(item.get("repo", "unknown"))
    for item in all_proposals:
        repos_seen.add(item.get("repo", "unknown"))

    context_lines = [f"## Cross-Repo Gremlin Activity ({len(repos_seen)} repos)\n"]
    if all_findings:
        context_lines.append(f"### Findings ({len(all_findings)} total)\n")
        by_repo = {}
        for f in all_findings:
            by_repo.setdefault(f.get("repo", "?"), []).append(f)
        for repo_name, entries in sorted(by_repo.items()):
            context_lines.append(f"**{repo_name}:** {len(entries)} findings\n")
            for entry in entries[-2:]:
                context_lines.append(f"  - {entry['title']}\n")
    if all_proposals:
        context_lines.append(f"\n### Pending Proposals ({len(all_proposals)} total)\n")
        for p in all_proposals[:5]:
            context_lines.append(f"- [{p.get('repo', '?')}] [{p['status']}] {p['title']}\n")
    if all_reviews:
        context_lines.append(f"\n### Reviews ({len(all_reviews)} total)\n")
        for r in all_reviews[-3:]:
            context_lines.append(f"- [{r.get('repo', '?')}] {r['title']}\n")

    model = resolve_gremlin_model(config, "herald", hat_id)
    fallback = hat_def.get("fallback_model")

    persona = hat_def.get("persona", "You are a process and formatting specialist.").strip()
    system_prompt = persona + "\n\n" + _GREMLIN_HERALD_SCHEMA

    user_prompt = (
        f"{chr(10).join(context_lines)}\n\n"
        "Compose a daily digest for the human operator covering ALL repos. "
        "Include what the Gremlins found, what proposals need approval, and what actions to take. "
        "Organize by repo with a cross-repo summary at the top."
    )

    base_timeout = hat_def.get("timeout_seconds", 300)
    timeout = get_overnight_timeout(config, base_timeout)

    result = try_model_chain(
        config, model, fallback, system_prompt, user_prompt,
        temperature=0.4,
        max_tokens=1024,
        timeout=timeout,
        hat_id=f"gremlin_{hat_id}",
    )

    if result["error"]:
        return {"phase": "herald", "status": "error", "error": result["error"], "model": result["model"]}

    content = result["content"] or ""
    try:
        parsed = json.loads(content)
        headline = parsed.get("headline", "Gremlin Daily Digest")
        digest = parsed.get("digest", content)
        action_items = parsed.get("action_items", [])
    except json.JSONDecodeError:
        headline = "Gremlin Daily Digest"
        digest = content
        action_items = []

    herald_content = f"# {headline}\n\n{digest}\n\n"
    if action_items:
        herald_content += "## Action Items\n\n"
        for item in action_items:
            herald_content += f"- {item}\n"

    write_herald(herald_dir, herald_content, author=hat_id)

    return {
        "phase": "herald",
        "status": "completed",
        "hat": hat_id,
        "model": result["model"],
        "headline": headline,
        "action_items": len(action_items),
        "repos_covered": len(repos_seen),
        "overnight_mode": is_overnight_mode(config),
    }


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def show_status(config: dict, gremlins_root: Path) -> dict:
    """Show current Gremlin swarm status across all repos."""
    # Per-repo stats
    repo_stats = []
    for repo_info in list_repos(gremlins_root):
        repo_name = repo_info["name"]
        repo_dir = Path(repo_info["path"])
        findings = read_ledger(repo_dir, category="findings")
        proposals = list_proposals(repo_dir)
        pending = [p for p in proposals if p["status"] == "PENDING_HUMAN"]
        reviews = read_ledger(repo_dir, category="reviews")
        repo_stats.append({
            "repo": repo_name,
            "findings": len(findings),
            "proposals": len(proposals),
            "pending": len(pending),
            "reviews": len(reviews),
        })

    # Global herald
    herald_dir = gremlins_root / "herald"
    herald = read_herald(herald_dir)

    phase_to_hat = config.get("gremlins", {}).get("phase_to_hat", {})
    overnight_active = is_overnight_mode(config)

    # Configured repos
    configured_repos = _get_configured_repos(config)

    return {
        "gremlins_initialized": True,
        "configured_repos": len(configured_repos),
        "repo_stats": repo_stats,
        "total_findings": sum(r["findings"] for r in repo_stats),
        "total_proposals": sum(r["proposals"] for r in repo_stats),
        "pending_proposals": sum(r["pending"] for r in repo_stats),
        "total_reviews": sum(r["reviews"] for r in repo_stats),
        "herald_entries": len(herald),
        "phase_to_hat": phase_to_hat,
        "overnight_mode": overnight_active,
        "governance": config.get("gremlins", {}).get("governance", {}),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Gremlin Runner -- multi-repo overnight autonomous review loop (hat-based)"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run all 4 phases sequentially"
    )
    parser.add_argument(
        "--phase", choices=["review", "propose", "analyze", "herald"],
        help="Run a single phase"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show current Gremlin swarm status"
    )
    parser.add_argument(
        "--repo", default=None,
        help="Run phases for a single repo only (by name, e.g., GrumpRolled)"
    )
    parser.add_argument(
        "--repos-only", action="store_true",
        help="List configured repos and exit"
    )
    parser.add_argument(
        "--config", default=str(DEFAULT_CONFIG),
        help="Path to hat_configs.yml"
    )
    parser.add_argument(
        "--gremlins-path", default=None,
        help="Path to Gremlins root (default: auto-detect .gremlins in repo)"
    )
    parser.add_argument(
        "--identity", default=None,
        help="Moltbook identity token (or set MOLTBOOK_IDENTITY_TOKEN env var)"
    )
    parser.add_argument(
        "--overnight", action="store_true",
        help="Force overnight mode (for testing)"
    )
    parser.add_argument(
        "--since", default="24 hours ago",
        help="Git log time window (default: '24 hours ago'). Use '1 week ago' or 'all' for testing."
    )

    args = parser.parse_args()

    if not args.all and not args.phase and not args.status and not args.repos_only:
        parser.print_help()
        sys.exit(1)

    # Load config
    config = load_config(args.config)

    # Force overnight mode if requested
    if args.overnight and "gremlins" in config:
        config["gremlins"].setdefault("overnight", {})["enabled"] = True

    # Preflight check
    issues = preflight_check(config)
    for msg in issues:
        print(msg, file=sys.stderr)

    # Send Wake-on-LAN if configured and in overnight mode
    if is_overnight_mode(config):
        send_wake_on_lan(config)

    # Determine Gremlins path
    if args.gremlins_path:
        gremlins_path = Path(args.gremlins_path)
    else:
        gremlins_path = Path.cwd()

    # Initialize global Gremlins memory (multi-repo)
    gremlins_root = init_gremlin_memory_global(gremlins_path)

    # List configured repos and exit
    if args.repos_only:
        repos = _get_configured_repos(config)
        print(f"Configured repos ({len(repos)}):", file=sys.stderr)
        for repo in repos:
            repo_name = _repo_name_from_path(repo["path"])
            enabled = repo.get("enabled", True)
            status_label = "enabled" if enabled else "disabled"
            print(f"  {repo_name}: {repo['path']} ({status_label})", file=sys.stderr)
        return

    # Filter to single repo if requested
    if args.repo:
        # Override config to only include the specified repo
        matching = [r for r in config.get("gremlins", {}).get("repos", [])
                    if _repo_name_from_path(r.get("path", "")) == args.repo]
        if not matching:
            print(f"ERROR: repo '{args.repo}' not found in config", file=sys.stderr)
            sys.exit(1)
        config["gremlins"]["repos"] = matching

    # Verify Moltbook identity if provided
    identity_token = args.identity or os.environ.get("MOLTBOOK_IDENTITY_TOKEN", "")
    agent_identity = None
    if identity_token:
        verify_result = verify_moltbook_identity(identity_token, config)
        if verify_result["valid"]:
            agent_identity = verify_result["agent"]
            print(f"Authenticated: {format_agent_identity(agent_identity)}", file=sys.stderr)
        else:
            print(f"Identity verification failed: {verify_result['error']}", file=sys.stderr)

    # Show phase-to-hat mapping
    phase_to_hat = config.get("gremlins", {}).get("phase_to_hat", {})
    if phase_to_hat:
        print(f"Phase-to-hat mapping: {phase_to_hat}", file=sys.stderr)
    if is_overnight_mode(config):
        print("OVERNIGHT MODE: using larger models with extended timeouts", file=sys.stderr)

    # Show configured repos
    repos = _get_configured_repos(config)
    print(f"Repos to scan: {len(repos)}", file=sys.stderr)

    if args.status:
        status = show_status(config, gremlins_root)
        if agent_identity:
            status["agent_identity"] = format_agent_identity(agent_identity)
        print(json.dumps(status, indent=2))
        return

    # Run phases
    phases = {
        "review": phase_review,
        "propose": phase_propose,
        "analyze": phase_analyze,
        "herald": phase_herald,
    }

    if args.all:
        order = ["review", "propose", "analyze", "herald"]
    else:
        order = [args.phase]

    results = []
    since = args.since
    for phase_name in order:
        hat_id = _resolve_phase_hat(config, phase_name)
        print(f"\nGremlin Phase: {phase_name.upper()} ({hat_id} hat)", file=sys.stderr)
        phase_fn = phases[phase_name]
        if phase_name == "review":
            result = phase_fn(config, gremlins_root, since=since)
        else:
            result = phase_fn(config, gremlins_root)
        results.append(result)
        status = result.get("status", "unknown")
        summary = result.get("summary", result.get("reason", ""))
        model = result.get("model", result.get("hat", ""))
        repos_scanned = result.get("repos_scanned", result.get("repos_covered", ""))
        print(f"  {status} [{model}]: repos={repos_scanned} {summary}", file=sys.stderr)

    # Output results
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()