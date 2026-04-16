#!/usr/bin/env python3
"""Unit tests for hats_common.py"""

import sys
import os
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hats_common import (
    detect_sensitive_mode,
    build_comparable_model_sequence,
    estimate_cost,
    truncate_to_context_window,
    RetryPolicy,
    CircuitBreakerState,
    CircuitBreakerRegistry,
    LocalModelQueue,
    CloudModelPool,
    ConcurrencyCoordinator,
    load_config,
)

# Minimal config for testing
TEST_CONFIG = {
    "api": {
        "cloud_url_env": "OLLAMA_CLOUD_URL",
        "default_cloud_url": "https://ollama.com",
        "local_url_env": "OLLAMA_LOCAL_URL",
        "default_local_url": "http://localhost:11434",
        "api_key_env": "OLLAMA_API_KEY",
    },
    "models": {
        "glm-5.1:cloud": {"tier": 1, "context_window": 200000, "input_cost_per_m": 0.40, "output_cost_per_m": 1.10, "local": False},
        "deepseek-v3.2:cloud": {"tier": 1, "context_window": 128000, "input_cost_per_m": 0.10, "output_cost_per_m": 0.28, "local": False},
        "devstral-2:123b-cloud": {"tier": 2, "context_window": 256000, "input_cost_per_m": 0.15, "output_cost_per_m": 0.60, "local": False},
        "gemma4:e2b": {"tier": 0, "context_window": 128000, "input_cost_per_m": 0.0, "output_cost_per_m": 0.0, "local": True},
        "gemma4:e4b": {"tier": 0, "context_window": 128000, "input_cost_per_m": 0.0, "output_cost_per_m": 0.0, "local": True},
        "qwen3.5:9b": {"tier": 0, "context_window": 128000, "input_cost_per_m": 0.0, "output_cost_per_m": 0.0, "local": True},
        "phi4-mini:3.8b": {"tier": 0, "context_window": 128000, "input_cost_per_m": 0.0, "output_cost_per_m": 0.0, "local": True},
        "gemma3:4b": {"tier": 0, "context_window": 128000, "input_cost_per_m": 0.0, "output_cost_per_m": 0.0, "local": True},
    },
    "hats": {
        "black": {"name": "Black Hat", "emoji": "⚫", "number": 2, "always_run": True,
                  "primary_model": "devstral-2:123b-cloud", "fallback_model": "glm-5.1:cloud",
                  "local_model": "gemma4:e4b", "local_only": False,
                  "temperature": 0.2, "max_tokens": 4096, "timeout_seconds": 150, "triggers": [],
                  "persona": "Test persona"},
        "blue": {"name": "Blue Hat", "emoji": "🔵", "number": 6, "always_run": True,
                 "primary_model": "gemma4:e2b", "fallback_model": "gemma4:e4b",
                 "local_model": "gemma4:e2b", "local_only": True,
                 "temperature": 0.1, "max_tokens": 2048, "timeout_seconds": 300, "triggers": [],
                 "persona": "Test persona"},
        "red": {"name": "Red Hat", "emoji": "🔴", "number": 1, "always_run": False,
                "primary_model": "deepseek-v3.2:cloud", "fallback_model": "glm-5.1:cloud",
                "local_model": "qwen3.5:9b",
                "temperature": 0.3, "max_tokens": 4096, "timeout_seconds": 120,
                "triggers": ["error", "retry"], "persona": "Test persona"},
    },
    "gates": {"cost_budget": {"max_usd_per_pr": 0.15}},
    "execution": {
        "max_concurrent_hats": 6,
        "max_cloud_parallel": 4,
        "retry": {"max_attempts": 3, "initial_backoff_seconds": 1, "backoff_multiplier": 2, "max_backoff_seconds": 10},
    },
    "risk_score": {"critical_weight": 20, "critical_cap": 80, "high_weight": 5, "high_cap": 40,
                   "medium_weight": 1, "medium_cap": 10, "low_weight": 0.1, "low_cap": 5,
                   "allow_threshold": 20, "escalate_threshold": 60},
}


def test_detect_sensitive_mode_env():
    assert detect_sensitive_mode("--- a/.env\n+++ b/.env\nAPI_KEY=abc123") is True


def test_detect_sensitive_mode_auth():
    assert detect_sensitive_mode("--- a/src/auth.ts\n+++ b/src/auth.ts\n") is True


def test_detect_sensitive_mode_credential():
    assert detect_sensitive_mode("--- a/credentials.json\n+++ b/credentials.json\n") is True


def test_detect_sensitive_mode_clean():
    assert detect_sensitive_mode("--- a/src/utils.ts\n+++ b/src/utils.ts\nexport function add() {}") is False


def test_detect_sensitive_mode_api_key_value():
    assert detect_sensitive_mode('api_key = "sk-1234567890abcdef"') is True


def test_detect_sensitive_mode_ssn():
    assert detect_sensitive_mode("ssn = 123-45-6789") is True


def test_detect_sensitive_mode_changed_files():
    assert detect_sensitive_mode("", changed_files=["src/auth.ts"]) is True
    assert detect_sensitive_mode("", changed_files=["src/utils.ts"]) is False


def test_build_comparable_model_sequence():
    # When OLLAMA_API_KEY is set, cloud models should appear
    original_key = os.environ.get("OLLAMA_API_KEY")
    try:
        os.environ["OLLAMA_API_KEY"] = "test-key"
        chain = build_comparable_model_sequence(TEST_CONFIG, "glm-5.1:cloud", "deepseek-v3.2:cloud")
        assert chain[0] == "glm-5.1:cloud"
        assert chain[1] == "deepseek-v3.2:cloud"
        assert len(chain) >= 2

        # Without API key, cloud models are filtered out
        del os.environ["OLLAMA_API_KEY"]
        chain_local = build_comparable_model_sequence(TEST_CONFIG, "glm-5.1:cloud", "deepseek-v3.2:cloud")
        # Only local models should appear
        for m in chain_local:
            assert TEST_CONFIG["models"][m].get("local", False) is True
        assert len(chain_local) >= 1
    finally:
        if original_key:
            os.environ["OLLAMA_API_KEY"] = original_key
        elif "OLLAMA_API_KEY" in os.environ:
            del os.environ["OLLAMA_API_KEY"]


def test_estimate_cost():
    cost, within = estimate_cost(TEST_CONFIG, ["black", "red"], 1000)
    assert cost > 0
    assert isinstance(within, bool)


def test_truncate_to_context_window():
    short_text = "Hello world"
    assert truncate_to_context_window(short_text, 128000) == short_text

    long_text = "x" * 1_000_000
    truncated = truncate_to_context_window(long_text, 32000)
    assert len(truncated) < len(long_text)
    assert "truncated" in truncated.lower()


def test_retry_policy():
    rp = RetryPolicy(max_attempts=3, initial_backoff=1.0, multiplier=2.0, max_backoff=10.0)
    assert rp.max_attempts == 3
    backoff = rp.compute_backoff(0)
    assert 0.8 <= backoff <= 1.2  # 1.0 ± 20%


def test_retry_policy_is_retryable():
    rp = RetryPolicy()
    assert rp.is_retryable_error("429 Too Many Requests") is True
    assert rp.is_retryable_error("500 Internal Server Error") is True
    assert rp.is_retryable_error("401 Unauthorized") is False
    assert rp.is_retryable_error("Timeout after 30s") is True


def test_circuit_breaker():
    cb = CircuitBreakerState(failure_threshold=3, reset_timeout_seconds=0.1)
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.allow_request() is True

    cb.record_failure()
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.allow_request() is False

    time.sleep(0.15)
    assert cb.state == CircuitBreakerState.HALF_OPEN
    assert cb.allow_request() is True

    cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED


def test_circuit_breaker_registry():
    reg = CircuitBreakerRegistry()
    assert reg.allow_request("hat", "black") is True
    for _ in range(5):
        reg.record_failure("hat", "black")
    assert reg.allow_request("hat", "black") is False


def test_local_model_queue():
    q = LocalModelQueue()
    acquired = []
    with q:
        acquired.append(True)
    assert acquired == [True]


def test_local_model_queue_serialization():
    q = LocalModelQueue()
    results = []
    errors = []

    def worker(idx):
        try:
            with q:
                time.sleep(0.05)
                results.append(idx)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(results) == 3
    # Results should be in order since local queue serializes
    assert results == sorted(results)


def test_concurrency_coordinator_classify():
    coord = ConcurrencyCoordinator(max_cloud=4)
    # Blue is local_only -> "local"
    assert coord.classify_hat(TEST_CONFIG, "blue", sensitive_mode=False) == "local"
    # Black is dual-mode: cloud normally, local when sensitive
    assert coord.classify_hat(TEST_CONFIG, "black", sensitive_mode=False) == "cloud"
    assert coord.classify_hat(TEST_CONFIG, "black", sensitive_mode=True) == "local"


def test_concurrency_coordinator_model_selection():
    coord = ConcurrencyCoordinator(max_cloud=4)
    # Blue always uses local model (gemma4:e2b)
    assert coord.get_model_for_hat(TEST_CONFIG, "blue", sensitive_mode=False) == "gemma4:e2b"
    # Black uses cloud model normally
    assert coord.get_model_for_hat(TEST_CONFIG, "black", sensitive_mode=False) == "devstral-2:123b-cloud"
    # Black uses local model when sensitive (gemma4:e4b)
    assert coord.get_model_for_hat(TEST_CONFIG, "black", sensitive_mode=True) == "gemma4:e4b"


if __name__ == "__main__":
    test_detect_sensitive_mode_env()
    test_detect_sensitive_mode_auth()
    test_detect_sensitive_mode_credential()
    test_detect_sensitive_mode_clean()
    test_detect_sensitive_mode_api_key_value()
    test_detect_sensitive_mode_ssn()
    test_detect_sensitive_mode_changed_files()
    test_build_comparable_model_sequence()
    test_estimate_cost()
    test_truncate_to_context_window()
    test_retry_policy()
    test_retry_policy_is_retryable()
    test_circuit_breaker()
    test_circuit_breaker_registry()
    test_local_model_queue()
    test_local_model_queue_serialization()
    test_concurrency_coordinator_classify()
    test_concurrency_coordinator_model_selection()
    print("All hats_common tests passed!")