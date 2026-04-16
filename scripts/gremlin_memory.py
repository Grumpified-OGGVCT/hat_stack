#!/usr/bin/env python3
"""
gremlin_memory.py -- Shared Git-Backed Memory for Gremlin Agents.

The .gremlins/ directory is the Gremlins' shared brain. Agents read/write
markdown and JSON here, git commits after each write. No direct
agent-to-agent API -- the filesystem IS the coordination layer.

Multi-repo layout:
  .gremlins/
    config.json              # Global: version, created, schedule
    repos/
      <repo_name>/
        config.json          # Per-repo: last_scanned, commit_count
        ledger/
          findings/
          proposals/
          reviews/
        proposals/
        social_log/
    herald/                  # Cross-repo Herald digests
      social_log/

Single-repo (backward compat) layout:
  .gremlins/
    config.json
    ledger/...
    proposals/...
    social_log/...

Every Gremlin output signs off with: -- Gremlin Legion
"""

import json
import os
import re
import subprocess
import time
import calendar
import warnings
from pathlib import Path
from typing import Any


GREMLIN_SIGNOFF = "\n\n-- Gremlin Legion"

_REPO_SUBDIRS = ["ledger/findings", "ledger/proposals", "ledger/reviews", "proposals", "social_log"]


def init_gremlin_memory(root_path: str | Path, repo_name: str | None = None) -> Path:
    """Create .gremlins/ directory structure with config.json.

    If repo_name is provided, creates the per-repo subdirectory
    .gremlins/repos/<repo_name>/ with its own ledger, proposals, and social_log.
    If repo_name is None, creates the top-level (backward compat single-repo) layout.

    Args:
        root_path: Parent directory where .gremlins/ will be created
        repo_name: Optional repo name for multi-repo layout

    Returns:
        Path to the created .gremlins/ directory (or repos/<repo_name>/ subdirectory)
    """
    root = Path(root_path)

    # Auto-migrate from old .moltbook/ directory
    migrate_moltbook_to_gremlins(root)

    gremlins_dir = root / ".gremlins"

    if repo_name:
        # Multi-repo: create repos/<repo_name>/ subdirectory
        repo_dir = gremlins_dir / "repos" / repo_name
        if repo_dir.exists():
            return repo_dir

        # Ensure global .gremlins/ exists first
        _ensure_global_dirs(gremlins_dir)

        # Create per-repo subdirectories
        for subdir in _REPO_SUBDIRS:
            (repo_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Create per-repo config.json
        repo_config = {
            "version": 1,
            "repo_name": repo_name,
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "last_scanned": None,
            "commit_count": 0,
        }
        (repo_dir / "config.json").write_text(json.dumps(repo_config, indent=2), encoding="utf-8")

        return repo_dir
    else:
        # Single-repo backward compat
        if gremlins_dir.exists():
            return gremlins_dir

        for subdir in _REPO_SUBDIRS:
            (gremlins_dir / subdir).mkdir(parents=True, exist_ok=True)

        config = {
            "version": 1,
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "gremlins_enabled": True,
        }
        (gremlins_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

        # Git init if not already in a git repo
        _git_init_if_needed(gremlins_dir.parent)

        return gremlins_dir


def init_gremlin_memory_global(root_path: str | Path) -> Path:
    """Create the global .gremlins/ directory with repos/ and herald/ subdirs.

    This is the entry point for multi-repo mode. Per-repo directories
    are created separately via init_gremlin_memory(root_path, repo_name=...).

    Returns:
        Path to the .gremlins/ directory
    """
    root = Path(root_path)

    # Auto-migrate from old .moltbook/ directory
    migrate_moltbook_to_gremlins(root)

    gremlins_dir = root / ".gremlins"
    _ensure_global_dirs(gremlins_dir)

    return gremlins_dir


def _ensure_global_dirs(gremlins_dir: Path):
    """Ensure the global .gremlins/ structure exists with repos/ and herald/."""
    if not gremlins_dir.exists():
        gremlins_dir.mkdir(parents=True, exist_ok=True)
        config = {
            "version": 2,  # v2 = multi-repo
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "gremlins_enabled": True,
        }
        (gremlins_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    # Ensure repos/, herald/, and experiments/ directories exist
    (gremlins_dir / "repos").mkdir(exist_ok=True)
    (gremlins_dir / "herald" / "social_log").mkdir(parents=True, exist_ok=True)
    (gremlins_dir / "experiments" / "candidates").mkdir(parents=True, exist_ok=True)
    (gremlins_dir / "experiments" / "published").mkdir(parents=True, exist_ok=True)
    (gremlins_dir / "experiments" / "results").mkdir(parents=True, exist_ok=True)


def list_repos(gremlins_root: str | Path) -> list[dict]:
    """List per-repo directories and their metadata.

    Returns:
        List of dicts with keys: name, path, config (or None if no config.json)
    """
    root = Path(gremlins_root)
    repos_dir = root / "repos"
    if not repos_dir.exists():
        return []

    repos = []
    for repo_dir in sorted(repos_dir.iterdir()):
        if not repo_dir.is_dir():
            continue
        config_path = repo_dir / "config.json"
        config = None
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        repos.append({
            "name": repo_dir.name,
            "path": str(repo_dir),
            "config": config,
        })
    return repos


def init_moltbook(root_path: str | Path) -> Path:
    """Deprecated alias for init_gremlin_memory(). Auto-migrates .moltbook/ -> .gremlins/."""
    warnings.warn(
        "init_moltbook() is deprecated -- use init_gremlin_memory() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return init_gremlin_memory(root_path)


def migrate_moltbook_to_gremlins(root_path: str | Path) -> Path | None:
    """Migrate old .moltbook/ directory to .gremlins/ if it exists.

    Returns the new .gremlins/ path if migration happened, None otherwise.
    """
    root = Path(root_path)
    old_dir = root / ".moltbook"
    new_dir = root / ".gremlins"

    if old_dir.exists() and not new_dir.exists():
        old_dir.rename(new_dir)
        print(f"Migrated {old_dir} -> {new_dir}", file=__import__("sys").stderr)
        return new_dir
    return None


def _git_init_if_needed(repo_root: Path):
    """Initialize git in repo_root if not already a git repo."""
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        subprocess.run(["git", "init"], cwd=str(repo_root), capture_output=True, timeout=10)


def _git_commit(gremlins_root: Path, message: str):
    """Stage and commit changes in the .gremlins/ directory.

    Best-effort: silently skips if git is not available or the directory
    is not in a git repo.
    """
    # Walk up to find the git repo root (could be the parent of .gremlins/
    # or the parent of .gremlins/repos/<name>/)
    repo_root = gremlins_root
    while repo_root.parent != repo_root:
        if (repo_root / ".git").exists():
            break
        # If we're inside .gremlins/repos/<name>/, go up to the .gremlins parent
        if ".gremlins" in repo_root.parts:
            # Find the directory containing .gremlins/
            idx = list(repo_root.parts).index(".gremlins")
            repo_root = Path(*repo_root.parts[:idx])
            break
        repo_root = repo_root.parent

    try:
        subprocess.run(
            ["git", "add", ".gremlins/"],
            cwd=str(repo_root), capture_output=True, timeout=10,
        )
        subprocess.run(
            ["git", "commit", "-m", message, "--allow-empty"],
            cwd=str(repo_root), capture_output=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass


# ---------------------------------------------------------------------------
# Ledger operations
# ---------------------------------------------------------------------------

def write_ledger_entry(gremlins_root: str | Path, category: str, title: str,
                       content: str, author: str = "gremlin") -> Path:
    """Write a ledger entry atomically.

    Args:
        gremlins_root: Path to .gremlins/ or repos/<name>/
        category: Subdirectory (findings, proposals, reviews)
        title: Entry title (slugified for filename)
        content: Markdown content
        author: Gremlin hat name (black, gold, purple, blue, etc.)

    Returns:
        Path to the created file
    """
    root = Path(gremlins_root)
    category_dir = root / "ledger" / category
    category_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(title)
    date_prefix = time.strftime("%Y-%m-%d", time.gmtime())
    filename = f"{date_prefix}-{slug}.md"
    filepath = category_dir / filename

    header = f"# {title}\n\n"
    header += f"**Author:** {author}  \n"
    header += f"**Date:** {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}  \n"
    header += f"**Category:** {category}\n\n---\n\n"

    full_content = header + content + GREMLIN_SIGNOFF
    filepath.write_text(full_content, encoding="utf-8")

    _git_commit(root, f"Gremlin {author}: {category}/{title}")

    return filepath


def read_ledger(gremlins_root: str | Path, category: str | None = None,
                since: str | None = None) -> list[dict]:
    """Read ledger entries, optionally filtered.

    Args:
        gremlins_root: Path to .gremlins/ or repos/<name>/
        category: Optional category filter (findings, proposals, reviews)
        since: Optional ISO date string -- only return entries after this date

    Returns:
        List of dicts with keys: path, title, author, date, category, content
    """
    root = Path(gremlins_root)
    ledger_dir = root / "ledger"

    if category:
        search_dirs = [ledger_dir / category]
    else:
        search_dirs = [d for d in ledger_dir.iterdir() if d.is_dir()] if ledger_dir.exists() else []

    entries = []
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        cat_name = search_dir.name
        for md_file in sorted(search_dir.glob("*.md")):
            date_str = md_file.name[:10] if len(md_file.name) >= 10 else ""
            if since and date_str < since:
                continue

            content = md_file.read_text(encoding="utf-8")
            title = ""
            author = ""
            for line in content.split("\n"):
                if line.startswith("# ") and not title:
                    title = line[2:].strip()
                if line.startswith("**Author:**"):
                    author = line.split("**Author:**")[1].strip()

            entries.append({
                "path": str(md_file),
                "title": title,
                "author": author,
                "date": date_str,
                "category": cat_name,
                "content": content,
            })

    return entries


# ---------------------------------------------------------------------------
# Governance proposals
# ---------------------------------------------------------------------------

def create_proposal(gremlins_root: str | Path, title: str, description: str,
                    proposed_action: str, author: str = "gold") -> dict:
    """Create a PENDING_HUMAN governance proposal.

    Returns:
        The proposal dict (also written to disk)
    """
    root = Path(gremlins_root)
    proposals_dir = root / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)

    # Determine next proposal ID
    existing = sorted(proposals_dir.glob("*.json"))
    next_id = len(existing) + 1
    proposal_id = f"{next_id:03d}"

    proposal = {
        "id": proposal_id,
        "title": title,
        "description": description,
        "proposed_action": proposed_action,
        "author": author,
        "status": "PENDING_HUMAN",
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "approved_by": None,
        "rejected_reason": None,
    }

    slug = _slugify(title)
    filepath = proposals_dir / f"{proposal_id}-{slug}.json"
    filepath.write_text(json.dumps(proposal, indent=2), encoding="utf-8")

    _git_commit(root, f"Gremlin {author}: proposal {proposal_id} -- {title}")

    # Also write a ledger entry for visibility
    write_ledger_entry(
        root, "proposals", f"Proposal {proposal_id}: {title}",
        f"## Proposal\n\n{description}\n\n## Proposed Action\n\n{proposed_action}\n\n"
        f"**Status:** PENDING_HUMAN\n",
        author=author,
    )

    return proposal


def approve_proposal(gremlins_root: str | Path, proposal_id: str,
                     approved_by: str = "human") -> dict | None:
    """Approve a PENDING_HUMAN proposal."""
    root = Path(gremlins_root)
    proposal = _find_proposal(root, proposal_id)
    if not proposal:
        return None

    proposal["status"] = "APPROVED"
    proposal["approved_by"] = approved_by
    proposal["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    _write_proposal(root, proposal)
    _git_commit(root, f"Proposal {proposal_id} APPROVED by {approved_by}")

    return proposal


def reject_proposal(gremlins_root: str | Path, proposal_id: str,
                    reason: str = "", rejected_by: str = "human") -> dict | None:
    """Reject a PENDING_HUMAN proposal."""
    root = Path(gremlins_root)
    proposal = _find_proposal(root, proposal_id)
    if not proposal:
        return None

    proposal["status"] = "REJECTED"
    proposal["rejected_reason"] = reason
    proposal["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    _write_proposal(root, proposal)
    _git_commit(root, f"Proposal {proposal_id} REJECTED by {rejected_by}: {reason}")

    return proposal


def list_proposals(gremlins_root: str | Path, status: str | None = None) -> list[dict]:
    """List governance proposals, optionally filtered by status.

    Args:
        status: Filter by status (PENDING_HUMAN, APPROVED, REJECTED, EXPIRED)
    """
    root = Path(gremlins_root)
    proposals_dir = root / "proposals"
    if not proposals_dir.exists():
        return []

    proposals = []
    for json_file in sorted(proposals_dir.glob("*.json")):
        try:
            proposal = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if status and proposal.get("status") != status:
            continue
        proposals.append(proposal)

    return proposals


def expire_stale_proposals(gremlins_root: str | Path, ttl_hours: int = 48) -> list[dict]:
    """Auto-expire proposals older than ttl_hours that are still PENDING_HUMAN.

    Returns list of expired proposals.
    """
    root = Path(gremlins_root)
    pending = list_proposals(root, status="PENDING_HUMAN")
    expired = []

    now = time.time()
    for proposal in pending:
        created = proposal.get("created", "")
        if not created:
            continue
        try:
            created_time = calendar.timegm(time.strptime(created, "%Y-%m-%dT%H:%M:%SZ"))
        except ValueError:
            continue

        age_hours = (now - created_time) / 3600
        if age_hours > ttl_hours:
            proposal["status"] = "EXPIRED"
            proposal["rejected_reason"] = f"Auto-expired after {age_hours:.0f}h (TTL: {ttl_hours}h)"
            proposal["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            _write_proposal(root, proposal)
            expired.append(proposal)

    if expired:
        _git_commit(root, f"Expired {len(expired)} stale proposal(s) (TTL: {ttl_hours}h)")

    return expired


def _find_proposal(gremlins_root: Path, proposal_id: str) -> dict | None:
    """Find a proposal by its ID prefix."""
    proposals_dir = gremlins_root / "proposals"
    if not proposals_dir.exists():
        return None

    for json_file in proposals_dir.glob("*.json"):
        if json_file.name.startswith(proposal_id):
            try:
                return json.loads(json_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    return None


def _write_proposal(gremlins_root: Path, proposal: dict):
    """Write a proposal back to disk."""
    proposals_dir = gremlins_root / "proposals"
    proposal_id = proposal["id"]
    slug = _slugify(proposal.get("title", "untitled"))
    filepath = proposals_dir / f"{proposal_id}-{slug}.json"
    filepath.write_text(json.dumps(proposal, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Herald (social output)
# ---------------------------------------------------------------------------

def write_herald(gremlins_root: str | Path, content: str,
                 channel: str = "social_log", author: str = "herald") -> Path:
    """Append a Herald social output entry.

    Args:
        gremlins_root: Path to .gremlins/ (for cross-repo) or repos/<name>/
        content: Markdown content for the social post
        channel: Output channel (default: social_log)
        author: Gremlin hat name

    Returns:
        Path to the created file
    """
    root = Path(gremlins_root)
    social_dir = root / "social_log"
    social_dir.mkdir(parents=True, exist_ok=True)

    date_str = time.strftime("%Y-%m-%d", time.gmtime())
    filename = f"{date_str}-{channel}.md"
    filepath = social_dir / filename

    # Append to existing file or create new
    entry = (
        f"\n---\n\n"
        f"## Herald Digest -- {time.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"{content}\n"
        f"{GREMLIN_SIGNOFF}\n"
    )

    if filepath.exists():
        with open(filepath, "a", encoding="utf-8") as fh:
            fh.write(entry)
    else:
        header = f"# Herald Social Log -- {date_str}\n"
        filepath.write_text(header + entry, encoding="utf-8")

    _git_commit(root, f"Gremlin {author}: herald {channel}")

    return filepath


def read_herald(gremlins_root: str | Path, since: str | None = None) -> list[dict]:
    """Read recent Herald social output.

    Args:
        gremlins_root: Path to .gremlins/ (for cross-repo) or repos/<name>/
        since: Optional ISO date string -- only return entries after this date

    Returns:
        List of dicts with keys: date, content, path
    """
    root = Path(gremlins_root)
    social_dir = root / "social_log"
    if not social_dir.exists():
        return []

    entries = []
    for md_file in sorted(social_dir.glob("*.md")):
        date_str = md_file.name[:10] if len(md_file.name) >= 10 else ""
        if since and date_str < since:
            continue

        entries.append({
            "date": date_str,
            "content": md_file.read_text(encoding="utf-8"),
            "path": str(md_file),
        })

    return entries


# ---------------------------------------------------------------------------
# Cross-repo helpers
# ---------------------------------------------------------------------------

def read_ledger_all_repos(gremlins_root: str | Path, category: str | None = None,
                           since: str | None = None) -> list[dict]:
    """Read ledger entries from all repos, annotated with repo_name.

    Returns:
        List of dicts with an additional 'repo' key
    """
    root = Path(gremlins_root)
    all_entries = []
    for repo_info in list_repos(root):
        repo_name = repo_info["name"]
        repo_dir = Path(repo_info["path"])
        entries = read_ledger(repo_dir, category=category, since=since)
        for entry in entries:
            entry["repo"] = repo_name
        all_entries.extend(entries)
    return all_entries


def list_proposals_all_repos(gremlins_root: str | Path, status: str | None = None) -> list[dict]:
    """List proposals from all repos, annotated with repo_name.

    Returns:
        List of dicts with an additional 'repo' key
    """
    root = Path(gremlins_root)
    all_proposals = []
    for repo_info in list_repos(root):
        repo_name = repo_info["name"]
        repo_dir = Path(repo_info["path"])
        proposals = list_proposals(repo_dir, status=status)
        for proposal in proposals:
            proposal["repo"] = repo_name
        all_proposals.extend(proposals)
    return all_proposals


# ---------------------------------------------------------------------------
# Experiment state helpers
# ---------------------------------------------------------------------------

def init_experiment_state(gremlins_root: str | Path) -> dict:
    """Initialize experiment state directory and return initial state.

    Creates .gremlins/experiments/ with candidates/, published/, and results/ subdirs.
    """
    root = Path(gremlins_root)
    experiments_dir = root / "experiments"

    for subdir in ["candidates", "published", "results"]:
        (experiments_dir / subdir).mkdir(parents=True, exist_ok=True)

    state = {
        "last_run": None,
        "total_runs": 0,
        "total_published": 0,
        "total_rejected": 0,
    }
    state_path = experiments_dir / "experiment_state.json"
    if not state_path.exists():
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def load_experiment_state(gremlins_root: str | Path) -> dict:
    """Load experiment state from .gremlins/experiments/experiment_state.json."""
    root = Path(gremlins_root)
    state_path = root / "experiments" / "experiment_state.json"
    if state_path.exists():
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    return init_experiment_state(gremlins_root)


def save_experiment_state(gremlins_root: str | Path, state: dict):
    """Save experiment state to .gremlins/experiments/experiment_state.json."""
    root = Path(gremlins_root)
    state_path = root / "experiments" / "experiment_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def write_experiment_result(gremlins_root: str | Path, result: dict) -> Path:
    """Write an experiment result to .gremlins/experiments/results/.

    Returns:
        Path to the written result file.
    """
    root = Path(gremlins_root)
    results_dir = root / "experiments" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y-%m-%d", time.gmtime())
    result_path = results_dir / f"{timestamp}-experiment.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:60] or "untitled"