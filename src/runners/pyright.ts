import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";
import { applyFingerprints } from "@/utils/apply-fingerprints";
import { safeParseJson } from "@/utils/parse";
import { resolveToolPath } from "@/utils/resolve-tool-path";

interface PyrightRange {
  start: { line: number; character: number };
  end: { line: number; character: number };
}

interface PyrightDiagnostic {
  file: string;
  severity: string;
  message: string;
  range: PyrightRange;
  rule?: string;
}

interface PyrightOutput {
  generalDiagnostics: PyrightDiagnostic[];
}

function isPyrightRange(value: unknown): value is PyrightRange {
  if (typeof value !== "object" || value === null) return false;
  const v = value as { start: unknown };
  const start = v.start;
  return (
    typeof start === "object" &&
    start !== null &&
    typeof (start as { line: unknown; character: unknown }).line === "number" &&
    typeof (start as { line: unknown; character: unknown }).character === "number"
  );
}

function isPyrightDiagnostic(value: unknown): value is PyrightDiagnostic {
  if (typeof value !== "object" || value === null) return false;
  const v = value as PyrightDiagnostic & { range: unknown };
  return (
    typeof v.file === "string" &&
    typeof v.severity === "string" &&
    typeof v.message === "string" &&
    isPyrightRange(v.range)
  );
}

function isPyrightOutput(value: unknown): value is PyrightOutput {
  if (typeof value !== "object" || value === null) return false;
  const v = value as { generalDiagnostics: unknown };
  return Array.isArray(v.generalDiagnostics);
}

/**
 * Parse pyright --outputjson output into raw issues without fingerprints.
 * Skips information-level diagnostics.
 * Returns [] for empty stdout or invalid JSON.
 *
 * LintIssue.file is the absolute path emitted by pyright.
 */
export function parsePyrightOutput(
  stdout: string,
  _projectDir: string
): Omit<LintIssue, "fingerprint">[] {
  if (!stdout.trim()) return [];

  const parsed = safeParseJson(stdout);
  if (parsed === null) return [];

  if (!isPyrightOutput(parsed)) return [];

  const issues: Omit<LintIssue, "fingerprint">[] = [];
  for (const diag of parsed.generalDiagnostics) {
    if (!isPyrightDiagnostic(diag)) continue;
    if (diag.severity === "information") continue;

    const rule = `pyright/${diag.rule ?? "unknown"}`;
    // pyright uses 0-indexed lines and columns; LintIssue is 1-indexed
    const line = diag.range.start.line + 1;
    const col = diag.range.start.character + 1;

    issues.push({
      rule,
      linter: "pyright",
      file: diag.file,
      line,
      col,
      message: diag.message,
      severity: diag.severity === "error" ? "error" : "warning",
    });
  }
  return issues;
}

export const pyrightRunner: LinterRunner = {
  id: "pyright",
  name: "Pyright",
  configFile: "pyrightconfig.json",
  installHint: {
    description: "Python type checker",
    npm: "npm install -D pyright",
    pip: "pip install pyright",
  },

  async isAvailable(runner: CommandRunner, projectDir?: string): Promise<boolean> {
    return (await resolveToolPath("pyright", projectDir ?? ".", runner)) !== null;
  },

  async run(opts: RunOptions): Promise<LintIssue[]> {
    const { projectDir, commandRunner, fileManager } = opts;
    const cmd =
      (await resolveToolPath("pyright", projectDir, commandRunner)) ?? "pyright";
    const result = await commandRunner.run([cmd, "--outputjson", projectDir], {
      cwd: projectDir,
    });
    const raw = parsePyrightOutput(result.stdout, projectDir);
    return applyFingerprints(raw, projectDir, fileManager);
  },
};
