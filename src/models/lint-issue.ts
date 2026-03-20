import { createHash } from "node:crypto";

export interface LintIssue {
  readonly rule: string; // "E501", "no-unused-vars", "S1481"
  readonly linter: string; // "ruff", "pyright", "biome"
  readonly file: string; // absolute path
  readonly line: number; // 1-indexed
  readonly col: number; // 1-indexed
  readonly message: string;
  readonly severity: "error" | "warning";
  readonly fingerprint: string; // content-stable SHA-256
}

export interface FingerprintOpts {
  rule: string;
  file: string;
  lineContent: string; // content of the flagged line
  contextBefore: string[]; // up to 2 lines before
  contextAfter: string[]; // up to 2 lines after
}

/**
 * Compute a fingerprint for a lint issue.
 * Hashes rule + file path + trimmed line content + surrounding context.
 * File path is included so identical issues in different files produce distinct fingerprints.
 *
 * NOTE: Callers must pass a project-relative path as `file`, NOT an absolute path.
 * Callers pass project-relative paths for portable baselines.
 */
export function computeFingerprint(opts: FingerprintOpts): string {
  const { rule, file, lineContent, contextBefore, contextAfter } = opts;
  const input = [
    rule,
    file,
    lineContent.trim(),
    ...contextBefore.map((l) => l.trim()),
    ...contextAfter.map((l) => l.trim()),
  ].join("\n");
  return createHash("sha256").update(input).digest("hex");
}
