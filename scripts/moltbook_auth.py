#!/usr/bin/env python3
"""
moltbook_auth.py — "Sign in with Moltbook" agent authentication for Hat Stack.

Verifies Moltbook identity tokens from the X-Moltbook-Identity header.
Calls POST https://moltbook.com/api/v1/agents/verify-identity with the
app's API key and the identity token.

Flow:
  1. Agent obtains identity token from Moltbook (POST /agents/me/identity-token)
  2. Agent sends token in X-Moltbook-Identity header to Hat Stack
  3. Hat Stack calls verify-identity with its MOLTBOOK_APP_KEY
  4. If valid, the agent profile (name, karma, owner) is attached to context

Usage:
  from moltbook_auth import verify_moltbook_identity, MoltbookAgent

  agent = verify_moltbook_identity(identity_token, config)
  if agent:
      print(f"Authenticated: {agent.name} (karma: {agent.karma})")
"""

import os
import time
from typing import Any, TypedDict

import requests


# Cache verified identities to reduce API calls (TTL: 5 minutes)
_identity_cache: dict[str, tuple[float, "MoltbookAgent"]] = {}
_CACHE_TTL = 300  # seconds


class MoltbookAgent(TypedDict, total=False):
    """Verified Moltbook agent profile."""
    id: str
    name: str
    description: str
    karma: int
    avatar_url: str
    is_claimed: bool
    created_at: str
    follower_count: int
    following_count: int
    stats: dict
    owner: dict
    human: dict


class MoltbookVerifyResult(TypedDict):
    """Result of a Moltbook identity verification."""
    valid: bool
    agent: MoltbookAgent | None
    error: str | None
    error_hint: str | None


def verify_moltbook_identity(
    identity_token: str,
    config: dict,
    audience: str | None = None,
    use_cache: bool = True,
) -> MoltbookVerifyResult:
    """Verify a Moltbook identity token.

    Args:
        identity_token: The token from the X-Moltbook-Identity header
        config: Hat Stack config dict (loaded from hat_configs.yml)
        audience: Override audience (default: from config)
        use_cache: Cache verified tokens for 5 minutes

    Returns:
        MoltbookVerifyResult with valid, agent, error fields
    """
    if not identity_token:
        return {
            "valid": False,
            "agent": None,
            "error": "missing_token",
            "error_hint": "No identity token provided in X-Moltbook-Identity header",
        }

    # Check config
    mb_cfg = config.get("moltbook", {})
    if not mb_cfg.get("enabled", False):
        return {
            "valid": False,
            "agent": None,
            "error": "moltbook_disabled",
            "error_hint": "Moltbook authentication is not enabled in hat_configs.yml",
        }

    app_key = os.environ.get(mb_cfg.get("app_key_env", "MOLTBOOK_APP_KEY"), "")
    if not app_key:
        return {
            "valid": False,
            "agent": None,
            "error": "missing_app_key",
            "error_hint": "MOLTBOOK_APP_KEY environment variable not set",
        }

    # Check cache
    if use_cache and identity_token in _identity_cache:
        cached_time, cached_agent = _identity_cache[identity_token]
        if time.time() - cached_time < _CACHE_TTL:
            return {
                "valid": True,
                "agent": cached_agent,
                "error": None,
                "error_hint": None,
            }

    # Call verify endpoint
    verify_url = mb_cfg.get("verify_url", "https://moltbook.com/api/v1/agents/verify-identity")
    effective_audience = audience or mb_cfg.get("audience")

    headers = {
        "Content-Type": "application/json",
        "X-Moltbook-App-Key": app_key,
    }

    body: dict[str, str] = {"token": identity_token}
    if effective_audience:
        body["audience"] = effective_audience

    try:
        resp = requests.post(verify_url, headers=headers, json=body, timeout=10)

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After", "60")
            return {
                "valid": False,
                "agent": None,
                "error": "rate_limit_exceeded",
                "error_hint": f"Rate limited. Retry after {retry_after}s.",
            }

        data = resp.json()

        if not data.get("valid", False):
            error = data.get("error", "invalid_token")
            hint = data.get("hint", "")
            return {
                "valid": False,
                "agent": None,
                "error": error,
                "error_hint": hint,
            }

        agent_data = data.get("agent", {})
        agent: MoltbookAgent = {
            "id": agent_data.get("id", ""),
            "name": agent_data.get("name", ""),
            "description": agent_data.get("description", ""),
            "karma": agent_data.get("karma", 0),
            "avatar_url": agent_data.get("avatar_url", ""),
            "is_claimed": agent_data.get("is_claimed", False),
            "created_at": agent_data.get("created_at", ""),
            "follower_count": agent_data.get("follower_count", 0),
            "following_count": agent_data.get("following_count", 0),
            "stats": agent_data.get("stats", {}),
            "owner": agent_data.get("owner", {}),
            "human": agent_data.get("human", {}),
        }

        # Cache the verified identity
        if use_cache:
            _identity_cache[identity_token] = (time.time(), agent)

        return {
            "valid": True,
            "agent": agent,
            "error": None,
            "error_hint": None,
        }

    except requests.exceptions.Timeout:
        return {
            "valid": False,
            "agent": None,
            "error": "verification_timeout",
            "error_hint": "Moltbook verify endpoint timed out",
        }
    except requests.exceptions.RequestException as exc:
        return {
            "valid": False,
            "agent": None,
            "error": "verification_failed",
            "error_hint": str(exc),
        }
    except (ValueError, KeyError) as exc:
        return {
            "valid": False,
            "agent": None,
            "error": "invalid_response",
            "error_hint": f"Unexpected response format: {exc}",
        }


def extract_moltbook_identity(headers: dict[str, str], config: dict) -> str | None:
    """Extract the Moltbook identity token from request headers.

    Args:
        headers: Dict of request headers (case-insensitive lookup)
        config: Hat Stack config dict

    Returns:
        The identity token string, or None if not present
    """
    mb_cfg = config.get("moltbook", {})
    header_name = mb_cfg.get("header_name", "X-Moltbook-Identity").lower()

    # Case-insensitive header lookup
    for key, value in headers.items():
        if key.lower() == header_name:
            return value

    return None


def format_agent_identity(agent: MoltbookAgent) -> str:
    """Format a verified agent identity for logging/display.

    Returns a human-readable string like:
      "GremlinBot (karma: 420, owner: @human_owner)"
    """
    name = agent.get("name", "Unknown")
    karma = agent.get("karma", 0)
    owner_info = agent.get("owner", {})
    owner_handle = owner_info.get("x_handle", "unclaimed")
    claimed = "claimed" if agent.get("is_claimed") else "unclaimed"

    return f"{name} (karma: {karma}, owner: @{owner_handle}, {claimed})"