"use strict";
/**
 * hats-client.ts — Python runner invoker for Hat Stack MCP server.
 *
 * Spawns hats_runner.py and hats_task_runner.py as subprocesses,
 * captures their JSON output, and returns structured results.
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.runHatReview = runHatReview;
exports.runHatTask = runHatTask;
exports.listModels = listModels;
exports.getConfig = getConfig;
exports.assembleTeam = assembleTeam;
const child_process_1 = require("child_process");
const os = __importStar(require("os"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const yaml = __importStar(require("js-yaml"));
const HAT_STACK_ROOT = path.resolve(__dirname, "../../");
const SCRIPTS_DIR = path.join(HAT_STACK_ROOT, "scripts");
const HATS_RUNNER = path.join(SCRIPTS_DIR, "hats_runner.py");
const HATS_TASK_RUNNER = path.join(SCRIPTS_DIR, "hats_task_runner.py");
const CONFIG_PATH = path.join(SCRIPTS_DIR, "hat_configs.yml");
/**
 * Run a hat review on a diff.
 */
async function runHatReview(diff, hats, context) {
    const args = [
        HATS_RUNNER,
        "--config", CONFIG_PATH,
        "--output", "json",
        "--diff", "-", // Read from stdin
    ];
    if (hats && hats.length > 0) {
        args.push("--hats", hats.join(","));
    }
    if (context) {
        args.push("--context", context);
    }
    const result = await spawnPython(args, diff);
    return JSON.parse(result);
}
/**
 * Run a hat task (generate_code, analyze, etc.).
 */
async function runHatTask(taskType, prompt, hats) {
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
        return JSON.parse(content);
    }
    throw new Error("Task runner did not produce output");
}
/**
 * List available models and their hat assignments from config.
 */
async function listModels() {
    const config = await loadConfig();
    return {
        models: config.models,
        hats: Object.entries(config.hats).map(([id, hat]) => ({
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
async function getConfig() {
    return fs.readFileSync(CONFIG_PATH, "utf-8");
}
/**
 * Assemble a custom team of hats for a specific task.
 */
async function assembleTeam(taskDescription, maxCloud = 4, maxLocal = 1, priority = "thoroughness", context) {
    const config = await loadConfig();
    const models = config.models;
    const hats = config.hats;
    // Detect sensitive content
    const sensitivePatterns = [
        /\.env/i, /api[_\s-]?key/i, /secret/i, /credential/i, /auth[_\s-]?token/i,
        /password/i, /\.pem/i, /private[_\s-]?key/i, /hardcoded/i, /pii/i,
    ];
    const isSensitive = sensitivePatterns.some(p => p.test(taskDescription) || (context && p.test(context)));
    // Always-on hats
    const alwaysHats = Object.entries(hats)
        .filter(([, h]) => h.always_run)
        .map(([id,]) => id);
    // Keyword-based selection from task description
    const descLower = taskDescription.toLowerCase();
    const conditionalHats = [];
    for (const [id, hat] of Object.entries(hats)) {
        if (hat.always_run)
            continue;
        const triggers = hat.triggers || [];
        if (triggers.some((t) => descLower.includes(t.toLowerCase()))) {
            conditionalHats.push(id);
        }
    }
    // Assemble team
    const selectedHats = [...new Set([...alwaysHats, ...conditionalHats])];
    // Build team roster
    const team = selectedHats.map(id => {
        const hat = hats[id];
        const modelInfo = models[hat.primary_model];
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
    }
    else if (priority === "speed") {
        effectiveMaxCloud = Math.min(maxCloud + 1, 5);
    }
    // Estimate token budget
    const diffTokens = context ? Math.floor(context.length / 4) : 500;
    let estimatedTokens = 0;
    for (const member of team) {
        const modelInfo = models[member.model];
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
function loadConfig() {
    return Promise.resolve(yaml.load(fs.readFileSync(CONFIG_PATH, "utf-8")));
}
function spawnPython(args, stdin) {
    return new Promise((resolve, reject) => {
        const proc = (0, child_process_1.spawn)("python", args, {
            cwd: SCRIPTS_DIR,
            env: { ...process.env },
            stdio: ["pipe", "pipe", "pipe"],
        });
        let stdout = "";
        let stderr = "";
        proc.stdout.on("data", (data) => { stdout += data.toString(); });
        proc.stderr.on("data", (data) => { stderr += data.toString(); });
        proc.on("close", (code) => {
            if (code !== 0 && code !== 1) {
                // Exit code 1 means ESCALATE/QUARANTINE verdict, not a crash
                reject(new Error(`Process exited with code ${code}: ${stderr}`));
            }
            else {
                resolve(stdout);
            }
        });
        proc.on("error", (err) => { reject(err); });
        if (stdin) {
            proc.stdin.write(stdin);
            proc.stdin.end();
        }
    });
}
//# sourceMappingURL=hats-client.js.map