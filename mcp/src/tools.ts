/**
 * tools.ts — MCP tool definitions for Hat Stack.
 *
 * Defines the 6 tools exposed by the MCP server:
 *   hats_review, hats_task, hats_list_models, hats_check_status,
 *   hats_get_config, hats_assemble_team
 */

import {
  ListToolsResult,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";

export const HAT_STACK_TOOLS: Tool[] = [
  {
    name: "hats_review",
    description:
      "Run a multi-hat review on a diff or PR. Selects appropriate hats based on " +
      "diff content, runs them with cloud/local models respecting security rules, " +
      "and returns a structured verdict (ALLOW/ESCALATE/QUARANTINE) with findings.",
    inputSchema: {
      type: "object" as const,
      properties: {
        diff: {
          type: "string",
          description: "The code diff to review (unified diff format)",
        },
        hats: {
          type: "string",
          description:
            "Comma-separated hat IDs to run (e.g., 'black,blue,purple'). " +
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
    description:
      "Run an agentic task using hat expertise. Tasks include: generate_code, " +
      "generate_docs, refactor, analyze, plan, test, review. Each task type selects " +
      "the optimal hat team and model tier.",
    inputSchema: {
      type: "object" as const,
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
    description:
      "List available Ollama models and their hat assignments. Shows model tiers, " +
      "context windows, SWE-bench scores, and which hats use each model.",
    inputSchema: {
      type: "object" as const,
      properties: {},
    },
  },
  {
    name: "hats_check_status",
    description:
      "Check the status of a hat pipeline run. Returns run state including " +
      "completed/failed/timed-out hats, current verdict, and gate results.",
    inputSchema: {
      type: "object" as const,
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
    description:
      "Get the current hat_configs.yml contents. Shows model pool, hat-to-model " +
      "assignments, gate settings, and risk score configuration.",
    inputSchema: {
      type: "object" as const,
      properties: {},
    },
  },
  {
    name: "hats_assemble_team",
    description:
      "Assemble a custom team of hats and models for a specific task. " +
      "The calling agent describes the task scope, and this tool returns the optimal " +
      "hat+model lineup, respecting concurrency limits and security rules. " +
      "Detects sensitive content and forces dual-mode hats to local models. " +
      "Returns an ordered team roster with primary/fallback/local model per hat, " +
      "estimated token budget, and execution plan (parallel cloud group + sequential local group).",
    inputSchema: {
      type: "object" as const,
      properties: {
        task_description: {
          type: "string",
          description:
            "Description of the task scope (e.g., 'reviewing a PR that touches auth and database migrations')",
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
          description:
            "Execution priority: 'speed' (max parallelism), 'thoroughness' (balanced, default), " +
            "'budget' (minimize cloud usage, trio mode)",
          default: "thoroughness",
        },
        context: {
          type: "string",
          description:
            "Diff content, file list, or PR URL for context-based hat selection",
        },
      },
      required: ["task_description"],
    },
  },
];

export function getToolList(): ListToolsResult {
  return {
    tools: HAT_STACK_TOOLS,
  };
}