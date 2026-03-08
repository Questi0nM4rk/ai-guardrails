import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { FileManager } from "@/infra/file-manager";
import type { LanguagePlugin } from "@/languages/types";
import type { LintIssue } from "@/models/lint-issue";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";
import type { RunOptions } from "@/runners/types";

export interface CheckStepResult {
  result: StepResult;
  issues: LintIssue[];
}

export async function checkStep(
  projectDir: string,
  languages: readonly LanguagePlugin[],
  config: ResolvedConfig,
  commandRunner: CommandRunner,
  fileManager: FileManager,
): Promise<CheckStepResult> {
  try {
    const opts: RunOptions = { projectDir, config, commandRunner, fileManager };

    const allIssues = (
      await Promise.all(
        languages.flatMap((plugin) => plugin.runners().map((runner) => runner.run(opts))),
      )
    ).flat();

    const filtered = allIssues.filter((issue) => !config.isAllowed(issue.rule, issue.file));

    const msg = filtered.length === 0 ? "No new issues found" : `Found ${filtered.length} issue(s)`;

    return {
      result: filtered.length > 0 ? error(msg) : ok(msg),
      issues: filtered,
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      result: error(`Check failed: ${message}`),
      issues: [],
    };
  }
}
