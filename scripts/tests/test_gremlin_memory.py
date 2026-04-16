#!/usr/bin/env python3
"""Unit tests for gremlin_memory.py — Gremlin shared Git-backed memory."""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gremlin_memory import (
    init_gremlin_memory,
    init_gremlin_memory_global,
    list_repos,
    read_ledger_all_repos,
    list_proposals_all_repos,
    init_moltbook,
    migrate_moltbook_to_gremlins,
    write_ledger_entry,
    read_ledger,
    create_proposal,
    approve_proposal,
    reject_proposal,
    list_proposals,
    expire_stale_proposals,
    write_herald,
    read_herald,
    GREMLIN_SIGNOFF,
)


def test_init_gremlin_memory():
    """init_gremlin_memory should create the .gremlins/ directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = init_gremlin_memory(tmpdir)
        assert root.exists()
        assert root.name == ".gremlins"
        assert (root / "config.json").exists()
        assert (root / "ledger" / "findings").exists()
        assert (root / "ledger" / "proposals").exists()
        assert (root / "ledger" / "reviews").exists()
        assert (root / "proposals").exists()
        assert (root / "social_log").exists()

        # Idempotent — calling again should not fail
        root2 = init_gremlin_memory(tmpdir)
        assert root2 == root
        print("OK: init_gremlin_memory creates directory structure")


def test_init_moltbook_deprecated():
    """init_moltbook() is a deprecated alias that still works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            root = init_moltbook(tmpdir)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "init_gremlin_memory" in str(w[0].message)
        assert root.name == ".gremlins"
        print("OK: init_moltbook emits DeprecationWarning and delegates to init_gremlin_memory")


def test_migrate_moltbook_to_gremlins():
    """migrate_moltbook_to_gremlins should rename .moltbook/ to .gremlins/."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create old .moltbook/ directory with some content
        old_dir = root / ".moltbook"
        old_dir.mkdir()
        (old_dir / "config.json").write_text('{"version": 1}', encoding="utf-8")
        (old_dir / "ledger").mkdir()
        (old_dir / "ledger" / "findings").mkdir()

        # Migrate
        result = migrate_moltbook_to_gremlins(tmpdir)
        assert result is not None
        assert result.name == ".gremlins"
        assert not (root / ".moltbook").exists()
        assert (root / ".gremlins").exists()
        assert (root / ".gremlins" / "config.json").exists()
        print("OK: migrate_moltbook_to_gremlins renames .moltbook/ -> .gremlins/")


def test_migrate_moltbook_noop_when_no_old_dir():
    """migrate_moltbook_to_gremlins returns None when no .moltbook/ exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = migrate_moltbook_to_gremlins(tmpdir)
        assert result is None
        print("OK: migrate_moltbook_to_gremlins is no-op when .moltbook/ doesn't exist")


def test_migrate_moltbook_noop_when_gremlins_exists():
    """migrate_moltbook_to_gremlins is no-op if .gremlins/ already exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create both old and new directories
        (root / ".moltbook").mkdir()
        (root / ".gremlins").mkdir()

        result = migrate_moltbook_to_gremlins(tmpdir)
        assert result is None
        # Old directory should still exist (not overwritten)
        assert (root / ".moltbook").exists()
        assert (root / ".gremlins").exists()
        print("OK: migrate_moltbook_to_gremlins is no-op when .gremlins/ already exists")


def test_write_read_ledger():
    """write_ledger_entry + read_ledger should roundtrip."""
    with tempfile.TemporaryDirectory() as tmpdir:
        init_gremlin_memory(tmpdir)
        gremlins = Path(tmpdir) / ".gremlins"

        write_ledger_entry(
            gremlins, "findings", "SQL Injection Found",
            "Found SQL injection in auth.py line 42",
            author="black",
        )

        entries = read_ledger(gremlins, category="findings")
        assert len(entries) == 1
        assert "SQL Injection Found" in entries[0]["title"]
        assert entries[0]["author"] == "black"
        assert "auth.py" in entries[0]["content"]
        assert GREMLIN_SIGNOFF.strip() in entries[0]["content"]
        print("OK: write/read ledger roundtrip works")


def test_create_approve_proposal():
    """create_proposal + approve_proposal governance lifecycle."""
    with tempfile.TemporaryDirectory() as tmpdir:
        init_gremlin_memory(tmpdir)
        gremlins = Path(tmpdir) / ".gremlins"

        proposal = create_proposal(
            gremlins,
            title="Add Rate Limiting",
            description="API endpoints lack rate limiting",
            proposed_action="Add rate limiting middleware",
            author="gold",
        )

        assert proposal["status"] == "PENDING_HUMAN"
        assert proposal["id"] == "001"

        # List pending
        pending = list_proposals(gremlins, status="PENDING_HUMAN")
        assert len(pending) == 1

        # Approve
        approved = approve_proposal(gremlins, "001", approved_by="human")
        assert approved is not None
        assert approved["status"] == "APPROVED"
        assert approved["approved_by"] == "human"

        # No more pending
        pending_after = list_proposals(gremlins, status="PENDING_HUMAN")
        assert len(pending_after) == 0

        # Approved exists
        approved_list = list_proposals(gremlins, status="APPROVED")
        assert len(approved_list) == 1
        print("OK: create/approve proposal lifecycle works")


def test_create_reject_proposal():
    """create_proposal + reject_proposal."""
    with tempfile.TemporaryDirectory() as tmpdir:
        init_gremlin_memory(tmpdir)
        gremlins = Path(tmpdir) / ".gremlins"

        create_proposal(
            gremlins,
            title="Refactor Auth",
            description="Simplify auth flow",
            proposed_action="Rewrite auth module",
            author="gold",
        )

        rejected = reject_proposal(gremlins, "001", reason="Too risky right now")
        assert rejected is not None
        assert rejected["status"] == "REJECTED"
        assert "Too risky" in rejected["rejected_reason"]
        print("OK: create/reject proposal works")


def test_proposal_ttl_expiry():
    """expire_stale_proposals should auto-reject old PENDING_HUMAN proposals."""
    with tempfile.TemporaryDirectory() as tmpdir:
        init_gremlin_memory(tmpdir)
        gremlins = Path(tmpdir) / ".gremlins"

        # Create a proposal with an old timestamp
        proposal = create_proposal(
            gremlins,
            title="Old Proposal",
            description="This should expire",
            proposed_action="Do something",
            author="gold",
        )

        # Manually set the created timestamp to 49 hours ago
        proposals_dir = gremlins / "proposals"
        for json_file in proposals_dir.glob("*.json"):
            data = json.loads(json_file.read_text(encoding="utf-8"))
            # Set created to 49 hours ago (past 48h TTL)
            import time
            import calendar
            old_time = time.time() - (49 * 3600)
            data["created"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(old_time))
            json_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Expire with TTL of 48 hours
        expired = expire_stale_proposals(gremlins, ttl_hours=48)
        assert len(expired) == 1
        assert expired[0]["status"] == "EXPIRED"
        print("OK: proposal TTL expiry works")


def test_herald_write_read():
    """write_herald + read_herald should roundtrip."""
    with tempfile.TemporaryDirectory() as tmpdir:
        init_gremlin_memory(tmpdir)
        gremlins = Path(tmpdir) / ".gremlins"

        write_herald(
            gremlins,
            content="## Daily Digest\n\n- 3 findings\n- 1 proposal pending",
            author="blue",
        )

        entries = read_herald(gremlins)
        assert len(entries) >= 1
        assert "Daily Digest" in entries[0]["content"]
        assert GREMLIN_SIGNOFF.strip() in entries[0]["content"]
        print("OK: write/read herald roundtrip works")


def test_auto_migration_on_init():
    """init_gremlin_memory should auto-migrate .moltbook/ -> .gremlins/."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create old .moltbook/ with content
        old_dir = root / ".moltbook"
        old_dir.mkdir()
        (old_dir / "config.json").write_text('{"version": 1}', encoding="utf-8")

        # init_gremlin_memory auto-migrates
        gremlins = init_gremlin_memory(tmpdir)
        assert gremlins.name == ".gremlins"
        assert not (root / ".moltbook").exists()
        assert (root / ".gremlins" / "config.json").exists()
        print("OK: init_gremlin_memory auto-migrates .moltbook/ -> .gremlins/")


def test_init_gremlin_memory_global():
    """init_gremlin_memory_global should create .gremlins/ with repos/ and herald/."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gremlins = init_gremlin_memory_global(tmpdir)
        assert gremlins.name == ".gremlins"
        assert (gremlins / "config.json").exists()
        assert (gremlins / "repos").exists()
        assert (gremlins / "herald" / "social_log").exists()
        print("OK: init_gremlin_memory_global creates repos/ and herald/")


def test_init_gremlin_memory_per_repo():
    """init_gremlin_memory with repo_name creates repos/<name>/ subdirectory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = init_gremlin_memory(tmpdir, repo_name="GrumpRolled")
        assert repo_dir.name == "GrumpRolled"
        assert repo_dir.parent.name == "repos"
        assert (repo_dir / "config.json").exists()
        assert (repo_dir / "ledger" / "findings").exists()
        assert (repo_dir / "proposals").exists()
        assert (repo_dir / "social_log").exists()

        # Idempotent
        repo_dir2 = init_gremlin_memory(tmpdir, repo_name="GrumpRolled")
        assert repo_dir2 == repo_dir
        print("OK: init_gremlin_memory with repo_name creates per-repo subdirectory")


def test_multiple_repos():
    """Multiple repos should coexist under repos/."""
    with tempfile.TemporaryDirectory() as tmpdir:
        r1 = init_gremlin_memory(tmpdir, repo_name="GrumpRolled")
        r2 = init_gremlin_memory(tmpdir, repo_name="hat_stack")
        r3 = init_gremlin_memory(tmpdir, repo_name="HLF_MCP")

        assert r1.name == "GrumpRolled"
        assert r2.name == "hat_stack"
        assert r3.name == "HLF_MCP"
        assert r1 != r2 != r3
        print("OK: multiple repos coexist under repos/")


def test_list_repos():
    """list_repos should return per-repo metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        init_gremlin_memory(tmpdir, repo_name="GrumpRolled")
        init_gremlin_memory(tmpdir, repo_name="hat_stack")

        gremlins = Path(tmpdir) / ".gremlins"
        repos = list_repos(gremlins)
        assert len(repos) == 2
        names = [r["name"] for r in repos]
        assert "GrumpRolled" in names
        assert "hat_stack" in names
        # Each should have a config
        for r in repos:
            assert r["config"] is not None
            assert "repo_name" in r["config"]
        print("OK: list_repos returns per-repo metadata")


def test_write_ledger_per_repo():
    """write_ledger_entry should work with per-repo directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = init_gremlin_memory(tmpdir, repo_name="GrumpRolled")

        write_ledger_entry(
            repo_dir, "findings", "SQL Injection",
            "Found SQL injection in auth.py",
            author="black",
        )

        entries = read_ledger(repo_dir, category="findings")
        assert len(entries) == 1
        assert "SQL Injection" in entries[0]["title"]
        assert entries[0]["author"] == "black"
        print("OK: write/read ledger works per-repo")


def test_cross_repo_ledger():
    """read_ledger_all_repos should aggregate across repos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        r1 = init_gremlin_memory(tmpdir, repo_name="GrumpRolled")
        r2 = init_gremlin_memory(tmpdir, repo_name="hat_stack")

        write_ledger_entry(r1, "findings", "XSS in GrumpRolled", "desc", author="black")
        write_ledger_entry(r2, "findings", "SQL in hat_stack", "desc", author="black")

        gremlins = Path(tmpdir) / ".gremlins"
        all_entries = read_ledger_all_repos(gremlins, category="findings")
        assert len(all_entries) == 2
        repos_found = {e["repo"] for e in all_entries}
        assert repos_found == {"GrumpRolled", "hat_stack"}
        print("OK: read_ledger_all_repos aggregates across repos")


def test_herald_in_global_dir():
    """Cross-repo Herald should write to .gremlins/herald/social_log/."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gremlins = init_gremlin_memory_global(tmpdir)
        herald_dir = gremlins / "herald"

        write_herald(
            herald_dir,
            content="## Cross-Repo Digest\n\n- 2 repos scanned",
            author="blue",
        )

        entries = read_herald(herald_dir)
        assert len(entries) >= 1
        assert "Cross-Repo Digest" in entries[0]["content"]
        print("OK: Herald writes to global herald/ directory")


if __name__ == "__main__":
    tests = [
        test_init_gremlin_memory,
        test_init_moltbook_deprecated,
        test_migrate_moltbook_to_gremlins,
        test_migrate_moltbook_noop_when_no_old_dir,
        test_migrate_moltbook_noop_when_gremlins_exists,
        test_write_read_ledger,
        test_create_approve_proposal,
        test_create_reject_proposal,
        test_proposal_ttl_expiry,
        test_herald_write_read,
        test_auto_migration_on_init,
        test_init_gremlin_memory_global,
        test_init_gremlin_memory_per_repo,
        test_multiple_repos,
        test_list_repos,
        test_write_ledger_per_repo,
        test_cross_repo_ledger,
        test_herald_in_global_dir,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {test.__name__}: {e}")
            failed += 1

    print(f"\nGremlin memory tests: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)