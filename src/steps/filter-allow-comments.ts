import type { LintIssue } from "@/models/lint-issue";
import { ALLOW_COMMENT_RE } from "@/utils/allow-comment-re";

interface AllowDirective {
  /** 1-indexed line number of the directive itself */
  line: number;
  rule: string;
}

function parseDirectives(source: string): AllowDirective[] {
  const directives: AllowDirective[] = [];
  const lines = source.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line === undefined) continue;
    const match = ALLOW_COMMENT_RE.exec(line);
    if (match !== null) {
      const rule = match[1];
      if (rule !== undefined) {
        directives.push({ line: i + 1, rule });
      }
    }
  }
  return directives;
}

function isSuppressed(issue: LintIssue, directives: AllowDirective[]): boolean {
  return directives.some(
    (d) => d.rule === issue.rule && (d.line === issue.line || d.line + 1 === issue.line)
  );
}

export async function filterAllowComments(
  issues: readonly LintIssue[],
  fileManager: { readText(path: string): Promise<string> }
): Promise<LintIssue[]> {
  if (issues.length === 0) return [];

  // Group issue indices by file path
  const byFile = new Map<string, number[]>();
  for (let i = 0; i < issues.length; i++) {
    const issue = issues[i];
    if (issue === undefined) continue;
    const existing = byFile.get(issue.file);
    if (existing !== undefined) {
      existing.push(i);
    } else {
      byFile.set(issue.file, [i]);
    }
  }

  const suppressed = new Set<number>();

  await Promise.all(
    Array.from(byFile.entries()).map(async ([filePath, indices]) => {
      let source: string;
      try {
        source = await fileManager.readText(filePath);
      } catch {
        // File unreadable — leave all issues for this file in place
        return;
      }

      const directives = parseDirectives(source);
      if (directives.length === 0) return;

      for (const idx of indices) {
        const issue = issues[idx];
        if (issue !== undefined && isSuppressed(issue, directives)) {
          suppressed.add(idx);
        }
      }
    })
  );

  return issues.filter((_, i) => !suppressed.has(i));
}
