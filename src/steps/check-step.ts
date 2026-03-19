import { relative } from "node:path";
import { minimatch } from "minimatch";
import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { Console } from "@/infra/console";
import type { FileManager } from "@/infra/file-manager";
import type { LanguagePlugin } from "@/languages/types";
import { classifyFingerprint, loadBaselineFromFile } from "@/models/baseline";
import type { LintIssue } from "@/models/lint-issue";
import type { StepResult } from "@/models/step-result";
import { error, ok } from "@/models/step-result";
import type { RunOptions } from "@/runners/types";

export interface CheckStepResult {
  result: StepResult;
  issues: LintIssue[];
  newIssueCount: number;
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
    const filtered = allIssues.filter((issue) => {
      if (config.isAllowed(issue.rule, issue.file)) return false;
      if (config.ignorePaths.length > 0) {
        const relPath = relative(projectDir, issue.file);
        if (
          config.ignorePaths.some((pattern) =>
            minimatch(relPath, pattern, { dot: true })
          )
        ) {
          return false;
        }
      }
      return true;
    });

    const baseline = (await loadBaselineFromFile(projectDir, fileManager)) ?? new Map();

    const newIssues = filtered.filter(
      (issue) => classifyFingerprint(issue.fingerprint, baseline) === "new"
    );
    const baselinedCount = filtered.length - newIssues.length;

    const msg =
      newIssues.length === 0
        ? baselinedCount > 0
          ? `No new issues (${baselinedCount} baselined)`
          : "No issues found"
        : `Found ${newIssues.length} new issue(s)${baselinedCount > 0 ? ` (${baselinedCount} baselined)` : ""}`;

    return {
      result: newIssues.length > 0 ? error(msg) : ok(msg),
      issues: filtered,
      newIssueCount: newIssues.length,
      skipped,
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      result: error(`Check failed: ${message}`),
      issues: [],
      newIssueCount: 0,
      skipped: 0,
    };
  }
}
