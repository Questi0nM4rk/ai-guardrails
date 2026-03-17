import { resolve } from "node:path";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import { computeFingerprint } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";
import { safeParseJson } from "@/utils/parse";
import { resolveToolPath } from "@/utils/resolve-tool-path";

const BIOME_LINTER_ID = "biome";
const BIOME_RULE_PREFIX = "biome/";

// rdjson severity values from biome
const SEVERITY_ERROR = "ERROR";

interface RdjsonRange {
  // biome rdjson uses 1-based line/column (not the LSP 0-based line/character)
  start: { line: number; column: number };
  end: { line: number; column: number };
}

interface RdjsonDiagnostic {
  // location is absent for config-error diagnostics
  location?: {
    // biome rdjson emits path as a plain string (e.g. "src/main.ts")
    path?: string;
    range?: RdjsonRange;
  };
  severity: string;
  code?: { value: string };
  message: unknown; // may be string or object with content field
}

interface RdjsonOutput {
  diagnostics: RdjsonDiagnostic[];
}

function extractMessage(message: unknown): string {
  if (typeof message === "string") {
    return message;
  }
  if (
    typeof message === "object" &&
    message !== null &&
    "content" in message &&
    typeof (message as { content: unknown }).content === "string"
  ) {
    return (message as { content: string }).content;
  }
  return String(message);
}

function isRdjsonOutput(value: unknown): value is RdjsonOutput {
  return (
    typeof value === "object" &&
    value !== null &&
    "diagnostics" in value &&
    Array.isArray((value as RdjsonOutput).diagnostics)
  );
}

// biome emits ANSI reset codes before JSON output in TTY-like contexts.
// Build the regex via RegExp to avoid biome's noControlCharactersInRegex lint rule.
// The ESC character (U+001B) cannot appear as a literal in regex patterns per that rule.
const ANSI_RE = new RegExp(`${String.fromCharCode(27)}\\[[0-9;]*m`, "g");

export function parseBiomeRdjsonOutput(
  stdout: string,
  projectDir: string
): LintIssue[] {
  const parsed = safeParseJson(stdout.replace(ANSI_RE, ""));
  if (parsed === null) return [];

  if (!isRdjsonOutput(parsed)) {
    return [];
  }

  return parsed.diagnostics.flatMap((diag) => {
    // location is absent for config-error diagnostics (e.g. invalid biome.json)
    if (!diag.code || !diag.location?.path || !diag.location.range) return [];
    const filePath = resolve(projectDir, diag.location.path);
    // range.start.line and .column are already 1-based in biome's rdjson output
    const line = diag.location.range.start.line;
    const col = diag.location.range.start.column;
    const rule = BIOME_RULE_PREFIX + diag.code.value;
    const message = extractMessage(diag.message);
    const severity: "error" | "warning" =
      diag.severity === SEVERITY_ERROR ? "error" : "warning";
    const fingerprint = computeFingerprint({
      rule,
      file: filePath,
      lineContent: message,
      contextBefore: [],
      contextAfter: [],
    });
    return [
      {
        rule,
        linter: BIOME_LINTER_ID,
        file: filePath,
        line,
        col,
        message,
        severity,
        fingerprint,
      },
    ];
  });
}

export const biomeRunner: LinterRunner = {
  id: BIOME_LINTER_ID,
  name: "Biome",
  configFile: "biome.jsonc",
  installHint: {
    description: "TypeScript/JS linter and formatter",
    npm: "npm install -D @biomejs/biome",
  },

  async isAvailable(
    commandRunner: CommandRunner,
    projectDir?: string
  ): Promise<boolean> {
    return (await resolveToolPath("biome", projectDir ?? ".", commandRunner)) !== null;
  },

  async run({ projectDir, commandRunner }: RunOptions): Promise<LintIssue[]> {
    const cmd = (await resolveToolPath("biome", projectDir, commandRunner)) ?? "biome";
    const result = await commandRunner.run(
      [cmd, "ci", "--reporter=rdjson", projectDir],
      {
        cwd: projectDir,
      }
    );
    // biome exits non-zero when issues are found — parse stdout regardless
    return parseBiomeRdjsonOutput(result.stdout, projectDir);
  },
};
