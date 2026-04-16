#!/usr/bin/env node
/**
 * index.ts — MCP server entry point for Hat Stack.
 *
 * Exposes 10 tools via stdio transport:
 *   hats_review, hats_task, hats_list_models, hats_check_status,
 *   hats_get_config, hats_assemble_team,
 *   gremlin_kickoff, gremlin_proposal, gremlin_herald,
 *   moltbook_verify
 *
 * Usage:
 *   node dist/index.js
 *
 * Register in .mcp.json:
 *   { "mcpServers": { "hat_stack": { "command": "node", "args": ["mcp/dist/index.js"], "cwd": "/path/to/hat_stack" } } }
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

import { getToolList, HAT_STACK_TOOLS } from "./tools.js";
import {
  runHatReview,
  runHatTask,
  listModels,
  getConfig,
  assembleTeam,
  recommendSkills,
  runGremlinKickoff,
  handleGremlinProposal,
  readGremlinHerald,
  verifyMoltbookIdentityToken,
} from "./hats-client.js";

const server = new Server(
  {
    name: "hat-stack",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  },
);

// List tools handler
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return getToolList();
});

// Call tool handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "hats_review": {
        const diff = args?.diff as string;
        const hats = (args?.hats as string)?.split(",").map((s: string) => s.trim());
        const context = args?.context as string;

        if (!diff) {
          return {
            content: [{ type: "text", text: "Error: 'diff' parameter is required" }],
            isError: true,
          };
        }

        const result = await runHatReview(diff, hats, context);
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "hats_task": {
        const taskType = args?.task_type as string;
        const prompt = args?.prompt as string;
        const hats = (args?.hats as string)?.split(",").map((s: string) => s.trim());

        if (!taskType || !prompt) {
          return {
            content: [{ type: "text", text: "Error: 'task_type' and 'prompt' parameters are required" }],
            isError: true,
          };
        }

        const result = await runHatTask(taskType, prompt, hats);
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "hats_list_models": {
        const result = await listModels();
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "hats_check_status": {
        const runId = args?.run_id as string;
        if (!runId) {
          return {
            content: [{ type: "text", text: "Error: 'run_id' parameter is required" }],
            isError: true,
          };
        }

        // Read the checkpoint file if it exists
        const fs = await import("fs");
        const path = await import("path");
        const checkpointDir = path.join(process.cwd(), ".hats", "checkpoints");
        const checkpointPath = path.join(checkpointDir, `${runId}.json`);

        if (fs.existsSync(checkpointPath)) {
          const state = JSON.parse(fs.readFileSync(checkpointPath, "utf-8"));
          return {
            content: [{ type: "text", text: JSON.stringify(state, null, 2) }],
          };
        }

        return {
          content: [{ type: "text", text: `No checkpoint found for run_id: ${runId}` }],
          isError: true,
        };
      }

      case "hats_get_config": {
        const config = await getConfig();
        return {
          content: [{ type: "text", text: config }],
        };
      }

      case "hats_assemble_team": {
        const taskDescription = args?.task_description as string;
        const maxCloud = (args?.max_cloud as number) || 4;
        const maxLocal = (args?.max_local as number) || 1;
        const priority = (args?.priority as "speed" | "thoroughness" | "budget") || "thoroughness";
        const context = args?.context as string;

        if (!taskDescription) {
          return {
            content: [{ type: "text", text: "Error: 'task_description' parameter is required" }],
            isError: true,
          };
        }

        const result = await assembleTeam(taskDescription, maxCloud, maxLocal, priority, context);
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "hats_skill_recommend": {
        const taskDesc = args?.task_description as string;
        const maxResults = (args?.max_results as number) || 5;
        const categories = args?.categories as string[] | undefined;

        if (!taskDesc) {
          return {
            content: [{ type: "text", text: "Error: 'task_description' parameter is required" }],
            isError: true,
          };
        }

        const result = await recommendSkills(taskDesc, maxResults, categories);
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "gremlin_kickoff": {
        const scope = (args?.scope as string) || "all";
        const result = await runGremlinKickoff(scope);
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "gremlin_proposal": {
        const action = args?.action as string;
        const proposalId = args?.proposal_id as string;
        const reason = args?.reason as string;
        const statusFilter = args?.status_filter as string;

        if (!action) {
          return {
            content: [{ type: "text", text: "Error: 'action' parameter is required (list, approve, reject)" }],
            isError: true,
          };
        }

        const result = await handleGremlinProposal(action, proposalId, reason, statusFilter);
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "gremlin_herald": {
        const since = args?.since as string;
        const result = await readGremlinHerald(since);
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "moltbook_verify": {
        const identityToken = args?.identity_token as string;
        const audience = args?.audience as string;
        const useCache = args?.use_cache as boolean;

        if (!identityToken) {
          return {
            content: [{ type: "text", text: "Error: 'identity_token' parameter is required" }],
            isError: true,
          };
        }

        const result = await verifyMoltbookIdentityToken(identityToken, audience, useCache);
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      default:
        return {
          content: [{ type: "text", text: `Unknown tool: ${name}` }],
          isError: true,
        };
    }
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text", text: `Error: ${message}` }],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Hat Stack MCP server running on stdio");
}

main().catch((error: unknown) => {
  console.error("Fatal error:", error);
  process.exit(1);
});