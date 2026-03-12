import { createHash } from "node:crypto";

export const HASH_PREFIX = "# ai-guardrails:sha256=";
export const JSONC_HASH_PREFIX = "// ai-guardrails:sha256=";
export const MD_HASH_PREFIX = "<!-- ai-guardrails:sha256=";
export const MD_HASH_SUFFIX = " -->";

/** Compute a hex SHA-256 digest of a string. */
export function computeHash(content: string): string {
  return createHash("sha256").update(content).digest("hex");
}

/**
 * Compute a SHA-256 hash header for the given file body content.
 * The hash covers the body text below the header line.
 */
export function makeHashHeader(content: string): string {
  return `${HASH_PREFIX}${computeHash(content)}`;
}

/**
 * Compute a JSONC-compatible SHA-256 hash header using `//` comment syntax.
 * The hash covers the body text below the header line.
 */
export function makeJsoncHashHeader(content: string): string {
  return `${JSONC_HASH_PREFIX}${computeHash(content)}`;
}

/**
 * Prepend a hash header to the given content and return the combined string.
 * The format is: `<header line>\n<content>`.
 */
export function withHashHeader(content: string): string {
  return `${makeHashHeader(content)}\n${content}`;
}

/**
 * Prepend a JSONC-compatible hash header (using `//` comment syntax) to the given content.
 * The format is: `<header line>\n<content>`.
 */
export function withJsoncHashHeader(content: string): string {
  return `${makeJsoncHashHeader(content)}\n${content}`;
}

/**
 * Prepend a Markdown-safe hash header (using HTML comment syntax) to the given content.
 * The format is: `<!-- ai-guardrails:sha256=<hash> -->\n<content>`.
 */
export function withMarkdownHashHeader(content: string): string {
  return `${MD_HASH_PREFIX}${computeHash(content)}${MD_HASH_SUFFIX}\n${content}`;
}
