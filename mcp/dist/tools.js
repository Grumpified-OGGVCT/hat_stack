"use strict";
/**
 * tools.ts — MCP tool definitions for Hat Stack.
 *
 * Defines the 10 tools exposed by the MCP server:
 *   hats_review, hats_task, hats_list_models, hats_check_status,
 *   hats_get_config, hats_assemble_team,
 *   gremlin_kickoff, gremlin_proposal, gremlin_herald,
 *   moltbook_verify
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.HAT_STACK_TOOLS = void 0;
exports.getToolList = getToolList;
exports.HAT_STACK_TOOLS = [
    {
        name: "hats_review",
        description: "Run a multi-hat review on a diff or PR. Selects appropriate hats based on " +
            "diff content, runs them with cloud/local models respecting security rules, " +
            "and returns a structured verdict (ALLOW/ESCALATE/QUARANTINE) with findings.",
        inputSchema: {
            type: "object",
            properties: {
                diff: {
                    type: "string",
                    description: "The code diff to review (unified diff format)",
                },
                hats: {
                    type: "string",
                    description: "Comma-separated hat IDs to run (e.g., 'black,blue,purple'). " +
                        "Default: auto-select based on diff triggers.",
                },
                context: {
                    type: "string",
                    description: "Additional context (e.g., PR description, related issues)",
                },
            },
            required: ["diff"],
        },
    },
    {
        name: "hats_task",
        description: "Run an agentic task using hat expertise. Tasks include: generate_code, " +
            "generate_docs, refactor, analyze, plan, test, review. Each task type selects " +
            "the optimal hat team and model tier.",
        inputSchema: {
            type: "object",
            properties: {
                task_type: {
                    type: "string",
                    enum: [
                        "generate_code",
                        "generate_docs",
                        "refactor",
                        "analyze",
                        "plan",
                        "test",
                        "review",
                    ],
                    description: "Type of task to execute",
                },
                prompt: {
                    type: "string",
                    description: "Natural language description of what you want done",
                },
                hats: {
                    type: "string",
                    description: "Comma-separated hat IDs to use (overrides default task profile)",
                },
            },
            required: ["task_type", "prompt"],
        },
    },
    {
        name: "hats_list_models",
        description: "List available Ollama models and their hat assignments. Shows model tiers, " +
            "context windows, SWE-bench scores, and which hats use each model.",
        inputSchema: {
            type: "object",
            properties: {},
        },
    },
    {
        name: "hats_check_status",
        description: "Check the status of a hat pipeline run. Returns run state including " +
            "completed/failed/timed-out hats, current verdict, and gate results.",
        inputSchema: {
            type: "object",
            properties: {
                run_id: {
                    type: "string",
                    description: "The run ID to check",
                },
            },
            required: ["run_id"],
        },
    },
    {
        name: "hats_get_config",
        description: "Get the current hat_configs.yml contents. Shows model pool, hat-to-model " +
            "assignments, gate settings, and risk score configuration.",
        inputSchema: {
            type: "object",
            properties: {},
        },
    },
    {
        name: "hats_assemble_team",
        description: "Assemble a custom team of hats and models for a specific task. " +
            "The calling agent describes the task scope, and this tool returns the optimal " +
            "hat+model lineup, respecting concurrency limits and security rules. " +
            "Detects sensitive content and forces dual-mode hats to local models. " +
            "Returns an ordered team roster with primary/fallback/local model per hat, " +
            "estimated token budget, and execution plan (parallel cloud group + sequential local group).",
        inputSchema: {
            type: "object",
            properties: {
                task_description: {
                    type: "string",
                    description: "Description of the task scope (e.g., 'reviewing a PR that touches auth and database migrations')",
                },
                max_cloud: {
                    type: "number",
                    description: "Maximum cloud models to run in parallel (default: 4)",
                    default: 4,
                },
                max_local: {
                    type: "number",
                    description: "Maximum local models to run at a time (default: 1)",
                    default: 1,
                },
                priority: {
                    type: "string",
                    enum: ["speed", "thoroughness", "budget"],
                    description: "Execution priority: 'speed' (max parallelism), 'thoroughness' (balanced, default), " +
                        "'budget' (minimize cloud usage, trio mode)",
                    default: "thoroughness",
                },
                context: {
                    type: "string",
                    description: "Diff content, file list, or PR URL for context-based hat selection",
                },
            },
            required: ["task_description"],
        },
    },
    // --- Gremlin tools ---
    // --- Skills taxonomy tool ---
    {
        name: "hats_skill_recommend",
        description: "Recommend relevant skills from the _universal_skills/ taxonomy based on a task " +
            "description. Uses semantic matching on capabilities, categories, and trigger phrases " +
            "to find the best skill matches. Returns skill names, descriptions, categories, and " +
            "capability overlap scores.",
        inputSchema: {
            type: "object",
            properties: {
                task_description: {
                    type: "string",
                    description: "Description of the task or problem (e.g., 'building a Slack bot that posts notifications')",
                },
                max_results: {
                    type: "number",
                    description: "Maximum number of skill recommendations (default: 5)",
                    default: 5,
                },
                categories: {
                    type: "array",
                    items: { type: "string" },
                    description: "Filter to specific categories (automation, AI, research, etc.)",
                },
            },
            required: ["task_description"],
        },
    },
    {
        name: "gremlin_kickoff",
        description: "Start a Gremlin review cycle. The Gremlin Legion runs an overnight-style " +
            "autonomous review: Scout scans changes, Strategist creates proposals, " +
            "Analyst deep-dives, Herald writes a digest. All models are local (no cloud needed). " +
            "Use 'scope' to run a single phase or all phases.",
        inputSchema: {
            type: "object",
            properties: {
                scope: {
                    type: "string",
                    enum: ["all", "review", "propose", "analyze", "herald"],
                    description: "Which phase to run: 'all' (default) runs all 4 phases sequentially, " +
                        "or pick a single phase.",
                    default: "all",
                },
            },
        },
    },
    {
        name: "gremlin_proposal",
        description: "List, approve, or reject Gremlin governance proposals. Gremlins create " +
            "PENDING_HUMAN proposals for significant findings — these require human " +
            "approval before the Analyst will act on them. Proposals auto-expire after 48h.",
        inputSchema: {
            type: "object",
            properties: {
                action: {
                    type: "string",
                    enum: ["list", "approve", "reject"],
                    description: "Action: 'list' shows proposals, 'approve' approves one, 'reject' rejects one",
                },
                proposal_id: {
                    type: "string",
                    description: "Proposal ID (required for approve/reject, e.g., '001')",
                },
                reason: {
                    type: "string",
                    description: "Reason for rejection (optional, used with action='reject')",
                },
                status_filter: {
                    type: "string",
                    enum: ["PENDING_HUMAN", "APPROVED", "REJECTED", "EXPIRED"],
                    description: "Filter proposals by status (used with action='list')",
                },
            },
            required: ["action"],
        },
    },
    {
        name: "gremlin_herald",
        description: "Read recent Herald social output. The Herald Gremlin composes human-readable " +
            "daily digests summarizing the overnight Gremlin activity, including findings, " +
            "pending proposals, and action items. Signed off with 👾 Gremlin Legion.",
        inputSchema: {
            type: "object",
            properties: {
                since: {
                    type: "string",
                    description: "ISO date string — only return entries after this date (e.g., '2026-04-15')",
                },
            },
        },
    },
    // --- Moltbook auth tool ---
    {
        name: "moltbook_verify",
        description: "Verify a Moltbook identity token ('Sign in with Moltbook'). " +
            "Call POST https://moltbook.com/api/v1/agents/verify-identity with the app's " +
            "MOLTBOOK_APP_KEY and the agent's identity token. Returns the verified agent " +
            "profile (name, karma, owner, claim status) or an error if the token is " +
            "invalid/expired. Audience restriction prevents token forwarding attacks.",
        inputSchema: {
            type: "object",
            properties: {
                identity_token: {
                    type: "string",
                    description: "The Moltbook identity token to verify (from X-Moltbook-Identity header)",
                },
                audience: {
                    type: "string",
                    description: "Audience restriction (default: from hat_configs.yml, e.g. 'hat-stack')",
                },
                use_cache: {
                    type: "boolean",
                    description: "Cache verified identities for 5 minutes (default: true)",
                    default: true,
                },
            },
            required: ["identity_token"],
        },
    },
];
function getToolList() {
    return {
        tools: exports.HAT_STACK_TOOLS,
    };
}
//# sourceMappingURL=tools.js.map