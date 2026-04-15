#!/usr/bin/env python3
"""Unit tests for gates.py"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gates import (
    gate_cost_budget,
    gate_security_fast_path,
    gate_consistency,
    gate_timeout,
    gate_final_decision,
)

TEST_CONFIG = {
    "gates": {
        "cost_budget": {"max_usd_per_pr": 0.15, "max_tokens_per_pr": 150000},
        "security_fast_path": {"enabled": True, "trigger_severity": "CRITICAL"},
        "timeout": {"default_per_hat_seconds": 120},
    },
    "models": {
        "glm-5.1:cloud": {"tier": 1, "context_window": 200000, "input_cost_per_m": 0.40, "output_cost_per_m": 1.10},
        "devstral-2:123b-cloud": {"tier": 2, "context_window": 256000, "input_cost_per_m": 0.15, "output_cost_per_m": 0.60},
        "phi4-mini:3.8b": {"tier": 0, "context_window": 128000, "input_cost_per_m": 0.0, "output_cost_per_m": 0.0},
    },
    "hats": {
        "black": {"always_run": True, "primary_model": "devstral-2:123b-cloud", "fallback_model": "glm-5.1:cloud",
                  "max_tokens": 4096, "timeout_seconds": 150, "triggers": []},
        "blue": {"always_run": True, "primary_model": "phi4-mini:3.8b", "fallback_model": "gemma3:4b",
                 "max_tokens": 2048, "timeout_seconds": 60, "triggers": []},
        "red": {"always_run": False, "primary_model": "glm-5.1:cloud", "fallback_model": "devstral-2:123b-cloud",
                "max_tokens": 4096, "timeout_seconds": 120, "triggers": ["error"]},
        "gold": {"always_run": True, "primary_model": "glm-5.1:cloud", "fallback_model": "glm-5.1:cloud",
                 "max_tokens": 8192, "timeout_seconds": 300, "triggers": []},
    },
    "risk_score": {"allow_threshold": 20, "escalate_threshold": 60},
}


def test_cost_budget_pass():
    result = gate_cost_budget(TEST_CONFIG, ["black", "blue"], 1000)
    assert result["verdict"] in ("PASS", "TRIMMED", "BLOCKED")
    assert "estimated_cost" in result


def test_cost_budget_blocks():
    # Very large diff should push over budget
    result = gate_cost_budget(TEST_CONFIG, ["black", "blue", "red", "gold"], 10_000_000)
    assert result["verdict"] in ("BLOCKED", "TRIMMED")


def test_security_fast_path():
    report = {"findings": [{"severity": "CRITICAL", "title": "SQL Injection"}]}
    result = gate_security_fast_path(TEST_CONFIG, report)
    assert result["triggered"] is True
    assert result["action"] == "escalate"


def test_security_fast_path_clean():
    report = {"findings": [{"severity": "LOW", "title": "Style issue"}]}
    result = gate_security_fast_path(TEST_CONFIG, report)
    assert result["triggered"] is False
    assert result["action"] == "continue"


def test_consistency_no_conflicts():
    findings = [
        {"file": "a.ts", "line": 1, "category": "security", "severity": "HIGH", "title": "XSS", "recommendation": "fix"},
        {"file": "b.ts", "line": 1, "category": "performance", "severity": "MEDIUM", "title": "Slow query", "recommendation": "optimize"},
    ]
    result = gate_consistency(findings)
    assert result["verdict"] == "PASS"


def test_consistency_with_conflicts():
    findings = [
        {"file": "a.ts", "line": 1, "category": "add_feature", "severity": "HIGH", "title": "Add caching", "recommendation": "Add caching layer"},
        {"file": "a.ts", "line": 2, "category": "remove_feature", "severity": "MEDIUM", "title": "Remove caching", "recommendation": "Remove caching layer"},
    ]
    result = gate_consistency(findings)
    assert result["verdict"] == "CONFLICTS_DETECTED"


def test_timeout():
    result = gate_timeout(TEST_CONFIG, "black", 160)
    assert result["timed_out"] is True  # 160 > 150 limit

    result = gate_timeout(TEST_CONFIG, "black", 100)
    assert result["timed_out"] is False


def test_final_decision_allow():
    result = gate_final_decision("ALLOW", 10, TEST_CONFIG)
    assert result["verdict"] == "ALLOW"
    assert result["requires_human_review"] is False


def test_final_decision_escalate():
    result = gate_final_decision("ESCALATE", 35, TEST_CONFIG)
    assert result["verdict"] == "ESCALATE"
    assert result["requires_human_review"] is True


def test_final_decision_quarantine_with_fastpath():
    result = gate_final_decision("ALLOW", 10, TEST_CONFIG, security_fast_path_triggered=True)
    assert result["verdict"] == "QUARANTINE"
    assert result["requires_human_review"] is True


if __name__ == "__main__":
    test_cost_budget_pass()
    test_cost_budget_blocks()
    test_security_fast_path()
    test_security_fast_path_clean()
    test_consistency_no_conflicts()
    test_consistency_with_conflicts()
    test_timeout()
    test_final_decision_allow()
    test_final_decision_escalate()
    test_final_decision_quarantine_with_fastpath()
    print("All gates tests passed!")