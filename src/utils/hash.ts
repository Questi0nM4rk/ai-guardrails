import { createHash } from "node:crypto";

export const HASH_PREFIX = "# ai-guardrails:sha256=";

export function sha256hex(input: string): string {
  return createHash("sha256").update(input).digest("hex");
}

/**
 * Compute a SHA-256 hash header for the given file body content.
 * The hash covers the body text below the header line.
 */
export function makeHashHeader(content: string): string {
  return `${HASH_PREFIX}${sha256hex(content)}`;
}

/**
 * Verify that a file's hash header matches its content.
 * The file format is: `<header line>\n<body>`.
 * Returns false if the header is missing or the hash does not match.
 */
export function verifyHash(fileContent: string): boolean {
  const newlineIndex = fileContent.indexOf("\n");
  if (newlineIndex === -1) return false;

  const headerLine = fileContent.slice(0, newlineIndex);
  if (!headerLine.startsWith(HASH_PREFIX)) return false;

  const storedHash = headerLine.slice(HASH_PREFIX.length);
  const body = fileContent.slice(newlineIndex + 1);

  return storedHash === sha256hex(body);
}
