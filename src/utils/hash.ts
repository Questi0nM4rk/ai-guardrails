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
  const expectedHash = createHash("sha256").update(body).digest("hex");

  return storedHash === expectedHash;
}
