import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";
import { applyFingerprints } from "@/utils/apply-fingerprints";
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
  if (
    !("code" in value) ||
    typeof value.code !== "string" ||
    !("filename" in value) ||
    typeof value.filename !== "string" ||
    !("message" in value) ||
    typeof value.message !== "string"
  ) {
    return false;
  }
  if (!("location" in value)) return false;
  const loc = value.location;
  return (
    typeof loc === "object" &&
    loc !== null &&
    "row" in loc &&
    typeof loc.row === "number" &&
    "column" in loc &&
    typeof loc.column === "number"
  );
}

/**
 * Parse ruff JSON array output into raw issues without fingerprints.
 * Returns [] for empty stdout, invalid JSON, or non-array output.
 *
 * projectDir is used to resolve relative filenames to absolute paths.
 * LintIssue.file is always absolute.
 */
export function parseRuffOutput(
  stdout: string,
  _config: ResolvedConfig,
  projectDir: string
): Omit<LintIssue, "fingerprint">[] {
  if (!stdout.trim()) return [];

  const parsed = safeParseJson(stdout);
  if (!Array.isArray(parsed)) return [];

  const issues: Omit<LintIssue, "fingerprint">[] = [];
  for (const item of parsed) {
    if (!isRuffItem(item)) continue;

    const rule = `ruff/${item.code}`;
    const absFile = item.filename.startsWith("/")
      ? item.filename
      : resolve(projectDir, item.filename);

    issues.push({
      rule,
      linter: "ruff",
      file: absFile,
      line: item.location.row,
      col: item.location.column,
      message: item.message,
      severity: severityForCode(item.code),
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
    const { projectDir, config, commandRunner, fileManager } = opts;
    const result = await commandRunner.run(
      ["ruff", "check", "--output-format=json", projectDir],
      { cwd: projectDir }
    );
    const raw = parseRuffOutput(result.stdout, config, projectDir);
    return applyFingerprints(raw, projectDir, fileManager);
  },
};
