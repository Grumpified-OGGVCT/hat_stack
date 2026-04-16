#!/usr/bin/env node
"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
const index_js_1 = require("@modelcontextprotocol/sdk/server/index.js");
const stdio_js_1 = require("@modelcontextprotocol/sdk/server/stdio.js");
const types_js_1 = require("@modelcontextprotocol/sdk/types.js");
const tools_js_1 = require("./tools.js");
const hats_client_js_1 = require("./hats-client.js");
const server = new index_js_1.Server({
    name: "hat-stack",
    version: "1.0.0",
}, {
    capabilities: {
        tools: {},
    },
});
// List tools handler
server.setRequestHandler(types_js_1.ListToolsRequestSchema, async () => {
    return (0, tools_js_1.getToolList)();
});
// Call tool handler
server.setRequestHandler(types_js_1.CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    try {
        switch (name) {
            case "hats_review": {
                const diff = args?.diff;
                const hats = args?.hats?.split(",").map((s) => s.trim());
                const context = args?.context;
                if (!diff) {
                    return {
                        content: [{ type: "text", text: "Error: 'diff' parameter is required" }],
                        isError: true,
                    };
                }
                const result = await (0, hats_client_js_1.runHatReview)(diff, hats, context);
                return {
                    content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
                };
            }
            case "hats_task": {
                const taskType = args?.task_type;
                const prompt = args?.prompt;
                const hats = args?.hats?.split(",").map((s) => s.trim());
                if (!taskType || !prompt) {
                    return {
                        content: [{ type: "text", text: "Error: 'task_type' and 'prompt' parameters are required" }],
                        isError: true,
                    };
                }
                const result = await (0, hats_client_js_1.runHatTask)(taskType, prompt, hats);
                return {
                    content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
                };
            }
            case "hats_list_models": {
                const result = await (0, hats_client_js_1.listModels)();
                return {
                    content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
                };
            }
            case "hats_check_status": {
                const runId = args?.run_id;
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
                const config = await (0, hats_client_js_1.getConfig)();
                return {
                    content: [{ type: "text", text: config }],
                };
            }
            case "hats_assemble_team": {
                const taskDescription = args?.task_description;
                const maxCloud = args?.max_cloud || 4;
                const maxLocal = args?.max_local || 1;
                const priority = args?.priority || "thoroughness";
                const context = args?.context;
                if (!taskDescription) {
                    return {
                        content: [{ type: "text", text: "Error: 'task_description' parameter is required" }],
                        isError: true,
                    };
                }
                const result = await (0, hats_client_js_1.assembleTeam)(taskDescription, maxCloud, maxLocal, priority, context);
                return {
                    content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
                };
            }
            case "hats_skill_recommend": {
                const taskDesc = args?.task_description;
                const maxResults = args?.max_results || 5;
                const categories = args?.categories;
                if (!taskDesc) {
                    return {
                        content: [{ type: "text", text: "Error: 'task_description' parameter is required" }],
                        isError: true,
                    };
                }
                const result = await (0, hats_client_js_1.recommendSkills)(taskDesc, maxResults, categories);
                return {
                    content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
                };
            }
            case "gremlin_kickoff": {
                const scope = args?.scope || "all";
                const result = await (0, hats_client_js_1.runGremlinKickoff)(scope);
                return {
                    content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
                };
            }
            case "gremlin_proposal": {
                const action = args?.action;
                const proposalId = args?.proposal_id;
                const reason = args?.reason;
                const statusFilter = args?.status_filter;
                if (!action) {
                    return {
                        content: [{ type: "text", text: "Error: 'action' parameter is required (list, approve, reject)" }],
                        isError: true,
                    };
                }
                const result = await (0, hats_client_js_1.handleGremlinProposal)(action, proposalId, reason, statusFilter);
                return {
                    content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
                };
            }
            case "gremlin_herald": {
                const since = args?.since;
                const result = await (0, hats_client_js_1.readGremlinHerald)(since);
                return {
                    content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
                };
            }
            case "moltbook_verify": {
                const identityToken = args?.identity_token;
                const audience = args?.audience;
                const useCache = args?.use_cache;
                if (!identityToken) {
                    return {
                        content: [{ type: "text", text: "Error: 'identity_token' parameter is required" }],
                        isError: true,
                    };
                }
                const result = await (0, hats_client_js_1.verifyMoltbookIdentityToken)(identityToken, audience, useCache);
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
    }
    catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        return {
            content: [{ type: "text", text: `Error: ${message}` }],
            isError: true,
        };
    }
});
// Start server
async function main() {
    const transport = new stdio_js_1.StdioServerTransport();
    await server.connect(transport);
    console.error("Hat Stack MCP server running on stdio");
}
main().catch((error) => {
    console.error("Fatal error:", error);
    process.exit(1);
});
//# sourceMappingURL=index.js.map