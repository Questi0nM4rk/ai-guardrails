import { resolve } from "node:path";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";
import { applyFingerprints } from "@/utils/apply-fingerprints";
import { parseNdjson } from "@/utils/ndjson";

interface ClippySpan {
  file_name: string;
  line_start: number;
  column_start: number;
  is_primary: boolean;
}

interface ClippyMessage {
  code: { code: string } | null;
  level: string;
  message: string;
  spans: ClippySpan[];
}

interface ClippyEntry {
  reason: string;
  message?: ClippyMessage;
}

function isClippyEntry(value: unknown): value is ClippyEntry {
  return (
    typeof value === "object" &&
    value !== null &&
    "reason" in value &&
    typeof value.reason === "string"
  );
}

/**
 * Parse clippy NDJSON output into raw issues without fingerprints.
 * Filters build artifacts — only keeps compiler-message entries with non-null code.
 */
export function parseClippyNdjson(
  ndjson: string,
  projectDir: string
): Omit<LintIssue, "fingerprint">[] {
  const entries = parseNdjson(ndjson);
  const issues: Omit<LintIssue, "fingerprint">[] = [];

  for (const entry of entries) {
    if (!isClippyEntry(entry)) continue;
    if (entry.reason !== "compiler-message") continue;

    const msg = entry.message;
    if (!msg) continue;
    if (msg.code === null) continue;
    if (!msg.spans) continue;

    const primarySpan = msg.spans.find((s) => s.is_primary);
    if (!primarySpan) continue;

    const rule = `clippy/${msg.code.code}`;
    const file = resolve(projectDir, primarySpan.file_name);

    issues.push({
      rule,
      linter: "clippy",
      file,
      line: primarySpan.line_start,
      col: primarySpan.column_start,
      message: msg.message,
      severity: msg.level === "error" ? "error" : "warning",
    });
  }

  return issues;
}

export const clippyRunner: LinterRunner = {
  id: "clippy",
  name: "Clippy",
  configFile: null,
  installHint: {
    description: "Rust linter",
    rustup: "rustup component add clippy",
  },

  async isAvailable(commandRunner: CommandRunner): Promise<boolean> {
    const result = await commandRunner.run(["cargo", "clippy", "--version"]);
    return result.exitCode === 0;
  },

  async run(opts: RunOptions): Promise<LintIssue[]> {
    const { projectDir, commandRunner, fileManager } = opts;
    const result = await commandRunner.run(
      ["cargo", "clippy", "--message-format=json", "--", "-D", "warnings"],
      { cwd: projectDir }
    );
    const raw = parseClippyNdjson(result.stdout, projectDir);
    return applyFingerprints(raw, projectDir, fileManager);
  },
};
