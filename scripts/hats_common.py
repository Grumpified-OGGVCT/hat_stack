#!/usr/bin/env python3
"""
hats_common.py — Shared library for Hat Stack runners.

Extracted from hats_runner.py and hats_task_runner.py to eliminate duplication.
Provides:
  - Config loading
  - Multi-provider LLM API calls with retry, exponential backoff, and circuit breaker
  - Provider routing (Ollama Local, Ollama Cloud, OpenRouter, and any OpenAI-compatible API)
  - Local-only mode enforcement (PII-safe, no-cloud operation)
  - Sensitive mode detection (credentials/PII)
  - Model fallback chain construction with cross-provider support
  - Cost estimation
  - Context window truncation
  - Concurrency primitives: LocalModelQueue, CloudModelPool, ConcurrencyCoordinator
  - Shared type definitions
"""

import json
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, TypedDict

import requests
import yaml

from provider_router import ProviderRouter, get_router, clear_router_cache


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR / "hat_configs.yml"


# ---------------------------------------------------------------------------
# Shared type definitions
# ---------------------------------------------------------------------------

class HatFinding(TypedDict, total=False):
    severity: str
    title: str
    description: str
    file: str | None
    line: int | None
    line_range: str | None
    category: str
    recommendation: str
    source_hat: str
    source_emoji: str
    conflicted: bool


class HatReport(TypedDict, total=False):
    hat_id: str
    hat_name: str
    emoji: str
    model_used: str
    latency_seconds: float
    token_usage: dict
    error: str | None
    findings: list[dict]
    summary: str
    confidence: float


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config(config_path: str | Path) -> dict:
    """Load hat configuration from YAML file."""
    with open(config_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Retry policy — SPEC §8.1
# ---------------------------------------------------------------------------

class RetryPolicy:
    """Implements SPEC §8.1 retry with exponential backoff and jitter.

    Parameters:
        max_attempts: Maximum retry attempts (default 3)
        initial_backoff: Initial backoff in seconds (default 1.0)
        multiplier: Backoff multiplier (default 2.0)
        max_backoff: Maximum backoff in seconds (default 10.0)
        jitter_fraction: Jitter as ±fraction of backoff (default 0.2)
    """

    def __init__(self, max_attempts: int = 3, initial_backoff: float = 1.0,
                 multiplier: float = 2.0, max_backoff: float = 10.0,
                 jitter_fraction: float = 0.2):
        self.max_attempts = max_attempts
        self.initial_backoff = initial_backoff
        self.multiplier = multiplier
        self.max_backoff = max_backoff
        self.jitter_fraction = jitter_fraction

    @classmethod
    def from_config(cls, config: dict) -> "RetryPolicy":
        """Build RetryPolicy from the execution.retry section of hat_configs.yml."""
        retry_cfg = config.get("execution", {}).get("retry", {})
        return cls(
            max_attempts=retry_cfg.get("max_attempts", 3),
            initial_backoff=retry_cfg.get("initial_backoff_seconds", 1.0),
            multiplier=retry_cfg.get("backoff_multiplier", 2.0),
            max_backoff=retry_cfg.get("max_backoff_seconds", 10.0),
        )

    def compute_backoff(self, attempt: int) -> float:
        """Compute backoff duration for a given attempt number (0-indexed)."""
        import random
        base = min(self.initial_backoff * (self.multiplier ** attempt), self.max_backoff)
        jitter = base * self.jitter_fraction
        return base + random.uniform(-jitter, jitter)

    @staticmethod
    def is_retryable_error(error_str: str) -> bool:
        """Determine if an error is retryable per SPEC §8.1.

        Retryable: 429, 500, 502, 503, 504, timeout, connection error
        Non-retryable: 401, 400, content policy
        """
        retryable_indicators = ["429", "500", "502", "503", "504", "timeout", "timed out",
                                "connection", "reset", "overloaded"]
        non_retryable_indicators = ["401", "403", "content_policy", "content policy",
                                    "invalid api key", "unauthorized"]

        error_lower = error_str.lower()
        for indicator in non_retryable_indicators:
            if indicator in error_lower:
                return False
        for indicator in retryable_indicators:
            if indicator in error_lower:
                return True
        # Default: retry on unknown errors (conservative)
        return True


# ---------------------------------------------------------------------------
# Circuit breaker — SPEC §8.3
# ---------------------------------------------------------------------------

class CircuitBreakerState:
    """Per-hat and per-provider circuit breaker per SPEC §8.3.

    States: CLOSED (normal), OPEN (blocking), HALF-OPEN (probing).
    Opens after `failure_threshold` consecutive failures.
    Stays open for `reset_timeout_seconds`, then transitions to HALF-OPEN.
    One successful call in HALF-OPEN → CLOSED.
    One failure in HALF-OPEN → OPEN again.
    """

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(self, failure_threshold: int = 5, reset_timeout_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == self.OPEN:
                if time.time() - self._last_failure_time >= self.reset_timeout_seconds:
                    self._state = self.HALF_OPEN
            return self._state

    def record_success(self):
        with self._lock:
            self._failure_count = 0
            self._state = self.CLOSED

    def record_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                self._state = self.OPEN

    def allow_request(self) -> bool:
        """Check if a request should be allowed."""
        current = self.state
        if current == self.CLOSED:
            return True
        if current == self.HALF_OPEN:
            return True  # Allow one probe
        return False  # OPEN


class CircuitBreakerRegistry:
    """Registry of circuit breakers keyed by (scope, name).

    scope can be 'hat' or 'provider'.
    Per-hat: 5 failures → 60s open (SPEC §8.3)
    Per-provider: 10 failures → 120s open (SPEC §8.3)
    """

    def __init__(self):
        self._breakers: dict[tuple[str, str], CircuitBreakerState] = {}
        self._lock = threading.Lock()

    def get(self, scope: str, name: str) -> CircuitBreakerState:
        key = (scope, name)
        with self._lock:
            if key not in self._breakers:
                threshold = 10 if scope == "provider" else 5
                timeout = 120.0 if scope == "provider" else 60.0
                self._breakers[key] = CircuitBreakerState(
                    failure_threshold=threshold,
                    reset_timeout_seconds=timeout,
                )
            return self._breakers[key]

    def allow_request(self, scope: str, name: str) -> bool:
        return self.get(scope, name).allow_request()

    def record_success(self, scope: str, name: str):
        self.get(scope, name).record_success()

    def record_failure(self, scope: str, name: str):
        self.get(scope, name).record_failure()


# Global circuit breaker registry
_circuit_breakers = CircuitBreakerRegistry()


# ---------------------------------------------------------------------------
# Context window truncation
# ---------------------------------------------------------------------------

def truncate_to_context_window(text: str, context_window: int, reserve_output: int = 4096) -> str:
    """Truncate input text to fit within a model's context window.

    Reserves `reserve_output` tokens for the model's response.
    Assumes ~4 characters per token.
    """
    max_input_chars = (context_window - reserve_output) * 4
    if len(text) <= max_input_chars:
        return text
    # Truncate with a marker so the model knows content was cut
    return text[:max_input_chars - 100] + "\n\n[... content truncated to fit context window ...]"


# ---------------------------------------------------------------------------
# LLM API caller with multi-provider routing + retry + circuit breaker
# ---------------------------------------------------------------------------

def _is_local_model(config: dict, model: str) -> bool:
    """Check if a model is configured as local (runs on localhost Ollama)."""
    models_cfg = config.get("models", {})
    model_cfg = models_cfg.get(model, {})
    return bool(model_cfg.get("local", False))


def _has_available_provider(config: dict, model_name: str) -> bool:
    """Check if a model's provider has the necessary credentials available."""
    models_cfg = config.get("models", {})
    model_cfg = models_cfg.get(model_name, {})

    if model_cfg.get("local", False):
        return True  # Local models always available

    # Check explicit provider
    provider_name = model_cfg.get("provider")
    if provider_name:
        providers_cfg = config.get("providers", {})
        provider_cfg = providers_cfg.get(provider_name, {})
        api_key_env = provider_cfg.get("api_key_env", "")
        if api_key_env and not os.environ.get(api_key_env, ""):
            return False
        if not provider_cfg.get("enabled", True):
            return False

    return True


# Alias for new code — call_llm is the preferred name going forward
call_llm = None  # Forward reference, set after call_ollama definition


def call_ollama(config: dict, model: str, system_prompt: str, user_prompt: str,
                temperature: float = 0.3, max_tokens: int = 4096,
                timeout: int = 120, retry_policy: RetryPolicy | None = None,
                hat_id: str | None = None) -> dict:
    """Call an LLM model via the appropriate provider.

    Multi-provider routing: uses ProviderRouter to determine which API endpoint
    and format to use based on the model's `provider` field in config. Supports
    Ollama native (/api/chat) and OpenAI-compatible (/v1/chat/completions) APIs.

    Local-only mode: If config.local_only.enabled is true, cloud models are
    blocked (returns error to trigger fallback chain).

    Implements SPEC §8 retry policy with exponential backoff and jitter.
    Implements SPEC §8.3 circuit breaker (per-hat and per-provider).
    Truncates input to model's context window before sending.
    """
    router = get_router(config)
    models_cfg = config.get("models", {})
    model_cfg = models_cfg.get(model, {})
    is_local = model_cfg.get("local", False)

    # --- Local-only mode enforcement ---
    if router.is_local_only_mode() and not is_local:
        return {
            "error": "Local-only mode: cloud models disabled",
            "model": model,
            "content": None,
            "usage": {"input": 0, "output": 0},
        }

    # --- Get provider and resolve routing ---
    provider = router.get_provider(model)
    model_id = router.get_model_id(model)

    # Check provider availability
    if not is_local and not provider.is_available():
        return {
            "error": f"Provider {provider.name} not available (missing API key or disabled)",
            "model": model,
            "content": None,
            "usage": {"input": 0, "output": 0},
        }

    # --- Truncate input to fit context window ---
    context_window = model_cfg.get("context_window", 128000)
    combined_input = system_prompt + "\n" + user_prompt
    truncated_input = truncate_to_context_window(combined_input, context_window, reserve_output=max_tokens)
    if len(combined_input) > (context_window - max_tokens) * 4:
        user_prompt = truncated_input[len(system_prompt) + 1:]

    # --- Resolve retry policy ---
    if retry_policy is None:
        retry_policy = RetryPolicy.from_config(config)

    # Determine provider name for circuit breaker
    provider_name = provider.name

    # --- Build URL and headers using provider adapter ---
    url = provider.build_url()
    headers = provider.build_headers()

    # --- Build payload using provider adapter ---
    json_mode_models = (
        "gemma4:e2b", "gemma4:e4b", "qwen3.5:9b", "gemma3:12b",
        "granite3.3:8b", "phi4-mini:3.8b",
    )
    json_mode = not is_local or model in json_mode_models

    # Thinking models need more num_predict
    effective_num_predict = max_tokens
    if model.startswith("gemma4:"):
        effective_num_predict = max_tokens * 2

    num_ctx = config.get("execution", {}).get("local_num_ctx", 8192) if is_local else 32768

    payload = provider.build_payload(
        model_id=model_id,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=effective_num_predict,
        num_ctx=num_ctx,
        json_mode=json_mode,
    )

    last_error = None

    for attempt in range(retry_policy.max_attempts):
        # Check circuit breakers
        if hat_id and not _circuit_breakers.allow_request("hat", hat_id):
            last_error = f"Circuit breaker OPEN for hat {hat_id}"
            break
        if not _circuit_breakers.allow_request("provider", provider_name):
            last_error = f"Circuit breaker OPEN for provider {provider_name}"
            break

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)

            if resp.status_code in (429, 500, 502, 503, 504):
                error_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                _circuit_breakers.record_failure("provider", provider_name)
                if hat_id:
                    _circuit_breakers.record_failure("hat", hat_id)
                if attempt < retry_policy.max_attempts - 1 and retry_policy.is_retryable_error(error_msg):
                    backoff = retry_policy.compute_backoff(attempt)
                    print(f"  Warning: Retry {attempt + 1}/{retry_policy.max_attempts} for {model} "
                          f"via {provider_name}: {error_msg} (backoff {backoff:.1f}s)", file=sys.stderr)
                    time.sleep(backoff)
                    last_error = error_msg
                    continue
                return {
                    "error": error_msg,
                    "model": model,
                    "content": None,
                    "usage": {"input": 0, "output": 0},
                }

            resp.raise_for_status()
            data = resp.json()

            # --- Parse response using provider adapter ---
            parsed = provider.parse_response(data)

            # Record success
            _circuit_breakers.record_success("provider", provider_name)
            if hat_id:
                _circuit_breakers.record_success("hat", hat_id)

            return {
                "error": None,
                "model": model,
                "content": parsed["content"],
                "thinking": parsed.get("thinking"),
                "usage": parsed["usage"],
            }

        except requests.exceptions.Timeout:
            error_msg = f"Timeout after {timeout}s"
            _circuit_breakers.record_failure("provider", provider_name)
            if hat_id:
                _circuit_breakers.record_failure("hat", hat_id)
            if attempt < retry_policy.max_attempts - 1 and retry_policy.is_retryable_error(error_msg):
                backoff = retry_policy.compute_backoff(attempt)
                print(f"  Warning: Retry {attempt + 1}/{retry_policy.max_attempts} for {model} "
                      f"via {provider_name}: {error_msg} (backoff {backoff:.1f}s)", file=sys.stderr)
                time.sleep(backoff)
                last_error = error_msg
                continue
            return {
                "error": error_msg,
                "model": model,
                "content": None,
                "usage": {"input": 0, "output": 0},
            }

        except requests.exceptions.RequestException as exc:
            error_msg = str(exc)
            _circuit_breakers.record_failure("provider", provider_name)
            if hat_id:
                _circuit_breakers.record_failure("hat", hat_id)
            if attempt < retry_policy.max_attempts - 1 and retry_policy.is_retryable_error(error_msg):
                backoff = retry_policy.compute_backoff(attempt)
                print(f"  Warning: Retry {attempt + 1}/{retry_policy.max_attempts} for {model} "
                      f"via {provider_name}: {error_msg} (backoff {backoff:.1f}s)", file=sys.stderr)
                time.sleep(backoff)
                last_error = error_msg
                continue
            return {
                "error": error_msg,
                "model": model,
                "content": None,
                "usage": {"input": 0, "output": 0},
            }

    # All retries exhausted
    return {
        "error": last_error or f"All {retry_policy.max_attempts} attempts failed",
        "model": model,
        "content": None,
        "usage": {"input": 0, "output": 0},
    }


# Set the alias after definition
call_llm = call_ollama


# ---------------------------------------------------------------------------
# Sensitive mode detection
# ---------------------------------------------------------------------------

_SENSITIVE_FILE_PATTERNS = [
    r"\.env($|\.)", r"\.env\.local", r"\.env\.production", r"\.env\.staging",
    r"credentials", r"secrets?", r"auth[_\-]?token", r"api[_\-]?key",
    r"private[_\-]?key", r"service[_\-]?account",
]

_SENSITIVE_PATH_PATTERNS = [
    r"auth\.(ts|js|py|go|rs)$", r"login\.(ts|js|py|go|rs)$",
    r"session\.(ts|js|py|go|rs)$", r"passport\.(ts|js|py|go|rs)$",
    r"oauth\.(ts|js|py|go|rs)$", r"jwt\.(ts|js|py|go|rs)$",
    r"credential", r"secret", r"certificate", r"iam[_\-]?",
]

_SENSITIVE_CONTENT_PATTERNS = [
    r"(?i)api[_\-]?key\s*[:=]\s*['\"][^'\"]{8,}",
    r"(?i)secret[_\-]?key\s*[:=]\s*['\"][^'\"]{8,}",
    r"(?i)auth[_\-]?token\s*[:=]\s*['\"][^'\"]{8,}",
    r"(?i)access[_\-]?token\s*[:=]\s*['\"][^'\"]{8,}",
    r"(?i)password\s*[:=]\s*['\"][^'\"]{4,}",
    r"(?i)bearer\s+[a-zA-Z0-9\-._~+/]+=*",
    r"[0-9]{3}-[0-9]{2}-[0-9]{4}",  # SSN pattern
    r"[0-9]{4}[ -]?[0-9]{4}[ -]?[0-9]{4}[ -]?[0-9]{4}",  # Credit card pattern
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # Email
]


def detect_sensitive_mode(diff_text: str, changed_files: list[str] | None = None) -> bool:
    """Scan diff content for credentials, PII, or auth-related code.

    Returns True if sensitive content is detected, which triggers dual-mode hats
    (Black, Purple, Brown) to switch to local models per the security rule in soul.md.
    """
    # Check file names in diff
    if changed_files:
        for filepath in changed_files:
            for pattern in _SENSITIVE_FILE_PATTERNS + _SENSITIVE_PATH_PATTERNS:
                if re.search(pattern, filepath, re.IGNORECASE):
                    return True

    # Check diff content for file paths (--- a/path, +++ b/path lines)
    for line in diff_text.split("\n"):
        if line.startswith("--- ") or line.startswith("+++ "):
            for pattern in _SENSITIVE_FILE_PATTERNS + _SENSITIVE_PATH_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    return True

    # Check diff content for sensitive values
    for pattern in _SENSITIVE_CONTENT_PATTERNS:
        if re.search(pattern, diff_text):
            return True

    return False


# ---------------------------------------------------------------------------
# Model fallback chain
# ---------------------------------------------------------------------------

def build_comparable_model_sequence(
    config: dict,
    primary_model: str,
    fallback_model: str | None = None,
    local_only: bool = False,
    cross_provider: bool = True,
) -> list[str]:
    """Build a prioritized model fallback list using comparable configured tiers.

    If local_only=True, only include models marked as local in the config.
    If cross_provider=True, include same-tier models from other providers as fallbacks.
    """
    models_cfg = config.get("models", {})
    has_cloud_key = bool(os.environ.get("OLLAMA_API_KEY", "").strip())

    # Check for global local-only mode
    router = None
    try:
        router = get_router(config)
    except Exception:
        pass
    if router and router.is_local_only_mode():
        local_only = True

    seen = set()
    ordered_models = []

    def add(model_name: str | None):
        if model_name and model_name in models_cfg and model_name not in seen:
            model_cfg_item = models_cfg[model_name]
            # Skip cloud models when local_only or no API key
            if local_only or not has_cloud_key:
                if not model_cfg_item.get("local", False):
                    return
            # Skip models whose provider is not available
            if not _has_available_provider(config, model_name):
                return
            ordered_models.append(model_name)
            seen.add(model_name)

    add(primary_model)
    add(fallback_model)

    primary_tier = models_cfg.get(primary_model, {}).get("tier")
    fallback_tier = models_cfg.get(fallback_model, {}).get("tier") if fallback_model else None

    # Same-tier models (any provider)
    for model_name, model_meta in models_cfg.items():
        if model_meta.get("tier") == primary_tier:
            add(model_name)

    if fallback_tier and fallback_tier != primary_tier:
        for model_name, model_meta in models_cfg.items():
            if model_meta.get("tier") == fallback_tier:
                add(model_name)

    # All remaining models
    for model_name in models_cfg:
        add(model_name)

    return ordered_models


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

def estimate_cost(config: dict, selected_hats: list[str], diff_tokens: int) -> tuple[float, bool]:
    """Estimate pipeline cost and check against budget gate.

    Returns (estimated_cost_usd, within_budget).
    """
    models_cfg = config["models"]
    hats_cfg = config["hats"]
    budget = config["gates"]["cost_budget"]["max_usd_per_pr"]

    total_cost = 0.0
    for hat_id in selected_hats:
        hat_def = hats_cfg[hat_id]
        model_name = hat_def["primary_model"]
        model_cfg = models_cfg.get(model_name, {})

        input_tokens = min(diff_tokens + 500, model_cfg.get("context_window", 128000))
        output_tokens = hat_def.get("max_tokens", 4096)

        input_cost = (input_tokens / 1_000_000) * model_cfg.get("input_cost_per_m", 0.20)
        output_cost = (output_tokens / 1_000_000) * model_cfg.get("output_cost_per_m", 0.80)
        total_cost += input_cost + output_cost

    return total_cost, total_cost <= budget


# ---------------------------------------------------------------------------
# Concurrency primitives
# ---------------------------------------------------------------------------

class LocalModelQueue:
    """Enforces that only one local model runs at a time.

    Local models are serialized through this queue. A threading.Lock ensures
    mutual exclusion. Tracks ownership to prevent "release unlocked lock" errors.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._owned_by = None  # Thread identity that holds the lock

    def acquire(self, timeout: float = 600.0) -> bool:
        """Acquire the local model slot. Returns True if acquired."""
        acquired = self._lock.acquire(timeout=timeout)
        if acquired:
            self._owned_by = threading.get_ident()
        return acquired

    def release(self):
        """Release the local model slot. Safe to call if not owned."""
        if self._owned_by == threading.get_ident():
            self._owned_by = None
            self._lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()


class CloudModelPool:
    """Manages cloud model concurrency.

    Up to max_workers cloud model calls can run in parallel via ThreadPoolExecutor.
    Falls back to trio mode (max_workers=3) when budget is tight.
    """

    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers
        self._executor: ThreadPoolExecutor | None = None

    @property
    def max_workers(self) -> int:
        return self._max_workers

    @max_workers.setter
    def max_workers(self, value: int):
        self._max_workers = value

    def start(self):
        if self._executor is None or self._executor._max_workers != self._max_workers:
            if self._executor is not None:
                self._executor.shutdown(wait=False)
            self._executor = ThreadPoolExecutor(max_workers=self._max_workers)

    def submit(self, fn, *args, **kwargs):
        if self._executor is None:
            self.start()
        return self._executor.submit(fn, *args, **kwargs)

    def shutdown(self, wait: bool = True):
        if self._executor is not None:
            self._executor.shutdown(wait=wait)
            self._executor = None


class ConcurrencyCoordinator:
    """Orchestrates cloud pool and local queue for hat execution.

    At any given time, up to `max_cloud` cloud inferences + 1 local inference
    can run simultaneously. The coordinator ensures local model queue slots
    are filled whenever available, while cloud slots are parallelized up to their cap.

    Fallback "trio" mode: max_cloud=3 when budget is tight or after failures.
    """

    def __init__(self, max_cloud: int = 4):
        self.local_queue = LocalModelQueue()
        self.cloud_pool = CloudModelPool(max_workers=max_cloud)
        self.max_cloud = max_cloud

    def classify_hat(self, config: dict, hat_id: str, sensitive_mode: bool = False) -> str:
        """Classify a hat as 'cloud' or 'local' based on its model assignment.

        Dual-mode hats (Black, Purple, Brown) use local models when sensitive_mode is True.
        Tier 4 hats (White, Blue, Silver, Teal) are always local.
        Global local_only mode forces all hats to local.
        """
        # Local-only mode enforcement
        local_only_cfg = config.get("local_only", {})
        if local_only_cfg.get("enabled", False):
            return "local"

        hat_def = config["hats"][hat_id]
        model = hat_def["primary_model"]
        models_cfg = config.get("models", {})
        model_cfg = models_cfg.get(model, {})

        # Check if the hat is explicitly marked as local-only
        if hat_def.get("local_only"):
            return "local"

        # Check if model is local (no :cloud suffix typically, or has local flag)
        if model_cfg.get("local"):
            return "local"

        # Dual-mode hats: switch to local when processing sensitive content
        dual_mode_hats = {"black", "purple", "brown"}
        if hat_id in dual_mode_hats and sensitive_mode:
            return "local"

        return "cloud"

    def get_model_for_hat(self, config: dict, hat_id: str, sensitive_mode: bool = False) -> str:
        """Get the appropriate model for a hat considering sensitive mode."""
        hat_def = config["hats"][hat_id]

        if self.classify_hat(config, hat_id, sensitive_mode) == "local":
            # Use local_model if available, otherwise primary (which should be local)
            return hat_def.get("local_model", hat_def["primary_model"])

        return hat_def["primary_model"]

    def enable_trio_mode(self):
        """Switch to trio mode: 3 cloud + 1 local."""
        self.max_cloud = 3
        self.cloud_pool.max_workers = 3
        self.cloud_pool.start()

    def start(self):
        self.cloud_pool.start()

    def shutdown(self, wait: bool = True):
        self.cloud_pool.shutdown(wait=wait)


# ---------------------------------------------------------------------------
# Preflight health check
# ---------------------------------------------------------------------------

def preflight_check(config: dict | None = None, requested_hats: list[str] | None = None) -> list[str]:
    """Check that required environment is configured for all providers.

    Returns a list of warning/error messages. Empty list = all good.
    If config is provided, only requires API keys when cloud models are needed.
    If requested_hats is provided, only checks models for those specific hats.
    """
    issues = []

    # Check local-only mode
    local_only_cfg = config.get("local_only", {}) if config else {}
    if local_only_cfg.get("enabled", False):
        issues.append("INFO: Local-only mode is ENABLED. Cloud models will not be used.")

    # Check all configured providers (boolean check only — never log key values)
    providers_cfg = config.get("providers", {}) if config else {}
    for provider_name, provider_cfg in providers_cfg.items():
        if not provider_cfg.get("enabled", True):
            continue
        api_key_env = provider_cfg.get("api_key_env", "")
        if api_key_env and not os.environ.get(api_key_env, "").strip():
            issues.append(
                f"WARNING: {api_key_env} is not set. "
                f"Models using provider '{provider_name}' will fail."
            )

    # Legacy check: if no providers section, check OLLAMA_API_KEY
    if not providers_cfg:
        has_ollama_key = bool(os.environ.get("OLLAMA_API_KEY", "").strip())
        # Determine which hats will actually run
        hats_cfg = config.get("hats", {}) if config else {}
        if requested_hats:
            active_hats = {k: v for k, v in hats_cfg.items() if k in requested_hats}
        else:
            active_hats = hats_cfg

        needs_cloud = any(not h.get("local_only", False) for h in active_hats.values()) if active_hats else True
        if not has_ollama_key and needs_cloud:
            issues.append(
                "WARNING: OLLAMA_API_KEY is not set.\n"
                "   Cloud models will fail and fall back to local models.\n"
                "   For full cloud model support, set your key:\n"
                "     GitHub Actions: Add as Repository Secret\n"
                "     Local: Copy .env.example to .env and fill in your key\n"
                "     Get a key at: https://ollama.com/settings/keys"
            )

    # Check if any active hats need local models
    hats_cfg = config.get("hats", {}) if config else {}
    if requested_hats:
        active_hats = {k: v for k, v in hats_cfg.items() if k in requested_hats}
    else:
        active_hats = hats_cfg
    models_cfg = config.get("models", {}) if config else {}
    active_models = set()
    for hat_cfg in active_hats.values():
        active_models.add(hat_cfg.get("primary_model", ""))
        if hat_cfg.get("fallback_model"):
            active_models.add(hat_cfg["fallback_model"])
        if hat_cfg.get("local_model"):
            active_models.add(hat_cfg["local_model"])

    needs_local = any(models_cfg.get(m, {}).get("local", False) for m in active_models if m) if models_cfg else False

    # Check if any cloud provider has API keys (for CI/cloud-only mode)
    has_cloud_key = False
    if providers_cfg:
        for provider_name, provider_cfg in providers_cfg.items():
            api_key_env = provider_cfg.get("api_key_env", "")
            if api_key_env and os.environ.get(api_key_env, "").strip():
                has_cloud_key = True
                break
    else:
        # Legacy: check OLLAMA_API_KEY
        if os.environ.get("OLLAMA_API_KEY", "").strip():
            has_cloud_key = True

    if needs_local:
        local_url = os.environ.get("OLLAMA_LOCAL_URL", "http://localhost:11434")
        try:
            resp = requests.get(f"{local_url}/api/version", timeout=3)
            if resp.status_code != 200:
                issues.append(f"WARNING: Local Ollama at {local_url} returned status {resp.status_code}")
        except requests.exceptions.RequestException:
            if has_cloud_key:
                # CI/cloud-only mode: local Ollama unavailable but cloud works
                issues.append(
                    f"INFO: Local Ollama not reachable at {local_url}. "
                    f"Cloud models will be used (local-only hats will fail)."
                )
            else:
                # No cloud key either — truly fatal
                issues.append(
                    f"ERROR: Local Ollama server not reachable at {local_url}.\n"
                    "   Start it with: ollama serve\n"
                    "   Or set OLLAMA_API_KEY for cloud model support."
                )

    cloud_url = os.environ.get("OLLAMA_CLOUD_URL", "").strip()
    if not cloud_url and not providers_cfg:
        issues.append(
            "OLLAMA_CLOUD_URL not set — using default: https://ollama.com"
        )

    return issues


# ---------------------------------------------------------------------------
# Model chain with fallback — shared by hats_runner and gremlin_runner
# ---------------------------------------------------------------------------

def try_model_chain(config: dict, primary: str, fallback: str | None,
                    system_prompt: str, user_prompt: str,
                    temperature: float, max_tokens: int, timeout: int,
                    hat_id: str) -> dict:
    """Try primary model, then fallback, then full tier-based chain.

    Shared by hats_runner.run_hat() and gremlin_runner phases.
    Returns the result dict from call_ollama() with the first successful model,
    or the last error result if all models fail.
    """
    result = call_ollama(config, primary, system_prompt, user_prompt,
                         temperature=temperature, max_tokens=max_tokens,
                         timeout=timeout, hat_id=hat_id)

    if not result["error"]:
        return result

    # Try fallback model
    if fallback:
        print(f"  Primary model {primary} failed for {hat_id}, trying fallback {fallback}",
              file=sys.stderr)
        result = call_ollama(config, fallback, system_prompt, user_prompt,
                             temperature=temperature, max_tokens=max_tokens,
                             timeout=timeout, hat_id=hat_id)
        if not result["error"]:
            return result

    # Try full model fallback chain
    chain = build_comparable_model_sequence(config, primary, fallback)
    for model in chain:
        if model == primary or model == fallback:
            continue  # Already tried
        print(f"  Fallback chain: trying {model} for {hat_id}", file=sys.stderr)
        result = call_ollama(config, model, system_prompt, user_prompt,
                             temperature=temperature, max_tokens=max_tokens,
                             timeout=timeout, hat_id=hat_id)
        if not result["error"]:
            return result

    return result


# ---------------------------------------------------------------------------
# Overnight mode — larger local models, extended timeouts
# ---------------------------------------------------------------------------

def is_overnight_mode(config: dict) -> bool:
    """Check if current time is within the overnight window.

    The overnight window is configured in gremlins.overnight.schedule_start/end
    (local timezone, 24h format like "01:00" to "07:00").
    """
    overnight_cfg = config.get("gremlins", {}).get("overnight", {})
    if not overnight_cfg.get("enabled", False):
        return False

    import datetime
    now = datetime.datetime.now()
    start = overnight_cfg.get("schedule_start", "01:00")
    end = overnight_cfg.get("schedule_end", "07:00")
    start_h, start_m = map(int, start.split(":"))
    end_h, end_m = map(int, end.split(":"))
    start_min = start_h * 60 + start_m
    end_min = end_h * 60 + end_m
    now_min = now.hour * 60 + now.minute

    if start_min <= end_min:
        return start_min <= now_min < end_min
    else:
        # Window crosses midnight (e.g., 23:00 to 06:00)
        return now_min >= start_min or now_min < end_min


def get_overnight_timeout(config: dict, base_timeout: int) -> int:
    """Scale timeout by the overnight multiplier if in overnight mode."""
    if is_overnight_mode(config):
        multiplier = config.get("gremlins", {}).get("overnight", {}).get("timeout_multiplier", 1)
        return int(base_timeout * multiplier)
    return base_timeout


def resolve_gremlin_model(config: dict, phase: str, hat_id: str) -> str:
    """Resolve which model a gremlin phase should use.

    During overnight mode, checks gremlins.overnight.model_overrides[phase].
    Otherwise, uses the hat's primary_model (or local_model for local_only hats).
    """
    hat_def = config["hats"][hat_id]

    if is_overnight_mode(config):
        overrides = config.get("gremlins", {}).get("overnight", {}).get("model_overrides", {})
        if phase in overrides:
            return overrides[phase]

    # Default: use the hat's configured model
    if hat_def.get("local_only"):
        return hat_def.get("local_model", hat_def["primary_model"])
    return hat_def["primary_model"]


# ---------------------------------------------------------------------------
# Wake-on-LAN — wake a standby PC before overnight runs
# ---------------------------------------------------------------------------

def send_wake_on_lan(config: dict) -> bool:
    """Send a Wake-on-LAN magic packet to wake a standby machine.

    Reads config from gremlins.overnight.wake_on_lan:
      - enabled: bool
      - target_mac: MAC address string (e.g., "aa:bb:cc:dd:ee:ff")
      - broadcast_ip: broadcast address (default "255.255.255.255")

    Returns True if packet was sent, False if disabled or error.
    After sending, polls localhost:11434 to wait for Ollama readiness.
    """
    wol_cfg = config.get("gremlins", {}).get("overnight", {}).get("wake_on_lan", {})
    if not wol_cfg.get("enabled", False):
        return False

    target_mac = wol_cfg.get("target_mac", "")
    if not target_mac:
        return False

    # Parse MAC address
    mac_bytes = bytes(int(b, 16) for b in target_mac.replace("-", ":").split(":"))
    if len(mac_bytes) != 6:
        print(f"  Invalid MAC address for WoL: {target_mac}", file=sys.stderr)
        return False

    # Build magic packet: 6 x 0xFF + 16 x MAC
    magic_packet = b"\xff" * 6 + mac_bytes * 16

    broadcast_ip = wol_cfg.get("broadcast_ip", "255.255.255.255")

    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet, (broadcast_ip, 9))
        sock.close()
        print(f"  Wake-on-LAN packet sent to {target_mac}", file=sys.stderr)

        # Wait for Ollama to be ready (30s timeout)
        local_url = os.environ.get("OLLAMA_LOCAL_URL", "http://localhost:11434")
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                resp = requests.get(f"{local_url}/api/version", timeout=3)
                if resp.status_code == 200:
                    print("  Ollama is ready", file=sys.stderr)
                    return True
            except requests.exceptions.RequestException:
                time.sleep(3)

        print("  Ollama not ready after 30s (machine may still be waking)", file=sys.stderr)
        return True  # Packet was sent, even if Ollama isn't ready yet

    except Exception as exc:
        print(f"  Wake-on-LAN failed: {exc}", file=sys.stderr)
        return False