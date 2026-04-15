#!/usr/bin/env python3
"""Unit tests for state.py"""

import sys
import os
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import (
    create_initial_state,
    update_state,
    finalize_state,
    get_pending_hats,
    save_checkpoint,
    load_checkpoint,
)


def test_create_initial_state():
    state = create_initial_state(
        run_id="test-run-1",
        trigger_type="manual",
        diff_content="test diff",
        triggered_hats=["black", "blue", "gold"],
    )
    assert state["run_id"] == "test-run-1"
    assert state["trigger_type"] == "manual"
    assert state["verdict"] is None
    assert state["completed_hats"] == []
    assert state["failed_hats"] == []
    assert state["timed_out_hats"] == []


def test_update_state_completed():
    state = create_initial_state(run_id="test-2", triggered_hats=["black", "blue", "gold"])
    update_state(state, completed_hat="black")
    assert "black" in state["completed_hats"]
    assert get_pending_hats(state) == ["blue", "gold"]


def test_update_state_failed():
    state = create_initial_state(run_id="test-3", triggered_hats=["black", "red", "gold"])
    update_state(state, failed_hat="red")
    assert "red" in state["failed_hats"]


def test_update_state_verdict():
    state = create_initial_state(run_id="test-4", triggered_hats=["black"])
    update_state(state, verdict="ALLOW", risk_score=5)
    assert state["verdict"] == "ALLOW"
    assert state["risk_score"] == 5


def test_finalize_state():
    state = create_initial_state(run_id="test-5", triggered_hats=[])
    assert state["completed_at"] is None
    finalize_state(state)
    assert state["completed_at"] is not None


def test_get_pending_hats():
    state = create_initial_state(run_id="test-6", triggered_hats=["black", "blue", "red", "gold"])
    update_state(state, completed_hat="black")
    update_state(state, failed_hat="blue")
    update_state(state, timed_out_hat="red")
    pending = get_pending_hats(state)
    assert pending == ["gold"]


def test_save_and_load_checkpoint():
    state = create_initial_state(
        run_id="test-checkpoint",
        trigger_type="pr",
        triggered_hats=["black", "gold"],
    )
    update_state(state, completed_hat="black", verdict="ALLOW", risk_score=3)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_checkpoint(state, tmpdir)
        assert path.exists()

        loaded = load_checkpoint("test-checkpoint", tmpdir)
        assert loaded is not None
        assert loaded["run_id"] == "test-checkpoint"
        assert loaded["verdict"] == "ALLOW"
        assert "black" in loaded["completed_hats"]


def test_load_checkpoint_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        loaded = load_checkpoint("nonexistent", tmpdir)
        assert loaded is None


if __name__ == "__main__":
    test_create_initial_state()
    test_update_state_completed()
    test_update_state_failed()
    test_update_state_verdict()
    test_finalize_state()
    test_get_pending_hats()
    test_save_and_load_checkpoint()
    test_load_checkpoint_missing()
    print("All state tests passed!")