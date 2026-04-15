/**
 * hats-client.ts — Python runner invoker for Hat Stack MCP server.
 *
 * Spawns hats_runner.py and hats_task_runner.py as subprocesses,
 * captures their JSON output, and returns structured results.
 */

import { spawn } from "child_process";
import * as path from "path";
import * as fs from "fs";
import * as yaml from "js-yaml";

const HAT_STACK_ROOT = path.resolve(__dirname, "../../");
const SCRIPTS_DIR = path.join(HAT_STACK_ROOT, "scripts");
const HATS_RUNNER = path.join(SCRIPTS_DIR, "hats_runner.py");
const HATS_TASK_RUNNER = path.join(SCRIPTS_DIR, "hats_task_runner.py");
const CONFIG_PATH = path.join(SCRIPTS_DIR, "hat_configs.yml");

export interface HatReviewResult {
  verdict: string;
  risk_score: number;
  severity_counts: Record<string, number>;
  hats_executed: number;
  hats_failed: number;
  findings: unknown[];
  security_fast_path_triggered: boolean;
  sensitive_mode: boolean;
}

export interface HatTaskResult {
  task_type: string;
  status: string;
  primary_hat: string;
  files: Array<{ path: string; content: string; description: string }>;
  summary: string;
  notes: string[];
  stats: {
    hats_executed: number;
    total_tokens: { input: number; output: number };
    total_latency_seconds: number;
  };
}

/**
 * Run a hat review on a diff.
 */
export async function runHatReview(
  diff: string,
  hats?: string[],
  context?: string,
): Promise<HatReviewResult> {
  const args = [
    HATS_RUNNER,
    "--config", CONFIG_PATH,
    "--output", "json",
    "--diff", "-",  // Read from stdin
  ];

  if (hats && hats.length > 0) {
    args.push("--hats", hats.join(","));
  }
  if (context) {
    args.push("--context", context);
  }

  const result = await spawnPython(args, diff);
  return JSON.parse(result) as HatReviewResult;
}

/**
 * Run a hat task (generate_code, analyze, etc.).
 */
export async function runHatTask(
  taskType: string,
  prompt: string,
  hats?: string[],
): Promise<HatTaskResult> {
  const args = [
    HATS_TASK_RUNNER,
    "--config", CONFIG_PATH,
    "--task", taskType,
    "--prompt", prompt,
    "--output", "/tmp/hats-mcp-task-output",
  ];

  if (hats && hats.length > 0) {
    args.push("--hats", hats.join(","));
  }

  await spawnPython(args);

  // Read the result from the output JSON file
  const resultPath = "/tmp/hats-mcp-task-output/hats_task_result.json";
  if (fs.existsSync(resultPath)) {
    const content = fs.readFileSync(resultPath, "utf-8");
    return JSON.parse(content) as HatTaskResult;
  }

  throw new Error("Task runner did not produce output");
}

/**
 * List available models and their hat assignments from config.
 */
export async function listModels(): Promise<unknown> {
  const config = await loadConfig();
  return {
    models: config.models,
    hats: Object.entries(config.hats).map(([id, hat]: [string, any]) => ({
      id,
      name: hat.name,
      primary_model: hat.primary_model,
      fallback_model: hat.fallback_model,
      local_model: hat.local_model || null,
      local_only: hat.local_only || false,
      always_run: hat.always_run || false,
    })),
  };
}

/**
 * Get current hat_configs.yml contents.
 */
export async function getConfig(): Promise<string> {
  return fs.readFileSync(CONFIG_PATH, "utf-8");
}

/**
 * Assemble a custom team of hats for a specific task.
 */
export async function assembleTeam(
  taskDescription: string,
  maxCloud: number = 4,
  maxLocal: number = 1,
  priority: "speed" | "thoroughness" | "budget" = "thoroughness",
  context?: string,
): Promise<unknown> {
  const config = await loadConfig();
  const models = config.models;
  const hats = config.hats;

  // Detect sensitive content
  const sensitivePatterns = [
    /\.env/i, /api[_-]?key/i, /secret/i, /credential/i, /auth[_-]?token/i,
    /password/i, /\.pem/i, /private[_-]?key/i,
  ];
  const isSensitive = sensitivePatterns.some(p =>
    p.test(taskDescription) || (context && p.test(context))
  );

  // Always-on hats
  const alwaysHats = Object.entries(hats)
    .filter(([, h]: [string, any]) => h.always_run)
    .map(([id, ]: [string, any]) => id);

  // Keyword-based selection from task description
  const descLower = taskDescription.toLowerCase();
  const conditionalHats: string[] = [];
  for (const [id, hat] of Object.entries(hats)) {
    if ((hat as any).always_run) continue;
    const triggers = (hat as any).triggers || [];
    if (triggers.some((t: string) => descLower.includes(t.toLowerCase()))) {
      conditionalHats.push(id);
    }
  }

  // Assemble team
  const selectedHats = [...new Set([...alwaysHats, ...conditionalHats])];

  // Build team roster
  const team = selectedHats.map(id => {
    const hat = hats[id] as any;
    const modelInfo = models[hat.primary_model] as any;
    const useLocal = isSensitive && hat.local_model && !hat.local_only;
    const effectiveModel = (hat.local_only || useLocal)
      ? (hat.local_model || hat.primary_model)
      : hat.primary_model;

    return {
      hat_id: id,
      hat_name: hat.name,
      model: effectiveModel,
      model_type: (hat.local_only || useLocal) ? "local" : "cloud",
      context_window: modelInfo?.context_window || 128000,
      local_only: hat.local_only || false,
      switched_to_local: useLocal ? true : false,
    };
  });

  // Split into execution groups
  const cloudHats = team.filter(h => h.model_type === "cloud");
  const localHats = team.filter(h => h.model_type === "local");

  // Adjust parallelism based on priority
  let effectiveMaxCloud = maxCloud;
  if (priority === "budget") {
    effectiveMaxCloud = Math.min(maxCloud, 3);
  } else if (priority === "speed") {
    effectiveMaxCloud = Math.min(maxCloud + 1, 5);
  }

  // Estimate token budget
  const diffTokens = context ? Math.floor(context.length / 4) : 500;
  let estimatedTokens = 0;
  for (const member of team) {
    const modelInfo = models[member.model] as any;
    estimatedTokens += Math.min(diffTokens + 500, modelInfo?.context_window || 128000) + 4096;
  }

  return {
    team,
    execution_plan: {
      cloud_group: cloudHats.slice(0, effectiveMaxCloud),
      cloud_queued: cloudHats.slice(effectiveMaxCloud),
      local_queue: localHats,
      max_cloud_parallel: effectiveMaxCloud,
      max_local_parallel: 1,
    },
    sensitive_mode: isSensitive,
    estimated_tokens: estimatedTokens,
    priority,
    total_hats: team.length,
  };
}

// --- Helpers ---

function loadConfig(): Promise<any> {
  return Promise.resolve(yaml.load(fs.readFileSync(CONFIG_PATH, "utf-8")));
}

function spawnPython(args: string[], stdin?: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const proc = spawn("python", args, {
      cwd: SCRIPTS_DIR,
      env: { ...process.env },
      stdio: ["pipe", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data: Buffer) => { stdout += data.toString(); });
    proc.stderr.on("data", (data: Buffer) => { stderr += data.toString(); });

    proc.on("close", (code: number) => {
      if (code !== 0 && code !== 1) {
        // Exit code 1 means ESCALATE/QUARANTINE verdict, not a crash
        reject(new Error(`Process exited with code ${code}: ${stderr}`));
      } else {
        resolve(stdout);
      }
    });

    proc.on("error", (err: Error) => { reject(err); });

    if (stdin) {
      proc.stdin.write(stdin);
      proc.stdin.end();
    }
  });
}