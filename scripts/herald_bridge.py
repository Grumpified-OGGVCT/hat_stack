#!/usr/bin/env python3
"""
herald_bridge.py — Push Herald social output to external channels.

Reads .gremlins/herald/social_log/ and pushes to:
  - OpenClaw Factory bridge (localhost:8765)
  - Future: Telegram, Discord, Slack

This is a thin adapter — the Herald Gremlin produces the content,
this script delivers it.
"""

import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None


def push_to_openclaw(content: str | None = None, channel: str = "gremlin-herald",
                     gremlins_root: Path | None = None) -> bool:
    """Push Herald content to the OpenClaw Factory bridge.

    If content is empty/None, auto-reads the latest Herald entry from disk.
    """
    if not requests:
        return False

    # Auto-read from disk when content is empty
    if not content:
        content = _read_latest_herald(gremlins_root)
        if not content:
            return False

    bridge_url = os.environ.get("OPENCLAW_BRIDGE_URL", "http://localhost:8765")
    try:
        resp = requests.post(
            f"{bridge_url}/events",
            json={
                "type": "gremlin-herald",
                "channel": channel,
                "content": content,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            timeout=5,
        )
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False


def _read_latest_herald(gremlins_root: Path | None = None) -> str | None:
    """Read the latest Herald entry from disk.

    Looks in .gremlins/herald/social_log/ for today's entry, falling back
    to the most recent file.
    """
    if gremlins_root is None:
        gremlins_root = Path.cwd() / ".gremlins"

    # Try the new multi-repo herald location first
    social_dir = gremlins_root / "herald" / "social_log"
    if not social_dir.exists():
        # Fallback: old single-repo location
        social_dir = gremlins_root / "social_log"
    if not social_dir.exists():
        return None

    # Try today's file first
    today = time.strftime("%Y-%m-%d", time.gmtime())
    today_file = social_dir / f"{today}-social_log.md"
    if today_file.exists():
        return today_file.read_text(encoding="utf-8")

    # Fall back to the most recent file
    md_files = sorted(social_dir.glob("*-social_log.md"), reverse=True)
    if md_files:
        return md_files[0].read_text(encoding="utf-8")

    return None


def main():
    # Find the most recent Herald entry
    gremlins_path = Path.cwd() / ".gremlins"

    success = push_to_openclaw(gremlins_root=gremlins_path)
    if success:
        print("Pushed Herald digest to OpenClaw bridge", file=sys.stderr)
    else:
        print("OpenClaw bridge not available (non-blocking)", file=sys.stderr)


if __name__ == "__main__":
    main()