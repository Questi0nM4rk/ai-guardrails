import { dirname, join } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { FileManager } from "@/infra/file-manager";
import type { LanguagePlugin } from "@/languages/types";
import type { BaselineEntry } from "@/models/baseline";
import type { LintIssue } from "@/models/lint-issue";
import { BASELINE_PATH } from "@/models/paths";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";
import { runLinterCollection } from "@/steps/run-linters";

function issueToEntry(issue: LintIssue): BaselineEntry {
  return {
    fingerprint: issue.fingerprint,
    rule: issue.rule,
    linter: issue.linter,
    file: issue.file,
    line: issue.line,
    message: issue.message,
    capturedAt: new Date().toISOString(),
  };
}

export async function snapshotStep(
  projectDir: string,
  languages: readonly LanguagePlugin[],
  config: ResolvedConfig,
  commandRunner: CommandRunner,
  fileManager: FileManager,
  baselinePath?: string
): Promise<StepResult> {
  try {
    const allIssues = await runLinterCollection(
      projectDir,
      languages,
      config,
      commandRunner,
      fileManager
    );

    const filtered = allIssues.filter(
      (issue) => !config.isAllowed(issue.rule, issue.file)
    );

    const entries: BaselineEntry[] = filtered.map(issueToEntry);
    const dest = join(projectDir, baselinePath ?? BASELINE_PATH);
    await fileManager.mkdir(dirname(dest), { parents: true });
    await fileManager.writeText(dest, JSON.stringify(entries, null, 2));

    return ok(
      `Snapshot captured: ${entries.length} issue(s) written to ${baselinePath ?? BASELINE_PATH}`
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return error(`Snapshot failed: ${message}`);
  }
}
