#!/usr/bin/env python3
"""
provider_router.py -- Multi-provider LLM routing for Hat Stack.

Provides:
  - ProviderAdapter base class and format-specific subclasses
  - OllamaAdapter: formats requests for Ollama /api/chat (native format)
  - OpenAICompatibleAdapter: formats requests for /v1/chat/completions
    (OpenRouter, DeepInfra, Groq, Together AI, etc.)
  - ProviderRouter: resolves model -> provider -> adapter, with fallback
  - Local-only mode enforcement

Adding a new provider:
  1. Add provider definition to hat_configs.yml under `providers:`
  2. Set `api_format: openai_compatible` for any OpenAI-compatible API
     (or add a new Adapter subclass for non-standard APIs)
  3. Add models with `provider: <name>` and optional `model_id: "<provider-specific-name>"`
  4. Set the `OPENROUTER_API_KEY`, `DEEPINFRA_API_KEY`, etc. env var
  5. Set `enabled: true` on the provider

No code changes required for OpenAI-compatible providers.
"""

import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None


# ---------------------------------------------------------------------------
# Provider adapter base class
# ---------------------------------------------------------------------------

class ProviderAdapter:
    """Base class for LLM provider API format adapters.

    Each adapter knows how to build request URLs, headers, payloads,
    and parse responses for a specific API format.
    """

    def __init__(self, provider_config: dict):
        self.name = provider_config.get("name", "unknown")
        self.base_url_env = provider_config.get("base_url_env", "")
        self.default_base_url = provider_config.get("default_base_url", "")
        self.api_key_env = provider_config.get("api_key_env", "")
        self.api_format = provider_config.get("api_format", "ollama")
        self.enabled = provider_config.get("enabled", True)
        self.is_default = provider_config.get("default", False)

    def get_base_url(self) -> str:
        """Resolve the base URL from env var or default."""
        if self.base_url_env:
            return os.environ.get(self.base_url_env, self.default_base_url)
        return self.default_base_url

    def get_api_key(self) -> str | None:
        """Get the API key from env var, or None for local providers."""
        if not self.api_key_env:
            return None
        return os.environ.get(self.api_key_env, "").strip() or None

    def is_available(self) -> bool:
        """Check if this provider has the required credentials.

        Local providers (no api_key_env) are always available.
        Cloud providers need their API key set.
        """
        if not self.enabled:
            return False
        if self.api_key_env:
            return bool(os.environ.get(self.api_key_env, "").strip())
        return True  # Local providers don't need keys

    def build_url(self) -> str:
        """Build the full API endpoint URL."""
        raise NotImplementedError

    def build_headers(self) -> dict:
        """Build request headers including auth if needed."""
        raise NotImplementedError

    def build_payload(self, model_id: str, system_prompt: str,
                      user_prompt: str, temperature: float,
                      max_tokens: int, num_ctx: int,
                      json_mode: bool, **kwargs) -> dict:
        """Build the request payload."""
        raise NotImplementedError

    def parse_response(self, data: dict) -> dict:
        """Parse provider response into standard format.

        Returns: {"content": str, "thinking": str|None, "usage": {"input": int, "output": int}}
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Ollama adapter -- /api/chat native format
# ---------------------------------------------------------------------------

class OllamaAdapter(ProviderAdapter):
    """Adapter for Ollama /api/chat native format.

    Used by both Ollama Local (localhost:11434) and Ollama Cloud (ollama.com).
    Request format: {model, messages, stream, options: {temperature, num_predict, num_ctx}}
    Response format: {message: {content, thinking}, prompt_eval_count, eval_count}
    """

    def build_url(self) -> str:
        return f"{self.get_base_url().rstrip('/')}/api/chat"

    def build_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        api_key = self.get_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def build_payload(self, model_id: str, system_prompt: str,
                      user_prompt: str, temperature: float,
                      max_tokens: int, num_ctx: int,
                      json_mode: bool, **kwargs) -> dict:
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": num_ctx,
            },
        }
        if json_mode:
            payload["format"] = "json"
        return payload

    def parse_response(self, data: dict) -> dict:
        message = data.get("message", {})
        return {
            "content": message.get("content", ""),
            "thinking": message.get("thinking") or None,
            "usage": {
                "input": data.get("prompt_eval_count", 0),
                "output": data.get("eval_count", 0),
            },
        }


# ---------------------------------------------------------------------------
# OpenAI-compatible adapter -- /v1/chat/completions
# ---------------------------------------------------------------------------

class OpenAICompatibleAdapter(ProviderAdapter):
    """Adapter for OpenAI-compatible /v1/chat/completions format.

    Used by OpenRouter, DeepInfra, Groq, Together AI, and any provider
    that implements the OpenAI Chat Completions API.

    Request format: {model, messages, temperature, max_tokens, stream}
    Response format: {choices: [{message: {content}}], usage: {prompt_tokens, completion_tokens}}
    """

    def build_url(self) -> str:
        base = self.get_base_url().rstrip("/")
        # Handle providers that already include /v1 in base_url
        if base.endswith("/v1") or base.endswith("/v1/"):
            return f"{base.rstrip('/')}/chat/completions"
        return f"{base}/v1/chat/completions"

    def build_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        api_key = self.get_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        # OpenRouter uses HTTP-Referer for app identification
        if "openrouter" in self.name.lower():
            headers["HTTP-Referer"] = "https://github.com/hat-stack"
            headers["X-Title"] = "Hat Stack Gremlin"
        return headers

    def build_payload(self, model_id: str, system_prompt: str,
                      user_prompt: str, temperature: float,
                      max_tokens: int, num_ctx: int,
                      json_mode: bool, **kwargs) -> dict:
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def parse_response(self, data: dict) -> dict:
        choices = data.get("choices", [])
        content = ""
        if choices:
            content = choices[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})
        return {
            "content": content,
            "thinking": None,  # OpenAI-compatible doesn't have thinking
            "usage": {
                "input": usage.get("prompt_tokens", 0),
                "output": usage.get("completion_tokens", 0),
            },
        }


# ---------------------------------------------------------------------------
# Adapter registry
# ---------------------------------------------------------------------------

ADAPTER_CLASSES = {
    "ollama": OllamaAdapter,
    "openai_compatible": OpenAICompatibleAdapter,
}


# ---------------------------------------------------------------------------
# Provider Router
# ---------------------------------------------------------------------------

class ProviderRouter:
    """Resolves models to providers and builds API calls.

    Replaces the binary local/cloud routing in call_ollama().
    Supports multi-provider config, local-only mode, and cross-provider fallback.
    """

    def __init__(self, config: dict):
        self.config = config
        self._providers: dict[str, ProviderAdapter] = {}
        self._default_cloud_provider: str | None = None
        self._load_providers()

    def _load_providers(self):
        """Load providers from config. Falls back to defaults if none configured."""
        providers_cfg = self.config.get("providers", {})

        if not providers_cfg:
            # Build defaults from existing env vars (backward compat)
            providers_cfg = {
                "ollama_local": {
                    "name": "Ollama Local",
                    "base_url_env": "OLLAMA_LOCAL_URL",
                    "default_base_url": "http://localhost:11434",
                    "api_key_env": "",
                    "api_format": "ollama",
                    "enabled": True,
                },
                "ollama_cloud": {
                    "name": "Ollama Cloud",
                    "base_url_env": "OLLAMA_CLOUD_URL",
                    "default_base_url": "https://ollama.com",
                    "api_key_env": "OLLAMA_API_KEY",
                    "api_format": "ollama",
                    "enabled": True,
                    "default": True,
                },
            }

        for name, cfg in providers_cfg.items():
            cfg["name"] = cfg.get("name", name)
            api_format = cfg.get("api_format", "ollama")
            adapter_class = ADAPTER_CLASSES.get(api_format, OllamaAdapter)
            adapter = adapter_class(cfg)
            adapter.name = name
            self._providers[name] = adapter

            if cfg.get("default", False) and not cfg.get("local", False):
                self._default_cloud_provider = name

    def get_provider(self, model_name: str) -> ProviderAdapter:
        """Get the provider adapter for a model.

        Resolution order:
        1. Model's explicit `provider` field in config
        2. Default cloud provider (for cloud models)
        3. ollama_local (for local models)
        4. Ultimate fallback: Ollama cloud with env vars
        """
        models_cfg = self.config.get("models", {})
        model_cfg = models_cfg.get(model_name, {})

        # 1. Explicit provider on model
        provider_name = model_cfg.get("provider")
        if provider_name and provider_name in self._providers:
            return self._providers[provider_name]

        # 2. Local models -> ollama_local
        if model_cfg.get("local", False):
            local_provider = self._providers.get("ollama_local")
            if local_provider:
                return local_provider
            # Fallback: construct default local adapter
            return OllamaAdapter({
                "name": "ollama_local",
                "base_url_env": "OLLAMA_LOCAL_URL",
                "default_base_url": "http://localhost:11434",
                "api_key_env": "",
                "api_format": "ollama",
                "enabled": True,
            })

        # 3. Cloud models -> default cloud provider
        if self._default_cloud_provider and self._default_cloud_provider in self._providers:
            return self._providers[self._default_cloud_provider]

        # 4. Ultimate fallback
        return OllamaAdapter({
            "name": "ollama_cloud",
            "base_url_env": "OLLAMA_CLOUD_URL",
            "default_base_url": "https://ollama.com",
            "api_key_env": "OLLAMA_API_KEY",
            "api_format": "ollama",
        })

    def get_model_id(self, model_name: str) -> str:
        """Get the provider-specific model ID.

        If model config has `model_id`, use that (for providers like OpenRouter
        that use different naming conventions like 'anthropic/claude-sonnet-4').
        Otherwise, use the model name as-is.
        """
        models_cfg = self.config.get("models", {})
        model_cfg = models_cfg.get(model_name, {})
        return model_cfg.get("model_id", model_name)

    def is_local_only_mode(self) -> bool:
        """Check if global local-only mode is enabled."""
        local_only_cfg = self.config.get("local_only", {})
        return local_only_cfg.get("enabled", False)

    def is_cloud_model(self, model_name: str) -> bool:
        """Check if a model is a cloud model (non-local)."""
        models_cfg = self.config.get("models", {})
        model_cfg = models_cfg.get(model_name, {})
        return not model_cfg.get("local", False)

    def get_available_providers(self) -> list[str]:
        """Return list of provider names that have required credentials."""
        return [name for name, adapter in self._providers.items()
                if adapter.is_available()]

    def find_cross_provider_fallback(self, model_name: str) -> str | None:
        """Find an equivalent model on a different provider.

        Looks for same-tier models on other available providers.
        Returns the model name to try, or None if no cross-provider fallback exists.
        """
        if not self.config.get("execution", {}).get("fallback_across_providers", False):
            return None

        models_cfg = self.config.get("models", {})
        model_cfg = models_cfg.get(model_name, {})
        model_tier = model_cfg.get("tier", 99)
        model_provider = model_cfg.get("provider", "")

        # Find same-tier models on different providers that are available
        for other_model, other_cfg in models_cfg.items():
            if other_model == model_name:
                continue
            if other_cfg.get("tier") != model_tier:
                continue
            if other_cfg.get("local", False):
                continue  # Skip local models for cross-provider fallback
            other_provider = other_cfg.get("provider", "")
            if other_provider == model_provider:
                continue  # Same provider, not a cross-provider fallback
            if not other_provider:
                continue  # No explicit provider
            # Check if the provider is available
            if other_provider in self._providers and self._providers[other_provider].is_available():
                return other_model

        return None


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

_router_cache: dict[int, "ProviderRouter"] = {}


def get_router(config: dict) -> ProviderRouter:
    """Get or create a ProviderRouter for the given config.

    Caches by config dict id to avoid re-parsing on every call.
    """
    config_id = id(config)
    if config_id not in _router_cache:
        _router_cache[config_id] = ProviderRouter(config)
    return _router_cache[config_id]


def clear_router_cache():
    """Clear the router cache (useful for testing or config hot-reload)."""
    _router_cache.clear()