#!/usr/bin/env python3
"""
hat_selector.py — Hat selection engine for Hat Stack.

Implements SPEC §6.2:
  1. Keyword heuristic mapping (fast, <50ms)
  2. AST pattern detection (if Semgrep available)
  3. Dependency analysis (package.json, requirements.txt changes)
  4. Mandatory baseline (Black, Blue, Purple always-on)
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Keyword-to-hat mapping — SPEC §6.2 Layer 1
# ---------------------------------------------------------------------------

# Maps keyword patterns to hat IDs.
# These are the same triggers defined in hat_configs.yml but extracted here
# for the explicit 4-layer selection algorithm.
_KEYWORD_HAT_MAP = {
    # Red Hat — Failure & Resilience
    "red": [
        r"\berror\b", r"\bretry\b", r"\bcatch\b", r"\bexception\b",
        r"\basync\b", r"\bconcurrent\b", r"\bthread\b", r"\block\b",
        r"\bmutex\b", r"\btimeout\b", r"\bdeadlock\b", r"\bcircuit.?break",
    ],
    # Black Hat — Security & Exploits (always-on, but has triggers for emphasis)
    "black": [
        r"\bauth\b", r"\blogin\b", r"\bpassword\b", r"\btoken\b",
        r"\bsecret\b", r"\bcredential\b", r"\binject", r"\bsql\b",
        r"\bxss\b", r"\bcsrf\b", r"\brce\b", r"\bexploit\b",
    ],
    # White Hat — Efficiency & Resources
    "white": [
        r"\bloop\b", r"\bquery\b", r"\bselect\b", r"\binsert\b",
        r"\bbatch\b", r"\bcache\b", r"\bmemory\b", r"\btoken\b",
        r"\boptimiz", r"\bperform", r"\bn\+1\b", r"\ballocat",
    ],
    # Yellow Hat — Synergies & Integration
    "yellow": [
        r"\bimport\b", r"\bapi\b", r"\bservice\b", r"\bendpoint\b",
        r"\binterface\b", r"\bdependency\b", r"\bintegrat", r"\bwebhook\b",
    ],
    # Green Hat — Evolution & Extensibility
    "green": [
        r"\bmodule\b", r"\bplugin\b", r"\babstract\b", r"\binterface\b",
        r"\bversion\b", r"\bdeprecat", r"\bextensib", r"\bpolymorph",
    ],
    # Indigo Hat — Cross-Feature Architecture
    "indigo": [
        r"\bimport\b", r"\bshared\b", r"\bcommon\b", r"\butil\b",
        r"\bintegrat", r"\bcross.?cut", r"\bdry\b", r"\bduplicat",
    ],
    # Cyan Hat — Innovation & Feasibility
    "cyan": [
        r"\bexperiment\b", r"\bprototype\b", r"\bnovel\b", r"\bllm\b",
        r"\bagent\b", r"\bml\b", r"\bai\b", r"\bmodel\b", r"\bneural\b",
    ],
    # Orange Hat — DevOps & Automation
    "orange": [
        r"\bdocker\b", r"\bdockerfile\b", r"\bci\b", r"\bworkflow\b",
        r"\bterraform\b", r"\bhelm\b", r"\bk8s\b", r"\bdeploy\b",
        r"\bkubernetes\b", r"\bcontainer\b",
    ],
    # Silver Hat — Context & Token Optimization
    "silver": [
        r"\bprompt\b", r"\bcontext\b", r"\btoken\b", r"\brag\b",
        r"\bembed\b", r"\bvector\b", r"\bchunk\b", r"\bretriev",
    ],
    # Azure Hat — MCP & Protocol Integration
    "azure": [
        r"\bmcp\b", r"\btool\b", r"\bfunction_call\b", r"\bschema\b",
        r"\ba2a\b", r"\bprotocol\b", r"\brpc\b", r"\bgrpc\b",
    ],
    # Brown Hat — Data Governance & Privacy
    "brown": [
        r"\bpii\b", r"\buser.?data\b", r"\bdata\b", r"\blog\b",
        r"\bstore\b", r"\bprivacy\b", r"\bgdpr\b", r"\bpersonal\b",
        r"\bhipaa\b", r"\bccpa\b",
    ],
    # Gray Hat — Observability & Reliability
    "gray": [
        r"\btrace\b", r"\bmetric\b", r"\blog\b", r"\bmonitor\b",
        r"\balert\b", r"\bsla\b", r"\bslo\b", r"\blatency\b",
        r"\bprometheus\b", r"\bgrafana\b",
    ],
    # Teal Hat — Accessibility & Inclusion
    "teal": [
        r"\bui\b", r"\bhtml\b", r"\bcss\b", r"\brender\b",
        r"\baria\b", r"\ba11y\b", r"\bi18n\b", r"\bl10n\b",
        r"\baccessib", r"\bscreen.?reader",
    ],
    # Steel Hat — Supply Chain & Dependencies
    "steel": [
        r"\bpackage\.json\b", r"\brequirements\.txt\b", r"\bgemfile\b",
        r"\bgo\.mod\b", r"\bpom\.xml\b", r"\bcargo\.toml\b",
        r"\blockfile\b", r"\bdependency\b", r"\bsbom\b", r"\bcve\b",
    ],
    # Chartreuse Hat — Testing & Evaluation
    "chartreuse": [
        r"\btest\b", r"\bspec\b", r"\bassert\b", r"\bexpect\b",
        r"\bmock\b", r"\bfixture\b", r"\bbenchmark\b", r"\bcoverage\b",
    ],
}


# ---------------------------------------------------------------------------
# Dependency analysis patterns — SPEC §6.2 Layer 3
# ---------------------------------------------------------------------------

_DEPENDENCY_FILES = {
    "package.json": ["steel", "yellow", "orange"],
    "package-lock.json": ["steel"],
    "requirements.txt": ["steel", "yellow", "orange"],
    "Pipfile": ["steel"],
    "Pipfile.lock": ["steel"],
    "go.mod": ["steel", "yellow"],
    "go.sum": ["steel"],
    "Cargo.toml": ["steel", "yellow"],
    "Cargo.lock": ["steel"],
    "pom.xml": ["steel", "yellow"],
    "Gemfile": ["steel", "yellow"],
    "Gemfile.lock": ["steel"],
    "composer.json": ["steel", "yellow"],
    "composer.lock": ["steel"],
    ".github/workflows/": ["orange"],
    "Dockerfile": ["orange"],
    "docker-compose.yml": ["orange"],
    "terraform/": ["orange"],
}

# File extension → hat associations
_EXTENSION_HAT_MAP = {
    ".py": ["chartreuse", "white", "gray"],
    ".ts": ["chartreuse", "azure", "teal"],
    ".tsx": ["teal", "chartreuse"],
    ".js": ["chartreuse", "azure", "teal"],
    ".jsx": ["teal", "chartreuse"],
    ".go": ["chartreuse", "white", "gray"],
    ".rs": ["chartreuse", "white", "gray"],
    ".sql": ["white", "brown", "gray"],
    ".yml": ["orange", "blue"],
    ".yaml": ["orange", "blue"],
    ".md": ["blue", "silver"],
    ".env": ["black", "brown"],
    ".tf": ["orange", "steel"],
}


# ---------------------------------------------------------------------------
# Main selection function
# ---------------------------------------------------------------------------

def select_hats(
    config: dict,
    diff_text: str,
    requested_hats: list[str] | None = None,
    changed_files: list[str] | None = None,
) -> list[str]:
    """Select hats to run based on the 4-layer selection algorithm per SPEC §6.2.

    Layer 1: Keyword heuristics (fast, <50ms)
    Layer 2: AST pattern detection (if Semgrep available, <500ms)
    Layer 3: Dependency analysis (package.json, requirements.txt changes)
    Layer 4: Mandatory baseline (Black, Blue, Purple always-on)

    If requested_hats is provided, only those hats (plus always-on) are used.
    Gold/CoVE is always appended at the end.
    """
    hats_cfg = config["hats"]
    selected = set()

    # Layer 4: Mandatory baseline — always-on hats
    always_hats = {hat_id for hat_id, hat_def in hats_cfg.items() if hat_def.get("always_run")}
    selected.update(always_hats)

    # Identify run_last hats (e.g., Gold/CoVE) from config
    run_last_hats = {hat_id for hat_id, hat_def in hats_cfg.items() if hat_def.get("run_last")}

    # If caller requested specific hats, only include those (plus always-on)
    if requested_hats is not None:
        for hat_id in requested_hats:
            if hat_id in hats_cfg:
                selected.add(hat_id)
        # run_last hats must always run last
        last = selected & run_last_hats
        selected -= last
        ordered = _order_hats(selected, hats_cfg) + sorted(last)
        return ordered

    # Layer 1: Keyword heuristics
    diff_lower = diff_text.lower()
    for hat_id, patterns in _KEYWORD_HAT_MAP.items():
        for pattern in patterns:
            if re.search(pattern, diff_lower):
                selected.add(hat_id)
                break

    # Layer 3: Dependency analysis
    if changed_files:
        for filepath in changed_files:
            # Check explicit dependency files
            for dep_file, hat_ids in _DEPENDENCY_FILES.items():
                if dep_file in filepath:
                    selected.update(hat_ids)

            # Check file extensions
            ext = Path(filepath).suffix.lower()
            if ext in _EXTENSION_HAT_MAP:
                selected.update(_EXTENSION_HAT_MAP[ext])

            # Check against hat trigger keywords in filename
            for hat_id, hat_def in hats_cfg.items():
                triggers = hat_def.get("triggers", [])
                for trigger in triggers:
                    if trigger.lower() in filepath.lower():
                        selected.add(hat_id)
                        break
    else:
        # Extract changed files from diff headers
        extracted_files = _extract_changed_files(diff_text)
        for filepath in extracted_files:
            for dep_file, hat_ids in _DEPENDENCY_FILES.items():
                if dep_file in filepath:
                    selected.update(hat_ids)
            ext = Path(filepath).suffix.lower() if "." in filepath else ""
            if ext in _EXTENSION_HAT_MAP:
                selected.update(_EXTENSION_HAT_MAP[ext])

    # Layer 2: AST pattern detection (Semgrep) — placeholder
    # If semgrep is available, run rules and activate additional hats.
    # This is optional and not blocking; skip if semgrep is not installed.
    _ast_hats = _detect_ast_patterns(diff_text)
    selected.update(_ast_hats)

    # Ensure run_last hats (e.g., Gold/CoVE) are last
    last = selected & run_last_hats
    selected -= last

    # Order the selected hats
    ordered = _order_hats(selected, hats_cfg) + sorted(last)

    return ordered


def _extract_changed_files(diff_text: str) -> list[str]:
    """Extract file paths from diff headers (--- a/path, +++ b/path)."""
    files = []
    for line in diff_text.split("\n"):
        if line.startswith("+++ b/"):
            filepath = line[6:].strip()
            if filepath and filepath != "/dev/null":
                files.append(filepath)
    return files


# Semgrep rule categories → hat IDs
_SEMGREP_RULE_HAT_MAP = {
    "security": {"black", "purple"},
    "secrets": {"black", "brown"},
    "sql": {"black", "white"},
    "xss": {"black"},
    "injection": {"black"},
    "crypto": {"black"},
    "correctness": {"red", "blue"},
    "performance": {"white"},
    "accessibility": {"teal"},
    "best-practice": {"blue", "green"},
    "design": {"green"},
    "test": {"chartreuse"},
}


def _detect_ast_patterns(diff_text: str) -> set[str]:
    """Layer 2: AST pattern detection using Semgrep (optional).

    Runs `semgrep --config auto` on the diff if semgrep is installed.
    Maps rule categories to hat IDs. Falls back gracefully if semgrep
    is not available or times out.
    """
    import subprocess
    import shutil

    if not shutil.which("semgrep"):
        return set()

    activated_hats = set()
    try:
        # Write diff to a temp file for semgrep to scan
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False,
                                         encoding="utf-8") as tmp:
            tmp.write(diff_text)
            tmp_path = tmp.name

        result = subprocess.run(
            ["semgrep", "--config", "auto", "--json", "--quiet", tmp_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            for finding in data.get("results", []):
                check_id = finding.get("check_id", "")
                # Extract rule category from check_id (e.g., "security.sql-injection")
                category = check_id.split(".")[0] if "." in check_id else ""
                if category in _SEMGREP_RULE_HAT_MAP:
                    activated_hats.update(_SEMGREP_RULE_HAT_MAP[category])

        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, OSError):
        # Semgrep failed — not blocking, return what we have
        pass

    return activated_hats


def _order_hats(hat_ids: set[str], hats_cfg: dict) -> list[str]:
    """Order selected hats by their number for deterministic execution."""
    numbered = []
    for hat_id in hat_ids:
        hat_def = hats_cfg.get(hat_id, {})
        number = hat_def.get("number", 99)
        numbered.append((number, hat_id))
    numbered.sort(key=lambda x: x[0])
    return [hat_id for _, hat_id in numbered]