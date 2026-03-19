import { relative, resolve } from "node:path";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import { computeFingerprint } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";

const CLANG_TIDY_PATTERN =
  /^(.+):(\d+):(\d+):\s+(warning|error|note):\s+(.+?)\s+\[(.+)\]$/;

/**
 * Parse clang-tidy text output into LintIssue[].
 * Skips note-level diagnostics — only warning and error are actionable.
 *
 * projectDir is used to compute a project-relative path for the fingerprint.
 * LintIssue.file remains the absolute path emitted by clang-tidy.
 */
export function parseClangTidyOutput(text: string, projectDir: string): LintIssue[] {
  const issues: LintIssue[] = [];

  for (const line of text.split("\n")) {
    const match = CLANG_TIDY_PATTERN.exec(line);
    if (!match) continue;

    const level = match[4] ?? "";
    if (level === "note") continue;

    const rawFile = match[1] ?? "";
    const file = resolve(projectDir, rawFile);
    const lineNum = Number.parseInt(match[2] ?? "0", 10);
    const col = Number.parseInt(match[3] ?? "0", 10);
    const message = match[5] ?? "";
    const checkName = match[6] ?? "";
    const rule = `clang-tidy/${checkName}`;

    // rawFile is an absolute path from clang-tidy; make it relative for portable fingerprints
    const relFile = relative(projectDir, file);
    const fingerprint = computeFingerprint({
      rule,
      file: relFile,
      lineContent: message,
      contextBefore: [],
      contextAfter: [],
    });

    issues.push({
      rule,
      linter: "clang-tidy",
      file,
      line: lineNum,
      col,
      message,
      severity: level === "error" ? "error" : "warning",
      fingerprint,
    });
  }

  return issues;
}

const C_CPP_GLOBS = ["**/*.cpp", "**/*.c", "**/*.cxx", "**/*.cc", "**/*.h", "**/*.hpp"];

async function findCppFiles(
  fileManager: RunOptions["fileManager"],
  projectDir: string
): Promise<string[]> {
  const results = await Promise.all(
    C_CPP_GLOBS.map((g) => fileManager.glob(g, projectDir))
  );
  const seen = new Set<string>();
  const files: string[] = [];
  for (const batch of results) {
    for (const f of batch) {
      if (!seen.has(f)) {
        seen.add(f);
        files.push(f);
      }
    }
  }
  return files;
}

export const clangTidyRunner: LinterRunner = {
  id: "clang-tidy",
  name: "clang-tidy",
  configFile: ".clang-tidy",
  installHint: {
    description: "C/C++ linter",
    brew: "brew install llvm",
    apt: "sudo apt install clang-tidy",
  },

  async isAvailable(commandRunner: CommandRunner): Promise<boolean> {
    const result = await commandRunner.run(["clang-tidy", "--version"]);
    return result.exitCode === 0;
  },

  async run(opts: RunOptions): Promise<LintIssue[]> {
    const { projectDir, commandRunner, fileManager } = opts;
    const files = await findCppFiles(fileManager, projectDir);
    if (files.length === 0) return [];

    const result = await commandRunner.run(["clang-tidy", "--quiet", ...files], {
      cwd: projectDir,
    });
    return parseClangTidyOutput(result.stderr, projectDir);
  },
};
