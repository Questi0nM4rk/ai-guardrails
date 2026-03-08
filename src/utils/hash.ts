import { createHash } from "node:crypto";

export const HASH_PREFIX = "# ai-guardrails:sha256=";

/**
 * Compute a SHA-256 hash header for the given file body content.
 * The hash covers the body text below the header line.
 */
export function makeHashHeader(content: string): string {
    const hash = createHash("sha256").update(content).digest("hex");
    return `${HASH_PREFIX}${hash}`;
}

/**
 * Prepend a hash header to the given content and return the combined string.
 * The format is: `<header line>\n<content>`.
 */
export function withHashHeader(content: string): string {
    return `${makeHashHeader(content)}\n${content}`;
}
