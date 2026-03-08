import type { LintIssue } from "@/models/lint-issue";
import { computeFingerprint } from "@/models/lint-issue";

const CONTEXT_LINES = 2;

/**
 * Compute a stable fingerprint for a lint issue using surrounding source lines.
 * The fingerprint includes the file path to avoid collisions across files.
 *
 * NOTE: This function is not yet called by any runner. All runners currently
 * call computeFingerprint() directly with the tool's error message as lineContent,
 * which makes fingerprints dependent on tool output wording rather than source
 * code content. This means fingerprints will silently break when tools change
 * their error messages (e.g. version upgrades), invalidating saved baselines.
 *
 * TODO(baseline): Wire this into each runner's run() method by reading source
 * files and grouping issues by file before computing fingerprints.
 * See docs/bugs/baseline-fingerprint-gap.md for the full fix outline.
 */
export function fingerprintIssue(
    issue: Omit<LintIssue, "fingerprint">,
    sourceLines: string[]
): string {
    // line is 1-indexed; convert to 0-indexed for array access
    const lineIdx = issue.line - 1;
    const lineContent = sourceLines[lineIdx] ?? "";

    const contextBefore: string[] = [];
    for (let i = Math.max(0, lineIdx - CONTEXT_LINES); i < lineIdx; i++) {
        contextBefore.push(sourceLines[i] ?? "");
    }

    const contextAfter: string[] = [];
    for (
        let i = lineIdx + 1;
        i <= Math.min(sourceLines.length - 1, lineIdx + CONTEXT_LINES);
        i++
    ) {
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
