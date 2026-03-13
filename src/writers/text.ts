import type { LintIssue } from "@/models/lint-issue";

/**
 * Format a list of lint issues as human-readable text.
 * Returns an empty string if there are no issues.
 */
export function formatIssues(issues: LintIssue[]): string {
  if (issues.length === 0) return "";

  const lines: string[] = [];
  for (const issue of issues) {
    const location = `${issue.file}:${issue.line}:${issue.col}`;
    const severity = issue.severity.toUpperCase();
    lines.push(`${location}: [${severity}] ${issue.rule}: ${issue.message}`);
  }
  lines.push("");
  lines.push(`${issues.length} issue(s) found`);
  return lines.join("\n");
}

/**
 * Format a single lint issue as a string.
 */
export function formatIssue(issue: LintIssue): string {
  const location = `${issue.file}:${issue.line}:${issue.col}`;
  const severity = issue.severity.toUpperCase();
  return `${location}: [${severity}] ${issue.rule}: ${issue.message}`;
}
