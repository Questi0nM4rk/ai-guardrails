import { resolve } from "node:path";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import { computeFingerprint } from "@/models/lint-issue";
import { findShellFiles } from "@/runners/shellcheck";
import type { LinterRunner, RunOptions } from "@/runners/types";

/**
 * Parse shfmt -l stdout into LintIssue[].
 * shfmt -l lists one file per line that needs reformatting.
 * Returns [] for empty output.
 */
export function parseShfmtOutput(stdout: string, projectDir: string): LintIssue[] {
  const filenames = stdout
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  return filenames.map((filename) => {
    const rule = "shfmt/format";
    const file = resolve(projectDir, filename);
    const message = `File needs formatting — run: shfmt -w ${filename}`;
    // filename is project-relative (shfmt -l emits relative paths)
    const fingerprint = computeFingerprint({
      rule,
      file: filename,
      lineContent: message,
      contextBefore: [],
      contextAfter: [],
    });

    return {
      rule,
      linter: "shfmt",
      file,
      line: 1,
      col: 1,
      message,
      severity: "error",
      fingerprint,
    } satisfies LintIssue;
  });
}

export const shfmtRunner: LinterRunner = {
  id: "shfmt",
  name: "shfmt",
  configFile: null,
  installHint: {
    description: "Shell script formatter",
    brew: "brew install shfmt",
    go: "go install mvdan.cc/sh/v3/cmd/shfmt@latest",
  },

  async isAvailable(commandRunner: CommandRunner): Promise<boolean> {
    const result = await commandRunner.run(["shfmt", "--version"]);
    return result.exitCode === 0;
  },

  async run({
    projectDir,
    commandRunner,
    fileManager,
  }: RunOptions): Promise<LintIssue[]> {
    const files = await findShellFiles(fileManager, projectDir);
    if (files.length === 0) return [];

    const result = await commandRunner.run(["shfmt", "-l", ...files], {
      cwd: projectDir,
    });

    return parseShfmtOutput(result.stdout, projectDir);
  },
};
