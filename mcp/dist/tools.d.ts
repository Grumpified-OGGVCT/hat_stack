/**
 * tools.ts — MCP tool definitions for Hat Stack.
 *
 * Defines the 6 tools exposed by the MCP server:
 *   hats_review, hats_task, hats_list_models, hats_check_status,
 *   hats_get_config, hats_assemble_team
 */
import { ListToolsResult, Tool } from "@modelcontextprotocol/sdk/types.js";
export declare const HAT_STACK_TOOLS: Tool[];
export declare function getToolList(): ListToolsResult;
//# sourceMappingURL=tools.d.ts.map