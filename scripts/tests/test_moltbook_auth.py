#!/usr/bin/env python3
"""Unit tests for moltbook_auth.py — 'Sign in with Moltbook' agent authentication."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from moltbook_auth import (
    verify_moltbook_identity,
    extract_moltbook_identity,
    format_agent_identity,
)


# Minimal config for testing
TEST_CONFIG = {
    "moltbook": {
        "enabled": True,
        "app_key_env": "MOLTBOOK_APP_KEY",
        "verify_url": "https://moltbook.com/api/v1/agents/verify-identity",
        "audience": "hat-stack",
        "header_name": "X-Moltbook-Identity",
    }
}

SAMPLE_AGENT = {
    "id": "agent-abc-123",
    "name": "TestBot",
    "description": "A test agent",
    "karma": 420,
    "avatar_url": "https://moltbook.com/avatars/testbot.png",
    "is_claimed": True,
    "created_at": "2026-01-15T10:00:00Z",
    "follower_count": 42,
    "following_count": 10,
    "stats": {"posts": 156, "comments": 892},
    "owner": {
        "x_handle": "human_owner",
        "x_name": "Human Owner",
        "x_verified": True,
    },
    "human": {
        "username": "human_owner",
        "email_verified": True,
    },
}


def test_verify_missing_token():
    """verify_moltbook_identity should reject empty tokens."""
    result = verify_moltbook_identity("", TEST_CONFIG)
    assert result["valid"] is False
    assert result["error"] == "missing_token"
    assert "identity token" in result["error_hint"].lower()
    print("OK: verify rejects missing token")


def test_verify_moltbook_disabled():
    """verify_moltbook_identity should reject when moltbook is disabled."""
    config = {"moltbook": {"enabled": False}}
    result = verify_moltbook_identity("some-token", config)
    assert result["valid"] is False
    assert result["error"] == "moltbook_disabled"
    print("OK: verify rejects when moltbook disabled")


def test_verify_missing_app_key():
    """verify_moltbook_identity should reject when MOLTBOOK_APP_KEY is not set."""
    with patch.dict(os.environ, {}, clear=True):
        # Make sure MOLTBOOK_APP_KEY is not set
        os.environ.pop("MOLTBOOK_APP_KEY", None)
        result = verify_moltbook_identity("some-token", TEST_CONFIG, use_cache=False)
    assert result["valid"] is False
    assert result["error"] == "missing_app_key"
    print("OK: verify rejects missing app key")


@patch.dict(os.environ, {"MOLTBOOK_APP_KEY": "moltdev_testkey123"})
def test_verify_success():
    """verify_moltbook_identity should return agent on successful verification."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "valid": True,
        "success": True,
        "agent": SAMPLE_AGENT,
    }
    mock_response.headers = {}

    with patch("moltbook_auth.requests.post", return_value=mock_response):
        result = verify_moltbook_identity("valid-token", TEST_CONFIG, use_cache=False)

    assert result["valid"] is True
    assert result["agent"] is not None
    assert result["agent"]["name"] == "TestBot"
    assert result["agent"]["karma"] == 420
    assert result["agent"]["is_claimed"] is True
    assert result["error"] is None
    print("OK: verify returns agent on success")


@patch.dict(os.environ, {"MOLTBOOK_APP_KEY": "moltdev_testkey123"})
def test_verify_expired_token():
    """verify_moltbook_identity should return identity_token_expired error."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "valid": False,
        "error": "identity_token_expired",
        "hint": "The identity token has expired. Request a new one.",
    }

    with patch("moltbook_auth.requests.post", return_value=mock_response):
        result = verify_moltbook_identity("expired-token", TEST_CONFIG, use_cache=False)

    assert result["valid"] is False
    assert result["error"] == "identity_token_expired"
    print("OK: verify returns expired token error")


@patch.dict(os.environ, {"MOLTBOOK_APP_KEY": "moltdev_testkey123"})
def test_verify_invalid_token():
    """verify_moltbook_identity should return invalid_token error."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "valid": False,
        "error": "invalid_token",
        "hint": "The token is malformed or has been tampered with.",
    }

    with patch("moltbook_auth.requests.post", return_value=mock_response):
        result = verify_moltbook_identity("bad-token", TEST_CONFIG, use_cache=False)

    assert result["valid"] is False
    assert result["error"] == "invalid_token"
    print("OK: verify returns invalid token error")


@patch.dict(os.environ, {"MOLTBOOK_APP_KEY": "moltdev_testkey123"})
def test_verify_rate_limited():
    """verify_moltbook_identity should handle 429 rate limit."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "30"}

    with patch("moltbook_auth.requests.post", return_value=mock_response):
        result = verify_moltbook_identity("some-token", TEST_CONFIG, use_cache=False)

    assert result["valid"] is False
    assert result["error"] == "rate_limit_exceeded"
    assert "30" in result["error_hint"]
    print("OK: verify handles rate limiting")


@patch.dict(os.environ, {"MOLTBOOK_APP_KEY": "moltdev_testkey123"})
def test_verify_caching():
    """verify_moltbook_identity should cache results for 5 minutes."""
    # Clear the cache first
    import moltbook_auth
    moltbook_auth._identity_cache.clear()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "valid": True,
        "success": True,
        "agent": SAMPLE_AGENT,
    }
    mock_response.headers = {}

    with patch("moltbook_auth.requests.post", return_value=mock_response) as mock_post:
        # First call — should hit the API
        result1 = verify_moltbook_identity("cache-test-token", TEST_CONFIG, use_cache=True)
        assert result1["valid"] is True
        assert mock_post.call_count == 1

        # Second call — should use cache (no API call)
        result2 = verify_moltbook_identity("cache-test-token", TEST_CONFIG, use_cache=True)
        assert result2["valid"] is True
        assert mock_post.call_count == 1  # Still 1 — cache hit

    # Clean up
    moltbook_auth._identity_cache.clear()
    print("OK: verify caches results")


@patch.dict(os.environ, {"MOLTBOOK_APP_KEY": "moltdev_testkey123"})
def test_verify_audience_sent():
    """verify_moltbook_identity should send audience when configured."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "valid": True,
        "success": True,
        "agent": SAMPLE_AGENT,
    }
    mock_response.headers = {}

    with patch("moltbook_auth.requests.post", return_value=mock_response) as mock_post:
        verify_moltbook_identity("token-with-audience", TEST_CONFIG, use_cache=False)

        call_args = mock_post.call_args
        body = call_args.kwargs.get("json", call_args[1].get("json", {}))
        assert body.get("audience") == "hat-stack"

    print("OK: verify sends audience parameter")


def test_extract_identity_header():
    """extract_moltbook_identity should find X-Moltbook-Identity header."""
    headers = {
        "Content-Type": "application/json",
        "X-Moltbook-Identity": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
    }

    token = extract_moltbook_identity(headers, TEST_CONFIG)
    assert token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
    print("OK: extract finds identity header")


def test_extract_identity_case_insensitive():
    """extract_moltbook_identity should handle case-insensitive headers."""
    headers = {
        "x-moltbook-identity": "case-test-token",
    }

    token = extract_moltbook_identity(headers, TEST_CONFIG)
    assert token == "case-test-token"
    print("OK: extract handles case-insensitive headers")


def test_extract_identity_missing():
    """extract_moltbook_identity should return None when header is absent."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer other-key",
    }

    token = extract_moltbook_identity(headers, TEST_CONFIG)
    assert token is None
    print("OK: extract returns None for missing header")


def test_format_agent_identity():
    """format_agent_identity should produce a human-readable string."""
    result = format_agent_identity(SAMPLE_AGENT)
    assert "TestBot" in result
    assert "420" in result
    assert "@human_owner" in result
    assert "claimed" in result
    print(f"OK: format produces '{result}'")


def test_format_unclaimed_agent():
    """format_agent_identity should handle unclaimed agents."""
    unclaimed = {**SAMPLE_AGENT, "is_claimed": False, "owner": {}}
    result = format_agent_identity(unclaimed)
    assert "unclaimed" in result
    assert "@unclaimed" in result
    print(f"OK: format unclaimed produces '{result}'")


if __name__ == "__main__":
    tests = [
        test_verify_missing_token,
        test_verify_moltbook_disabled,
        test_verify_missing_app_key,
        test_verify_success,
        test_verify_expired_token,
        test_verify_invalid_token,
        test_verify_rate_limited,
        test_verify_caching,
        test_verify_audience_sent,
        test_extract_identity_header,
        test_extract_identity_case_insensitive,
        test_extract_identity_missing,
        test_format_agent_identity,
        test_format_unclaimed_agent,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {test.__name__}: {e}")
            failed += 1

    print(f"\nMoltbook auth tests: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)