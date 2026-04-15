#!/usr/bin/env python3
"""
state.py — Run state persistence for Hat Stack.

Implements SPEC §9.1:
  - HatsRunState TypedDict matching the spec
  - Checkpoint save/load (JSON-based for simplicity, PostgreSQL optional)
  - Resume from checkpoint
"""

import json
import time
from pathlib import Path
from typing import Any, TypedDict


class HatFindingState(TypedDict, total=False):
    severity: str
    title: str
    description: str
    file: str | None
    line: int | None
    line_range: str | None
    category: str
    recommendation: str
    source_hat: str


class GateState(TypedDict, total=False):
    gate_id: str
    passed: bool
    details: dict


class HatsRunState(TypedDict, total=False):
    """Run state schema per SPEC §9.1.

    Tracks the full lifecycle of a hats pipeline run for
    checkpoint persistence and resume capability.
    """
    run_id: str
    trigger_type: str  # "pr" | "push" | "manual" | "task"
    pr_number: int | None
    repo: str
    sha: str
    diff_content: str
    changed_files: list[str]
    triggered_hats: list[str]
    completed_hats: list[str]
    failed_hats: list[str]
    timed_out_hats: list[str]
    findings: list[dict]
    gates: list[dict]
    verdict: str | None  # "ALLOW" | "ESCALATE" | "QUARANTINE" | None
    risk_score: int | None
    started_at: str
    completed_at: str | None
    sensitive_mode: bool
    metadata: dict


def create_initial_state(
    run_id: str,
    trigger_type: str = "manual",
    pr_number: int | None = None,
    repo: str = "",
    sha: str = "",
    diff_content: str = "",
    changed_files: list[str] | None = None,
    triggered_hats: list[str] | None = None,
    sensitive_mode: bool = False,
) -> HatsRunState:
    """Create a new HatsRunState with initial values."""
    return HatsRunState(
        run_id=run_id,
        trigger_type=trigger_type,
        pr_number=pr_number,
        repo=repo,
        sha=sha,
        diff_content=diff_content,
        changed_files=changed_files or [],
        triggered_hats=triggered_hats or [],
        completed_hats=[],
        failed_hats=[],
        timed_out_hats=[],
        findings=[],
        gates=[],
        verdict=None,
        risk_score=None,
        started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        completed_at=None,
        sensitive_mode=sensitive_mode,
        metadata={},
    )


def save_checkpoint(state: HatsRunState, checkpoint_dir: str | Path) -> Path:
    """Save run state to a JSON checkpoint file.

    Checkpoints are saved to `checkpoint_dir/<run_id>.json`.
    Returns the path to the checkpoint file.
    """
    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = checkpoint_dir / f"{state['run_id']}.json"
    with open(checkpoint_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, default=str)

    return checkpoint_path


def load_checkpoint(run_id: str, checkpoint_dir: str | Path) -> HatsRunState | None:
    """Load run state from a JSON checkpoint file.

    Returns None if no checkpoint exists for the given run_id.
    """
    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_path = checkpoint_dir / f"{run_id}.json"

    if not checkpoint_path.exists():
        return None

    with open(checkpoint_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    return HatsRunState(**data)


def update_state(
    state: HatsRunState,
    completed_hat: str | None = None,
    failed_hat: str | None = None,
    timed_out_hat: str | None = None,
    findings: list[dict] | None = None,
    gate: dict | None = None,
    verdict: str | None = None,
    risk_score: int | None = None,
) -> HatsRunState:
    """Update run state with new information.

    Returns the updated state (mutates in place and returns).
    """
    if completed_hat and completed_hat not in state.get("completed_hats", []):
        state.setdefault("completed_hats", []).append(completed_hat)

    if failed_hat and failed_hat not in state.get("failed_hats", []):
        state.setdefault("failed_hats", []).append(failed_hat)

    if timed_out_hat and timed_out_hat not in state.get("timed_out_hats", []):
        state.setdefault("timed_out_hats", []).append(timed_out_hat)

    if findings:
        state.setdefault("findings", []).extend(findings)

    if gate:
        state.setdefault("gates", []).append(gate)

    if verdict:
        state["verdict"] = verdict

    if risk_score is not None:
        state["risk_score"] = risk_score

    return state


def finalize_state(state: HatsRunState) -> HatsRunState:
    """Mark the run as completed with a timestamp."""
    state["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return state


def get_pending_hats(state: HatsRunState) -> list[str]:
    """Get hats that haven't completed, failed, or timed out yet."""
    triggered = set(state.get("triggered_hats", []))
    done = (
        set(state.get("completed_hats", []))
        | set(state.get("failed_hats", []))
        | set(state.get("timed_out_hats", []))
    )
    return [h for h in state.get("triggered_hats", []) if h not in done]