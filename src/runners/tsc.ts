import { resolve } from "node:path";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import { computeFingerprint } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";
import { resolveToolPath } from "@/utils/resolve-tool-path";

const TSC_LINTER_ID = "tsc";
const TSC_RULE_PREFIX = "tsc/";

// Matches lines like: src/foo.ts(10,5): error TS2322: Type 'string' is not assignable...
const TSC_LINE_PATTERN = /^(.+)\((\d+),(\d+)\):\s+(error|warning)\s+(TS\d+):\s+(.+)$/;

interface TscMatch {
  file: string;
  line: number;
  col: number;
  severity: "error" | "warning";
  tsCode: string;
  message: string;
}

function parseTscLine(line: string): TscMatch | null {
  const match = TSC_LINE_PATTERN.exec(line);
  if (!match) return null;
  const [, file, lineStr, colStr, rawSeverity, tsCode, message] = match;
  if (!file || !lineStr || !colStr || !rawSeverity || !tsCode || !message) return null;
  return {
    file,
    line: Number.parseInt(lineStr, 10),
    col: Number.parseInt(colStr, 10),
    severity: rawSeverity === "warning" ? "warning" : "error",
    tsCode,
    message,
  };
}

export function parseTscOutput(output: string, projectDir: string): LintIssue[] {
  const issues: LintIssue[] = [];
  for (const line of output.split("\n")) {
    const parsed = parseTscLine(line);
    if (!parsed) continue;
    const filePath = resolve(projectDir, parsed.file);
    const rule = TSC_RULE_PREFIX + parsed.tsCode;
    // parsed.file is already project-relative (tsc emits relative paths)
    const fingerprint = computeFingerprint({
      rule,
      file: parsed.file,
      lineContent: parsed.message,
      contextBefore: [],
      contextAfter: [],
    });
    issues.push({
      rule,
      linter: TSC_LINTER_ID,
      file: filePath,
      line: parsed.line,
      col: parsed.col,
      message: parsed.message,
      severity: parsed.severity,
      fingerprint,
    });
  }
  return issues;
}

export const tscRunner: LinterRunner = {
  id: TSC_LINTER_ID,
  name: "TypeScript Compiler",
  configFile: null,
  installHint: {
    description: "TypeScript type checker",
    npm: "npm install -D typescript",
  },

  async isAvailable(
    commandRunner: CommandRunner,
    projectDir?: string
  ): Promise<boolean> {
    return (await resolveToolPath("tsc", projectDir ?? ".", commandRunner)) !== null;
  },

  async run({ projectDir, commandRunner }: RunOptions): Promise<LintIssue[]> {
    const tsc = (await resolveToolPath("tsc", projectDir, commandRunner)) ?? "tsc";
    const result = await commandRunner.run([tsc, "--noEmit", "--pretty", "false"], {
      cwd: projectDir,
    });
    // tsc exits non-zero when errors exist — parse stdout+stderr
    const combined = `${result.stdout}\n${result.stderr}`;
    return parseTscOutput(combined, projectDir);
  },
};
