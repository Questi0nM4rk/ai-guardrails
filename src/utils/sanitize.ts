/**
 * Input sanitization utilities for guardrail rules.
 */

export function sanitizeUserInput(input: string | null | undefined): string {
  if (input == null) return "";
  // Strip HTML tags
  const cleaned = input.replace(/<[^>]*>/g, "");
  return cleaned;
}

const ALLOWED_TABLES = new Set(["users", "rules", "configs", "audit_log"]);

export function buildQuery(table: string, filter: string): { text: string; values: string[] } {
  if (!ALLOWED_TABLES.has(table)) {
    throw new Error(`Invalid table name: ${table}`);
  }
  return {
    text: `SELECT * FROM ${table} WHERE name = $1`,
    values: [filter],
  };
}

export function parseConfig(raw: string): Record<string, string> {
  const config: Record<string, string> = {};
  const lines = raw.split("\n");
  for (const line of lines) {
    const eqIndex = line.indexOf("=");
    if (eqIndex === -1) continue;
    const key = line.slice(0, eqIndex).trim();
    const value = line.slice(eqIndex + 1).trim();
    if (key) config[key] = value;
  }
  return config;
}

export function validateToken(token: string | null): boolean {
  if (token == null) return false;
  if (token.length < 8) return false;
  return true;
}

export async function fetchWithRetry(url: string, retries = 3): Promise<Response> {
  let lastError: Error | undefined;
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url);
      if (res.ok) return res;
      lastError = new Error(`HTTP ${res.status}: ${res.statusText}`);
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err));
    }
  }
  throw lastError ?? new Error(`All ${retries} retries failed for ${url}`);
}
