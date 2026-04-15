#!/usr/bin/env python3
"""
consolidator.py — Finding consolidation for Hat Stack.

Implements SPEC §9.3:
  - Finding deduplication by (file, line_range, category) tuple
  - Severity normalization (keep highest severity)
  - Conflict detection (mutually exclusive recommendations)
  - Timed-out hat gap recording (NOT_EVALUATED)
"""

from typing import Any

# Severity ordering for comparison
_SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}


def normalize_severity(severity: str) -> str:
    """Normalize a severity string to one of: CRITICAL, HIGH, MEDIUM, LOW, INFO."""
    s = (severity or "LOW").strip().upper()
    if s in _SEVERITY_ORDER:
        return s
    # Common aliases
    aliases = {
        "FATAL": "CRITICAL", "BLOCKER": "CRITICAL", "CRIT": "CRITICAL",
        "ERROR": "HIGH", "MAJOR": "HIGH", "WARN": "MEDIUM", "WARNING": "MEDIUM",
        "MINOR": "LOW", "INFO": "INFO", "NOTE": "INFO", "SUGGESTION": "LOW",
    }
    return aliases.get(s, "LOW")


def severity_rank(severity: str) -> int:
    """Return numeric rank for a severity level. Higher = more severe."""
    return _SEVERITY_ORDER.get(normalize_severity(severity), 0)


def dedup_key(finding: dict) -> tuple:
    """Build a deduplication key from (file, line_range, category).

    Per SPEC §9.3, findings with the same key are duplicates — keep the
    highest severity version.
    """
    file_path = finding.get("file") or "*"
    line = finding.get("line")
    line_range = finding.get("line_range") or (str(line) if line else "*")
    category = finding.get("category") or finding.get("severity", "LOW")
    return (file_path, str(line_range), category)


def consolidate_findings(
    reports: list[dict],
    timed_out_hats: list[str] | None = None,
) -> dict:
    """Consolidate findings from all hat reports per SPEC §9.3.

    Operations:
    1. Deduplication by (file, line_range, category) — keep highest severity
    2. Severity normalization
    3. Conflict detection — tag contradictory findings as conflicted: true
    4. Timed-out hat gap recording — mark areas as NOT_EVALUATED

    Returns dict with keys:
      all_findings: list[dict] — deduplicated, normalized findings
      severity_counts: dict[str, int]
      dedup_stats: dict — counts of original vs deduplicated
      not_evaluated_hats: list[str] — hats that timed out
      conflicts: list[dict] — pairs of conflicting findings
    """
    timed_out_hats = timed_out_hats or []

    # Collect all findings from all reports
    raw_findings: list[dict] = []
    hat_summaries: list[dict] = []
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    total_tokens = {"input": 0, "output": 0}

    for report in reports:
        hat_summaries.append({
            "hat": report["hat_name"],
            "emoji": report["emoji"],
            "model": report["model_used"],
            "latency_s": report["latency_seconds"],
            "findings_count": len(report["findings"]),
            "error": report.get("error"),
        })

        total_tokens["input"] += report["token_usage"]["input"]
        total_tokens["output"] += report["token_usage"]["output"]

        for finding in report["findings"]:
            # Normalize severity
            finding["severity"] = normalize_severity(finding.get("severity", "LOW"))
            finding["source_hat"] = report["hat_name"]
            finding["source_emoji"] = report["emoji"]
            finding["conflicted"] = False
            raw_findings.append(finding)

    # Deduplicate by key, keeping highest severity
    dedup_map: dict[tuple, dict] = {}
    for finding in raw_findings:
        key = dedup_key(finding)
        if key not in dedup_map:
            dedup_map[key] = finding
        else:
            existing = dedup_map[key]
            if severity_rank(finding["severity"]) > severity_rank(existing["severity"]):
                # Keep the higher-severity version, but preserve both source hats
                sources = set()
                sources.add(existing.get("source_hat", ""))
                sources.add(finding.get("source_hat", ""))
                finding["source_hats"] = list(s for s in sources if s)
                dedup_map[key] = finding
            else:
                # Keep existing, but note additional source
                sources = set()
                sources.add(existing.get("source_hat", ""))
                sources.add(finding.get("source_hat", ""))
                existing["source_hats"] = list(s for s in sources if s)

    deduplicated = list(dedup_map.values())

    # Count severities after dedup
    for finding in deduplicated:
        sev = finding["severity"]
        if sev in severity_counts:
            severity_counts[sev] += 1

    # Detect conflicts (simple: same file, opposite recommendations)
    conflicts = _detect_conflicts(deduplicated)

    # Tag conflicted findings
    conflicted_indices = set()
    for conflict in conflicts:
        conflicted_indices.add(conflict["index_a"])
        conflicted_indices.add(conflict["index_b"])

    for idx in conflicted_indices:
        if idx < len(deduplicated):
            deduplicated[idx]["conflicted"] = True

    return {
        "all_findings": deduplicated,
        "severity_counts": severity_counts,
        "hat_summaries": hat_summaries,
        "total_tokens": total_tokens,
        "hats_executed": len(reports),
        "hats_failed": sum(1 for r in reports if r.get("error")),
        "dedup_stats": {
            "original_count": len(raw_findings),
            "deduplicated_count": len(deduplicated),
            "removed_duplicates": len(raw_findings) - len(deduplicated),
        },
        "not_evaluated_hats": timed_out_hats,
        "conflicts": conflicts,
    }


def _detect_conflicts(findings: list[dict]) -> list[dict]:
    """Detect conflicting findings — same file, opposite actions.

    Two findings conflict if they reference the same file and have
    contradictory recommendations (e.g., "add X" vs "remove X").
    """
    conflicts = []

    # Group findings by file
    by_file: dict[str, list[tuple[int, dict]]] = {}
    for i, finding in enumerate(findings):
        filepath = finding.get("file") or ""
        if filepath:
            by_file.setdefault(filepath, []).append((i, finding))

    _opposite_patterns = [
        (r"add\s+", r"remove\s+"),
        (r"increase\s+", r"decrease\s+"),
        (r"enable\s+", r"disable\s+"),
        (r"expand\s+", r"restrict\s+"),
        (r"implement\s+", r"remove\s+"),
        (r"create\s+", r"delete\s+"),
        (r"introduce\s+", r"eliminate\s+"),
    ]

    import re

    for filepath, file_findings in by_file.items():
        for i, (idx_a, finding_a) in enumerate(file_findings):
            for idx_b, finding_b in file_findings[i + 1:]:
                rec_a = (finding_a.get("recommendation") or "").lower()
                rec_b = (finding_b.get("recommendation") or "").lower()
                for pos_pattern, neg_pattern in _opposite_patterns:
                    if (re.search(pos_pattern, rec_a) and re.search(neg_pattern, rec_b)) or \
                       (re.search(neg_pattern, rec_a) and re.search(pos_pattern, rec_b)):
                        conflicts.append({
                            "index_a": idx_a,
                            "index_b": idx_b,
                            "finding_a": finding_a,
                            "finding_b": finding_b,
                            "conflict_type": "opposite_recommendation",
                        })
                        break

    return conflicts