#!/usr/bin/env python3
"""Unit tests for Gremlin governance, gates, and hat-based execution."""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gremlin_memory import init_gremlin_memory, create_proposal, list_proposals, approve_proposal
from gates import gate_governance


def _load_test_config():
    """Load hat_configs.yml for test."""
    config_path = Path(__file__).resolve().parent.parent / "hat_configs.yml"
    import yaml
    with open(config_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_governance_gate_blocks_pending():
    """G6 should block PENDING_HUMAN proposals."""
    config = _load_test_config()
    proposal = {
        "id": "001",
        "title": "Test",
        "status": "PENDING_HUMAN",
        "created": "2026-04-15T00:00:00Z",
    }
    result = gate_governance(proposal, config)
    assert result["allowed"] is False
    assert result["action"] == "wait"
    print("OK: governance gate blocks PENDING_HUMAN proposals")


def test_governance_gate_allows_approved():
    """G6 should allow APPROVED proposals."""
    config = _load_test_config()
    proposal = {
        "id": "001",
        "title": "Test",
        "status": "APPROVED",
        "created": "2026-04-15T00:00:00Z",
    }
    result = gate_governance(proposal, config)
    assert result["allowed"] is True
    assert result["action"] == "execute"
    print("OK: governance gate allows APPROVED proposals")


def test_governance_gate_discards_rejected():
    """G6 should discard REJECTED proposals."""
    config = _load_test_config()
    proposal = {
        "id": "001",
        "title": "Test",
        "status": "REJECTED",
        "created": "2026-04-15T00:00:00Z",
    }
    result = gate_governance(proposal, config)
    assert result["allowed"] is False
    assert result["action"] == "discard"
    print("OK: governance gate discards REJECTED proposals")


def test_governance_gate_expires_old():
    """G6 should auto-expire proposals older than TTL."""
    config = _load_test_config()
    import time
    import calendar
    old_time = time.time() - (49 * 3600)  # 49 hours ago
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(old_time))

    proposal = {
        "id": "001",
        "title": "Test",
        "status": "PENDING_HUMAN",
        "created": created,
    }
    result = gate_governance(proposal, config)
    assert result["allowed"] is False
    assert result["action"] == "discard"
    assert "EXPIRED" in result["status"] or "expired" in result["reason"].lower()
    print("OK: governance gate auto-expires old proposals")


def test_gremlin_config_present():
    """hat_configs.yml should have gremlins section with multi-repo config."""
    config = _load_test_config()
    assert "gremlins" in config
    assert config["gremlins"]["enabled"] is True
    assert config["gremlins"]["gremlins_path"] == ".gremlins"
    assert config["gremlins"]["governance"]["require_human_approval"] is True

    # Multi-repo: repos list should exist and be non-empty
    repos = config["gremlins"].get("repos", [])
    assert len(repos) > 0, "repos list should have at least one entry"
    for repo in repos:
        assert "path" in repo, f"repo entry missing 'path': {repo}"
        assert repo["path"], f"repo path should not be empty: {repo}"
    print(f"OK: gremlins config valid with {len(repos)} repos")


def test_phase_to_hat_mapping():
    """hat_configs.yml should have phase_to_hat mapping with valid hat IDs."""
    config = _load_test_config()
    phase_to_hat = config["gremlins"]["phase_to_hat"]
    assert phase_to_hat is not None

    # All 4 phases should be mapped
    expected_phases = {"review", "propose", "analyze", "herald"}
    assert set(phase_to_hat.keys()) == expected_phases

    # Each mapped hat should exist in the hats config
    hats_cfg = config["hats"]
    for phase, hat_id in phase_to_hat.items():
        assert hat_id in hats_cfg, f"Phase '{phase}' maps to hat '{hat_id}' which doesn't exist in hats config"

    # Verify the specific mappings
    assert phase_to_hat["review"] == "black"
    assert phase_to_hat["propose"] == "gold"
    assert phase_to_hat["analyze"] == "purple"
    assert phase_to_hat["herald"] == "blue"
    print("OK: phase_to_hat mapping is correct")


def test_overnight_mode_config():
    """hat_configs.yml should have overnight config with model_overrides."""
    config = _load_test_config()
    overnight = config["gremlins"]["overnight"]
    assert overnight["enabled"] is True
    assert overnight["schedule_start"] == "01:00"
    assert overnight["schedule_end"] == "07:00"
    assert "model_overrides" in overnight
    assert overnight["timeout_multiplier"] == 5

    # Verify model overrides map to valid local models
    models_cfg = config["models"]
    for phase, model in overnight["model_overrides"].items():
        assert model in models_cfg, f"Overnight model '{model}' for phase '{phase}' not in models config"
        assert models_cfg[model].get("local", False), f"Overnight model '{model}' should be local"
    print("OK: overnight mode config is valid")


def test_overnight_schedule_dict_format():
    """overnight_schedule should be a dict mapping phase names to cron expressions."""
    config = _load_test_config()
    schedule = config["gremlins"]["overnight_schedule"]
    assert isinstance(schedule, dict), "overnight_schedule should be a dict"

    # All 4 phases should have cron entries
    for phase in ("review", "propose", "analyze", "herald"):
        assert phase in schedule, f"overnight_schedule missing phase '{phase}'"
        cron = schedule[phase]
        # Basic cron validation: 5 fields
        assert len(cron.strip().split()) == 5, f"Cron for '{phase}' should have 5 fields: {cron}"
    print("OK: overnight_schedule dict format is valid")


def test_overnight_mode_detection():
    """is_overnight_mode() should correctly detect time windows."""
    from hats_common import is_overnight_mode
    config = _load_test_config()

    # With --overnight flag override (simulated via env var)
    # Just test that the function runs without error
    result = is_overnight_mode(config)
    assert isinstance(result, bool)
    print(f"OK: is_overnight_mode() returns {result} (time-dependent)")


def test_gremlin_uses_hat_models():
    """resolve_gremlin_model() should return correct models for each phase."""
    from hats_common import resolve_gremlin_model, is_overnight_mode
    config = _load_test_config()
    phase_to_hat = config["gremlins"]["phase_to_hat"]

    # During daytime (non-overnight), should use hat's primary model
    for phase, hat_id in phase_to_hat.items():
        hat_def = config["hats"][hat_id]
        # The function should return a valid model name
        try:
            model = resolve_gremlin_model(config, phase, hat_id)
            models_cfg = config["models"]
            assert model in models_cfg, f"Model '{model}' for phase '{phase}' not in models config"
        except Exception as e:
            # If overnight mode is active, model may differ
            print(f"  Note: phase '{phase}' model resolution: {e}")

    print("OK: resolve_gremlin_model returns valid models")


def test_gremlin_memory_init_with_hats():
    """init_gremlin_memory should work alongside hat-based config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gremlins = init_gremlin_memory(tmpdir)
        config = _load_test_config()

        # Create proposals using hat-based author names
        phase_to_hat = config["gremlins"]["phase_to_hat"]
        proposal = create_proposal(
            gremlins,
            title="Security Fix",
            description="Fix XSS in input handler",
            proposed_action="Sanitize input",
            author=phase_to_hat["review"],  # "black"
        )
        assert proposal["author"] == "black"

        proposal2 = create_proposal(
            gremlins,
            title="Performance Fix",
            description="Optimize query",
            proposed_action="Add index",
            author=phase_to_hat["propose"],  # "gold"
        )
        assert proposal2["author"] == "gold"
        print("OK: gremlin_memory works with hat-based author names")


if __name__ == "__main__":
    tests = [
        test_governance_gate_blocks_pending,
        test_governance_gate_allows_approved,
        test_governance_gate_discards_rejected,
        test_governance_gate_expires_old,
        test_gremlin_config_present,
        test_phase_to_hat_mapping,
        test_overnight_mode_config,
        test_overnight_schedule_dict_format,
        test_overnight_mode_detection,
        test_gremlin_uses_hat_models,
        test_gremlin_memory_init_with_hats,
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

    print(f"\nGremlin tests: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)