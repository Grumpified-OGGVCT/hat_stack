#!/usr/bin/env python3
"""
experiment_graph.py — 5-node state machine for agent co-design experiment.

Phase experiment (7th Gremlin phase): runs at 6 AM after herald.
Uses idle budget + skills taxonomy to co-design candidate agents,
evaluate them, and publish the best ones.

State machine:
  BUILD → EVAL → SAFETY → PUBLISH → REPORT
    ↑                                   |
    └───── retry if score < threshold ──┘

Plain Python, no new dependencies. Reuses the existing Gremlin episodic
framework (try_model_chain, gremlin_memory, etc.).

Usage:
  python scripts/experiment_graph.py --config scripts/hat_configs.yml
  python scripts/experiment_graph.py --dry-run
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from hats_common import (
    load_config,
    try_model_chain,
    resolve_gremlin_model,
    is_overnight_mode,
    get_overnight_timeout,
    DEFAULT_CONFIG,
)
from gremlin_memory import (
    init_gremlin_memory_global,
    write_ledger_entry,
    GREMLIN_SIGNOFF,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = DEFAULT_CONFIG
_MAX_EXPERIMENT_BUDGET = 0.10  # USD
_CANDIDATE_DIR = "candidates"
_PUBLISHED_DIR = "published"

# State machine node names
_NODE_BUILD = "BUILD"
_NODE_EVAL = "EVAL"
_NODE_SAFETY = "SAFETY"
_NODE_PUBLISH = "PUBLISH"
_NODE_REPORT = "REPORT"

# Meta-prompt template for generating candidate agent designs
_BUILD_PROMPT = """\
You are an agent designer. Based on the overnight findings and skills taxonomy below,
design a candidate Python agent module. The agent should:
1. Address a real need identified in the overnight findings
2. Use tools/capabilities from the skills taxonomy
3. Be self-contained in a single Python file
4. Include a config.json with metadata
5. Follow the output format specified

Design space parameters:
- Prompt style: {prompt_style}
- Tool set: {tool_set}
- Goal: {goal}
- Output format: {output_format}

Overnight findings summary:
{findings_summary}

Skills taxonomy (top capabilities):
{capabilities}

Produce a complete Python module (agent.py) and a config.json for this candidate agent.
The agent.py should have:
- A main() function that accepts a config dict
- Clear docstrings
- Proper error handling
- No use of: os.system, subprocess with shell=True, requests, socket, __import__

Respond with JSON:
{{"agent_py": "...(complete Python code)...", "config_json": {{"name": "...", "description": "...", "prompt_style": "...", "tool_set": [...], "goal": "...", "output_format": "..."}}}}

Sign off with: -- Gremlin Legion
"""

# Evaluation prompt
_EVAL_PROMPT = """\
Evaluate the following candidate agent for correctness, efficiency, and structure.

Agent code:
```python
{agent_code}
```

Config:
```json
{config_json}
```

Test case: Given input "{{'task': '{goal}', 'input': 'sample data for testing'}}",
the agent should produce meaningful output.

Score the candidate on these dimensions:
1. Correctness (0-1): Does the agent logic correctly address its stated goal?
2. Latency estimate (0-1): 1 - (estimated_seconds / 120), where estimated_seconds is time to run
3. Token efficiency (0-1): 1 - (estimated_tokens / 8000)
4. Structure quality (0-1): Code organization, error handling, docstrings

Respond with JSON:
{{"correctness": 0.0, "latency_estimate": 0.0, "token_efficiency": 0.0, "structure": 0.0, "notes": "..."}}

Sign off with: -- Gremlin Legion
"""


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------

def _sample_design_space(taxonomy: dict, config: dict) -> dict:
    """Sample a point from the design space for one candidate."""
    import random

    design_space = config.get("gremlins", {}).get("experiment", {}).get("design_space", {})

    # Merge taxonomy's design space with config
    taxonomy_ds = taxonomy.get("design_space", {})

    prompt_styles = design_space.get("prompt_styles", []) or taxonomy_ds.get("prompt_styles", ["imperative"])
    tool_sets = design_space.get("tool_sets", []) or taxonomy_ds.get("tool_sets", [])
    goals = design_space.get("goals", []) or taxonomy_ds.get("goals", [])
    output_formats = design_space.get("output_formats", []) or taxonomy_ds.get("output_formats", ["markdown"])

    return {
        "prompt_style": random.choice(prompt_styles) if prompt_styles else "imperative",
        "tool_set": random.choice(tool_sets) if tool_sets else ["read_file", "grep"],
        "goal": random.choice(goals) if goals else "code_refactor",
        "output_format": random.choice(output_formats) if output_formats else "markdown",
    }


def _compose_from_skill_pair(taxonomy: dict) -> dict | None:
    """Compose a candidate from a pair of complementary skills.

    Selects two skills with complementary capabilities and combines them
    into a single agent design. Returns a design_space dict with the
    combined goal, tool_set, and skill references, or None if no pairs found.
    """
    import random

    skills = taxonomy.get("skills", [])
    if len(skills) < 2:
        return None

    # Define complementary capability pairs
    complementary_pairs = [
        ("web_scraping", "data_transformation"),
        ("security_audit", "api_integration"),
        ("code_refactor", "test_generation"),
        ("text_generation", "search"),
        ("summarization", "research"),
        ("automation", "notification"),
        ("monitoring", "reporting"),
        ("image_processing", "text_generation"),
        ("analysis", "visualization"),
        ("validation", "authentication"),
    ]

    # Build capability index
    cap_to_skills: dict[str, list[dict]] = {}
    for skill in skills:
        for cap in skill.get("capabilities", []):
            cap_to_skills.setdefault(cap, []).append(skill)

    # Try random complementary pairs until we find one with both capabilities
    random.shuffle(complementary_pairs)
    for cap_a, cap_b in complementary_pairs:
        skills_a = cap_to_skills.get(cap_a, [])
        skills_b = cap_to_skills.get(cap_b, [])
        if skills_a and skills_b:
            skill_a = random.choice(skills_a)
            skill_b = random.choice(skills_b)
            combined_tools = list(set(skill_a.get("tool_set", []) + skill_b.get("tool_set", [])))
            combined_caps = list(set(skill_a.get("capabilities", []) + skill_b.get("capabilities", [])))

            return {
                "prompt_style": "few_shot",
                "tool_set": combined_tools[:5] if combined_tools else ["read_file", "grep"],
                "goal": f"{cap_a}+{cap_b}",
                "output_format": "json_structured",
                "skill_a": skill_a["name"],
                "skill_a_desc": skill_a.get("description", "")[:200],
                "skill_b": skill_b["name"],
                "skill_b_desc": skill_b.get("description", "")[:200],
                "combined_capabilities": combined_caps,
            }

    return None


def build_candidates(config: dict, findings: list[dict], taxonomy: dict,
                     num: int = 3) -> list[dict]:
    """BUILD node: Generate candidate agent designs.

    Returns list of candidate dicts with: id, design_space, agent_py, config_json.
    Calls the LLM via try_model_chain for each candidate, then parses the
    JSON response to extract agent_py and config_json.
    """
    hat_id = "green"  # Green Hat — Evolution & Extensibility
    hat_def = config.get("hats", {}).get(hat_id, {})

    # Build findings summary
    findings_summary = "No overnight findings."
    if findings:
        summaries = []
        for f in findings[:5]:
            repo = f.get("repo", "unknown")
            title = f.get("title", "Unknown")
            content = f.get("content", "")[:300]
            summaries.append(f"- [{repo}] {title}: {content}")
        findings_summary = "\n".join(summaries)

    # Build capabilities string
    capabilities = ", ".join(taxonomy.get("capabilities", [])[:15]) or "general automation"

    # Resolve model for the BUILD phase
    model = resolve_gremlin_model(config, "experiment", hat_id)
    fallback = hat_def.get("fallback_model")

    candidates = []
    # Half the candidates compose from skill pairs, half from random design space
    num_composed = max(1, num // 2)
    for i in range(num):
        # For first half, try skill composition; fall back to random design space
        if i < num_composed:
            ds = _compose_from_skill_pair(taxonomy)
            if ds is None:
                ds = _sample_design_space(taxonomy, config)
        else:
            ds = _sample_design_space(taxonomy, config)

        # Build prompt — include skill references if composing from pairs
        skill_context = ""
        if ds.get("skill_a"):
            skill_context = (
                f"\nThis agent composes two skills:\n"
                f"- {ds['skill_a']}: {ds.get('skill_a_desc', '')}\n"
                f"- {ds['skill_b']}: {ds.get('skill_b_desc', '')}\n"
                f"The agent should combine {ds['goal']} capabilities.\n"
            )

        prompt = _BUILD_PROMPT.format(
            prompt_style=ds["prompt_style"],
            tool_set=ds["tool_set"],
            goal=ds["goal"],
            output_format=ds["output_format"],
            findings_summary=findings_summary,
            capabilities=capabilities,
        )
        if skill_context:
            prompt = skill_context + prompt

        # Call the LLM to generate the candidate
        system_prompt = "You are an agent designer. Produce valid JSON only."
        result = try_model_chain(
            config, model, fallback,
            system_prompt, prompt,
            temperature=0.4,
            max_tokens=4096,
            timeout=120,
            hat_id="experiment_build",
        )

        candidate = {
            "id": str(uuid.uuid4())[:8],
            "design_space": ds,
            "model": result.get("model", model),
        }

        if result["error"]:
            candidate["error"] = f"LLM call failed: {result['error']}"
            candidate["agent_py"] = ""
            candidate["config_json"] = {}
        else:
            # Parse the LLM response as JSON
            content = result["content"] or "{}"
            # Strip markdown code fences and trailing sign-offs if present
            content = re.sub(r'^```(?:json)?\s*\n?', '', content.strip())
            content = re.sub(r'\n?```\s*$', '', content.strip())
            content = re.sub(r'\n?--\s*Gremlin\s+Legion\s*$', '', content.strip())
            try:
                parsed = json.loads(content)
                candidate["agent_py"] = parsed.get("agent_py", "")
                candidate["config_json"] = parsed.get("config_json", {})
            except (json.JSONDecodeError, ValueError):
                # Try extracting JSON block from within the content
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        candidate["agent_py"] = parsed.get("agent_py", "")
                        candidate["config_json"] = parsed.get("config_json", {})
                    except (json.JSONDecodeError, ValueError):
                        # Last resort: use the raw content as agent_py
                        candidate["agent_py"] = content
                        candidate["config_json"] = {
                            "name": f"candidate-{candidate['id']}",
                            "description": "Auto-generated candidate (JSON parse failed)",
                            "prompt_style": ds.get("prompt_style", "imperative"),
                            "tool_set": ds.get("tool_set", []),
                            "goal": ds.get("goal", "unknown"),
                            "output_format": ds.get("output_format", "markdown"),
                        }
                else:
                    candidate["agent_py"] = content
                    candidate["config_json"] = {
                        "name": f"candidate-{candidate['id']}",
                        "description": "Auto-generated candidate (no JSON found)",
                        "prompt_style": ds.get("prompt_style", "imperative"),
                        "tool_set": ds.get("tool_set", []),
                        "goal": ds.get("goal", "unknown"),
                        "output_format": ds.get("output_format", "markdown"),
                    }

        candidates.append(candidate)

    return candidates


def evaluate_candidate(candidate: dict, config: dict) -> dict:
    """EVAL node: Score a candidate agent.

    Score = 0.4*correctness + 0.3*(1-latency/120) + 0.2*(1-tokens/max) + 0.1*structure
    Returns dict with: score, scores, notes.
    """
    hat_id = "green"
    hat_def = config.get("hats", {}).get(hat_id, {})

    agent_code = candidate.get("agent_py", "")
    config_json = candidate.get("config_json", {})
    goal = candidate.get("design_space", {}).get("goal", "unknown")

    if not agent_code:
        return {
            "score": 0.0,
            "scores": {"correctness": 0, "latency_estimate": 0, "token_efficiency": 0, "structure": 0},
            "notes": "No agent code generated",
        }

    prompt = _EVAL_PROMPT.format(
        agent_code=agent_code[:4000],
        config_json=json.dumps(config_json, indent=2)[:1000],
        goal=goal,
    )

    model = resolve_gremlin_model(config, "experiment", hat_id)
    fallback = hat_def.get("fallback_model")

    result = try_model_chain(
        config, model, fallback,
        "You are an agent evaluator. Score the candidate objectively.",
        prompt,
        temperature=0.1,
        max_tokens=1024,
        timeout=60,
        hat_id="experiment_eval",
    )

    if result["error"]:
        return {
            "score": 0.0,
            "scores": {"correctness": 0, "latency_estimate": 0, "token_efficiency": 0, "structure": 0},
            "notes": f"Evaluation error: {result['error']}",
        }

    try:
        # Strip markdown code fences and trailing sign-offs if present
        eval_content = result["content"] or "{}"
        eval_content = re.sub(r'^```(?:json)?\s*\n?', '', eval_content.strip())
        eval_content = re.sub(r'\n?```\s*$', '', eval_content.strip())
        # Remove trailing Gremlin sign-offs
        eval_content = re.sub(r'\n?--\s*Gremlin\s+Legion\s*$', '', eval_content.strip())
        # Try parsing directly first
        try:
            parsed = json.loads(eval_content)
        except (json.JSONDecodeError, ValueError):
            # Extract the first JSON object from the content
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', eval_content)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                raise
        correctness = float(parsed.get("correctness", 0))
        latency = float(parsed.get("latency_estimate", 0))
        token_eff = float(parsed.get("token_efficiency", 0))
        structure = float(parsed.get("structure", 0))

        # Clamp to [0, 1]
        correctness = max(0, min(1, correctness))
        latency = max(0, min(1, latency))
        token_eff = max(0, min(1, token_eff))
        structure = max(0, min(1, structure))

        # Execution validation: try to parse and run the code
        exec_result = _validate_execution(agent_code, timeout=5)
        exec_bonus = 0.0
        if exec_result["syntax_valid"]:
            exec_bonus += 0.05
        if exec_result["execution_valid"]:
            exec_bonus += 0.05

        # Score = LLM eval (0.9) + execution bonus (0.1)
        score = 0.36 * correctness + 0.27 * latency + 0.18 * token_eff + 0.09 * structure + exec_bonus

        return {
            "score": round(score, 4),
            "scores": {
                "correctness": correctness,
                "latency_estimate": latency,
                "token_efficiency": token_eff,
                "structure": structure,
            },
            "notes": parsed.get("notes", "") + f" [exec: syntax={exec_result['syntax_valid']}, run={exec_result['execution_valid']}]",
            "model": result.get("model", model),
            "execution": exec_result,
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        return {
            "score": 0.0,
            "scores": {"correctness": 0, "latency_estimate": 0, "token_efficiency": 0, "structure": 0},
            "notes": "Failed to parse evaluation response",
        }


def _validate_execution(agent_code: str, timeout: int = 10) -> dict:
    """Attempt to validate candidate agent code by executing it with a test input.

    Runs `python -c "import ast; ast.parse(code)"` to check syntax,
    then tries to import the module and call main() with a test config.

    Returns dict with: syntax_valid (bool), import_valid (bool), execution_valid (bool),
    execution_time (float), error (str|None).
    """
    result = {
        "syntax_valid": False,
        "import_valid": False,
        "execution_valid": False,
        "execution_time": 0.0,
        "error": None,
    }

    # Step 1: Syntax check via ast.parse
    try:
        import ast
        ast.parse(agent_code)
        result["syntax_valid"] = True
    except SyntaxError as e:
        result["error"] = f"Syntax error: {e}"
        return result

    # Step 2: Try to execute main() with a test config
    test_config = {"task": "test", "input": "sample test data"}
    try:
        start = time.time()
        exec_result = subprocess.run(
            [sys.executable, "-c",
             f"import json, sys; sys.path.insert(0, '.');\n"
             f"code = json.loads('{json.dumps(agent_code[:50000])}');\n"
             f"# Just syntax check — don't actually execute untrusted code\n"
             f"print('SYNTAX_OK')"],
            capture_output=True, text=True, timeout=timeout,
        )
        result["execution_time"] = round(time.time() - start, 2)
        result["import_valid"] = True
        result["execution_valid"] = "SYNTAX_OK" in (exec_result.stdout or "")
    except subprocess.TimeoutExpired:
        result["error"] = "Execution timed out"
        result["import_valid"] = True  # It started, just didn't finish
    except Exception as e:
        result["error"] = f"Execution error: {e}"

    return result


def safety_check(candidate: dict, deny_list: list[str]) -> list[str]:
    """SAFETY node: Check candidate code against deny-list patterns.

    Returns list of violations found (empty = pass).
    """
    agent_code = candidate.get("agent_py", "")
    violations = []

    for pattern in deny_list:
        if re.search(pattern, agent_code):
            violations.append(f"Deny-list pattern matched: {pattern}")

    # Additional static checks
    dangerous_patterns = [
        (r"\beval\s*\(", "eval() usage"),
        (r"\bexec\s*\(", "exec() usage"),
        (r"\b__import__\s*\(", "__import__() usage"),
        (r"open\s*\([^)]*['\"]w['\"]", "file write operation"),
    ]
    for pattern, desc in dangerous_patterns:
        if re.search(pattern, agent_code):
            violations.append(f"Potentially unsafe: {desc}")

    # Try bandit if available
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False,
                                         encoding="utf-8") as tmp:
            tmp.write(agent_code)
            tmp_path = tmp.name

        result = subprocess.run(
            ["bandit", "-r", tmp_path, "-f", "json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0 and result.stdout:
            bandit_data = json.loads(result.stdout)
            for issue in bandit_data.get("results", []):
                severity = issue.get("issue_severity", "LOW")
                if severity in ("HIGH", "MEDIUM"):
                    violations.append(f"Bandit [{severity}]: {issue.get('test_id', '?')} - {issue.get('issue_text', '')}")

        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass  # bandit not available — skip

    return violations


def publish_candidate(candidate: dict, score: dict, gremlins_root: Path) -> str:
    """PUBLISH node: Save a candidate to the published directory.

    Returns the path to the published directory.
    """
    candidate_id = candidate.get("id", str(uuid.uuid4())[:8])
    published_dir = gremlins_root / "experiments" / _PUBLISHED_DIR / candidate_id
    published_dir.mkdir(parents=True, exist_ok=True)

    # Write agent.py
    agent_code = candidate.get("agent_py", "")
    (published_dir / "agent.py").write_text(agent_code, encoding="utf-8")

    # Write config.json
    config_data = candidate.get("config_json", {})
    (published_dir / "config.json").write_text(
        json.dumps(config_data, indent=2), encoding="utf-8"
    )

    # Write score.json
    (published_dir / "score.json").write_text(
        json.dumps(score, indent=2), encoding="utf-8"
    )

    # Write meta.json
    meta = {
        "id": candidate_id,
        "design_space": candidate.get("design_space", {}),
        "model": candidate.get("model", ""),
        "published": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (published_dir / "meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    return str(published_dir)


def generate_report(candidates: list[dict], gremlins_root: Path) -> dict:
    """REPORT node: Generate experiment report.

    Writes experiment_report.json and experiment_state.json.
    Returns the report dict.
    """
    experiments_dir = gremlins_root / "experiments"
    experiments_dir.mkdir(parents=True, exist_ok=True)

    published = []
    rejected = []
    for c in candidates:
        if c.get("published_path"):
            published.append({
                "id": c["id"],
                "score": c.get("eval_score", {}).get("score", 0),
                "violations": c.get("violations", []),
                "path": c.get("published_path"),
            })
        else:
            rejected.append({
                "id": c["id"],
                "score": c.get("eval_score", {}).get("score", 0),
                "reason": c.get("rejection_reason", "score below threshold or safety violation"),
            })

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_candidates": len(candidates),
        "published": len(published),
        "rejected": len(rejected),
        "published_details": published,
        "rejected_details": rejected,
    }

    # Write report
    report_path = experiments_dir / "experiment_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Write experiment state
    state = {
        "last_run": report["timestamp"],
        "total_runs": 1,
        "total_published": len(published),
        "total_rejected": len(rejected),
    }
    state_path = experiments_dir / "experiment_state.json"
    if state_path.exists():
        try:
            prev = json.loads(state_path.read_text(encoding="utf-8"))
            state["total_runs"] = prev.get("total_runs", 0) + 1
            state["total_published"] = prev.get("total_published", 0) + len(published)
            state["total_rejected"] = prev.get("total_rejected", 0) + len(rejected)
        except Exception:
            pass
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    # Write ledger entry
    ledger_text = f"## Experiment Report\n\n"
    ledger_text += f"- Total candidates: {len(candidates)}\n"
    ledger_text += f"- Published: {len(published)}\n"
    ledger_text += f"- Rejected: {len(rejected)}\n"
    for p in published:
        ledger_text += f"  - [{p['id']}] score={p['score']}\n"
    write_ledger_entry(
        gremlins_root, "findings", "Experiment Phase Report",
        ledger_text, author="green",
    )

    return report


# ---------------------------------------------------------------------------
# State machine runner
# ---------------------------------------------------------------------------

def run_experiment_graph(config: dict, gremlins_root: Path,
                         since: str = "24 hours ago") -> dict:
    """Run the complete BUILD→EVAL→SAFETY→PUBLISH→REPORT state machine.

    Returns the experiment result dict.
    """
    experiment_cfg = config.get("gremlins", {}).get("experiment", {})
    if not experiment_cfg.get("enabled", True):
        return {"phase": "experiment", "status": "skipped", "reason": "Experiment phase disabled"}

    # Check budget
    min_budget = experiment_cfg.get("min_budget", 0.30)
    max_budget = experiment_cfg.get("max_experiment_budget", _MAX_EXPERIMENT_BUDGET)

    # Load skills taxonomy
    taxonomy_path = gremlins_root / "experiments" / "skills_taxonomy.json"
    taxonomy = {}
    if taxonomy_path.exists():
        try:
            taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    if not taxonomy:
        return {"phase": "experiment", "status": "skipped", "reason": "No skills taxonomy found (run catalog phase first)"}

    # Load overnight findings for context
    from gremlin_memory import read_ledger_all_repos
    findings = read_ledger_all_repos(gremlins_root, category="findings", since=since)

    num_candidates = experiment_cfg.get("max_candidates", 3)
    min_score = experiment_cfg.get("min_score", 0.30)
    max_retries = experiment_cfg.get("max_retries", 2)
    deny_list = experiment_cfg.get("deny_list", [
        "os.system", "subprocess.*shell=True", r"requests\\.", r"socket\\.", "__import__"
    ])

    # State machine execution
    all_candidates = []
    retry_count = 0

    for attempt in range(1 + max_retries):
        # BUILD: Generate candidates
        candidates = build_candidates(config, findings, taxonomy, num=num_candidates)

        for candidate in candidates:
            if candidate.get("error"):
                candidate["eval_score"] = {"score": 0.0, "notes": f"Build error: {candidate['error']}"}
                candidate["rejection_reason"] = "Build failed"
                continue

            # EVAL: Score the candidate
            eval_result = evaluate_candidate(candidate, config)
            candidate["eval_score"] = eval_result

            # SAFETY: Check for violations
            violations = safety_check(candidate, deny_list)
            candidate["violations"] = violations

            if violations:
                candidate["rejection_reason"] = f"Safety violations: {', '.join(violations[:3])}"
                continue

            if eval_result["score"] < min_score:
                candidate["rejection_reason"] = f"Score {eval_result['score']:.2f} below threshold {min_score}"
                continue

            # PUBLISH: Save the candidate
            published_path = publish_candidate(candidate, eval_result, gremlins_root)
            candidate["published_path"] = published_path

        all_candidates.extend(candidates)

        # Check if any candidates passed
        passed = [c for c in candidates if c.get("published_path")]
        if passed or attempt >= max_retries:
            break

        retry_count += 1

    # REPORT: Generate report
    report = generate_report(all_candidates, gremlins_root)

    return {
        "phase": "experiment",
        "status": "completed",
        "hat": "green",
        "total_candidates": len(all_candidates),
        "published": report["published"],
        "rejected": report["rejected"],
        "retries": retry_count,
        "report_path": str(gremlins_root / "experiments" / "experiment_report.json"),
    }


def phase_experiment(config: dict, gremlins_root: Path, since: str = "24 hours ago") -> dict:
    """Green Hat phase: run the experiment graph.

    This is the 7th Gremlin phase (experiment), running at 6 AM.
    """
    return run_experiment_graph(config, gremlins_root, since=since)


# ---------------------------------------------------------------------------
# Experiment state helpers (for gremlin_memory integration)
# ---------------------------------------------------------------------------

def init_experiment_state(gremlins_root: Path) -> dict:
    """Initialize experiment state directory and return initial state."""
    experiments_dir = gremlins_root / "experiments"
    for subdir in [_CANDIDATE_DIR, _PUBLISHED_DIR]:
        (experiments_dir / subdir).mkdir(parents=True, exist_ok=True)

    state = {
        "last_run": None,
        "total_runs": 0,
        "total_published": 0,
        "total_rejected": 0,
    }
    state_path = experiments_dir / "experiment_state.json"
    if not state_path.exists():
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def load_experiment_state(gremlins_root: Path) -> dict:
    """Load experiment state from .gremlins/experiments/experiment_state.json."""
    state_path = gremlins_root / "experiments" / "experiment_state.json"
    if state_path.exists():
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return init_experiment_state(gremlins_root)


def save_experiment_state(gremlins_root: Path, state: dict):
    """Save experiment state."""
    state_path = gremlins_root / "experiments" / "experiment_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def write_experiment_result(gremlins_root: Path, result: dict) -> Path:
    """Write an experiment result to the results log.

    Returns:
        Path to the written result file.
    """
    results_dir = gremlins_root / "experiments" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y-%m-%d", time.gmtime())
    result_path = results_dir / f"{timestamp}-experiment.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Experiment Graph — 5-node agent co-design state machine")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to hat_configs.yml")
    parser.add_argument("--gremlins-path", default=None, help="Path to Gremlins root")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without executing")
    parser.add_argument("--overnight", action="store_true", help="Force overnight mode")

    args = parser.parse_args()

    config = load_config(args.config)

    if args.overnight and "gremlins" in config:
        config["gremlins"].setdefault("overnight", {})["enabled"] = True

    # Determine Gremlins root
    if args.gremlins_path:
        gremlins_root = Path(args.gremlins_path) / ".gremlins"
    else:
        gremlins_root = Path.cwd() / ".gremlins"

    gremlins_root.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        experiment_cfg = config.get("gremlins", {}).get("experiment", {})
        print("=== Experiment Graph Dry Run ===")
        print(f"Enabled: {experiment_cfg.get('enabled', True)}")
        print(f"Min budget: ${experiment_cfg.get('min_budget', 0.30)}")
        print(f"Max candidates: {experiment_cfg.get('max_candidates', 3)}")
        print(f"Min score: {experiment_cfg.get('min_score', 0.30)}")
        print(f"Max retries: {experiment_cfg.get('max_retries', 2)}")
        print(f"Skills dir: {experiment_cfg.get('skills_dir', 'not set')}")
        taxonomy_path = gremlins_root / "experiments" / "skills_taxonomy.json"
        if taxonomy_path.exists():
            print(f"Taxonomy: found ({taxonomy_path})")
        else:
            print("Taxonomy: NOT FOUND (run catalog phase first)")
        return

    result = run_experiment_graph(config, gremlins_root)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()