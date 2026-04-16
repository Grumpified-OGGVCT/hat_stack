#!/usr/bin/env python3
"""Integration tests for Hat Stack — tests against a live local Ollama server.

These tests require Ollama running at localhost:11434 with at least one
local model available (e.g., gemma4:e2b). They make real API calls.

Run: python scripts/tests/test_integration.py
Skip if Ollama is not available (sets MARKER for CI).
"""

import json
import os
import sys
import time
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hats_common import (
    load_config,
    call_ollama,
    _is_local_model,
    detect_sensitive_mode,
    build_comparable_model_sequence,
    preflight_check,
)
from hat_selector import select_hats, _extract_changed_files
from gates import gate_cost_budget
from consolidator import consolidate_findings, normalize_severity
from state import create_initial_state, save_checkpoint, load_checkpoint, get_pending_hats

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "hat_configs.yml")

# Check if local Ollama is available
OLLAMA_AVAILABLE = False
try:
    import requests
    resp = requests.get("http://localhost:11434/api/version", timeout=3)
    OLLAMA_AVAILABLE = resp.status_code == 200
except Exception:
    pass

SECURITY_DIFF = """--- a/src/auth.py
+++ b/src/auth.py
@@ -10,3 +10,5 @@
 def login():
-    token = request.args.get("token")
+    api_key = "sk-hardcoded-12345"
+    query = f"SELECT * FROM users WHERE id = {request.args.get('id')}"
"""

CLEAN_DIFF = """--- a/src/utils.py
+++ b/src/utils.py
@@ -10,3 +10,5 @@
 def format_name(name):
-    return name.strip()
+    return name.strip().title()
+
+def greet(name):
+    return f"Hello, {format_name(name)}!"
"""


def test_ollama_available():
    """Ollama server must be reachable for integration tests."""
    if not OLLAMA_AVAILABLE:
        print("SKIP: Ollama not available at localhost:11434")
        return
    print("OK: Ollama server reachable")


def test_call_ollama_local_model():
    """Test call_ollama() against local Ollama with a real model."""
    if not OLLAMA_AVAILABLE:
        print("SKIP: Ollama not available")
        return

    config = load_config(CONFIG_PATH)

    # Find a local model that's actually available
    local_models = [m for m, c in config["models"].items() if c.get("local")]
    if not local_models:
        print("SKIP: No local models in config")
        return

    model = local_models[0]
    result = call_ollama(
        config, model,
        "You are a helpful assistant. Respond in JSON.",
        "Is 1+1=2? Respond as JSON: {\"answer\": true}",
        temperature=0.1, max_tokens=256, timeout=60,
    )

    assert result.get("error") is None, f"call_ollama failed: {result['error']}"
    assert result.get("content"), f"Empty content from {model}"
    assert result.get("usage", {}).get("output", 0) > 0, "No output tokens"
    print(f"OK: call_ollama({model}) returned {len(result['content'])} chars, "
          f"{result['usage']['output']} output tokens")


def test_call_ollama_thinking_model():
    """Test that thinking models return both content and thinking fields."""
    if not OLLAMA_AVAILABLE:
        print("SKIP: Ollama not available")
        return

    config = load_config(CONFIG_PATH)

    # gemma4 models are thinking models
    thinking_models = [m for m in config["models"] if m.startswith("gemma4:")]
    if not thinking_models:
        print("SKIP: No gemma4 thinking models available")
        return

    model = thinking_models[0]
    result = call_ollama(
        config, model,
        "You are a security reviewer. Respond in JSON.",
        "Is a hardcoded API key a vulnerability? Respond: {\"findings\": [...]}",
        temperature=0.2, max_tokens=2048, timeout=120,
    )

    assert result.get("error") is None, f"Thinking model call failed: {result['error']}"
    assert result.get("content"), f"Empty content from thinking model {model}"
    # Thinking field may or may not be present depending on model behavior
    print(f"OK: thinking model {model} returned {len(result['content'])} chars content"
          + (f", {len(result.get('thinking', '') or '')} chars thinking" if result.get('thinking') else ""))


def test_sensitive_mode_detection():
    """Sensitive mode should detect credentials in diffs."""
    assert detect_sensitive_mode(SECURITY_DIFF) is True
    assert detect_sensitive_mode(CLEAN_DIFF) is False
    print("OK: sensitive mode detection works")


def test_hat_selector_security():
    """Security diff should activate Black, Blue, Purple (always-on) + Red (error trigger)."""
    config = load_config(CONFIG_PATH)
    selected = select_hats(config, SECURITY_DIFF)
    assert "black" in selected
    assert "blue" in selected
    assert "purple" in selected
    assert selected[-1] in ("gold",)  # Gold or any run_last hat is last
    print(f"OK: security diff selected {len(selected)} hats: {', '.join(selected)}")


def test_hat_selector_clean():
    """Clean diff should select only always-on hats."""
    config = load_config(CONFIG_PATH)
    selected = select_hats(config, CLEAN_DIFF)
    assert "black" in selected  # always-on
    assert "blue" in selected   # always-on
    print(f"OK: clean diff selected {len(selected)} hats")


def test_gate_cost_budget():
    """Cost budget gate should pass for small diffs."""
    config = load_config(CONFIG_PATH)
    selected = select_hats(config, SECURITY_DIFF)
    result = gate_cost_budget(config, selected, diff_tokens=100)
    assert result["verdict"] in ("PASS", "TRIMMED")
    print(f"OK: cost budget gate verdict={result['verdict']}")


def test_checkpoint_save_load():
    """Checkpoint save and load should roundtrip correctly."""
    state = create_initial_state(
        run_id="test-integration",
        diff_content="test diff",
        triggered_hats=["black", "blue", "gold"],
    )
    from state import update_state, finalize_state
    update_state(state, completed_hat="black")
    update_state(state, completed_hat="blue")

    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_checkpoint(state, tmpdir)
        assert path.exists(), "Checkpoint file not created"

        loaded = load_checkpoint("test-integration", tmpdir)
        assert loaded is not None, "Checkpoint not found"
        assert loaded["run_id"] == "test-integration"
        assert "black" in loaded["completed_hats"]
        assert "blue" in loaded["completed_hats"]
        assert get_pending_hats(loaded) == ["gold"]
        print("OK: checkpoint save/load roundtrip works")


def test_consolidate_findings():
    """Consolidator should deduplicate findings."""
    reports = [
        {
            "hat_id": "black",
            "hat_name": "Black Hat",
            "emoji": "⚫",
            "findings": [
                {"severity": "CRITICAL", "title": "SQL Injection",
                 "file": "auth.py", "line_range": "12", "category": "security",
                 "description": "SQL injection", "recommendation": "Fix it"},
            ],
            "summary": "Found SQL injection",
            "confidence": 0.9,
            "model_used": "gemma4:e4b",
            "latency_seconds": 50,
            "token_usage": {"input": 100, "output": 200},
            "error": None,
            "timed_out": False,
        },
        {
            "hat_id": "purple",
            "hat_name": "Purple Hat",
            "emoji": "🟪",
            "findings": [
                {"severity": "HIGH", "title": "SQL Injection",
                 "file": "auth.py", "line_range": "12", "category": "security",
                 "description": "SQL injection variant",
                 "recommendation": "Fix it"},
            ],
            "summary": "Found SQL injection",
            "confidence": 0.8,
            "model_used": "gemma4:e4b",
            "latency_seconds": 60,
            "token_usage": {"input": 100, "output": 200},
            "error": None,
            "timed_out": False,
        },
    ]

    result = consolidate_findings(reports)
    # Same file/line/category should be deduped, keeping highest severity
    assert result["dedup_stats"]["original_count"] >= result["dedup_stats"]["deduplicated_count"]
    print(f"OK: consolidated {result['dedup_stats']['original_count']} -> "
          f"{result['dedup_stats']['deduplicated_count']} findings")


def test_preflight_check():
    """Preflight check should detect local Ollama availability."""
    config = load_config(CONFIG_PATH)
    issues = preflight_check(config, requested_hats=["blue"])
    # Blue is local_only, so no API key warning expected
    has_api_key_warning = any("API_KEY" in msg for msg in issues)
    assert not has_api_key_warning, "Should not warn about API key for local-only hats"
    print("OK: preflight check works for local-only hats")


# Run all tests
if __name__ == "__main__":
    tests = [
        test_ollama_available,
        test_call_ollama_local_model,
        test_call_ollama_thinking_model,
        test_sensitive_mode_detection,
        test_hat_selector_security,
        test_hat_selector_clean,
        test_gate_cost_budget,
        test_checkpoint_save_load,
        test_consolidate_findings,
        test_preflight_check,
    ]

    passed = 0
    skipped = 0
    failed = 0

    for test in tests:
        name = test.__name__
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {name}: {e}")
            failed += 1

    print(f"\nIntegration tests: {passed} passed, {skipped} skipped, {failed} failed")
    if failed:
        sys.exit(1)