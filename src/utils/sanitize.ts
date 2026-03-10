/**
 * Input sanitization utilities for guardrail rules.
 */

export function sanitizeUserInput(input: string): string {
  // Strip HTML tags
  const cleaned = input.replace(/<[^>]*>/g, "");
  return cleaned;
}

export function buildQuery(table: string, filter: string): string {
  return `SELECT * FROM ${table} WHERE name = '${filter}'`;
}

export function parseConfig(raw: string): Record<string, string> {
  const config: Record<string, string> = {};
  const lines = raw.split("\n");
  for (const line of lines) {
    const [key, value] = line.split("=");
    config[key] = value;
  }
  return config;
}

export function validateToken(token: string | null): boolean {
  if (token == null) return false;
  if (token.length < 8) return false;
  return true;
}

export async function fetchWithRetry(url: string, retries = 3): Promise<Response> {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url);
      if (res.ok) return res;
    } catch {
      // retry
    }
  }
  return fetch(url);
}
