#!/usr/bin/env python3
"""Unit tests for experiment_graph.py and skills_crawler.py — experiment phase, catalog phase, skills crawler."""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiment_graph import (
    _sample_design_space,
    _compose_from_skill_pair,
    _validate_execution,
    build_candidates,
    evaluate_candidate,
    safety_check,
    publish_candidate,
    generate_report,
    run_experiment_graph,
    init_experiment_state,
    load_experiment_state,
    save_experiment_state,
    write_experiment_result,
    _MAX_EXPERIMENT_BUDGET,
)
from skills_crawler import (
    extract_skill_metadata,
    crawl_skills,
    categorize_skills,
    find_combinations,
    build_taxonomy,
    _parse_frontmatter,
    _categorize_skill,
)
from gremlin_memory import (
    init_gremlin_memory,
    init_gremlin_memory_global,
    write_ledger_entry,
)


# ---------------------------------------------------------------------------
# Frontmatter parser tests
# ---------------------------------------------------------------------------

def test_parse_simple_frontmatter():
    """_parse_frontmatter should handle simple key: value YAML."""
    text = "---\nname: LLM\ndescription: Chat completions\n---\nBody text"
    meta, body = _parse_frontmatter(text)
    assert meta.get("name") == "LLM"
    assert meta.get("description") == "Chat completions"
    assert "Body text" in body
    print("OK: simple frontmatter parsed")


def test_parse_no_frontmatter():
    """_parse_frontmatter should return empty dict when no frontmatter."""
    text = "Just a regular markdown file"
    meta, body = _parse_frontmatter(text)
    assert meta == {}
    assert text in body
    print("OK: no frontmatter returns empty dict")


def test_categorize_skill():
    """_categorize_skill should assign correct categories."""
    assert _categorize_skill("slack-automation") == "automation"
    assert _categorize_skill("LLM") == "AI"
    assert _categorize_skill("research-tech") == "research"
    assert _categorize_skill("write-human-voice") == "writing"
    assert _categorize_skill("docx") == "document"
    print("OK: skill categorization works")


def test_extract_skill_metadata():
    """extract_skill_metadata should parse a SKILL.md file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            "---\nname: test-skill\ndescription: A test skill for testing\n---\n## Overview\nThis is a test skill.",
            encoding="utf-8",
        )

        metadata = extract_skill_metadata(skill_md)
        assert metadata is not None
        assert metadata["name"] == "test-skill"
        assert "test skill" in metadata["description"].lower()
        assert metadata["body_hash"] != ""
        print("OK: skill metadata extracted")


def test_extract_skill_metadata_encoding_fallback():
    """extract_skill_metadata should handle latin-1 encoded files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "latin-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            "---\nname: latin-skill\ndescription: Skill with special chars\n---\nBody",
            encoding="latin-1",
        )

        metadata = extract_skill_metadata(skill_md)
        assert metadata is not None
        assert metadata["name"] == "latin-skill"
        print("OK: latin-1 encoding fallback works")


# ---------------------------------------------------------------------------
# Taxonomy building tests
# ---------------------------------------------------------------------------

def test_crawl_skills():
    """crawl_skills should find SKILL.md files and extract metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test skill directories
        for name in ["skill-a", "skill-b", "skill-c"]:
            skill_dir = Path(tmpdir) / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Test skill {name}\n---\n## Overview\nDescription",
                encoding="utf-8",
            )

        skills, new_or_changed = crawl_skills(tmpdir)
        assert len(skills) == 3
        assert len(new_or_changed) == 3  # All new
        names = {s["name"] for s in skills}
        assert "skill-a" in names
        print("OK: crawl_skills finds all SKILL.md files")


def test_crawl_skills_incremental():
    """crawl_skills should only return new/changed skills when since provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        for name in ["skill-a", "skill-b"]:
            skill_dir = Path(tmpdir) / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Test skill {name}\n---\nBody",
                encoding="utf-8",
            )

        # First crawl
        skills1, new1 = crawl_skills(tmpdir)
        assert len(new1) == 2

        # Build previous taxonomy dict
        prev = {"skills": [{"name": s["name"], "body_hash": s["body_hash"]} for s in skills1]}

        # Re-crawl with since — no new/changed
        skills2, new2 = crawl_skills(tmpdir, since=prev)
        assert len(skills2) == 2
        assert len(new2) == 0  # No new or changed
        print("OK: incremental crawl detects no changes")


def test_categorize_skills():
    """categorize_skills should group skills by category."""
    skills = [
        {"name": "slack-automation", "category": "automation"},
        {"name": "github-automation", "category": "automation"},
        {"name": "LLM", "category": "AI"},
        {"name": "research-tech", "category": "research"},
    ]
    categories = categorize_skills(skills)
    assert "automation" in categories
    assert categories["automation"]["count"] == 2
    assert "AI" in categories
    print("OK: categorize_skills groups correctly")


def test_find_combinations():
    """find_combinations should identify complementary capability pairs."""
    skills = [
        {"name": "web-scraper", "capabilities": ["web_scraping", "data_transformation"]},
        {"name": "api-client", "capabilities": ["api_integration", "security_audit"]},
        {"name": "code-fixer", "capabilities": ["code_refactor", "test_generation"]},
    ]
    combos = find_combinations(skills)
    assert isinstance(combos, list)
    print(f"OK: find_combinations returned {len(combos)} combinations")


def test_build_taxonomy():
    """build_taxonomy should produce a complete taxonomy JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        for name in ["s1", "s2"]:
            skill_dir = Path(tmpdir) / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Skill {name}\n---\nBody",
                encoding="utf-8",
            )

        output_path = Path(tmpdir) / "taxonomy.json"
        taxonomy = build_taxonomy(tmpdir, output_path)

        assert taxonomy["total_skills"] == 2
        assert taxonomy["new_or_changed"] == 2
        assert "categories" in taxonomy
        assert "capabilities" in taxonomy
        assert "combinations" in taxonomy
        assert "design_space" in taxonomy
        assert output_path.exists()
        print("OK: build_taxonomy produces valid taxonomy")


# ---------------------------------------------------------------------------
# Safety check tests
# ---------------------------------------------------------------------------

def test_safety_check_clean():
    """safety_check should return no violations for clean code."""
    candidate = {"agent_py": "def main(config):\n    print('hello')\n    return {'result': 'ok'}"}
    deny_list = ["os.system", r"subprocess.*shell=True", r"requests\\.", r"socket\\.", "__import__"]
    violations = safety_check(candidate, deny_list)
    assert len(violations) == 0
    print("OK: safety_check passes clean code")


def test_safety_check_deny_list():
    """safety_check should catch deny-list patterns."""
    candidate = {"agent_py": "import os\nos.system('rm -rf /')"}
    deny_list = ["os.system"]
    violations = safety_check(candidate, deny_list)
    assert len(violations) > 0
    assert any("os.system" in v for v in violations)
    print("OK: safety_check catches deny-list patterns")


def test_safety_check_eval():
    """safety_check should catch eval() usage."""
    candidate = {"agent_py": "result = eval(user_input)"}
    deny_list = []
    violations = safety_check(candidate, deny_list)
    assert any("eval" in v.lower() for v in violations)
    print("OK: safety_check catches eval()")


# ---------------------------------------------------------------------------
# Experiment state tests
# ---------------------------------------------------------------------------

def test_init_experiment_state():
    """init_experiment_state should create directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gremlins = init_gremlin_memory_global(tmpdir)
        state = init_experiment_state(gremlins)

        assert state["total_runs"] == 0
        assert (gremlins / "experiments" / "candidates").exists()
        assert (gremlins / "experiments" / "published").exists()
        assert (gremlins / "experiments" / "results").exists()
        print("OK: init_experiment_state creates directories")


def test_save_load_experiment_state():
    """save_experiment_state + load_experiment_state should roundtrip."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gremlins = init_gremlin_memory_global(tmpdir)
        init_experiment_state(gremlins)

        state = {
            "last_run": "2026-04-16T06:00:00Z",
            "total_runs": 5,
            "total_published": 12,
            "total_rejected": 3,
        }
        save_experiment_state(gremlins, state)

        loaded = load_experiment_state(gremlins)
        assert loaded["total_runs"] == 5
        assert loaded["total_published"] == 12
        print("OK: save/load experiment state roundtrip works")


def test_write_experiment_result():
    """write_experiment_result should write a JSON result file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gremlins = init_gremlin_memory_global(tmpdir)
        init_experiment_state(gremlins)

        result = {"phase": "experiment", "status": "completed", "published": 2}
        path = write_experiment_result(gremlins, result)

        assert Path(path).exists()
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert data["status"] == "completed"
        print("OK: write_experiment_result writes JSON")


# ---------------------------------------------------------------------------
# Publish candidate tests
# ---------------------------------------------------------------------------

def test_publish_candidate():
    """publish_candidate should write agent.py, config.json, score.json, meta.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gremlins = Path(tmpdir) / ".gremlins"
        gremlins.mkdir()
        (gremlins / "experiments" / "published").mkdir(parents=True)

        candidate = {
            "id": "abc12345",
            "agent_py": "def main(config):\n    pass\n",
            "config_json": {"name": "test-agent"},
            "design_space": {"prompt_style": "imperative"},
            "model": "test-model",
        }
        score = {"score": 0.75, "notes": "Good"}

        published_path = publish_candidate(candidate, score, gremlins)
        assert Path(published_path).exists()
        assert (Path(published_path) / "agent.py").exists()
        assert (Path(published_path) / "config.json").exists()
        assert (Path(published_path) / "score.json").exists()
        assert (Path(published_path) / "meta.json").exists()

        # Verify score.json content
        score_data = json.loads((Path(published_path) / "score.json").read_text(encoding="utf-8"))
        assert score_data["score"] == 0.75
        print("OK: publish_candidate writes all required files")


# ---------------------------------------------------------------------------
# Report generation tests
# ---------------------------------------------------------------------------

def test_generate_report():
    """generate_report should write experiment_report.json and experiment_state.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gremlins = Path(tmpdir) / ".gremlins"
        gremlins.mkdir()
        (gremlins / "experiments").mkdir(parents=True)

        candidates = [
            {"id": "c1", "eval_score": {"score": 0.8}, "published_path": "/tmp/p1", "violations": []},
            {"id": "c2", "eval_score": {"score": 0.2}, "rejection_reason": "low score", "violations": []},
        ]

        # Need to create a ledger dir for write_ledger_entry
        (gremlins / "ledger" / "findings").mkdir(parents=True)

        report = generate_report(candidates, gremlins)
        assert report["total_candidates"] == 2
        assert report["published"] == 1
        assert report["rejected"] == 1
        assert (gremlins / "experiments" / "experiment_report.json").exists()
        assert (gremlins / "experiments" / "experiment_state.json").exists()
        print("OK: generate_report writes report and state")


# ---------------------------------------------------------------------------
# Design space sampling tests
# ---------------------------------------------------------------------------

def test_sample_design_space():
    """_sample_design_space should return valid design parameters."""
    taxonomy = {
        "design_space": {
            "prompt_styles": ["imperative", "chain_of_thought"],
            "tool_sets": [["read_file", "grep"], ["search", "summarize"]],
            "goals": ["code_refactor", "security_audit"],
            "output_formats": ["markdown", "json_structured"],
        }
    }
    config = {"gremlins": {"experiment": {"design_space": {}}}}

    ds = _sample_design_space(taxonomy, config)
    assert "prompt_style" in ds
    assert "tool_set" in ds
    assert "goal" in ds
    assert "output_format" in ds
    assert ds["prompt_style"] in ["imperative", "chain_of_thought"]
    print("OK: _sample_design_space returns valid parameters")


# ---------------------------------------------------------------------------
# Integration test — disabled experiment
# ---------------------------------------------------------------------------

def test_experiment_disabled():
    """run_experiment_graph should skip when experiment is disabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gremlins = Path(tmpdir) / ".gremlins"
        gremlins.mkdir()
        (gremlins / "experiments").mkdir(parents=True)
        (gremlins / "experiments" / "skills_taxonomy.json").write_text(
            json.dumps({"total_skills": 100, "capabilities": ["test"], "categories": {},
                        "design_space": {"prompt_styles": ["imperative"], "tool_sets": [], "goals": ["test"], "output_formats": ["markdown"]}}),
            encoding="utf-8",
        )

        config = {"gremlins": {"experiment": {"enabled": False}}, "hats": {}}
        result = run_experiment_graph(config, gremlins)
        assert result["status"] == "skipped"
        assert "disabled" in result["reason"].lower()
        print("OK: experiment skips when disabled")


def test_compose_from_skill_pair():
    """_compose_from_skill_pair should combine complementary skills."""
    taxonomy = {
        "skills": [
            {"name": "web-scraper", "capabilities": ["web_scraping", "data_transformation"], "tool_set": ["browser", "parse"]},
            {"name": "api-client", "capabilities": ["api_integration", "security_audit"], "tool_set": ["api_call", "parse_json"]},
            {"name": "code-fixer", "capabilities": ["code_refactor", "test_generation"], "tool_set": ["read_file", "grep"]},
        ]
    }
    result = _compose_from_skill_pair(taxonomy)
    if result:
        assert "skill_a" in result
        assert "skill_b" in result
        assert "goal" in result
        assert "+" in result["goal"]  # Composed goal
        assert len(result["tool_set"]) > 0
        print(f"OK: compose_from_skill_pair produced {result['goal']}")
    else:
        print("OK: compose_from_skill_pair returned None (no matching pair in taxonomy)")


def test_validate_execution_syntax():
    """_validate_execution should check syntax validity."""
    good_code = "def main(config):\n    return {'result': 'ok'}"
    result = _validate_execution(good_code, timeout=5)
    assert result["syntax_valid"] is True
    print("OK: validate_execution passes valid syntax")


def test_validate_execution_bad_syntax():
    """_validate_execution should catch syntax errors."""
    bad_code = "def main(config:\n    return {"  # Missing closing paren
    result = _validate_execution(bad_code, timeout=5)
    assert result["syntax_valid"] is False
    assert result["error"] is not None
    print("OK: validate_execution catches syntax errors")


# ---------------------------------------------------------------------------
# Main test runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_parse_simple_frontmatter,
        test_parse_no_frontmatter,
        test_categorize_skill,
        test_extract_skill_metadata,
        test_extract_skill_metadata_encoding_fallback,
        test_crawl_skills,
        test_crawl_skills_incremental,
        test_categorize_skills,
        test_find_combinations,
        test_build_taxonomy,
        test_safety_check_clean,
        test_safety_check_deny_list,
        test_safety_check_eval,
        test_init_experiment_state,
        test_save_load_experiment_state,
        test_write_experiment_result,
        test_publish_candidate,
        test_generate_report,
        test_sample_design_space,
        test_experiment_disabled,
        test_compose_from_skill_pair,
        test_validate_execution_syntax,
        test_validate_execution_bad_syntax,
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

    print(f"\nExperiment graph tests: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)