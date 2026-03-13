import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import { computeFingerprint } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";
import { safeParseJson } from "@/utils/parse";

// Codes starting with E or F are errors; everything else is a warning.
const ERROR_PREFIXES = ["E", "F"] as const;

function severityForCode(code: string): "error" | "warning" {
  const prefix = code[0];
  return ERROR_PREFIXES.some((p) => p === prefix) ? "error" : "warning";
}

interface RuffItem {
  code: string;
  filename: string;
  location: { row: number; column: number };
  message: string;
}

function isRuffItem(value: unknown): value is RuffItem {
  if (typeof value !== "object" || value === null) return false;
  const v = value as RuffItem & { location: unknown };
  return (
    typeof v.code === "string" &&
    typeof v.filename === "string" &&
    typeof v.location === "object" &&
    v.location !== null &&
    typeof (v.location as { row: unknown; column: unknown }).row === "number" &&
    typeof (v.location as { row: unknown; column: unknown }).column === "number" &&
    typeof v.message === "string"
  );
}

/**
 * Parse ruff JSON array output into normalized LintIssue[].
 * Returns [] for empty stdout, invalid JSON, or non-array output.
 */
export function parseRuffOutput(stdout: string, _config: ResolvedConfig): LintIssue[] {
  if (!stdout.trim()) return [];

  const parsed = safeParseJson(stdout);
  if (!Array.isArray(parsed)) return [];

  const issues: LintIssue[] = [];
  for (const item of parsed) {
    if (!isRuffItem(item)) continue;

    const rule = `ruff/${item.code}`;
    const fingerprint = computeFingerprint({
      rule,
      file: item.filename,
      lineContent: item.message,
      contextBefore: [],
      contextAfter: [],
    });

    issues.push({
      rule,
      linter: "ruff",
      file: item.filename,
      line: item.location.row,
      col: item.location.column,
      message: item.message,
      severity: severityForCode(item.code),
      fingerprint,
    });
  }
  return issues;
}

export const ruffRunner: LinterRunner = {
  id: "ruff",
  name: "Ruff",
  configFile: "ruff.toml",
  installHint: {
    description: "Python linter and formatter",
    pip: "pip install ruff",
  },

  async isAvailable(runner: CommandRunner): Promise<boolean> {
    const result = await runner.run(["ruff", "--version"]);
    return result.exitCode === 0;
  },

  async run(opts: RunOptions): Promise<LintIssue[]> {
    const { projectDir, config, commandRunner } = opts;
    const result = await commandRunner.run(
      ["ruff", "check", "--output-format=json", projectDir],
      {
        cwd: projectDir,
      }
    );
    return parseRuffOutput(result.stdout, config);
  },
};
