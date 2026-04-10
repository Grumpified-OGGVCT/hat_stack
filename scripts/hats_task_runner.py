#!/usr/bin/env python3
"""
🎩 Hats Task Runner — Agentic Task Execution via Hat Expertise

Goes beyond PR review: uses the Hats model pool to *do work* on projects.
Your local agent (e.g., GitHub Copilot in VS Code) dispatches tasks here,
and hat_stack executes them using the right hat expertise and model tier.

Supported task types:
  - generate_code    — Build modules, functions, classes, APIs
  - generate_docs    — Write documentation, READMEs, ADRs, specs
  - refactor         — Restructure, optimize, or modernize existing code
  - analyze          — Deep analysis with a written report (architecture, security, etc.)
  - plan             — Create implementation plans, roadmaps, task breakdowns
  - test             — Generate test suites, test cases, fixtures
  - review           — Review code/diff (delegates to hats_runner for structured review)

Usage:
  python hats_task_runner.py \\
    --task "generate_code" \\
    --prompt "Build a FastAPI authentication module with JWT tokens" \\
    --target-repo owner/repo \\
    --target-branch feature/auth \\
    --hats black,blue,green \\
    --output /tmp/hats-task-output

Environment:
  OLLAMA_API_KEY   — Ollama Cloud API key (required)
  OLLAMA_BASE_URL  — API base URL (default: https://api.ollama.ai/v1)
"""

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR / "hat_configs.yml"

# Task type → which hats are most useful + what system role to use
TASK_PROFILES = {
    "generate_code": {
        "description": "Generate code: modules, functions, classes, APIs",
        "recommended_hats": ["green", "yellow", "blue", "black", "purple", "gold"],
        "primary_hat": "green",  # Green Hat = evolution & extensibility
        "model_tier": 1,  # Use best models for code generation
        "output_type": "code",
    },
    "generate_docs": {
        "description": "Generate documentation, READMEs, ADRs, specs",
        "recommended_hats": ["blue", "green", "purple", "gold"],
        "primary_hat": "blue",  # Blue Hat = process & specification
        "model_tier": 2,
        "output_type": "markdown",
    },
    "refactor": {
        "description": "Refactor, restructure, or optimize existing code",
        "recommended_hats": ["white", "red", "indigo", "green", "black", "gold"],
        "primary_hat": "white",  # White Hat = efficiency
        "model_tier": 1,
        "output_type": "code",
    },
    "analyze": {
        "description": "Deep analysis with written report",
        "recommended_hats": ["black", "purple", "red", "gray", "brown", "gold"],
        "primary_hat": "black",  # Black Hat is default for security-focused analysis
        "model_tier": 1,
        "output_type": "markdown",
    },
    "plan": {
        "description": "Implementation plans, roadmaps, task breakdowns",
        "recommended_hats": ["green", "yellow", "cyan", "blue", "gold"],
        "primary_hat": "cyan",  # Cyan Hat = innovation & feasibility
        "model_tier": 2,
        "output_type": "markdown",
    },
    "test": {
        "description": "Generate test suites, test cases, fixtures",
        "recommended_hats": ["chartreuse", "red", "black", "blue", "gold"],
        "primary_hat": "chartreuse",  # Chartreuse Hat = testing & evaluation
        "model_tier": 2,
        "output_type": "code",
    },
}

DEFAULT_CATEGORIES = {
    "generate_code": "code",
    "generate_docs": "docs",
    "refactor": "code",
    "analyze": "analysis",
    "plan": "plans",
    "test": "tests",
}

# ---------------------------------------------------------------------------
# Task-mode system prompts — transform hats from reviewers to builders
# ---------------------------------------------------------------------------

_TASK_SYSTEM_PREFIX = """\
You are operating in TASK MODE — you are not reviewing code, you are CREATING deliverables.
Your output will be used directly in a project. Be thorough, production-quality, and complete.
"""

_OUTPUT_SCHEMAS = {
    "code": """\
Respond with a JSON object:
{
  "files": [
    {
      "path": "relative/path/to/file.ext",
      "content": "full file content here",
      "description": "what this file does"
    }
  ],
  "summary": "what was created and why",
  "notes": ["any important notes for the developer"]
}
""",
    "markdown": """\
Respond with a JSON object:
{
  "files": [
    {
      "path": "relative/path/to/file.md",
      "content": "full markdown content here",
      "description": "what this document covers"
    }
  ],
  "summary": "what was created and why",
  "notes": ["any important notes for the developer"]
}
""",
}


def load_config(config_path: str | Path) -> dict:
    """Load hat configuration from YAML file."""
    with open(config_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def slugify_path_component(value: str | None, default: str) -> str:
    """Normalize workspace path components for predictable human-readable folders."""
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip(".-")
    return text or default


def infer_project_slug(source_repo: str | None, task_type: str) -> str:
    """Choose a stable project folder name."""
    if source_repo:
        repo_name = source_repo.rsplit("/", 1)[-1]
        return slugify_path_component(repo_name, "project")
    return slugify_path_component(task_type, "adhoc")


def build_run_id(explicit_run_id: str | None = None) -> str:
    """Build a deterministic run id for workspace storage."""
    if explicit_run_id:
        return slugify_path_component(explicit_run_id, "run")

    github_run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    github_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "").strip()
    if github_run_id:
        attempt_suffix = f"-attempt-{github_attempt}" if github_attempt else ""
        return f"run-{slugify_path_component(github_run_id, 'run')}{attempt_suffix}"

    return time.strftime("run-%Y%m%d-%H%M%S", time.gmtime())


def resolve_workspace_root(workspace_root: str | None) -> Path | None:
    """Resolve and validate the optional workspace root."""
    if not workspace_root:
        return None
    return Path(workspace_root).expanduser().resolve()


def ensure_path_within_root(root: Path, candidate: Path) -> Path:
    """Ensure candidate resolves inside the declared sandbox root."""
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path escapes sandbox root: {candidate}") from exc
    return resolved


def safe_output_path(output_dir: Path, relative_path: str) -> Path:
    """Return a safe output path within the output directory."""
    rel = Path(relative_path)
    if rel.is_absolute() or not relative_path.strip():
        raise ValueError(f"Unsafe generated file path: {relative_path!r}")
    if any(part in ("..", "") for part in rel.parts):
        raise ValueError(f"Unsafe generated file path: {relative_path!r}")
    return ensure_path_within_root(output_dir.resolve(), output_dir / rel)


def prepare_workspace(
    task_type: str,
    workspace_root: str | None = None,
    category: str | None = None,
    genre: str | None = None,
    project: str | None = None,
    run_id: str | None = None,
    source_repo: str | None = None,
    explicit_output_dir: str | None = None,
) -> dict:
    """Prepare sandbox workspace metadata and return resolved output path."""
    resolved_workspace_root = resolve_workspace_root(workspace_root)
    if not resolved_workspace_root:
        output_dir = Path(explicit_output_dir or "/tmp/hats-task-output").expanduser().resolve()
        return {
            "workspace_root": None,
            "output_dir": output_dir,
            "category": None,
            "genre": None,
            "project": None,
            "run_id": None,
        }

    normalized_category = slugify_path_component(
        category, DEFAULT_CATEGORIES.get(task_type, "misc")
    )
    normalized_genre = slugify_path_component(genre, "general")
    normalized_project = slugify_path_component(
        project, infer_project_slug(source_repo, task_type)
    )
    normalized_run_id = build_run_id(run_id)

    output_dir = ensure_path_within_root(
        resolved_workspace_root,
        resolved_workspace_root / normalized_category / normalized_genre / normalized_project / normalized_run_id,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    return {
        "workspace_root": resolved_workspace_root,
        "output_dir": output_dir,
        "category": normalized_category,
        "genre": normalized_genre,
        "project": normalized_project,
        "run_id": normalized_run_id,
    }


def build_run_manifest(
    task_result: dict,
    prompt: str,
    requested_hats: list[str] | None,
    source_repo: str | None,
    source_pr: str | None,
    source_issue: str | None,
    workspace_info: dict,
) -> dict:
    """Build manifest metadata for a sandboxed task run."""
    output_dir = workspace_info["output_dir"]
    files = [
        {
            "path": entry["path"],
            "description": entry.get("description", ""),
            "absolute_path": str((output_dir / entry["path"]).resolve()),
        }
        for entry in task_result.get("files", [])
    ]

    return {
        "schema_version": 1,
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "completed",
        "task_type": task_result["task_type"],
        "prompt": prompt,
        "requested_hats": requested_hats or [],
        "primary_hat": task_result["primary_hat"],
        "summary": task_result["summary"],
        "notes": task_result.get("notes", []),
        "source": {
            "repo": source_repo or "",
            "pr": source_pr or "",
            "issue": source_issue or "",
        },
        "workspace": {
            "root": str(workspace_info["workspace_root"]) if workspace_info["workspace_root"] else "",
            "category": workspace_info["category"] or "",
            "genre": workspace_info["genre"] or "",
            "project": workspace_info["project"] or "",
            "run_id": workspace_info["run_id"] or "",
            "output_dir": str(output_dir),
        },
        "generated_files": files,
        "stats": task_result.get("stats", {}),
    }


def write_workspace_indexes(workspace_root: Path):
    """Write human-readable indexes for the sandbox workspace."""
    categories = []
    for category_dir in sorted(p for p in workspace_root.iterdir() if p.is_dir()):
        category_lines = [f"# {category_dir.name} playground index", ""]
        category_projects = []

        for genre_dir in sorted(p for p in category_dir.iterdir() if p.is_dir()):
            for project_dir in sorted(p for p in genre_dir.iterdir() if p.is_dir()):
                runs = sorted(p for p in project_dir.iterdir() if p.is_dir())
                if not runs:
                    continue
                latest = runs[-1]
                category_projects.append((genre_dir.name, project_dir.name, latest.name, len(runs)))

        if category_projects:
            category_lines.append("| Genre | Project | Latest Run | Runs |")
            category_lines.append("|-------|---------|------------|------|")
            for genre_name, project_name, latest_run, run_count in category_projects:
                category_lines.append(
                    f"| {genre_name} | {project_name} | `{latest_run}` | {run_count} |"
                )
            category_lines.append("")
        else:
            category_lines.append("_No projects yet._")
            category_lines.append("")

        (category_dir / "CATEGORY_INDEX.md").write_text(
            "\n".join(category_lines), encoding="utf-8"
        )
        categories.append((category_dir.name, len(category_projects)))

    root_lines = ["# Hats Playground Index", ""]
    if categories:
        root_lines.append("| Category | Projects |")
        root_lines.append("|----------|----------|")
        for category_name, project_count in categories:
            root_lines.append(f"| {category_name} | {project_count} |")
        root_lines.append("")
        root_lines.append(
            "Folder layout: `playground/<category>/<genre>/<project>/<run-id>/`"
        )
    else:
        root_lines.append("_No playground runs yet._")
    root_lines.append("")

    (workspace_root / "PLAYGROUND_INDEX.md").write_text(
        "\n".join(root_lines), encoding="utf-8"
    )


def call_ollama(config: dict, model: str, system_prompt: str, user_prompt: str,
                temperature: float = 0.3, max_tokens: int = 8192,
                timeout: int = 300) -> dict:
    """Call the Ollama Cloud API."""
    api_cfg = config["api"]
    base_url = os.environ.get(
        api_cfg.get("base_url_env", "OLLAMA_BASE_URL"),
        api_cfg.get("default_base_url", "https://api.ollama.ai/v1"),
    )
    api_key = os.environ.get(
        api_cfg.get("api_key_env", "OLLAMA_API_KEY"), ""
    )

    if not api_key:
        return {"error": "OLLAMA_API_KEY not set", "model": model, "content": None,
                "usage": {"input": 0, "output": 0}}

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        choice = data.get("choices", [{}])[0]
        usage = data.get("usage", {})
        return {
            "error": None, "model": model,
            "content": choice.get("message", {}).get("content", ""),
            "usage": {"input": usage.get("prompt_tokens", 0),
                      "output": usage.get("completion_tokens", 0)},
        }
    except requests.exceptions.Timeout:
        return {"error": f"Timeout after {timeout}s", "model": model,
                "content": None, "usage": {"input": 0, "output": 0}}
    except requests.exceptions.RequestException as exc:
        return {"error": str(exc), "model": model,
                "content": None, "usage": {"input": 0, "output": 0}}


def select_model_for_task(config: dict, hat_id: str, task_type: str) -> str:
    """Select the best model for a task, using task tier to pick model quality.

    Tier 1 tasks (generate_code, analyze, refactor) use Tier 1 models (e.g. glm-5.1).
    Tier 2+ tasks (generate_docs, plan, test) use the hat's assigned primary_model.
    """
    hats_cfg = config["hats"]
    hat_def = hats_cfg.get(hat_id, {})
    profile = TASK_PROFILES.get(task_type, {})
    models_cfg = config.get("models", {})

    # For Tier 1 tasks, pick the best available Tier 1 model
    if profile.get("model_tier", 2) == 1:
        # Prefer the hat's own primary if it's already Tier 1
        hat_model = hat_def.get("primary_model", "glm-5.1")
        model_info = models_cfg.get(hat_model, {})
        if model_info.get("tier") == 1:
            return hat_model
        # Otherwise find a Tier 1 model from the config
        for model_name, model_meta in models_cfg.items():
            if model_meta.get("tier") == 1:
                return model_name
        return "glm-5.1"  # ultimate fallback

    # For Tier 2+ tasks, use the hat's assigned primary model
    return hat_def.get("primary_model", "nemotron-3-super")


def build_task_prompt(config: dict, hat_id: str, task_type: str,
                      user_prompt: str, context_files: dict | None = None) -> tuple[str, str]:
    """Build the system and user prompts for a task execution.

    Returns (system_prompt, user_prompt).
    """
    hats_cfg = config["hats"]
    hat_def = hats_cfg.get(hat_id, {})
    profile = TASK_PROFILES.get(task_type, {})
    output_type = profile.get("output_type", "markdown")

    # System prompt: task mode prefix + hat persona + output schema
    system = (
        _TASK_SYSTEM_PREFIX + "\n"
        + hat_def.get("persona", "You are an expert software engineer.").strip() + "\n\n"
        + _OUTPUT_SCHEMAS.get(output_type, _OUTPUT_SCHEMAS["markdown"])
    )

    # User prompt: the actual task + any context files
    user = f"## Task\n\n{user_prompt}\n"
    if context_files:
        user += "\n## Existing Project Files (for context)\n\n"
        for filepath, content in context_files.items():
            user += f"### `{filepath}`\n```\n{content[:5000]}\n```\n\n"

    return system, user


def run_task_hat(config: dict, hat_id: str, task_type: str,
                 user_prompt: str, context_files: dict | None = None) -> dict:
    """Execute a single hat in task mode."""
    model = select_model_for_task(config, hat_id, task_type)
    hat_def = config["hats"].get(hat_id, {})
    system_prompt, full_user_prompt = build_task_prompt(
        config, hat_id, task_type, user_prompt, context_files
    )

    start = time.time()
    result = call_ollama(
        config, model, system_prompt, full_user_prompt,
        temperature=hat_def.get("temperature", 0.3),
        max_tokens=8192,  # Task mode needs more output room
        timeout=hat_def.get("timeout_seconds", 300),
    )
    elapsed = time.time() - start

    # Try fallback if primary fails
    if result["error"] and hat_def.get("fallback_model"):
        result = call_ollama(
            config, hat_def["fallback_model"], system_prompt, full_user_prompt,
            temperature=hat_def.get("temperature", 0.3),
            max_tokens=8192,
            timeout=hat_def.get("timeout_seconds", 300),
        )
        elapsed = time.time() - start

    report = {
        "hat_id": hat_id,
        "hat_name": hat_def.get("name", hat_id),
        "emoji": hat_def.get("emoji", "🎩"),
        "model_used": result["model"],
        "latency_seconds": round(elapsed, 2),
        "token_usage": result["usage"],
        "error": result["error"],
        "files": [],
        "summary": "",
        "notes": [],
    }

    if result["content"]:
        try:
            parsed = json.loads(result["content"])
            report["files"] = parsed.get("files", [])
            report["summary"] = parsed.get("summary", "")
            report["notes"] = parsed.get("notes", [])
        except json.JSONDecodeError:
            # Wrap raw output as a single markdown file
            report["files"] = [{
                "path": "output.md",
                "content": result["content"],
                "description": "Raw model output (JSON parsing failed)",
            }]
            report["summary"] = "Model returned unstructured output"

    return report


def run_task_pipeline(config: dict, task_type: str, user_prompt: str,
                      requested_hats: list[str] | None = None,
                      context_files: dict | None = None) -> dict:
    """Run the full task pipeline.

    1. Select hats based on task profile (or use requested hats)
    2. Primary hat generates the deliverable
    3. Supporting hats review/enhance the deliverable
    4. Gold Hat does final quality check
    """
    profile = TASK_PROFILES.get(task_type)
    if not profile:
        print(f"❌ Unknown task type: {task_type}", file=sys.stderr)
        print(f"   Available: {', '.join(TASK_PROFILES.keys())}", file=sys.stderr)
        sys.exit(2)

    # Select hats
    if requested_hats and len(requested_hats) > 0:
        hat_ids = requested_hats
    else:
        hat_ids = profile["recommended_hats"]

    primary_hat = hat_ids[0] if requested_hats and len(requested_hats) > 0 else profile["primary_hat"]
    supporting_hats = [h for h in hat_ids if h != primary_hat and h != "gold"]

    print(f"🎩 Task: {profile['description']}", file=sys.stderr)
    print(f"🎩 Primary hat: {primary_hat}", file=sys.stderr)
    print(f"🎩 Supporting hats: {', '.join(supporting_hats) or 'none'}", file=sys.stderr)

    # Step 1: Primary hat generates the main deliverable
    print(f"\n📝 Phase 1: Generating with {primary_hat}...", file=sys.stderr)
    primary_result = run_task_hat(config, primary_hat, task_type, user_prompt, context_files)
    print(f"  {primary_result['emoji']} {primary_result['hat_name']}: "
          f"{len(primary_result['files'])} files, {primary_result['latency_seconds']:.1f}s"
          + (f" ⚠️ {primary_result['error']}" if primary_result['error'] else ""),
          file=sys.stderr)

    # Step 2: Supporting hats review/enhance (parallel)
    supporting_results = []
    if supporting_hats and primary_result["files"]:
        print(f"\n🔍 Phase 2: Review/enhance with {len(supporting_hats)} supporting hats...",
              file=sys.stderr)

        # Build a review prompt from the primary output
        review_context = json.dumps({
            "primary_hat": primary_hat,
            "task_type": task_type,
            "generated_files": primary_result["files"],
        }, indent=2)

        review_prompt = (
            f"A {primary_hat} hat generated the following deliverable for this task:\n"
            f"Original task: {user_prompt}\n\n"
            f"Generated output:\n```json\n{review_context}\n```\n\n"
            f"Review this output through YOUR hat's expertise lens. "
            f"Suggest improvements, flag issues, or enhance the deliverable. "
            f"If you have file improvements, include them in your response."
        )

        max_workers = min(len(supporting_hats), config["execution"]["max_concurrent_hats"])
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(run_task_hat, config, hat_id, "analyze", review_prompt, context_files): hat_id
                for hat_id in supporting_hats
            }
            for future in as_completed(futures):
                hat_id = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = {
                        "hat_id": hat_id,
                        "hat_name": config["hats"].get(hat_id, {}).get("name", hat_id),
                        "emoji": config["hats"].get(hat_id, {}).get("emoji", "🎩"),
                        "model_used": "N/A",
                        "latency_seconds": 0,
                        "token_usage": {"input": 0, "output": 0},
                        "error": str(exc),
                        "files": [], "summary": "", "notes": [],
                    }
                supporting_results.append(result)
                print(f"  {result['emoji']} {result['hat_name']}: "
                      f"{len(result['notes'])} notes, {result['latency_seconds']:.1f}s"
                      + (f" ⚠️ {result['error']}" if result['error'] else ""),
                      file=sys.stderr)

    # Step 3: Gold Hat final QA (if in hat list)
    gold_result = None
    if "gold" in hat_ids:
        print(f"\n✨ Phase 3: Gold Hat final QA...", file=sys.stderr)
        gold_context = json.dumps({
            "task_type": task_type,
            "primary_output": {"hat": primary_hat, "files": primary_result["files"]},
            "supporting_reviews": [
                {"hat": r["hat_id"], "summary": r["summary"], "notes": r["notes"]}
                for r in supporting_results
            ],
        }, indent=2)

        gold_prompt = (
            f"Original task: {user_prompt}\n\n"
            f"Review the complete task output and all supporting hat feedback:\n"
            f"```json\n{gold_context}\n```\n\n"
            f"Provide final quality assessment and any last improvements."
        )
        gold_result = run_task_hat(config, "gold", "analyze", gold_prompt, context_files)
        print(f"  {gold_result['emoji']} {gold_result['hat_name']}: "
              f"{gold_result['latency_seconds']:.1f}s", file=sys.stderr)

    # Compile final output
    all_notes = primary_result.get("notes", [])
    for r in supporting_results:
        all_notes.extend(r.get("notes", []))
    if gold_result:
        all_notes.extend(gold_result.get("notes", []))

    total_tokens = {"input": 0, "output": 0}
    all_results = [primary_result] + supporting_results + ([gold_result] if gold_result else [])
    for r in all_results:
        total_tokens["input"] += r["token_usage"]["input"]
        total_tokens["output"] += r["token_usage"]["output"]

    return {
        "task_type": task_type,
        "primary_hat": primary_hat,
        "files": primary_result["files"],
        "summary": primary_result["summary"],
        "notes": all_notes,
        "supporting_reviews": [
            {"hat": r["hat_id"], "summary": r["summary"], "notes": r["notes"]}
            for r in supporting_results
        ],
        "gold_review": {
            "summary": gold_result["summary"] if gold_result else "",
            "notes": gold_result.get("notes", []) if gold_result else [],
        },
        "stats": {
            "hats_executed": len(all_results),
            "total_tokens": total_tokens,
            "total_latency_seconds": sum(r["latency_seconds"] for r in all_results),
        },
    }


def write_output_files(
    task_result: dict,
    output_dir: str | Path,
    workspace_info: dict | None = None,
    prompt: str = "",
    requested_hats: list[str] | None = None,
    source_repo: str | None = None,
    source_pr: str | None = None,
    source_issue: str | None = None,
):
    """Write generated files to the output directory."""
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    for file_entry in task_result.get("files", []):
        filepath = safe_output_path(out, file_entry["path"])
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(file_entry["content"], encoding="utf-8")
        print(f"  📄 {filepath}", file=sys.stderr)

    # Write summary
    summary_lines = [f"# 🎩 Hats Task Output\n"]
    summary_lines.append(f"**Task:** {task_result['task_type']}")
    summary_lines.append(f"**Primary Hat:** {task_result['primary_hat']}")
    summary_lines.append(f"**Summary:** {task_result['summary']}\n")

    if task_result["files"]:
        summary_lines.append("## Generated Files\n")
        for f in task_result["files"]:
            summary_lines.append(f"- `{f['path']}` — {f.get('description', '')}")

    if task_result["notes"]:
        summary_lines.append("\n## Notes\n")
        for note in task_result["notes"]:
            summary_lines.append(f"- {note}")

    if task_result.get("supporting_reviews"):
        summary_lines.append("\n## Supporting Hat Reviews\n")
        for rev in task_result["supporting_reviews"]:
            if rev["summary"]:
                summary_lines.append(f"### {rev['hat']}\n{rev['summary']}\n")

    summary_path = out / "HATS_TASK_SUMMARY.md"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"  📋 {summary_path}", file=sys.stderr)

    # Write JSON report
    json_path = out / "hats_task_result.json"
    json_path.write_text(json.dumps(task_result, indent=2), encoding="utf-8")
    print(f"  📊 {json_path}", file=sys.stderr)

    if workspace_info and workspace_info.get("workspace_root"):
        manifest = build_run_manifest(
            task_result,
            prompt=prompt,
            requested_hats=requested_hats,
            source_repo=source_repo,
            source_pr=source_pr,
            source_issue=source_issue,
            workspace_info=workspace_info,
        )
        manifest_path = out / "PLAYGROUND_MANIFEST.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"  🗂️ {manifest_path}", file=sys.stderr)
        write_workspace_indexes(workspace_info["workspace_root"])


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="🎩 Hats Task Runner — execute agentic tasks using hat expertise"
    )
    parser.add_argument(
        "--task", required=True,
        choices=list(TASK_PROFILES.keys()),
        help="Type of task to execute"
    )
    parser.add_argument(
        "--prompt", required=True,
        help="What you want done (natural language task description)"
    )
    parser.add_argument(
        "--config", default=str(DEFAULT_CONFIG),
        help="Path to hat_configs.yml"
    )
    parser.add_argument(
        "--hats", default=None,
        help="Comma-separated hat IDs to use (default: auto-select per task profile)"
    )
    parser.add_argument(
        "--context-dir", default=None,
        help="Directory of existing project files to provide as context"
    )
    parser.add_argument(
        "--output", default="/tmp/hats-task-output",
        help="Output directory for generated files"
    )
    parser.add_argument(
        "--json-file", default=None,
        help="Path to write JSON result (in addition to output dir)"
    )
    parser.add_argument(
        "--workspace-root", default=None,
        help="Optional sandbox root for structured playground storage"
    )
    parser.add_argument(
        "--category", default=None,
        help="Optional playground category (default: inferred from task type)"
    )
    parser.add_argument(
        "--genre", default=None,
        help="Optional playground genre/type bucket"
    )
    parser.add_argument(
        "--project", default=None,
        help="Optional playground project slug"
    )
    parser.add_argument(
        "--run-id", default=None,
        help="Optional run id folder name inside the playground project"
    )
    parser.add_argument(
        "--source-repo", default=None,
        help="Source repo for manifest metadata"
    )
    parser.add_argument(
        "--source-pr", default=None,
        help="Source PR number for manifest metadata"
    )
    parser.add_argument(
        "--source-issue", default=None,
        help="Source issue number for manifest metadata"
    )

    args = parser.parse_args()

    workspace_info = prepare_workspace(
        task_type=args.task,
        workspace_root=args.workspace_root,
        category=args.category,
        genre=args.genre,
        project=args.project,
        run_id=args.run_id,
        source_repo=args.source_repo,
        explicit_output_dir=args.output,
    )
    output_dir = workspace_info["output_dir"]

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write(f"output_dir={output_dir}\n")
            fh.write(
                f"workspace_root={workspace_info['workspace_root'] or ''}\n"
            )

    # Preflight
    api_key = os.environ.get("OLLAMA_API_KEY", "").strip()
    if not api_key:
        print("❌ OLLAMA_API_KEY is not set.", file=sys.stderr)
        print("   See FORK_SETUP.md for setup instructions.", file=sys.stderr)
        sys.exit(2)

    config = load_config(args.config)

    # Load context files if provided
    context_files = None
    if args.context_dir:
        context_dir = Path(args.context_dir)
        if context_dir.is_dir():
            context_files = {}
            for p in sorted(context_dir.rglob("*")):
                if p.is_file() and p.stat().st_size < 50000:  # Skip huge files
                    try:
                        context_files[str(p.relative_to(context_dir))] = p.read_text(encoding="utf-8")
                    except (UnicodeDecodeError, PermissionError):
                        pass
            print(f"📁 Loaded {len(context_files)} context files from {context_dir}",
                  file=sys.stderr)

    requested_hats = None
    if args.hats:
        requested_hats = [h.strip() for h in args.hats.split(",") if h.strip()]

    # Run the task
    result = run_task_pipeline(
        config, args.task, args.prompt,
        requested_hats=requested_hats,
        context_files=context_files,
    )

    # Write outputs
    print(f"\n📦 Writing output to {output_dir}/", file=sys.stderr)
    write_output_files(
        result,
        output_dir,
        workspace_info=workspace_info,
        prompt=args.prompt,
        requested_hats=requested_hats,
        source_repo=args.source_repo,
        source_pr=args.source_pr,
        source_issue=args.source_issue,
    )

    if args.json_file:
        with open(args.json_file, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)

    # GitHub Actions outputs
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write(f"task_type={result['task_type']}\n")
            fh.write(f"files_generated={len(result['files'])}\n")
            fh.write(f"hats_executed={result['stats']['hats_executed']}\n")

    print(f"\n✅ Task complete: {len(result['files'])} files generated, "
          f"{result['stats']['hats_executed']} hats used", file=sys.stderr)


if __name__ == "__main__":
    main()
