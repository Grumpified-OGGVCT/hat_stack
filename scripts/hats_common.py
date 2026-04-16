#!/usr/bin/env python3
"""
hats_common.py — Shared library for Hat Stack runners.

Extracted from hats_runner.py and hats_task_runner.py to eliminate duplication.
Provides:
  - Config loading
  - Ollama API calls with retry, exponential backoff, and circuit breaker
  - Sensitive mode detection (credentials/PII)
  - Model fallback chain construction
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
# Ollama Cloud API caller with retry + circuit breaker
# ---------------------------------------------------------------------------

def _is_local_model(config: dict, model: str) -> bool:
    """Check if a model is configured as local (runs on localhost Ollama)."""
    models_cfg = config.get("models", {})
    model_cfg = models_cfg.get(model, {})
    return bool(model_cfg.get("local", False))


def call_ollama(config: dict, model: str, system_prompt: str, user_prompt: str,
                temperature: float = 0.3, max_tokens: int = 4096,
                timeout: int = 120, retry_policy: RetryPolicy | None = None,
                hat_id: str | None = None) -> dict:
    """Call an Ollama model — local or cloud — via the native Ollama API.

    Uses /api/chat endpoint (native Ollama format, not OpenAI-compatible).
    Local models route to localhost:11434/api/chat (no auth).
    Cloud models route to https://ollama.com/api/chat (Bearer token).

    Implements SPEC §8 retry policy with exponential backoff and jitter.
    Implements SPEC §8.3 circuit breaker (per-hat and per-provider).
    Truncates input to model's context window before sending.
    """
    is_local = _is_local_model(config, model)

    if is_local:
        base_url = os.environ.get(
            "OLLAMA_LOCAL_URL", "http://localhost:11434"
        )
        api_key = None
    else:
        base_url = os.environ.get(
            "OLLAMA_CLOUD_URL", "https://ollama.com"
        )
        api_key = os.environ.get("OLLAMA_API_KEY", "")

        if not api_key:
            return {
                "error": "OLLAMA_API_KEY not set (required for cloud model)",
                "model": model,
                "content": None,
                "usage": {"input": 0, "output": 0},
            }

    # Truncate input to fit context window
    models_cfg = config.get("models", {})
    model_cfg = models_cfg.get(model, {})
    context_window = model_cfg.get("context_window", 128000)
    combined_input = system_prompt + "\n" + user_prompt
    truncated_input = truncate_to_context_window(combined_input, context_window, reserve_output=max_tokens)
    if len(combined_input) > (context_window - max_tokens) * 4:
        user_prompt = truncated_input[len(system_prompt) + 1:]

    # Resolve retry policy
    if retry_policy is None:
        retry_policy = RetryPolicy.from_config(config)

    # Determine provider from model name for circuit breaker
    provider = model.split(":")[0] if ":" in model else "default"

    # Native Ollama /api/chat endpoint
    url = f"{base_url.rstrip('/')}/api/chat"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Thinking models (gemma4) need more num_predict because thinking tokens
    # count toward the limit. Double the budget for thinking models.
    effective_num_predict = max_tokens
    if model.startswith("gemma4:"):
        effective_num_predict = max_tokens * 2

    last_error = None

    for attempt in range(retry_policy.max_attempts):
        # Check circuit breakers
        if hat_id and not _circuit_breakers.allow_request("hat", hat_id):
            last_error = f"Circuit breaker OPEN for hat {hat_id}"
            break
        if not _circuit_breakers.allow_request("provider", provider):
            last_error = f"Circuit breaker OPEN for provider {provider}"
            break

        # Native Ollama /api/chat payload format
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": effective_num_predict,
                "num_ctx": config.get("execution", {}).get("local_num_ctx", 8192) if is_local else 32768,
            },
        }

        # Use Ollama format="json" for JSON mode — works on all models
        # that support it. All local models in our pool handle JSON mode.
        json_mode_models = (
            "gemma4:e2b", "gemma4:e4b", "qwen3.5:9b", "gemma3:12b",
            "granite3.3:8b", "phi4-mini:3.8b",
        )
        if not is_local or model in json_mode_models:
            payload["format"] = "json"

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)

            if resp.status_code in (429, 500, 502, 503, 504):
                error_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                _circuit_breakers.record_failure("provider", provider)
                if hat_id:
                    _circuit_breakers.record_failure("hat", hat_id)
                if attempt < retry_policy.max_attempts - 1 and retry_policy.is_retryable_error(error_msg):
                    backoff = retry_policy.compute_backoff(attempt)
                    print(f"  ⚠️ Retry {attempt + 1}/{retry_policy.max_attempts} for {model}: "
                          f"{error_msg} (backoff {backoff:.1f}s)", file=sys.stderr)
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

            # Native /api/chat response format: message.content at top level
            message = data.get("message", {})
            content = message.get("content", "")
            # Thinking models put reasoning in message.thinking
            thinking = message.get("thinking", "")

            # Record success
            _circuit_breakers.record_success("provider", provider)
            if hat_id:
                _circuit_breakers.record_success("hat", hat_id)

            return {
                "error": None,
                "model": model,
                "content": content,
                "thinking": thinking if thinking else None,
                "usage": {
                    "input": data.get("prompt_eval_count", 0),
                    "output": data.get("eval_count", 0),
                },
            }

        except requests.exceptions.Timeout:
            error_msg = f"Timeout after {timeout}s"
            _circuit_breakers.record_failure("provider", provider)
            if hat_id:
                _circuit_breakers.record_failure("hat", hat_id)
            if attempt < retry_policy.max_attempts - 1 and retry_policy.is_retryable_error(error_msg):
                backoff = retry_policy.compute_backoff(attempt)
                print(f"  ⚠️ Retry {attempt + 1}/{retry_policy.max_attempts} for {model}: "
                      f"{error_msg} (backoff {backoff:.1f}s)", file=sys.stderr)
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
            _circuit_breakers.record_failure("provider", provider)
            if hat_id:
                _circuit_breakers.record_failure("hat", hat_id)
            if attempt < retry_policy.max_attempts - 1 and retry_policy.is_retryable_error(error_msg):
                backoff = retry_policy.compute_backoff(attempt)
                print(f"  ⚠️ Retry {attempt + 1}/{retry_policy.max_attempts} for {model}: "
                      f"{error_msg} (backoff {backoff:.1f}s)", file=sys.stderr)
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
) -> list[str]:
    """Build a prioritized model fallback list using comparable configured tiers.

    If local_only=True, only include models marked as local in the config.
    """
    models_cfg = config.get("models", {})
    has_cloud_key = bool(os.environ.get("OLLAMA_API_KEY", "").strip())

    seen = set()
    ordered_models = []

    def add(model_name: str | None):
        if model_name and model_name in models_cfg and model_name not in seen:
            # Skip cloud models when local_only or no API key
            if local_only or not has_cloud_key:
                if not models_cfg[model_name].get("local", False):
                    return
            ordered_models.append(model_name)
            seen.add(model_name)

    add(primary_model)
    add(fallback_model)

    primary_tier = models_cfg.get(primary_model, {}).get("tier")
    fallback_tier = models_cfg.get(fallback_model, {}).get("tier") if fallback_model else None

    for model_name, model_meta in models_cfg.items():
        if model_meta.get("tier") == primary_tier:
            add(model_name)

    if fallback_tier and fallback_tier != primary_tier:
        for model_name, model_meta in models_cfg.items():
            if model_meta.get("tier") == fallback_tier:
                add(model_name)

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
        """
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
    """Check that required environment is configured.

    Returns a list of warning/error messages. Empty list = all good.
    If config is provided, only requires OLLAMA_API_KEY when cloud models are needed.
    If requested_hats is provided, only checks models for those specific hats.
    """
    issues = []

    api_key = os.environ.get("OLLAMA_API_KEY", "").strip()

    # Determine which hats will actually run
    hats_cfg = config.get("hats", {}) if config else {}
    if requested_hats:
        active_hats = {k: v for k, v in hats_cfg.items() if k in requested_hats}
    else:
        active_hats = hats_cfg

    # Check if any active hats need cloud models
    needs_cloud = any(not h.get("local_only", False) for h in active_hats.values()) if active_hats else True

    if not api_key and needs_cloud:
        issues.append(
            "WARNING: OLLAMA_API_KEY is not set.\n"
            "   Cloud models will fail and fall back to local models.\n"
            "   For full cloud model support, set your key:\n"
            "     GitHub Actions: Add as Repository Secret\n"
            "     Local: Copy .env.example to .env and fill in your key\n"
            "     Get a key at: https://ollama.com/settings/keys"
        )

    # Check if any active hats need local models
    models_cfg = config.get("models", {}) if config else {}
    active_models = set()
    for hat_cfg in active_hats.values():
        active_models.add(hat_cfg.get("primary_model", ""))
        if hat_cfg.get("fallback_model"):
            active_models.add(hat_cfg["fallback_model"])
        if hat_cfg.get("local_model"):
            active_models.add(hat_cfg["local_model"])

    needs_local = any(models_cfg.get(m, {}).get("local", False) for m in active_models if m) if models_cfg else False

    if needs_local:
        local_url = os.environ.get("OLLAMA_LOCAL_URL", "http://localhost:11434")
        try:
            resp = requests.get(f"{local_url}/api/version", timeout=3)
            if resp.status_code != 200:
                issues.append(f"Local Ollama at {local_url} returned status {resp.status_code}")
        except requests.exceptions.RequestException:
            issues.append(
                f"Local Ollama server not reachable at {local_url}.\n"
                "   Start it with: ollama serve"
            )

    cloud_url = os.environ.get("OLLAMA_CLOUD_URL", "").strip()
    if not cloud_url and needs_cloud and api_key:
        issues.append(
            "OLLAMA_CLOUD_URL not set — using default: https://ollama.com"
        )

    return issues