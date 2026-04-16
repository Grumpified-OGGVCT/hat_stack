#!/usr/bin/env python3
"""Unit tests for provider_router.py -- Multi-provider LLM routing."""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from provider_router import (
    OllamaAdapter,
    OpenAICompatibleAdapter,
    ProviderRouter,
    get_router,
    clear_router_cache,
)


# ---------------------------------------------------------------------------
# OllamaAdapter tests
# ---------------------------------------------------------------------------

def test_ollama_adapter_build_payload():
    """OllamaAdapter should build Ollama-native /api/chat payload."""
    adapter = OllamaAdapter({
        "name": "test_ollama",
        "base_url_env": "",
        "default_base_url": "http://localhost:11434",
        "api_key_env": "",
        "api_format": "ollama",
    })
    payload = adapter.build_payload(
        model_id="gemma4:e2b",
        system_prompt="You are a tester.",
        user_prompt="Hello",
        temperature=0.2,
        max_tokens=4096,
        num_ctx=8192,
        json_mode=True,
    )
    assert payload["model"] == "gemma4:e2b"
    assert payload["stream"] is False
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"
    assert payload["options"]["temperature"] == 0.2
    assert payload["options"]["num_predict"] == 4096
    assert payload["options"]["num_ctx"] == 8192
    assert payload["format"] == "json"
    print("OK: OllamaAdapter builds correct payload")


def test_ollama_adapter_parse_response():
    """OllamaAdapter should parse Ollama /api/chat response."""
    adapter = OllamaAdapter({"name": "test", "api_format": "ollama"})
    response = {
        "message": {"content": "Hello back!", "thinking": "reasoning..."},
        "prompt_eval_count": 50,
        "eval_count": 20,
    }
    parsed = adapter.parse_response(response)
    assert parsed["content"] == "Hello back!"
    assert parsed["thinking"] == "reasoning..."
    assert parsed["usage"]["input"] == 50
    assert parsed["usage"]["output"] == 20
    print("OK: OllamaAdapter parses response correctly")


def test_ollama_adapter_build_url():
    """OllamaAdapter should build /api/chat URL."""
    adapter = OllamaAdapter({"default_base_url": "http://localhost:11434"})
    url = adapter.build_url()
    assert url == "http://localhost:11434/api/chat"
    print("OK: OllamaAdapter builds correct URL")


# ---------------------------------------------------------------------------
# OpenAICompatibleAdapter tests
# ---------------------------------------------------------------------------

def test_openai_adapter_build_payload():
    """OpenAICompatibleAdapter should build /v1/chat/completions payload."""
    adapter = OpenAICompatibleAdapter({
        "name": "test_openrouter",
        "base_url_env": "",
        "default_base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "api_format": "openai_compatible",
    })
    payload = adapter.build_payload(
        model_id="anthropic/claude-sonnet-4",
        system_prompt="You are a tester.",
        user_prompt="Hello",
        temperature=0.3,
        max_tokens=2048,
        num_ctx=32768,
        json_mode=True,
    )
    assert payload["model"] == "anthropic/claude-sonnet-4"
    assert payload["stream"] is False
    assert payload["temperature"] == 0.3
    assert payload["max_tokens"] == 2048
    assert "options" not in payload
    assert payload["response_format"] == {"type": "json_object"}
    print("OK: OpenAICompatibleAdapter builds correct payload")


def test_openai_adapter_parse_response():
    """OpenAICompatibleAdapter should parse /v1/chat/completions response."""
    adapter = OpenAICompatibleAdapter({"name": "test"})
    response = {
        "choices": [{"message": {"content": "Hi from OpenRouter!"}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 30},
    }
    parsed = adapter.parse_response(response)
    assert parsed["content"] == "Hi from OpenRouter!"
    assert parsed["thinking"] is None
    assert parsed["usage"]["input"] == 100
    assert parsed["usage"]["output"] == 30
    print("OK: OpenAICompatibleAdapter parses response correctly")


def test_openai_adapter_build_url():
    """OpenAICompatibleAdapter should build /v1/chat/completions URL."""
    adapter = OpenAICompatibleAdapter({"default_base_url": "https://openrouter.ai/api/v1"})
    url = adapter.build_url()
    assert url == "https://openrouter.ai/api/v1/chat/completions"
    print("OK: OpenAICompatibleAdapter builds correct URL")


def test_openai_adapter_openrouter_headers():
    """OpenAICompatibleAdapter should add OpenRouter-specific headers."""
    adapter = OpenAICompatibleAdapter({
        "name": "openrouter",
        "api_key_env": "OPENROUTER_API_KEY",
    })
    os.environ["OPENROUTER_API_KEY"] = "sk-or-test-key"
    try:
        headers = adapter.build_headers()
        assert "HTTP-Referer" in headers
        assert headers["Authorization"] == "Bearer sk-or-test-key"
    finally:
        del os.environ["OPENROUTER_API_KEY"]
    print("OK: OpenAICompatibleAdapter adds OpenRouter headers")


# ---------------------------------------------------------------------------
# ProviderRouter tests
# ---------------------------------------------------------------------------

def test_provider_router_resolve_local_model():
    """ProviderRouter should resolve local models to ollama_local."""
    config = {
        "models": {"gemma4:e2b": {"local": True}},
        "providers": {
            "ollama_local": {"name": "Ollama Local", "default_base_url": "http://localhost:11434",
                            "api_format": "ollama", "enabled": True},
            "ollama_cloud": {"name": "Ollama Cloud", "default_base_url": "https://ollama.com",
                            "api_key_env": "OLLAMA_API_KEY", "api_format": "ollama",
                            "enabled": True, "default": True},
        },
    }
    router = ProviderRouter(config)
    provider = router.get_provider("gemma4:e2b")
    assert provider.name == "ollama_local"
    print("OK: local model routes to ollama_local")


def test_provider_router_resolve_cloud_model():
    """ProviderRouter should resolve cloud models to default cloud provider."""
    config = {
        "models": {"glm-5.1:cloud": {"local": False}},
        "providers": {
            "ollama_local": {"name": "Ollama Local", "default_base_url": "http://localhost:11434",
                            "api_format": "ollama", "enabled": True},
            "ollama_cloud": {"name": "Ollama Cloud", "default_base_url": "https://ollama.com",
                            "api_key_env": "OLLAMA_API_KEY", "api_format": "ollama",
                            "enabled": True, "default": True},
        },
    }
    router = ProviderRouter(config)
    provider = router.get_provider("glm-5.1:cloud")
    assert provider.name == "ollama_cloud"
    print("OK: cloud model routes to default cloud provider")


def test_provider_router_resolve_explicit_provider():
    """ProviderRouter should use model's explicit provider field."""
    config = {
        "models": {
            "glm-5.1:openrouter": {
                "local": False,
                "provider": "openrouter",
                "model_id": "anthropic/claude-sonnet-4",
            }
        },
        "providers": {
            "ollama_cloud": {"name": "Ollama Cloud", "default_base_url": "https://ollama.com",
                            "api_format": "ollama", "enabled": True, "default": True},
            "openrouter": {"name": "OpenRouter", "default_base_url": "https://openrouter.ai/api/v1",
                          "api_key_env": "OPENROUTER_API_KEY", "api_format": "openai_compatible",
                          "enabled": True},
        },
    }
    router = ProviderRouter(config)
    provider = router.get_provider("glm-5.1:openrouter")
    assert provider.name == "openrouter"
    model_id = router.get_model_id("glm-5.1:openrouter")
    assert model_id == "anthropic/claude-sonnet-4"
    print("OK: explicit provider field overrides default")


def test_provider_router_default_no_config():
    """ProviderRouter should build defaults when no providers in config."""
    config = {"models": {"gemma4:e2b": {"local": True}, "glm-5.1:cloud": {"local": False}}}
    router = ProviderRouter(config)
    # Local model should get a default local provider
    local_provider = router.get_provider("gemma4:e2b")
    assert "ollama" in local_provider.name.lower() or "local" in local_provider.name.lower()
    # Cloud model should get default cloud
    cloud_provider = router.get_provider("glm-5.1:cloud")
    assert "ollama" in cloud_provider.name.lower() or "cloud" in cloud_provider.name.lower()
    print("OK: ProviderRouter builds defaults from empty config")


def test_local_only_mode():
    """ProviderRouter.is_local_only_mode() should reflect config."""
    router_off = ProviderRouter({"local_only": {"enabled": False}})
    assert not router_off.is_local_only_mode()

    router_on = ProviderRouter({"local_only": {"enabled": True}})
    assert router_on.is_local_only_mode()

    router_default = ProviderRouter({})
    assert not router_default.is_local_only_mode()
    print("OK: local_only mode detection works")


def test_provider_availability_check():
    """Provider adapters should check API key availability."""
    # No API key env -> always available
    local_adapter = OllamaAdapter({"api_key_env": ""})
    assert local_adapter.is_available()

    # API key env set but key missing -> not available
    cloud_adapter = OllamaAdapter({"api_key_env": "MISSING_KEY", "enabled": True})
    assert not cloud_adapter.is_available()

    # API key present -> available
    os.environ["TEST_KEY_FOR_ROUTER"] = "sk-test"
    available_adapter = OllamaAdapter({"api_key_env": "TEST_KEY_FOR_ROUTER", "enabled": True})
    assert available_adapter.is_available()
    del os.environ["TEST_KEY_FOR_ROUTER"]

    # Disabled -> not available
    disabled_adapter = OllamaAdapter({"api_key_env": "", "enabled": False})
    assert not disabled_adapter.is_available()
    print("OK: provider availability checks work correctly")


def test_cross_provider_fallback():
    """ProviderRouter should find cross-provider fallback models."""
    config = {
        "models": {
            "glm-5.1:cloud": {"tier": 1, "local": False, "provider": "ollama_cloud"},
            "glm-5.1:openrouter": {"tier": 1, "local": False, "provider": "openrouter",
                                  "model_id": "anthropic/claude-sonnet-4"},
        },
        "providers": {
            "ollama_cloud": {"name": "Ollama Cloud", "default_base_url": "https://ollama.com",
                            "api_key_env": "OLLAMA_API_KEY", "api_format": "ollama",
                            "enabled": True, "default": True},
            "openrouter": {"name": "OpenRouter", "default_base_url": "https://openrouter.ai/api/v1",
                          "api_key_env": "OPENROUTER_API_KEY", "api_format": "openai_compatible",
                          "enabled": True},
        },
        "execution": {"fallback_across_providers": True},
    }
    router = ProviderRouter(config)

    # Set OpenRouter key so provider is available
    os.environ["OPENROUTER_API_KEY"] = "sk-or-test"
    try:
        fallback = router.find_cross_provider_fallback("glm-5.1:cloud")
        assert fallback is not None
        assert "openrouter" in fallback
    finally:
        del os.environ["OPENROUTER_API_KEY"]
    print("OK: cross-provider fallback finds equivalent models")


def test_cross_provider_fallback_disabled():
    """Cross-provider fallback should return None when disabled."""
    config = {
        "models": {
            "glm-5.1:cloud": {"tier": 1, "local": False, "provider": "ollama_cloud"},
        },
        "execution": {"fallback_across_providers": False},
    }
    router = ProviderRouter(config)
    fallback = router.find_cross_provider_fallback("glm-5.1:cloud")
    assert fallback is None
    print("OK: cross-provider fallback disabled returns None")


def test_providers_in_config():
    """Validate providers section in hat_configs.yml."""
    import yaml
    config_path = Path(__file__).resolve().parent.parent / "hat_configs.yml"
    with open(config_path, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    providers = config.get("providers", {})
    assert len(providers) >= 2, "Should have at least 2 providers (ollama_local + ollama_cloud)"

    for name, cfg in providers.items():
        assert "api_format" in cfg, f"Provider '{name}' missing api_format"
        assert cfg["api_format"] in ("ollama", "openai_compatible"), \
            f"Provider '{name}' has invalid api_format: {cfg['api_format']}"
        if cfg.get("enabled", True) and cfg.get("api_key_env"):
            # Just verify the field exists, not that the key is set
            assert isinstance(cfg["api_key_env"], str)

    # Check local_only section exists
    local_only = config.get("local_only", {})
    assert "enabled" in local_only

    # Check cloud models have provider field
    models = config.get("models", {})
    cloud_models = [k for k, v in models.items() if not v.get("local", False)]
    for model_name in cloud_models:
        assert "provider" in models[model_name], f"Cloud model '{model_name}' missing 'provider' field"

    print(f"OK: providers config valid with {len(providers)} providers, {len(cloud_models)} cloud models")


if __name__ == "__main__":
    clear_router_cache()
    tests = [
        test_ollama_adapter_build_payload,
        test_ollama_adapter_parse_response,
        test_ollama_adapter_build_url,
        test_openai_adapter_build_payload,
        test_openai_adapter_parse_response,
        test_openai_adapter_build_url,
        test_openai_adapter_openrouter_headers,
        test_provider_router_resolve_local_model,
        test_provider_router_resolve_cloud_model,
        test_provider_router_resolve_explicit_provider,
        test_provider_router_default_no_config,
        test_local_only_mode,
        test_provider_availability_check,
        test_cross_provider_fallback,
        test_cross_provider_fallback_disabled,
        test_providers_in_config,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            clear_router_cache()
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {test.__name__}: {e}")
            failed += 1

    print(f"\nProvider router tests: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)