import { resolve } from "node:path";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";
import { applyFingerprints } from "@/utils/apply-fingerprints";

const CODESPELL_LINTER_ID = "codespell";
const CODESPELL_RULE = "codespell/spell";

// Matches lines like: ./src/foo.py:3: <typo> ==> <correction>
const CODESPELL_LINE_PATTERN = /^(.+):(\d+):\s+(.+?)\s+==>(.+)$/;

/**
 * Parse codespell --quiet-level=2 stdout into raw issues without fingerprints.
 * Returns [] on empty or non-matching input.
 */
export function parseCodespellOutput(
  stdout: string,
  projectDir: string
): Omit<LintIssue, "fingerprint">[] {
  const issues: Omit<LintIssue, "fingerprint">[] = [];
  for (const line of stdout.split("\n")) {
    const match = CODESPELL_LINE_PATTERN.exec(line);
    if (!match) continue;
    const [, rawPath, lineStr, typo, correction] = match;
    if (!rawPath || !lineStr || !typo || !correction) continue;

    // Strip leading ./ if present
    const relativePath = rawPath.startsWith("./") ? rawPath.slice(2) : rawPath;
    const file = resolve(projectDir, relativePath);
    const lineNum = Number.parseInt(lineStr, 10);
    const message = `Spelling: ${typo.trim()} ==> ${correction.trim()}`;
    issues.push({
      rule: CODESPELL_RULE,
      linter: CODESPELL_LINTER_ID,
      file,
      line: lineNum,
      col: 1,
      message,
      severity: "warning",
    });
  }
  return issues;
}

export const codespellRunner: LinterRunner = {
  id: CODESPELL_LINTER_ID,
  name: "Codespell",
  configFile: ".codespellrc",
  installHint: {
    description: "Spell checker",
    pip: "pip install codespell",
  },

  async isAvailable(commandRunner: CommandRunner): Promise<boolean> {
    const result = await commandRunner.run(["codespell", "--version"]);
    return result.exitCode === 0;
  },

  async run({
    projectDir,
    commandRunner,
    fileManager,
  }: RunOptions): Promise<LintIssue[]> {
    const result = await commandRunner.run(["codespell", "--quiet-level=2"], {
      cwd: projectDir,
    });
    // codespell exits non-zero when issues are found — parse stdout regardless
    const raw = parseCodespellOutput(result.stdout, projectDir);
    return applyFingerprints(raw, projectDir, fileManager);
  },
};
