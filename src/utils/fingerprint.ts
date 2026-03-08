import type { LintIssue } from "@/models/lint-issue";
import { computeFingerprint } from "@/models/lint-issue";

const CONTEXT_LINES = 2;

/**
 * Compute a stable fingerprint for a lint issue using surrounding source lines.
 * The fingerprint does not include the file path so it survives file moves.
 */
export function fingerprintIssue(
  issue: Omit<LintIssue, "fingerprint">,
  sourceLines: string[],
): string {
  // line is 1-indexed; convert to 0-indexed for array access
  const lineIdx = issue.line - 1;
  const lineContent = sourceLines[lineIdx] ?? "";

  const contextBefore: string[] = [];
  for (let i = Math.max(0, lineIdx - CONTEXT_LINES); i < lineIdx; i++) {
    contextBefore.push(sourceLines[i] ?? "");
  }

  const contextAfter: string[] = [];
  for (let i = lineIdx + 1; i <= Math.min(sourceLines.length - 1, lineIdx + CONTEXT_LINES); i++) {
    contextAfter.push(sourceLines[i] ?? "");
  }

  return computeFingerprint({
    rule: issue.rule,
    file: issue.file,
    lineContent,
    contextBefore,
    contextAfter,
  });
}
