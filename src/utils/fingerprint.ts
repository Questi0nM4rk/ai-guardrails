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
  if (issue.line < 1) {
    throw new Error(`fingerprintIssue: invalid line number ${issue.line} (must be >= 1)`);
  }

  // line is 1-indexed; convert to 0-indexed for array access
  const lineIdx = issue.line - 1;
  const lineContent = sourceLines[lineIdx] ?? "";

  const contextBefore = sourceLines.slice(Math.max(0, lineIdx - CONTEXT_LINES), lineIdx);
  const contextAfter = sourceLines.slice(
    lineIdx + 1,
    Math.min(sourceLines.length, lineIdx + CONTEXT_LINES + 1),
  );

  return computeFingerprint({
    rule: issue.rule,
    file: issue.file,
    lineContent,
    contextBefore,
    contextAfter,
  });
}
