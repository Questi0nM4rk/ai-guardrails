import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { Console } from "@/infra/console";
import type { FileManager } from "@/infra/file-manager";
import type { LanguagePlugin } from "@/languages/types";
import type { LintIssue } from "@/models/lint-issue";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";
import type { RunOptions } from "@/runners/types";

export interface CheckStepResult {
  result: StepResult;
  issues: LintIssue[];
  skipped: number;
}

export async function checkStep(
  projectDir: string,
  languages: readonly LanguagePlugin[],
  config: ResolvedConfig,
  commandRunner: CommandRunner,
  fileManager: FileManager,
  cons?: Console
): Promise<CheckStepResult> {
  try {
    const opts: RunOptions = { projectDir, config, commandRunner, fileManager };

    let skipped = 0;
    const runnerResults = await Promise.all(
      languages.flatMap((plugin) =>
        plugin.runners().map(async (runner) => {
          const available = await runner.isAvailable(commandRunner, projectDir);
          if (!available) {
            cons?.warning(
              `  ${runner.name} not found — skipping (${runner.installHint.description})`
            );
            skipped++;
            return [] as LintIssue[];
          }
          return runner.run(opts);
        })
      )
    );

    if (skipped > 0) {
      cons?.warning(
        `${skipped} runner(s) skipped — run \`ai-guardrails init\` to install missing tools`
      );
    }

    const allIssues = runnerResults.flat();
    const filtered = allIssues.filter(
      (issue) => !config.isAllowed(issue.rule, issue.file)
    );

    // TODO(baseline): Load .ai-guardrails/baseline.json and call
    // classifyFingerprint() to filter out "existing" issues from the
    // failure set — only "new" issues since the last snapshot should
    // cause the check to fail ("hold-the-line" enforcement).
    // See docs/bugs/baseline-fingerprint-gap.md for full details and fix outline.

    const msg =
      filtered.length === 0
        ? "No new issues found"
        : `Found ${filtered.length} issue(s)`;

    return {
      result: filtered.length > 0 ? error(msg) : ok(msg),
      issues: filtered,
      skipped,
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      result: error(`Check failed: ${message}`),
      issues: [],
      skipped: 0,
    };
  }
}
