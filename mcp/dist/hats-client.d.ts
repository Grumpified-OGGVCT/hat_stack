/**
 * hats-client.ts — Python runner invoker for Hat Stack MCP server.
 *
 * Spawns hats_runner.py and hats_task_runner.py as subprocesses,
 * captures their JSON output, and returns structured results.
 */
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
    files: Array<{
        path: string;
        content: string;
        description: string;
    }>;
    summary: string;
    notes: string[];
    stats: {
        hats_executed: number;
        total_tokens: {
            input: number;
            output: number;
        };
        total_latency_seconds: number;
    };
}
/**
 * Run a hat review on a diff.
 */
export declare function runHatReview(diff: string, hats?: string[], context?: string): Promise<HatReviewResult>;
/**
 * Run a hat task (generate_code, analyze, etc.).
 */
export declare function runHatTask(taskType: string, prompt: string, hats?: string[]): Promise<HatTaskResult>;
/**
 * List available models and their hat assignments from config.
 */
export declare function listModels(): Promise<unknown>;
/**
 * Get current hat_configs.yml contents.
 */
export declare function getConfig(): Promise<string>;
/**
 * Assemble a custom team of hats for a specific task.
 */
export declare function assembleTeam(taskDescription: string, maxCloud?: number, maxLocal?: number, priority?: "speed" | "thoroughness" | "budget", context?: string): Promise<unknown>;
//# sourceMappingURL=hats-client.d.ts.map