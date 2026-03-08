import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import { computeFingerprint } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";

interface GolangciIssue {
  FromLinter: string;
  Text: string;
  Pos: {
    Filename: string;
    Line: number;
    Column: number;
  };
}

interface GolangciOutput {
  Issues: GolangciIssue[] | null;
}

function isGolangciOutput(value: unknown): value is GolangciOutput {
  return typeof value === "object" && value !== null && "Issues" in value;
}

/**
 * Parse golangci-lint JSON output into LintIssue[].
 * Handles null Issues array (no issues found).
 */
export function parseGolangciOutput(json: string, projectDir: string): LintIssue[] {
  let parsed: unknown;
  try {
    parsed = JSON.parse(json);
  } catch {
    return [];
  }

  if (!isGolangciOutput(parsed)) return [];

  const rawIssues = parsed.Issues;
  if (!rawIssues) return [];

  return rawIssues.map((issue) => {
    const rule = `golangci-lint/${issue.FromLinter}`;
    const file = resolve(projectDir, issue.Pos.Filename);
    const fingerprint = computeFingerprint({
      rule,
      file,
      lineContent: "",
      contextBefore: [],
      contextAfter: [],
    });

    return {
      rule,
      linter: "golangci-lint",
      file,
      line: issue.Pos.Line,
      col: issue.Pos.Column,
      message: issue.Text,
      severity: "error" as const,
      fingerprint,
    };
  });
}

/**
 * Detect golangci-lint version and choose the appropriate JSON output flag.
 * v1.64+ uses --output.json.path=stdout; older versions use --out-format=json.
 */
async function detectJsonFlag(commandRunner: CommandRunner, cwd: string): Promise<string> {
  const result = await commandRunner.run(["golangci-lint", "--version"], { cwd });
  const match = /(\d+)\.(\d+)/.exec(result.stdout);
  const major = Number.parseInt(match?.[1] ?? "0", 10);
  const minor = Number.parseInt(match?.[2] ?? "0", 10);
  const isV164Plus = major > 1 || (major === 1 && minor >= 64);
  return isV164Plus ? "--output.json.path=stdout" : "--out-format=json";
}

export const golangciLintRunner: LinterRunner = {
  id: "golangci-lint",
  name: "golangci-lint",
  configFile: ".golangci.yml",

  async isAvailable(commandRunner: CommandRunner): Promise<boolean> {
    const result = await commandRunner.run(["golangci-lint", "--version"]);
    return result.exitCode === 0;
  },

  async run(opts: RunOptions): Promise<LintIssue[]> {
    const { projectDir, commandRunner } = opts;
    const jsonFlag = await detectJsonFlag(commandRunner, projectDir);
    const result = await commandRunner.run(["golangci-lint", "run", jsonFlag, "./..."], {
      cwd: projectDir,
    });
    return parseGolangciOutput(result.stdout, projectDir);
  },

  generateConfig(_config: ResolvedConfig): string {
    return `run:
  timeout: 5m

linters:
  enable-all: false
  enable:
    - errcheck
    - gosimple
    - govet
    - ineffassign
    - staticcheck
    - unused

linters-settings: {}
`;
  },
};
