/**
 * moltbook-auth.ts — "Sign in with Moltbook" agent authentication.
 *
 * Verifies Moltbook identity tokens from the X-Moltbook-Identity header.
 * Calls POST https://moltbook.com/api/v1/agents/verify-identity with the
 * app's API key and the identity token.
 *
 * Flow:
 *   1. Agent obtains identity token from Moltbook
 *   2. Agent sends token in X-Moltbook-Identity header
 *   3. This module calls verify-identity with MOLTBOOK_APP_KEY
 *   4. If valid, the agent profile is returned
 */

import * as fs from "fs";
import * as path from "path";
import * as yaml from "js-yaml";

const HAT_STACK_ROOT = path.resolve(__dirname, "../../");
const CONFIG_PATH = path.join(HAT_STACK_ROOT, "scripts", "hat_configs.yml");

export interface MoltbookAgent {
  id: string;
  name: string;
  description?: string;
  karma: number;
  avatar_url?: string;
  is_claimed: boolean;
  created_at?: string;
  follower_count?: number;
  following_count?: number;
  stats?: Record<string, number>;
  owner?: {
    x_handle?: string;
    x_name?: string;
    x_avatar?: string;
    x_verified?: boolean;
    x_follower_count?: number;
  };
  human?: {
    username?: string;
    email_verified?: boolean;
  };
}

export interface MoltbookVerifyResult {
  valid: boolean;
  agent: MoltbookAgent | null;
  error: string | null;
  error_hint?: string;
}

// Cache verified identities (TTL: 5 minutes)
const identityCache = new Map<string, { expires: number; agent: MoltbookAgent }>();
const CACHE_TTL = 300_000; // ms

function loadMoltbookConfig(): Record<string, any> {
  try {
    const config = yaml.load(fs.readFileSync(CONFIG_PATH, "utf-8")) as Record<string, any>;
    return config?.moltbook || {};
  } catch {
    return {};
  }
}

/**
 * Verify a Moltbook identity token.
 */
export async function verifyMoltbookIdentity(
  identityToken: string,
  options?: { audience?: string; useCache?: boolean },
): Promise<MoltbookVerifyResult> {
  const mbConfig = loadMoltbookConfig();
  const audience = options?.audience || mbConfig.audience;
  const useCache = options?.useCache !== false;

  if (!identityToken) {
    return {
      valid: false,
      agent: null,
      error: "missing_token",
      error_hint: "No identity token provided in X-Moltbook-Identity header",
    };
  }

  if (!mbConfig.enabled) {
    return {
      valid: false,
      agent: null,
      error: "moltbook_disabled",
      error_hint: "Moltbook authentication is not enabled in hat_configs.yml",
    };
  }

  const appKeyEnv = mbConfig.app_key_env || "MOLTBOOK_APP_KEY";
  const appKey = process.env[appKeyEnv] || "";
  if (!appKey) {
    return {
      valid: false,
      agent: null,
      error: "missing_app_key",
      error_hint: `${appKeyEnv} environment variable not set`,
    };
  }

  // Check cache
  if (useCache) {
    const cached = identityCache.get(identityToken);
    if (cached && cached.expires > Date.now()) {
      return { valid: true, agent: cached.agent, error: null };
    }
  }

  // Call verify endpoint
  const verifyUrl =
    mbConfig.verify_url || "https://moltbook.com/api/v1/agents/verify-identity";

  const body: Record<string, string> = { token: identityToken };
  if (audience) {
    body.audience = audience;
  }

  try {
    const resp = await fetch(verifyUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Moltbook-App-Key": appKey,
      },
      body: JSON.stringify(body),
    });

    if (resp.status === 429) {
      const retryAfter = resp.headers.get("Retry-After") || "60";
      return {
        valid: false,
        agent: null,
        error: "rate_limit_exceeded",
        error_hint: `Rate limited. Retry after ${retryAfter}s.`,
      };
    }

    const data = (await resp.json()) as Record<string, any>;

    if (!data.valid) {
      return {
        valid: false,
        agent: null,
        error: data.error || "invalid_token",
        error_hint: data.hint || "",
      };
    }

    const agent: MoltbookAgent = {
      id: data.agent?.id || "",
      name: data.agent?.name || "",
      description: data.agent?.description,
      karma: data.agent?.karma || 0,
      avatar_url: data.agent?.avatar_url,
      is_claimed: data.agent?.is_claimed || false,
      created_at: data.agent?.created_at,
      follower_count: data.agent?.follower_count,
      following_count: data.agent?.following_count,
      stats: data.agent?.stats,
      owner: data.agent?.owner,
      human: data.agent?.human,
    };

    // Cache
    if (useCache) {
      identityCache.set(identityToken, { expires: Date.now() + CACHE_TTL, agent });
    }

    return { valid: true, agent, error: null };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      valid: false,
      agent: null,
      error: "verification_failed",
      error_hint: message,
    };
  }
}

/**
 * Extract Moltbook identity token from request headers.
 */
export function extractMoltbookIdentity(
  headers: Record<string, string | string[] | undefined>,
): string | null {
  const mbConfig = loadMoltbookConfig();
  const headerName = (mbConfig.header_name || "X-Moltbook-Identity").toLowerCase();

  for (const [key, value] of Object.entries(headers)) {
    if (key.toLowerCase() === headerName) {
      const token = Array.isArray(value) ? value[0] : value;
      return token || null;
    }
  }

  return null;
}

/**
 * Format a verified agent identity for display.
 */
export function formatAgentIdentity(agent: MoltbookAgent): string {
  const name = agent.name || "Unknown";
  const karma = agent.karma || 0;
  const ownerHandle = agent.owner?.x_handle || "unclaimed";
  const claimed = agent.is_claimed ? "claimed" : "unclaimed";
  return `${name} (karma: ${karma}, owner: @${ownerHandle}, ${claimed})`;
}