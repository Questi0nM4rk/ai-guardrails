import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { FileManager } from "@/infra/file-manager";
import type { LintIssue } from "@/models/lint-issue";
import { computeFingerprint } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";

/** Shape of a single comment in shellcheck --format=json1 output */
interface ShellcheckComment {
  file: string;
  line: number;
  column: number;
  level: string;
  code: number;
  message: string;
}

/** Shape of the top-level shellcheck --format=json1 output */
interface ShellcheckOutput {
  comments: ShellcheckComment[];
}

/**
 * Parse shellcheck --format=json1 stdout into LintIssue[].
 * Returns [] on malformed/empty input.
 */
export function parseShellcheckOutput(stdout: string, projectDir: string): LintIssue[] {
  let parsed: unknown;
  try {
    parsed = JSON.parse(stdout);
  } catch {
    return [];
  }

  if (!isShellcheckOutput(parsed)) return [];

  return parsed.comments.map((comment) => {
    const rule = `shellcheck/SC${comment.code}`;
    const file = resolve(projectDir, comment.file);
    const severity = comment.level === "error" ? "error" : "warning";
    const fingerprint = computeFingerprint({
      rule,
      file,
      lineContent: comment.message,
      contextBefore: [],
      contextAfter: [],
    });

    return {
      rule,
      linter: "shellcheck",
      file,
      line: comment.line,
      col: comment.column,
      message: comment.message,
      severity,
      fingerprint,
    } satisfies LintIssue;
  });
}

function isShellcheckOutput(value: unknown): value is ShellcheckOutput {
  return (
    typeof value === "object" &&
    value !== null &&
    "comments" in value &&
    Array.isArray((value as ShellcheckOutput).comments)
  );
}

/** Glob for all shell script files across supported extensions. */
export async function findShellFiles(
  fileManager: FileManager,
  projectDir: string,
): Promise<string[]> {
  const [sh, bash, zsh] = await Promise.all([
    fileManager.glob("**/*.sh", projectDir),
    fileManager.glob("**/*.bash", projectDir),
    fileManager.glob("**/*.zsh", projectDir),
  ]);
  return [...sh, ...bash, ...zsh];
}

export const shellcheckRunner: LinterRunner = {
  id: "shellcheck",
  name: "ShellCheck",
  configFile: null,
  installHint: {
    description: "Shell script linter",
    brew: "brew install shellcheck",
    apt: "sudo apt install shellcheck",
  },

  async isAvailable(commandRunner: CommandRunner): Promise<boolean> {
    const result = await commandRunner.run(["shellcheck", "--version"]);
    return result.exitCode === 0;
  },

  async run({ projectDir, commandRunner, fileManager }: RunOptions): Promise<LintIssue[]> {
    const files = await findShellFiles(fileManager, projectDir);
    if (files.length === 0) return [];

    const result = await commandRunner.run(["shellcheck", "--format=json1", ...files], {
      cwd: projectDir,
    });

    return parseShellcheckOutput(result.stdout, projectDir);
  },

  generateConfig(_config: ResolvedConfig): null {
    return null;
  },
};
