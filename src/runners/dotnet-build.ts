import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";
import { applyFingerprints } from "@/utils/apply-fingerprints";

const DOTNET_LINTER_ID = "dotnet-build";
const DOTNET_RULE_PREFIX = "dotnet-build/";

// Matches: src/MyClass.cs(12,5): warning CS0168: Variable 'e' is declared but never used [/path/MyProject.csproj]
// The project path suffix [...] is optional.
const MSBUILD_LINE_PATTERN =
  /^(.+?)\((\d+),(\d+)\):\s+(warning|error)\s+(CS\d+):\s+(.+?)(?:\s+\[.+\])?$/;

interface MsBuildMatch {
  file: string;
  line: number;
  col: number;
  severity: "error" | "warning";
  csCode: string;
  message: string;
}

function parseMsBuildLine(line: string): MsBuildMatch | null {
  const match = MSBUILD_LINE_PATTERN.exec(line);
  if (!match) return null;
  const [, file, lineStr, colStr, rawSeverity, csCode, message] = match;
  if (!file || !lineStr || !colStr || !rawSeverity || !csCode || !message) return null;
  return {
    file,
    line: Number.parseInt(lineStr, 10),
    col: Number.parseInt(colStr, 10),
    severity: rawSeverity === "warning" ? "warning" : "error",
    csCode,
    message,
  };
}

/**
 * Parse MSBuild text output from `dotnet build` into raw issues without fingerprints.
 *
 * Respects the profile: "minimal" emits errors only; "standard" and "strict" include warnings.
 * LintIssue.file is always absolute (resolved from projectDir).
 */
export function parseDotnetBuildOutput(
  output: string,
  projectDir: string,
  config: ResolvedConfig
): Omit<LintIssue, "fingerprint">[] {
  const issues: Omit<LintIssue, "fingerprint">[] = [];
  for (const line of output.split("\n")) {
    const parsed = parseMsBuildLine(line);
    if (!parsed) continue;
    if (config.profile === "minimal" && parsed.severity !== "error") continue;
    const absFile = parsed.file.startsWith("/")
      ? parsed.file
      : resolve(projectDir, parsed.file);
    issues.push({
      rule: DOTNET_RULE_PREFIX + parsed.csCode,
      linter: DOTNET_LINTER_ID,
      file: absFile,
      line: parsed.line,
      col: parsed.col,
      message: parsed.message,
      severity: parsed.severity,
    });
  }
  return issues;
}

export const dotnetBuildRunner: LinterRunner = {
  id: DOTNET_LINTER_ID,
  name: "dotnet build",
  configFile: null,
  installHint: {
    description: ".NET SDK",
  },

  async isAvailable(
    commandRunner: CommandRunner,
    projectDir?: string
  ): Promise<boolean> {
    try {
      const opts = projectDir !== undefined ? { cwd: projectDir } : undefined;
      const result = await commandRunner.run(["dotnet", "--version"], opts);
      return result.exitCode === 0;
    } catch {
      return false;
    }
  },

  async run(opts: RunOptions): Promise<LintIssue[]> {
    const { projectDir, config, commandRunner, fileManager } = opts;
    const result = await commandRunner.run(
      ["dotnet", "build", "--no-restore", "-v:q"],
      { cwd: projectDir }
    );
    const raw = parseDotnetBuildOutput(
      `${result.stdout}\n${result.stderr}`,
      projectDir,
      config
    );
    return applyFingerprints(raw, projectDir, fileManager);
  },
};
