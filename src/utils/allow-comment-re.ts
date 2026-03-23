/**
 * Matches inline ai-guardrails-allow directives in source files.
 *
 * Supports all common comment styles:
 *   // ai-guardrails-allow biome/noConsole "reason"
 *   #  ai-guardrails-allow ruff/E501 "reason"
 *   -- ai-guardrails-allow selene/shadowing "reason"
 */
export const ALLOW_COMMENT_RE = /ai-guardrails-allow\s+([\w-]+\/[\w\-.]+)\s+"([^"]+)"/;
