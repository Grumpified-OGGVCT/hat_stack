#!/usr/bin/env python3
"""Unit tests for consolidator.py"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from consolidator import (
    normalize_severity,
    severity_rank,
    dedup_key,
    consolidate_findings,
)


def test_normalize_severity():
    assert normalize_severity("CRITICAL") == "CRITICAL"
    assert normalize_severity("critical") == "CRITICAL"
    assert normalize_severity("FATAL") == "CRITICAL"
    assert normalize_severity("WARN") == "MEDIUM"
    assert normalize_severity("unknown") == "LOW"
    assert normalize_severity("") == "LOW"


def test_severity_rank():
    assert severity_rank("CRITICAL") > severity_rank("HIGH")
    assert severity_rank("HIGH") > severity_rank("MEDIUM")
    assert severity_rank("MEDIUM") > severity_rank("LOW")
    assert severity_rank("LOW") > severity_rank("INFO")


def test_dedup_key():
    finding = {"file": "src/app.ts", "line": 42, "line_range": "42-50", "category": "security"}
    key = dedup_key(finding)
    assert key == ("src/app.ts", "42-50", "security")


def test_consolidate_deduplicates():
    reports = [
        {
            "hat_name": "Black Hat",
            "emoji": "⚫",
            "model_used": "devstral-2:123b-cloud",
            "latency_seconds": 10.0,
            "token_usage": {"input": 1000, "output": 500},
            "error": None,
            "findings": [
                {"severity": "HIGH", "title": "SQL Injection", "description": "Unsanitized input",
                 "file": "db.ts", "line": 42, "category": "security", "recommendation": "Use parameterized queries"},
            ],
        },
        {
            "hat_name": "Red Hat",
            "emoji": "🔴",
            "model_used": "deepseek-v3.2:cloud",
            "latency_seconds": 8.0,
            "token_usage": {"input": 800, "output": 400},
            "error": None,
            "findings": [
                # Same file+line+category -> duplicate, but lower severity -> should be deduped
                {"severity": "MEDIUM", "title": "SQL Injection risk", "description": "Input not sanitized",
                 "file": "db.ts", "line": 42, "category": "security", "recommendation": "Sanitize input"},
            ],
        },
    ]

    result = consolidate_findings(reports)
    assert result["hats_executed"] == 2
    assert result["dedup_stats"]["original_count"] == 2
    assert result["dedup_stats"]["deduplicated_count"] == 1
    assert result["dedup_stats"]["removed_duplicates"] == 1
    # The HIGH severity finding should be kept over MEDIUM
    assert result["all_findings"][0]["severity"] == "HIGH"


def test_consolidate_keeps_highest_severity():
    reports = [
        {
            "hat_name": "Red Hat", "emoji": "🔴", "model_used": "test",
            "latency_seconds": 5.0, "token_usage": {"input": 100, "output": 50}, "error": None,
            "findings": [
                {"severity": "LOW", "title": "Issue", "description": "d", "file": "a.ts",
                 "line": 1, "category": "style", "recommendation": "fix"},
            ],
        },
        {
            "hat_name": "Black Hat", "emoji": "⚫", "model_used": "test",
            "latency_seconds": 5.0, "token_usage": {"input": 100, "output": 50}, "error": None,
            "findings": [
                # Same key, higher severity
                {"severity": "CRITICAL", "title": "Issue!", "description": "d!", "file": "a.ts",
                 "line": 1, "category": "style", "recommendation": "fix now"},
            ],
        },
    ]

    result = consolidate_findings(reports)
    assert len(result["all_findings"]) == 1
    assert result["all_findings"][0]["severity"] == "CRITICAL"


def test_consolidate_timed_out_hats():
    reports = [
        {
            "hat_name": "Blue Hat", "emoji": "🔵", "model_used": "phi4-mini",
            "latency_seconds": 5.0, "token_usage": {"input": 100, "output": 50}, "error": None,
            "findings": [],
        },
    ]

    result = consolidate_findings(reports, timed_out_hats=["red"])
    assert "red" in result["not_evaluated_hats"]


if __name__ == "__main__":
    test_normalize_severity()
    test_severity_rank()
    test_dedup_key()
    test_consolidate_deduplicates()
    test_consolidate_keeps_highest_severity()
    test_consolidate_timed_out_hats()
    print("All consolidator tests passed!")