import { resolve } from "node:path";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import { computeFingerprint } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";

const MARKDOWNLINT_LINTER_ID = "markdownlint";
const MARKDOWNLINT_RULE_PREFIX = "markdownlint/";

// Matches lines like: docs/README.md:3 MD013/line-length Line length [...]
const MARKDOWNLINT_LINE_PATTERN = /^(.+):(\d+)\s+(MD\d+)(?:\/[\w-]+)?\s+(.+)$/;

/**
 * Parse markdownlint-cli2 stdout into LintIssue[].
 * Returns [] on empty or non-matching input.
 */
export function parseMarkdownlintOutput(
  stdout: string,
  projectDir: string
): LintIssue[] {
  const issues: LintIssue[] = [];
  for (const line of stdout.split("\n")) {
    const match = MARKDOWNLINT_LINE_PATTERN.exec(line);
    if (!match) continue;
    const [, filePath, lineStr, ruleCode, message] = match;
    if (!filePath || !lineStr || !ruleCode || !message) continue;

    const file = resolve(projectDir, filePath);
    const lineNum = Number.parseInt(lineStr, 10);
    const rule = MARKDOWNLINT_RULE_PREFIX + ruleCode;
    const fingerprint = computeFingerprint({
      rule,
      file,
      lineContent: message,
      contextBefore: [],
      contextAfter: [],
    });
    issues.push({
      rule,
      linter: MARKDOWNLINT_LINTER_ID,
      file,
      line: lineNum,
      col: 1,
      message,
      severity: "warning",
      fingerprint,
    });
  }
  return issues;
}

export const markdownlintRunner: LinterRunner = {
  id: MARKDOWNLINT_LINTER_ID,
  name: "markdownlint",
  configFile: ".markdownlint.jsonc",
  installHint: {
    description: "Markdown linter",
    npm: "npm install -g markdownlint-cli2",
  },

  async isAvailable(commandRunner: CommandRunner): Promise<boolean> {
    const result = await commandRunner.run(["markdownlint-cli2", "--version"]);
    return result.exitCode === 0;
  },

  async run({ projectDir, commandRunner }: RunOptions): Promise<LintIssue[]> {
    const result = await commandRunner.run(
      [
        "markdownlint-cli2",
        "**/*.md",
        "!node_modules/**",
        "!dist/**",
        "!.venv/**",
        "!venv/**",
        "!build/**",
        "--config",
        ".markdownlint.jsonc",
      ],
      { cwd: projectDir }
    );
    // markdownlint-cli2 exits non-zero on issues — parse stdout regardless
    return parseMarkdownlintOutput(result.stdout, projectDir);
  },
};
