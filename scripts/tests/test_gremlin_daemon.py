#!/usr/bin/env python3
"""Unit tests for gremlin_daemon.py -- Cron parser, schedule builder, daemon."""

import datetime
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gremlin_daemon import CronExpression, parse_cron, build_schedule


# ---------------------------------------------------------------------------
# Cron parser tests
# ---------------------------------------------------------------------------

def test_parse_basic_cron():
    """CronExpression should parse a basic 5-field cron expression."""
    cron = parse_cron("0 2 * * *")
    assert cron.fields["minute"] == {0}
    assert cron.fields["hour"] == {2}
    assert cron.fields["day_of_month"] == set(range(1, 32))
    assert cron.fields["month"] == set(range(1, 13))
    assert cron.fields["day_of_week"] == set(range(0, 7))
    print("OK: basic cron parsed correctly")


def test_parse_star_cron():
    """CronExpression should handle all-wildcard cron (* * * * *)."""
    cron = parse_cron("* * * * *")
    assert cron.fields["minute"] == set(range(0, 60))
    assert cron.fields["hour"] == set(range(0, 24))
    print("OK: star cron parsed correctly")


def test_parse_range_cron():
    """CronExpression should parse range expressions (e.g., 1-5)."""
    cron = parse_cron("0 1-5 * * *")
    assert cron.fields["hour"] == {1, 2, 3, 4, 5}
    print("OK: range cron parsed correctly")


def test_parse_step_cron():
    """CronExpression should parse step expressions (e.g., */15)."""
    cron = parse_cron("*/15 * * * *")
    assert 0 in cron.fields["minute"]
    assert 15 in cron.fields["minute"]
    assert 30 in cron.fields["minute"]
    assert 45 in cron.fields["minute"]
    print("OK: step cron parsed correctly")


def test_parse_list_cron():
    """CronExpression should parse comma-separated values (e.g., 1,15,30)."""
    cron = parse_cron("1,15,30 * * * *")
    assert cron.fields["minute"] == {1, 15, 30}
    print("OK: list cron parsed correctly")


def test_parse_range_step_cron():
    """CronExpression should parse range with step (e.g., 1-5/2)."""
    cron = parse_cron("1-5/2 * * * *")
    assert cron.fields["minute"] == {1, 3, 5}
    print("OK: range+step cron parsed correctly")


def test_parse_invalid_cron():
    """CronExpression should raise ValueError for invalid expressions."""
    try:
        parse_cron("invalid")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("OK: invalid cron raises ValueError")


def test_cron_matches():
    """CronExpression.matches() should match correct datetimes."""
    cron = parse_cron("0 2 * * *")
    # 2 AM on any day should match
    dt_match = datetime.datetime(2026, 4, 16, 2, 0)
    assert cron.matches(dt_match)
    # 2:01 AM should NOT match (minute must be 0)
    dt_no_match = datetime.datetime(2026, 4, 16, 2, 1)
    assert not cron.matches(dt_no_match)
    # 3 AM should NOT match (hour must be 2)
    dt_no_match2 = datetime.datetime(2026, 4, 16, 3, 0)
    assert not cron.matches(dt_no_match2)
    print("OK: cron matches correct datetimes")


def test_cron_next_run_basic():
    """CronExpression.next_run() should calculate next run time."""
    cron = parse_cron("0 2 * * *")
    # At 1 AM, next run should be 2 AM today
    after = datetime.datetime(2026, 4, 16, 1, 0)
    next_run = cron.next_run(after)
    assert next_run.hour == 2
    assert next_run.minute == 0
    assert next_run.day == 16
    print("OK: next_run calculates correctly")


def test_cron_next_run_same_day():
    """next_run after 2 AM should return 2 AM tomorrow."""
    cron = parse_cron("0 2 * * *")
    after = datetime.datetime(2026, 4, 16, 3, 0)
    next_run = cron.next_run(after)
    assert next_run.day == 17
    assert next_run.hour == 2
    assert next_run.minute == 0
    print("OK: next_run goes to next day correctly")


def test_cron_next_run_weekday():
    """Cron with day-of-week should match correct weekdays."""
    # Mondays only (cron weekday 1 = Python weekday 0)
    cron = parse_cron("0 9 * * 1")
    # Friday April 10 2026
    friday = datetime.datetime(2026, 4, 10, 10, 0)
    next_run = cron.next_run(friday)
    # Should be Monday April 13
    assert next_run.weekday() == 0  # Monday
    assert next_run.day == 13
    print("OK: weekday cron matches correctly")


# ---------------------------------------------------------------------------
# Schedule builder tests
# ---------------------------------------------------------------------------

def test_schedule_from_dict_config():
    """build_schedule should parse overnight_schedule dict from config."""
    import yaml
    config_path = Path(__file__).resolve().parent.parent / "hat_configs.yml"
    with open(config_path, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    schedule = build_schedule(config)
    assert "review" in schedule
    assert "propose" in schedule
    assert "analyze" in schedule
    assert "herald" in schedule

    # Each should be a CronExpression
    for phase, cron in schedule.items():
        assert isinstance(cron, CronExpression), f"{phase} should be CronExpression"
    print("OK: build_schedule parses dict config correctly")


def test_schedule_default():
    """build_schedule should provide defaults for empty config."""
    schedule = build_schedule({})
    assert "review" in schedule
    assert "propose" in schedule
    assert "analyze" in schedule
    assert "herald" in schedule
    print("OK: build_schedule provides defaults")


# ---------------------------------------------------------------------------
# Multi-repo config tests
# ---------------------------------------------------------------------------

def test_multi_repo_config():
    """Validate repos list in hat_configs.yml."""
    import yaml
    config_path = Path(__file__).resolve().parent.parent / "hat_configs.yml"
    with open(config_path, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    repos = config.get("gremlins", {}).get("repos", [])
    assert len(repos) >= 1, "repos list should have entries"

    for repo in repos:
        assert "path" in repo, f"repo entry missing 'path': {repo}"
        assert repo["path"], f"repo path should not be empty: {repo}"
    print(f"OK: {len(repos)} repos configured correctly")


def test_daemon_dry_run():
    """GremlinDaemon dry-run should not execute any phases."""
    from gremlin_daemon import GremlinDaemon

    import yaml
    config_path = Path(__file__).resolve().parent.parent / "hat_configs.yml"
    with open(config_path, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    with tempfile.TemporaryDirectory() as tmpdir:
        daemon = GremlinDaemon(str(config_path), gremlins_path=tmpdir)
        daemon.config = config

        # dry_run prints to stdout/stderr but should not crash
        # Redirect stdout to capture output
        import io
        from contextlib import redirect_stdout

        output = io.StringIO()
        with redirect_stdout(output):
            daemon.run_dry()

        result = output.getvalue()
        assert "Dry Run" in result
        assert "review" in result
        assert "propose" in result
        assert "Configured repos" in result
        assert "No phases were executed" in result
        print("OK: daemon dry-run works without errors")


def test_daemon_status():
    """GremlinDaemon status should show schedule and repo info."""
    from gremlin_daemon import GremlinDaemon

    import yaml
    config_path = Path(__file__).resolve().parent.parent / "hat_configs.yml"
    with open(config_path, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    with tempfile.TemporaryDirectory() as tmpdir:
        daemon = GremlinDaemon(str(config_path), gremlins_path=tmpdir)
        daemon.config = config

        import io
        from contextlib import redirect_stdout

        output = io.StringIO()
        with redirect_stdout(output):
            daemon.show_daemon_status()

        result = output.getvalue()
        assert "Daemon" in result
        assert "Next scheduled runs" in result
        assert "review" in result
        print("OK: daemon status shows schedule and repos")


def test_pid_management():
    """PID file write/read/cleanup should work correctly."""
    from gremlin_daemon import _write_pid, _read_pid, _remove_pid, _cleanup_stale_pid, _PID_FILE

    with tempfile.TemporaryDirectory() as tmpdir:
        import gremlin_daemon
        original_pid_dir = gremlin_daemon._PID_DIR
        original_pid_file = gremlin_daemon._PID_FILE
        gremlin_daemon._PID_DIR = Path(tmpdir)
        gremlin_daemon._PID_FILE = Path(tmpdir) / "gremlin_daemon.pid"

        try:
            # Write current PID
            _write_pid()
            pid = _read_pid()
            assert pid == os.getpid()

            # Remove PID
            _remove_pid()
            pid = _read_pid()
            assert pid is None

            # Stale PID cleanup
            gremlin_daemon._PID_FILE.write_text("999999999", encoding="utf-8")
            _cleanup_stale_pid()
            assert not gremlin_daemon._PID_FILE.exists()

            print("OK: PID management works correctly")
        finally:
            gremlin_daemon._PID_DIR = original_pid_dir
            gremlin_daemon._PID_FILE = original_pid_file


if __name__ == "__main__":
    tests = [
        test_parse_basic_cron,
        test_parse_star_cron,
        test_parse_range_cron,
        test_parse_step_cron,
        test_parse_list_cron,
        test_parse_range_step_cron,
        test_parse_invalid_cron,
        test_cron_matches,
        test_cron_next_run_basic,
        test_cron_next_run_same_day,
        test_cron_next_run_weekday,
        test_schedule_from_dict_config,
        test_schedule_default,
        test_multi_repo_config,
        test_daemon_dry_run,
        test_daemon_status,
        test_pid_management,
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

    print(f"\nGremlin daemon tests: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)