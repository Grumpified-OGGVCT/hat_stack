/**
 * hats-client.ts — Python runner invoker for Hat Stack MCP server.
 *
 * Spawns hats_runner.py, hats_task_runner.py, and gremlin_runner.py as
 * subprocesses, captures their JSON output, and returns structured results.
 * Also reads/writes .gremlins/ directly for Gremlin governance operations.
 */

import { spawn } from "child_process";
import * as os from "os";
import * as path from "path";
import * as fs from "fs";
import * as yaml from "js-yaml";

const HAT_STACK_ROOT = path.resolve(__dirname, "../../");
const SCRIPTS_DIR = path.join(HAT_STACK_ROOT, "scripts");
const HATS_RUNNER = path.join(SCRIPTS_DIR, "hats_runner.py");
const HATS_TASK_RUNNER = path.join(SCRIPTS_DIR, "hats_task_runner.py");
const GREMLIN_RUNNER = path.join(SCRIPTS_DIR, "gremlin_runner.py");
const CONFIG_PATH = path.join(SCRIPTS_DIR, "hat_configs.yml");
const MOLTBOOK_ROOT = HAT_STACK_ROOT; // .gremlins/ is at repo root

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
    "--output", path.join(os.tmpdir(), "hats-mcp-task-output"),
  ];

  if (hats && hats.length > 0) {
    args.push("--hats", hats.join(","));
  }

  await spawnPython(args);

  // Read the result from the output JSON file
  const resultPath = path.join(os.tmpdir(), "hats-mcp-task-output", "hats_task_result.json");
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
    /\.env/i, /api[_\s-]?key/i, /secret/i, /credential/i, /auth[_\s-]?token/i,
    /password/i, /\.pem/i, /private[_\s-]?key/i, /hardcoded/i, /pii/i,
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

// --- Gremlin functions ---

/**
 * Run a Gremlin review cycle (spawns gremlin_runner.py).
 */
export async function runGremlinKickoff(scope: string = "all"): Promise<unknown> {
  const args = [
    GREMLIN_RUNNER,
    "--config", CONFIG_PATH,
    "--gremlins-path", MOLTBOOK_ROOT,
  ];

  if (scope === "all") {
    args.push("--all");
  } else {
    args.push("--phase", scope);
  }

  const result = await spawnPython(args);
  try {
    return JSON.parse(result);
  } catch {
    return { raw_output: result };
  }
}

/**
 * List, approve, or reject Gremlin governance proposals.
 * Reads .gremlins/proposals/ directly.
 */
export async function handleGremlinProposal(
  action: string,
  proposalId?: string,
  reason?: string,
  statusFilter?: string,
): Promise<unknown> {
  const moltbookDir = path.join(MOLTBOOK_ROOT, ".gremlins");
  const proposalsDir = path.join(moltbookDir, "proposals");

  if (action === "list") {
    if (!fs.existsSync(proposalsDir)) {
      return { proposals: [] };
    }
    const files = fs.readdirSync(proposalsDir).filter(f => f.endsWith(".json"));
    const proposals = files.map(f => {
      try {
        return JSON.parse(fs.readFileSync(path.join(proposalsDir, f), "utf-8"));
      } catch { return null; }
    }).filter(Boolean);

    if (statusFilter) {
      return { proposals: proposals.filter((p: any) => p?.status === statusFilter) };
    }
    return { proposals };
  }

  if (!proposalId) {
    throw new Error("proposal_id is required for approve/reject actions");
  }

  // Find the proposal file
  if (!fs.existsSync(proposalsDir)) {
    throw new Error(`No proposals directory found at ${proposalsDir}`);
  }

  const matchingFile = fs.readdirSync(proposalsDir)
    .find(f => f.startsWith(proposalId) && f.endsWith(".json"));

  if (!matchingFile) {
    throw new Error(`Proposal ${proposalId} not found`);
  }

  const filePath = path.join(proposalsDir, matchingFile);
  const proposal = JSON.parse(fs.readFileSync(filePath, "utf-8"));

  if (action === "approve") {
    proposal.status = "APPROVED";
    proposal.approved_by = "human";
    proposal.updated = new Date().toISOString();
  } else if (action === "reject") {
    proposal.status = "REJECTED";
    proposal.rejected_reason = reason || "Rejected by human operator";
    proposal.updated = new Date().toISOString();
  }

  fs.writeFileSync(filePath, JSON.stringify(proposal, null, 2), "utf-8");
  return proposal;
}

/**
 * Read recent Herald social output from .gremlins/social_log/.
 */
export async function readGremlinHerald(since?: string): Promise<unknown> {
  const socialDir = path.join(MOLTBOOK_ROOT, ".gremlins", "social_log");

  if (!fs.existsSync(socialDir)) {
    return { entries: [] };
  }

  const files = fs.readdirSync(socialDir)
    .filter(f => f.endsWith(".md"))
    .sort();

  const entries = files.map(f => {
    const date = f.substring(0, 10);
    if (since && date < since) return null;
    return {
      date,
      content: fs.readFileSync(path.join(socialDir, f), "utf-8"),
      path: path.join(socialDir, f),
    };
  }).filter(Boolean);

  return { entries };
}

// --- Moltbook auth function ---

/**
 * Verify a Moltbook identity token.
 * Delegates to moltbook-auth.ts module.
 */
export async function verifyMoltbookIdentityToken(
  identityToken: string,
  audience?: string,
  useCache?: boolean,
): Promise<unknown> {
  // Dynamic import to avoid loading yaml/fs at module level
  const { verifyMoltbookIdentity, formatAgentIdentity } = await import("./moltbook-auth.js");

  const result = await verifyMoltbookIdentity(identityToken, {
    audience,
    useCache: useCache !== false,
  });

  if (result.valid && result.agent) {
    return {
      valid: true,
      agent: result.agent,
      display: formatAgentIdentity(result.agent),
    };
  }

  return result;
}


// --- Helpers ---

function loadConfig(): Promise<any> {
  return Promise.resolve(yaml.load(fs.readFileSync(CONFIG_PATH, "utf-8")));
}

function resolvePythonBinary(): string {
  // Inside Docker (Linux container): python3 is standard
  // On Windows: "python" resolves to the Python launcher
  // On macOS/Linux: "python3" is the norm
  if (process.platform === "win32") {
    return "python";
  }
  return "python3";
}

function spawnPython(args: string[], stdin?: string): Promise<string> {
  const pythonBin = resolvePythonBinary();
  return new Promise((resolve, reject) => {
    const proc = spawn(pythonBin, args, {
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