#!/usr/bin/env python3
"""
skills_crawler.py — Crawl _universal_skills/ SKILL.md files and build a searchable taxonomy.

Phase catalog (6th Gremlin phase): runs at 1 AM before the review phase.
Scans _universal_skills/*/SKILL.md, extracts metadata from YAML front-matter,
groups skills by category, identifies cross-skill combination opportunities,
and writes skills_taxonomy.json to .gremlins/experiments/.

Incremental: only processes new/changed skills since last crawl.

Usage:
  python scripts/skills_crawler.py --config scripts/hat_configs.yml
  python scripts/skills_crawler.py --full  # Force full re-crawl
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# YAML front-matter parser (tolerant — handles nested YAML, inline JSON, etc.)
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML front-matter from a SKILL.md file.

    Returns (metadata_dict, body_text).
    Handles: simple key: value, nested YAML, inline JSON in metadata field,
    multi-line folded scalars (description: >).
    """
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    yaml_text = parts[1].strip()
    body = parts[2].strip()

    metadata = {}
    # Try PyYAML first for proper parsing
    try:
        import yaml
        metadata = yaml.safe_load(yaml_text) or {}
        if not isinstance(metadata, dict):
            metadata = {}
        return metadata, body
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: simple line-by-line parser (handles flat key: value only)
    for line in yaml_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"\'').strip()

    return metadata, body


# ---------------------------------------------------------------------------
# Skill metadata extraction
# ---------------------------------------------------------------------------

# Category detection patterns — ordered by specificity
_CATEGORY_PATTERNS = [
    ("automation", r"-automation$"),
    ("AI", r"^(?:LLM|VLM|ASR|TTS|image-generation|video-generation)"),
    ("research", r"^research-"),
    ("writing", r"^(?:write-|content-|seo-|blog-|writing-)"),
    ("document", r"^(?:docx|xlsx|pdf|pptx|ppt|charts)$"),
    ("design", r"^(?:frontend-design|canvas-design|ui-ux|visual-design)"),
    ("devops", r"^(?:mcp-builder|skill-creator|mcporter|coding-agent)"),
    ("communication", r"^(?:chatoverflow|forum-|moltbook|public)"),
    ("platform", r"^(?:fastapi|fullstack-dev)"),
    ("specialized", r"^((?!.*-automation$).)*$"),  # Catch-all
]


def _categorize_skill(name: str) -> str:
    """Assign a category to a skill based on its name."""
    for category, pattern in _CATEGORY_PATTERNS:
        if re.search(pattern, name, re.IGNORECASE):
            return category
    return "specialized"


def _extract_capabilities(description: str, body: str) -> list[str]:
    """Extract capability keywords from skill description and body."""
    text = f"{description} {body[:2000]}".lower()
    capability_keywords = [
        "security_audit", "code_refactor", "documentation_gen", "web_scraping",
        "data_transformation", "api_integration", "test_generation", "model_routing",
        "image_processing", "voice_synthesis", "text_generation", "search",
        "summarization", "translation", "sentiment_analysis", "monitoring",
        "deployment", "notification", "scheduling", "reporting", "analysis",
        "automation", "workflow", "communication", "research", "design",
        "formatting", "validation", "authentication", "migration",
    ]
    found = []
    for cap in capability_keywords:
        # Match the capability or close variants
        pattern = cap.replace("_", r"[._-]?")
        if re.search(pattern, text):
            found.append(cap)
    return found


def _calculate_quality(body: str, skill_dir: Path) -> float:
    """Calculate quality score (0-100) for a skill.

    Reuses the scoring logic from skill_registry.py:
    - Body length (longer = better documented)
    - Presence of key sections (description, examples, parameters, references, workflow)
    - Bundled resources (references/, scripts/, assets/)
    """
    score = 0.0

    if len(body) > 500:
        score += 20
    if len(body) > 2000:
        score += 10

    if re.search(r'(description|purpose|goal)', body, re.I):
        score += 10
    if re.search(r'(example|usage|```)', body, re.I):
        score += 15
    if re.search(r'(parameter|input|schema)', body, re.I):
        score += 15
    if re.search(r'(reference|api|endpoint)', body, re.I):
        score += 10
    if re.search(r'(step|workflow|process)', body, re.I):
        score += 10

    # Check bundled resources
    if (skill_dir / "references").exists():
        score += 10
    if (skill_dir / "scripts").exists():
        score += 10

    return min(score, 100)


def _assess_skill_health(metadata: dict, quality: float) -> dict:
    """Assess the health of a skill and identify issues.

    Returns dict with: healthy (bool), issues (list of strings), quality (float).
    """
    issues = []

    if quality < 30:
        issues.append(f"Low quality score ({quality:.0f}/100) — missing key sections")
    if not metadata.get("description"):
        issues.append("Missing description in front-matter")
    if len(metadata.get("description", "")) < 20:
        issues.append("Description too short (<20 chars)")
    if not metadata.get("capabilities"):
        issues.append("No detectable capabilities")
    if not metadata.get("tool_set"):
        issues.append("No tool set detected")
    if not metadata.get("trigger_phrases"):
        issues.append("No trigger phrases found — hard to discover")

    return {
        "healthy": len(issues) == 0,
        "issues": issues,
        "quality": quality,
    }


def _extract_tool_sets(body: str) -> list[str]:
    """Extract tool/command references from the skill body."""
    tools = set()
    # Common tool patterns in SKILL.md files
    patterns = [
        r"`(read_file|write_file|grep|git_diff|search|summarize|compare)`",
        r"`(browser|snapshot|fill|click|navigate)`",
        r"`(api_call|parse_json|transform|http_request)`",
        r"`(run_command|execute|subprocess|shell)`",
        r"`(test_run|pytest|vitest|jest)`",
        r"tool[:\s]+(\w+)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, body[:5000]):
            tools.add(match.group(1))
    return sorted(tools)


def extract_skill_metadata(skill_md_path: Path) -> dict | None:
    """Extract structured metadata from a SKILL.md file.

    Returns dict with: name, description, category, path, capabilities,
    tool_set, body_hash, license, version, requires, or None on error.
    """
    # Read with encoding fallback
    text = None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            text = skill_md_path.read_text(encoding=encoding)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if text is None:
        return None

    metadata, body = _parse_frontmatter(text)

    name = metadata.get("name", skill_md_path.parent.name)
    if isinstance(name, dict):
        name = str(name)
    description = metadata.get("description", "")
    if isinstance(description, (list, dict)):
        description = str(description)

    # Handle nested metadata fields
    meta_nested = metadata.get("metadata", {})
    if isinstance(meta_nested, str):
        try:
            meta_nested = json.loads(meta_nested)
        except json.JSONDecodeError:
            meta_nested = {}

    version = metadata.get("version", meta_nested.get("version", ""))
    license_info = metadata.get("license", "")
    requires = metadata.get("requires", {})

    body_hash = hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest()[:16]
    category = _categorize_skill(str(name))
    capabilities = _extract_capabilities(str(description), body)
    tool_set = _extract_tool_sets(body)

    # Calculate quality score
    quality = _calculate_quality(body, skill_md_path.parent)

    # Assess health
    health = _assess_skill_health(metadata, quality)

    # Detect trigger phrases from body
    trigger_phrases = []
    for section_match in re.finditer(
        r"##\s+(?:When\s+To\s+Use|Trigger|Usage|Activation)", body, re.IGNORECASE
    ):
        start = section_match.end()
        snippet = body[start:start + 500]
        next_section = re.search(r"##\s", snippet)
        if next_section:
            snippet = snippet[:next_section.start()]
        for line in snippet.split("\n"):
            line = line.strip().lstrip("-*• ")
            if line and len(line) > 5:
                trigger_phrases.append(line[:100])

    return {
        "name": str(name),
        "description": str(description)[:500],
        "category": category,
        "path": str(skill_md_path.parent),
        "capabilities": capabilities,
        "tool_set": tool_set,
        "trigger_phrases": trigger_phrases[:10],
        "body_hash": body_hash,
        "license": str(license_info) if license_info else "",
        "version": str(version) if version else "",
        "requires": requires if isinstance(requires, dict) else {},
        "quality": quality,
        "healthy": health["healthy"],
        "health_issues": health["issues"],
    }


# ---------------------------------------------------------------------------
# Crawl and taxonomy building
# ---------------------------------------------------------------------------

def crawl_skills(skills_dir: str | Path, since: dict | None = None) -> tuple[list[dict], list[dict]]:
    """Crawl _universal_skills/ for SKILL.md files.

    Args:
        skills_dir: Path to _universal_skills/
        since: Previous taxonomy for incremental crawl (dict with skill_name -> body_hash)

    Returns:
        (skills_list, new_or_changed_skills_list)
    """
    skills_dir = Path(skills_dir)
    if not skills_dir.exists():
        return [], []

    previous_hashes = {}
    if since and "skills" in since:
        for skill in since["skills"]:
            previous_hashes[skill.get("name", "")] = skill.get("body_hash", "")

    skills = []
    new_or_changed = []

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        if skill_dir.name.startswith(".") or skill_dir.name.startswith("_"):
            continue
        # Skip __pycache__ and other non-skill directories
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        metadata = extract_skill_metadata(skill_md)
        if metadata is None:
            continue

        skills.append(metadata)

        # Check if new or changed since last crawl
        prev_hash = previous_hashes.get(metadata["name"])
        if prev_hash is None or prev_hash != metadata["body_hash"]:
            new_or_changed.append(metadata)

    return skills, new_or_changed


def categorize_skills(skills: list[dict]) -> dict[str, dict]:
    """Group skills by category, with counts and examples."""
    categories = {}
    for skill in skills:
        cat = skill.get("category", "specialized")
        if cat not in categories:
            categories[cat] = {"count": 0, "examples": []}
        categories[cat]["count"] += 1
        if len(categories[cat]["examples"]) < 5:
            categories[cat]["examples"].append(skill["name"])

    # Sort by count descending
    return dict(sorted(categories.items(), key=lambda x: x[1]["count"], reverse=True))


def find_combinations(skills: list[dict]) -> list[list[str]]:
    """Identify skill combinations that pair well together.

    Finds skills with complementary capabilities that can be combined
    into more powerful agent designs.
    """
    # Map capabilities to skills
    cap_to_skills: dict[str, list[str]] = {}
    for skill in skills:
        for cap in skill.get("capabilities", []):
            cap_to_skills.setdefault(cap, []).append(skill["name"])

    # Find capability pairs that appear in different skills but complement each other
    complementary_pairs = [
        {"web_scraping", "data_transformation"},
        {"security_audit", "api_integration"},
        {"code_refactor", "test_generation"},
        {"text_generation", "search"},
        {"summarization", "research"},
        {"automation", "notification"},
        {"monitoring", "reporting"},
        {"image_processing", "text_generation"},
    ]

    combinations = []
    for pair in complementary_pairs:
        caps = list(pair)
        skills_a = set(cap_to_skills.get(caps[0], []))
        skills_b = set(cap_to_skills.get(caps[1], []))
        if skills_a and skills_b:
            # Pick up to 2 examples from each side
            examples_a = sorted(skills_a)[:2]
            examples_b = sorted(skills_b)[:2]
            combinations.append([caps[0], caps[1]])

    return combinations[:10]


def _extract_all_tool_sets(skills: list[dict]) -> list[list[str]]:
    """Extract distinct tool set patterns from all skills."""
    tool_sets = []
    seen = set()
    for skill in skills:
        ts = tuple(sorted(skill.get("tool_set", [])))
        if ts and ts not in seen and len(ts) >= 2:
            seen.add(ts)
            tool_sets.append(list(ts))
    return tool_sets[:20]


def _extract_all_capabilities(skills: list[dict]) -> list[str]:
    """Extract unique capabilities across all skills."""
    caps = set()
    for skill in skills:
        for cap in skill.get("capabilities", []):
            caps.add(cap)
    return sorted(caps)[:20]


def build_taxonomy(skills_dir: str | Path, output_path: str | Path,
                   since: dict | None = None) -> dict:
    """Build the complete skills taxonomy and write to JSON.

    Args:
        skills_dir: Path to _universal_skills/
        output_path: Path to write skills_taxonomy.json
        since: Previous taxonomy for incremental crawl

    Returns:
        The taxonomy dict
    """
    skills, new_or_changed = crawl_skills(skills_dir, since)
    categories = categorize_skills(skills)
    combinations = find_combinations(skills)
    tool_sets = _extract_all_tool_sets(skills)
    capabilities = _extract_all_capabilities(skills)

    taxonomy = {
        "last_crawled": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_skills": len(skills),
        "new_or_changed": len(new_or_changed),
        "categories": categories,
        "tool_sets": tool_sets,
        "capabilities": capabilities,
        "combinations": combinations,
        "design_space": {
            "prompt_styles": ["imperative", "chain_of_thought", "few_shot"],
            "tool_sets": tool_sets,
            "goals": capabilities,
            "output_formats": ["markdown", "json_structured"],
        },
        "skills": skills,
    }

    # Build skill health report
    unhealthy = [s for s in skills if not s.get("healthy", True)]
    low_quality = [s for s in skills if s.get("quality", 100) < 30]
    taxonomy["health_report"] = {
        "healthy_count": len(skills) - len(unhealthy),
        "unhealthy_count": len(unhealthy),
        "low_quality_count": len(low_quality),
        "avg_quality": round(sum(s.get("quality", 0) for s in skills) / max(len(skills), 1), 1),
        "unhealthy_skills": [{"name": s["name"], "quality": s.get("quality", 0), "issues": s.get("health_issues", [])} for s in unhealthy[:20]],
    }

    # Write health report separately
    health_path = Path(output_path).parent / "skill_health_report.json"
    health_path.parent.mkdir(parents=True, exist_ok=True)
    health_path.write_text(json.dumps(taxonomy["health_report"], indent=2), encoding="utf-8")

    # Write output
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(taxonomy, indent=2), encoding="utf-8")

    return taxonomy


# ---------------------------------------------------------------------------
# Gremlin phase integration
# ---------------------------------------------------------------------------

def _resolve_skills_dir(config: dict) -> str:
    """Resolve the skills directory from config or environment.

    Resolution order:
    1. config['gremlins']['experiment']['skills_dir']
    2. HAT_STACK_SKILLS_DIR environment variable
    3. ./skills relative to hat_stack root (symlink or copy)
    4. ../_universal_skills relative to hat_stack root
    """
    from pathlib import Path

    # Check config
    skills_dir_cfg = config.get("gremlins", {}).get("experiment", {}).get("skills_dir")
    if skills_dir_cfg:
        skills_path = Path(skills_dir_cfg)
        if not skills_path.is_absolute():
            # Relative path — resolve from hat_stack root (parent of scripts/)
            scripts_dir = Path(__file__).resolve().parent
            skills_path = (scripts_dir.parent / skills_dir_cfg).resolve()
        if skills_path.exists():
            return str(skills_path)

    # Check environment variable
    env_dir = os.environ.get("HAT_STACK_SKILLS_DIR", "")
    if env_dir and Path(env_dir).exists():
        return env_dir

    # Check ./skills symlink/directory
    scripts_dir = Path(__file__).resolve().parent
    default_path = (scripts_dir.parent / "skills").resolve()
    if default_path.exists():
        return str(default_path)

    # Fallback: sibling _universal_skills
    fallback_path = (scripts_dir.parent / "_universal_skills").resolve()
    if fallback_path.exists():
        return str(fallback_path)

    # Last resort: return the default path anyway
    return str(default_path)


def phase_catalog(config: dict, gremlins_root: Path, since: str = "24 hours ago") -> dict:
    """Cyan Hat phase: crawl skills and build taxonomy.

    This is the 6th Gremlin phase (catalog), running at 1 AM.
    """
    skills_dir = _resolve_skills_dir(config)

    # Determine output path
    experiments_dir = gremlins_root / "experiments"
    experiments_dir.mkdir(parents=True, exist_ok=True)
    output_path = experiments_dir / "skills_taxonomy.json"

    # Load previous taxonomy for incremental crawl
    previous = None
    if output_path.exists():
        try:
            previous = json.loads(output_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    taxonomy = build_taxonomy(skills_dir, output_path, since=previous)

    return {
        "phase": "catalog",
        "status": "completed",
        "hat": "cyan",
        "total_skills": taxonomy["total_skills"],
        "new_or_changed": taxonomy["new_or_changed"],
        "categories": {k: v["count"] for k, v in taxonomy["categories"].items()},
        "capabilities": len(taxonomy["capabilities"]),
        "combinations": len(taxonomy["combinations"]),
        "output": str(output_path),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Skills Crawler — build taxonomy from _universal_skills/")
    parser.add_argument("--config", default=None, help="Path to hat_configs.yml")
    parser.add_argument("--skills-dir", default=None, help="Path to _universal_skills/ directory")
    parser.add_argument("--output", default=None, help="Output path for skills_taxonomy.json")
    parser.add_argument("--full", action="store_true", help="Force full re-crawl (ignore previous taxonomy)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be crawled without writing")

    args = parser.parse_args()

    # Determine skills directory
    skills_dir = args.skills_dir
    if not skills_dir and args.config:
        try:
            import yaml
            with open(args.config, "r", encoding="utf-8") as fh:
                config = yaml.safe_load(fh)
            skills_dir = _resolve_skills_dir(config)
        except Exception:
            pass
    if not skills_dir:
        # Fallback: check relative paths from scripts directory
        scripts_dir = Path(__file__).resolve().parent
        for candidate in [
            scripts_dir.parent / "skills",
            scripts_dir.parent / "_universal_skills",
        ]:
            if candidate.exists():
                skills_dir = str(candidate)
                break
        if not skills_dir:
            skills_dir = str(scripts_dir.parent / "skills")

    # Determine output path
    output_path = args.output or os.path.join(skills_dir, "..", ".gremlins", "experiments", "skills_taxonomy.json")

    # Load previous taxonomy for incremental crawl
    previous = None
    if not args.full and Path(output_path).exists():
        try:
            previous = json.loads(Path(output_path).read_text(encoding="utf-8"))
            print(f"Previous taxonomy: {previous.get('total_skills', 0)} skills, "
                  f"crawled {previous.get('last_crawled', 'unknown')}")
        except Exception:
            pass

    if args.dry_run:
        skills, new_or_changed = crawl_skills(skills_dir, since=previous)
        categories = categorize_skills(skills)
        print(f"Would crawl: {len(skills)} skills ({len(new_or_changed)} new/changed)")
        print(f"Categories: {json.dumps({k: v['count'] for k, v in categories.items()}, indent=2)}")
        return

    taxonomy = build_taxonomy(skills_dir, output_path, since=previous)

    print(f"Crawled {taxonomy['total_skills']} skills ({taxonomy['new_or_changed']} new/changed)")
    print(f"Categories: {json.dumps({k: v['count'] for k, v in taxonomy['categories'].items()}, indent=2)}")
    print(f"Capabilities: {len(taxonomy['capabilities'])}")
    print(f"Combinations: {len(taxonomy['combinations'])}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()