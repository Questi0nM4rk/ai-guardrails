import { sha256hex } from "@/utils/hash";

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
 * Compute a fingerprint that survives file moves and minor reformats.
 * Hashes rule + trimmed line content + surrounding context.
 */
export function computeFingerprint(opts: FingerprintOpts): string {
  const { rule, file: _file, lineContent, contextBefore, contextAfter } = opts;
  const input = [
    rule,
    lineContent.trim(),
    ...contextBefore.map((l) => l.trim()),
    ...contextAfter.map((l) => l.trim()),
  ].join("\n");
  return sha256hex(input);
}
