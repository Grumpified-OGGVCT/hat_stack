#!/usr/bin/env python3
"""
gremlin_daemon.py -- Self-scheduling daemon for the Gremlin overnight scanner.

Reads cron schedule from hat_configs.yml (gremlins.overnight_schedule),
sleeps until each phase's trigger time, and calls gremlin_runner phase functions
across all configured repos.

Features:
  - Lightweight 5-field cron parser (no external deps)
  - Config hot-reload: rebuilds schedule every loop
  - PID file management with stale PID cleanup
  - Signal handlers (SIGINT, SIGTERM, SIGBREAK on Windows)
  - Wake-on-LAN support
  - Herald bridge push after each phase
  - Single-cycle and dry-run modes for testing

Usage:
  python scripts/gremlin_daemon.py --daemon          # background daemon loop
  python scripts/gremlin_daemon.py --once             # single check-and-run cycle
  python scripts/gremlin_daemon.py --dry-run          # show plan without executing
  python scripts/gremlin_daemon.py --status           # show next runs + per-repo stats
  python scripts/gremlin_daemon.py --stop             # stop running daemon
"""

import argparse
import datetime
import json
import os
import signal
import sys
import time
from pathlib import Path

from hats_common import (
    load_config,
    is_overnight_mode,
    send_wake_on_lan,
    DEFAULT_CONFIG,
    preflight_check,
)
from gremlin_memory import (
    init_gremlin_memory_global,
    list_repos,
    read_ledger,
    list_proposals,
    read_herald,
)
from gremlin_runner import (
    phase_review,
    phase_propose,
    phase_analyze,
    phase_herald,
    show_status,
    _get_configured_repos,
    _repo_name_from_path,
)
from herald_bridge import push_to_openclaw


# ---------------------------------------------------------------------------
# PID file management
# ---------------------------------------------------------------------------

_PID_DIR = Path.home() / ".gremlins"
_PID_FILE = _PID_DIR / "gremlin_daemon.pid"
_LOG_FILE = _PID_DIR / "gremlin_daemon.log"


def _ensure_pid_dir():
    _PID_DIR.mkdir(parents=True, exist_ok=True)


def _write_pid():
    _ensure_pid_dir()
    _PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


def _read_pid():
    if not _PID_FILE.exists():
        return None
    try:
        return int(_PID_FILE.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def _remove_pid():
    try:
        _PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def _is_pid_running(pid: int) -> bool:
    """Check if a PID is still alive (cross-platform)."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    except (OSError, AttributeError):
        # Fallback: try os.kill(pid, 0) — works on Unix, may fail on Windows
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def _cleanup_stale_pid():
    """Remove PID file if the process is no longer running."""
    pid = _read_pid()
    if pid is not None and not _is_pid_running(pid):
        _remove_pid()


# ---------------------------------------------------------------------------
# Cron parser — lightweight 5-field cron (no deps)
# ---------------------------------------------------------------------------

_CRON_FIELDS = ["minute", "hour", "day_of_month", "month", "day_of_week"]


class CronExpression:
    """Parse and match a 5-field cron expression.

    Supported syntax:
      *       — any value
      5       — exact value
      1-5     — range (1 through 5)
      */15    — step (every 15)
      1,15,30 — list (values 1, 15, 30)
      1-5/2   — range with step (1, 3, 5)

    Day-of-week: 0=Sunday, 1=Monday, ..., 6=Saturday
    """

    def __init__(self, expression: str):
        self.raw = expression.strip()
        self.fields = self._parse(self.raw)

    def _parse_field(self, field_str: str, min_val: int, max_val: int) -> set[int]:
        """Parse a single cron field into a set of matching values."""
        values = set()
        for part in field_str.split(","):
            if "/" in part:
                base, step_str = part.split("/", 1)
                step = int(step_str)
                if base == "*":
                    start = min_val
                    end = max_val
                elif "-" in base:
                    start, end = map(int, base.split("-", 1))
                else:
                    start = int(base)
                    end = max_val
                for v in range(start, end + 1, step):
                    values.add(v % (max_val + 1) if v > max_val else v)
            elif "-" in part:
                start, end = map(int, part.split("-", 1))
                for v in range(start, end + 1):
                    values.add(v)
            elif part == "*":
                values.update(range(min_val, max_val + 1))
            else:
                values.add(int(part))
        return values

    def _parse(self, expression: str) -> dict:
        """Parse all 5 cron fields."""
        parts = expression.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression (expected 5 fields): {expression!r}")

        ranges = [
            (0, 59),   # minute
            (0, 23),   # hour
            (1, 31),   # day of month
            (1, 12),   # month
            (0, 6),    # day of week
        ]

        fields = {}
        for i, (field_name, (lo, hi)) in enumerate(zip(_CRON_FIELDS, ranges)):
            fields[field_name] = self._parse_field(parts[i], lo, hi)
        return fields

    def matches(self, dt: datetime.datetime) -> bool:
        """Check if this cron expression matches the given datetime."""
        return (
            dt.minute in self.fields["minute"]
            and dt.hour in self.fields["hour"]
            and dt.day in self.fields["day_of_month"]
            and dt.month in self.fields["month"]
            and dt.weekday() in self._weekday_map(self.fields["day_of_week"])
        )

    @staticmethod
    def _weekday_map(cron_dows: set[int]) -> set[int]:
        """Map cron day-of-week (0=Sun) to Python weekday (0=Mon)."""
        result = set()
        for dow in cron_dows:
            # Cron: 0=Sun, 1=Mon, ..., 6=Sat
            # Python: 0=Mon, 1=Tue, ..., 6=Sun
            if dow == 0:
                result.add(6)  # Sunday
            else:
                result.add(dow - 1)
        return result

    def next_run(self, after: datetime.datetime | None = None) -> datetime.datetime:
        """Calculate the next run time after 'after' (default: now).

        Brute-force approach: iterate minute-by-minute up to 1 year.
        """
        if after is None:
            after = datetime.datetime.now()

        candidate = after.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)

        # Limit search to 1 year from now
        deadline = after + datetime.timedelta(days=366)

        while candidate <= deadline:
            if self.matches(candidate):
                return candidate
            candidate += datetime.timedelta(minutes=1)

        # Should never happen with valid cron, but return far future
        return deadline


def parse_cron(expression: str) -> CronExpression:
    """Parse a cron expression string."""
    return CronExpression(expression)


# ---------------------------------------------------------------------------
# Schedule builder
# ---------------------------------------------------------------------------

def build_schedule(config: dict) -> dict[str, CronExpression]:
    """Build schedule from config's overnight_schedule dict.

    Returns dict mapping phase name -> CronExpression.
    Handles both dict and list formats (list gets DeprecationWarning).
    """
    gremlins_cfg = config.get("gremlins", {})
    schedule_cfg = gremlins_cfg.get("overnight_schedule")

    schedule = {}

    if schedule_cfg is None or (isinstance(schedule_cfg, dict) and len(schedule_cfg) == 0):
        # Default schedule when none configured
        defaults = {"review": "0 2 * * *", "propose": "0 3 * * *",
                    "analyze": "0 4 * * *", "herald": "0 5 * * *"}
        for phase, cron_str in defaults.items():
            schedule[phase] = CronExpression(cron_str)
    elif isinstance(schedule_cfg, dict):
        for phase, cron_str in schedule_cfg.items():
            try:
                schedule[phase] = CronExpression(cron_str)
            except ValueError as e:
                print(f"  WARNING: invalid cron for phase '{phase}': {e}", file=sys.stderr)
    elif isinstance(schedule_cfg, list):
        # Backward compat: list format was positional [review, propose, analyze, herald]
        import warnings
        warnings.warn(
            "overnight_schedule list format is deprecated. Use dict format: "
            "{review: '0 2 * * *', propose: '0 3 * * *', ...}",
            DeprecationWarning,
            stacklevel=2,
        )
        phase_names = ["review", "propose", "analyze", "herald"]
        default_crons = ["0 2 * * *", "0 3 * * *", "0 4 * * *", "0 5 * * *"]
        for i, cron_str in enumerate(schedule_cfg):
            phase = phase_names[i] if i < len(phase_names) else f"phase_{i}"
            try:
                schedule[phase] = CronExpression(cron_str)
            except ValueError:
                schedule[phase] = CronExpression(default_crons[i] if i < len(default_crons) else "0 0 * * *")
    # Fallback: if nothing was set, use defaults
    if not schedule:
        defaults = {"review": "0 2 * * *", "propose": "0 3 * * *",
                    "analyze": "0 4 * * *", "herald": "0 5 * * *"}
        for phase, cron_str in defaults.items():
            schedule[phase] = CronExpression(cron_str)

    return schedule


# ---------------------------------------------------------------------------
# GremlinDaemon
# ---------------------------------------------------------------------------

class GremlinDaemon:
    """Self-scheduling daemon that drives the multi-repo Gremlin system."""

    PHASE_ORDER = ["review", "propose", "analyze", "herald"]
    PHASE_FUNCTIONS = {
        "review": phase_review,
        "propose": phase_propose,
        "analyze": phase_analyze,
        "herald": phase_herald,
    }

    def __init__(self, config_path: str, gremlins_path: str | None = None):
        self.config_path = config_path
        self.gremlins_path = gremlins_path
        self.config = load_config(config_path)
        self.schedule = build_schedule(self.config)
        self.running = False
        self._last_run = {}  # phase -> datetime of last successful run
        self._wol_sent_today = False
        self._last_wol_date = None

        # Determine Gremlins root
        if gremlins_path:
            self.gremlins_root = init_gremlin_memory_global(Path(gremlins_path))
        else:
            self.gremlins_root = init_gremlin_memory_global(Path.cwd())

    def _reload_config(self):
        """Hot-reload config: re-read YAML, rebuild schedule."""
        try:
            self.config = load_config(self.config_path)
            self.schedule = build_schedule(self.config)
        except Exception as e:
            print(f"  WARNING: config reload failed: {e}", file=sys.stderr)

    def _maybe_send_wol(self):
        """Send Wake-on-LAN once per night before the first phase."""
        today = datetime.date.today()
        if self._last_wol_date == today:
            return

        wol_cfg = self.config.get("gremlins", {}).get("overnight", {}).get("wake_on_lan", {})
        if not wol_cfg.get("enabled", False):
            return

        if send_wake_on_lan(self.config):
            self._last_wol_date = today
            self._log("Wake-on-LAN packet sent")

    def _log(self, message: str):
        """Log a message with timestamp to stderr and log file."""
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}"
        print(line, file=sys.stderr)
        try:
            _ensure_pid_dir()
            with open(_LOG_FILE, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass

    def execute_phase(self, phase: str) -> dict | None:
        """Execute a single phase and push Herald output."""
        phase_fn = self.PHASE_FUNCTIONS.get(phase)
        if phase_fn is None:
            self._log(f"Unknown phase: {phase}")
            return None

        self._log(f"Starting phase: {phase.upper()}")
        try:
            result = phase_fn(self.config, self.gremlins_root)
            self._last_run[phase] = datetime.datetime.now()

            status = result.get("status", "unknown")
            self._log(f"Phase {phase.upper()}: {status}")

            # After Herald phase, push to bridge
            if phase == "herald" and status == "completed":
                try:
                    herald_dir = self.gremlins_root / "herald"
                    entries = read_herald(herald_dir)
                    if entries:
                        latest = entries[-1]["content"]
                        pushed = push_to_openclaw(latest)
                        self._log(f"Herald bridge push: {'ok' if pushed else 'unavailable'}")
                except Exception as e:
                    self._log(f"Herald bridge error: {e}")

            return result

        except Exception as e:
            self._log(f"Phase {phase.upper()} ERROR: {e}")
            return {"phase": phase, "status": "error", "error": str(e)}

    def run_once(self):
        """Single check-and-run cycle: check schedule, run any due phases."""
        now = datetime.datetime.now()
        self._reload_config()

        for phase in self.PHASE_ORDER:
            if phase not in self.schedule:
                continue

            cron = self.schedule[phase]

            # Check if this phase should run now (match current minute)
            if cron.matches(now):
                # Avoid re-running within the same minute
                last = self._last_run.get(phase)
                if last and (now - last).total_seconds() < 120:
                    continue

                # Send WoL before first phase of the night
                self._maybe_send_wol()

                self.execute_phase(phase)

    def run_forever(self):
        """Main daemon loop: sleep in 30s chunks, wake at scheduled times."""
        self.running = True
        _write_pid()
        self._log(f"Daemon started (PID {os.getpid()})")

        # Print schedule
        self._log("Schedule:")
        now = datetime.datetime.now()
        for phase in self.PHASE_ORDER:
            if phase in self.schedule:
                next_run = self.schedule[phase].next_run(now)
                self._log(f"  {phase}: next run at {next_run.strftime('%Y-%m-%d %H:%M')}")

        try:
            while self.running:
                self.run_once()
                time.sleep(30)  # Check every 30 seconds
        except KeyboardInterrupt:
            self._log("Interrupted by user")
        finally:
            self._remove_pid()
            self._log("Daemon stopped")

    def run_dry(self):
        """Show schedule plan + repos without executing."""
        now = datetime.datetime.now()
        print("=== Gremlin Daemon Dry Run ===\n")
        print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Overnight mode: {is_overnight_mode(self.config)}")

        # Schedule
        print("\nSchedule:")
        for phase in self.PHASE_ORDER:
            if phase in self.schedule:
                cron = self.schedule[phase]
                next_run = cron.next_run(now)
                matches_now = cron.matches(now)
                flag = " <-- NOW" if matches_now else ""
                print(f"  {phase}: cron='{cron.raw}'  next={next_run.strftime('%Y-%m-%d %H:%M')}{flag}")

        # Repos
        repos = _get_configured_repos(self.config)
        print(f"\nConfigured repos ({len(repos)}):")
        for repo in repos:
            repo_name = _repo_name_from_path(repo["path"])
            skip = repo.get("skip_phases", [])
            enabled = repo.get("enabled", True)
            skip_str = f" (skip: {', '.join(skip)})" if skip else ""
            status_str = "enabled" if enabled else "disabled"
            print(f"  {repo_name}: {repo['path']} [{status_str}]{skip_str}")

        # Per-repo stats
        print("\nPer-repo stats:")
        for repo_info in list_repos(self.gremlins_root):
            repo_name = repo_info["name"]
            repo_dir = Path(repo_info["path"])
            findings = read_ledger(repo_dir, category="findings")
            proposals = list_proposals(repo_dir)
            pending = [p for p in proposals if p["status"] == "PENDING_HUMAN"]
            reviews = read_ledger(repo_dir, category="reviews")
            print(f"  {repo_name}: {len(findings)} findings, {len(proposals)} proposals "
                  f"({len(pending)} pending), {len(reviews)} reviews")

        print("\nNo phases were executed (dry run).")

    def show_daemon_status(self):
        """Show daemon status: next runs, PID, per-repo stats."""
        now = datetime.datetime.now()
        print("=== Gremlin Daemon Status ===\n")

        # PID check
        pid = _read_pid()
        if pid and _is_pid_running(pid):
            print(f"Daemon: RUNNING (PID {pid})")
        else:
            print("Daemon: NOT RUNNING")
            _cleanup_stale_pid()

        print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Overnight mode: {is_overnight_mode(self.config)}")

        # Next runs
        print("\nNext scheduled runs:")
        for phase in self.PHASE_ORDER:
            if phase in self.schedule:
                cron = self.schedule[phase]
                next_run = cron.next_run(now)
                last_run = self._last_run.get(phase, "never")
                print(f"  {phase}: next={next_run.strftime('%Y-%m-%d %H:%M')}  last={last_run}")

        # Runner status
        status = show_status(self.config, self.gremlins_root)
        print(f"\nConfigured repos: {status['configured_repos']}")
        if status["repo_stats"]:
            for rs in status["repo_stats"]:
                print(f"  {rs['repo']}: {rs['findings']} findings, {rs['proposals']} proposals "
                      f"({rs['pending']} pending), {rs['reviews']} reviews")

        print(f"\nTotal findings: {status['total_findings']}")
        print(f"Total proposals: {status['total_proposals']} ({status['pending_proposals']} pending)")
        print(f"Total reviews: {status['total_reviews']}")
        print(f"Herald entries: {status['herald_entries']}")

    def stop_daemon(self):
        """Stop a running daemon by signaling its PID."""
        pid = _read_pid()
        if pid is None:
            print("No daemon PID file found. Daemon may not be running.")
            return

        if not _is_pid_running(pid):
            print(f"Daemon PID {pid} is not running. Cleaning up stale PID file.")
            _remove_pid()
            return

        print(f"Stopping daemon (PID {pid})...")
        try:
            # Try SIGTERM first
            os.kill(pid, signal.SIGTERM)
            # Wait for process to exit
            for _ in range(20):
                time.sleep(0.5)
                if not _is_pid_running(pid):
                    print("Daemon stopped.")
                    _remove_pid()
                    return
            # Force kill if still running
            os.kill(pid, signal.SIGKILL if hasattr(signal, 'SIGKILL') else signal.SIGTERM)
            print("Daemon force-stopped.")
            _remove_pid()
        except OSError as e:
            print(f"Error stopping daemon: {e}")
            _remove_pid()


# ---------------------------------------------------------------------------
# Signal handlers
# ---------------------------------------------------------------------------

_daemon_instance = None


def _signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _daemon_instance
    if _daemon_instance:
        _daemon_instance.running = False
        _daemon_instance._log(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def _setup_signal_handlers():
    """Install signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    # Windows-specific
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _signal_handler)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Gremlin Daemon -- self-scheduling multi-repo overnight scanner"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--daemon", action="store_true",
        help="Start daemon loop (runs in foreground, schedule with OS)"
    )
    mode.add_argument(
        "--once", action="store_true",
        help="Single check-and-run cycle (useful for testing)"
    )
    mode.add_argument(
        "--dry-run", action="store_true",
        help="Show schedule plan + repos without executing"
    )
    mode.add_argument(
        "--status", action="store_true",
        help="Show daemon status, next runs, per-repo stats"
    )
    mode.add_argument(
        "--stop", action="store_true",
        help="Stop a running daemon"
    )

    parser.add_argument(
        "--config", default=str(DEFAULT_CONFIG),
        help="Path to hat_configs.yml"
    )
    parser.add_argument(
        "--gremlins-path", default=None,
        help="Path to Gremlins root (default: .gremlins in current dir)"
    )
    parser.add_argument(
        "--overnight", action="store_true",
        help="Force overnight mode (for testing)"
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Force overnight mode if requested
    if args.overnight and "gremlins" in config:
        config["gremlins"].setdefault("overnight", {})["enabled"] = True

    # Preflight
    issues = preflight_check(config)
    for msg in issues:
        print(msg, file=sys.stderr)

    # Handle --stop (doesn't need daemon instance)
    if args.stop:
        GremlinDaemon(args.config, args.gremlins_path).stop_daemon()
        return

    # Create daemon
    daemon = GremlinDaemon(args.config, args.gremlins_path)
    daemon.config = config  # Use possibly-overridden config

    global _daemon_instance
    _daemon_instance = daemon

    if args.dry_run:
        daemon.run_dry()

    elif args.status:
        daemon.show_daemon_status()

    elif args.once:
        daemon.run_once()
        daemon._log("Single cycle completed")

    elif args.daemon:
        _cleanup_stale_pid()
        _setup_signal_handlers()
        daemon.run_forever()


if __name__ == "__main__":
    main()