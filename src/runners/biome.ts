import { resolve } from "node:path";
import type { ResolvedConfig } from "@/config/schema";
import type { CommandRunner } from "@/infra/command-runner";
import type { LintIssue } from "@/models/lint-issue";
import { computeFingerprint } from "@/models/lint-issue";
import type { LinterRunner, RunOptions } from "@/runners/types";

const BIOME_LINTER_ID = "biome";
const BIOME_RULE_PREFIX = "biome/";

// rdjson severity values from biome
const SEVERITY_ERROR = "ERROR";

interface RdjsonRange {
  start: { line: number; character: number };
  end: { line: number; character: number };
}

interface RdjsonDiagnostic {
  location: {
    path: { text: string };
    range: RdjsonRange;
  };
  severity: string;
  code: { value: string };
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

export function parseBiomeRdjsonOutput(stdout: string, projectDir: string): LintIssue[] {
  let parsed: unknown;
  try {
    parsed = JSON.parse(stdout);
  } catch {
    return [];
  }

  if (!isRdjsonOutput(parsed)) {
    return [];
  }

  return parsed.diagnostics.map((diag) => {
    const filePath = resolve(projectDir, diag.location.path.text);
    const line = diag.location.range.start.line + 1;
    const col = diag.location.range.start.character + 1;
    const rule = BIOME_RULE_PREFIX + diag.code.value;
    const message = extractMessage(diag.message);
    const severity: "error" | "warning" = diag.severity === SEVERITY_ERROR ? "error" : "warning";
    const fingerprint = computeFingerprint({
      rule,
      file: filePath,
      lineContent: message,
      contextBefore: [],
      contextAfter: [],
    });
    return {
      rule,
      linter: BIOME_LINTER_ID,
      file: filePath,
      line,
      col,
      message,
      severity,
      fingerprint,
    };
  });
}

const BIOME_CONFIG_TEMPLATE: string = JSON.stringify(
  {
    $schema: "https://biomejs.dev/schemas/2.3.15/schema.json",
    organizeImports: { enabled: true },
    linter: {
      enabled: true,
      rules: {
        recommended: true,
        correctness: {
          noUnusedVariables: "error",
          noUnusedImports: "error",
        },
        style: {
          noVar: "error",
          useConst: "error",
          useTemplate: "error",
        },
        suspicious: {
          noExplicitAny: "error",
          noConsole: "warn",
        },
      },
    },
    formatter: {
      enabled: true,
      indentStyle: "space",
      indentWidth: 2,
      lineWidth: 100,
    },
    javascript: {
      formatter: {
        quoteStyle: "double",
        trailingCommas: "es5",
      },
    },
  },
  null,
  2,
);

export const biomeRunner: LinterRunner = {
  id: BIOME_LINTER_ID,
  name: "Biome",
  configFile: "biome.json",
  installHint: {
    description: "TypeScript/JS linter and formatter",
    npm: "npm install -D @biomejs/biome",
  },

  async isAvailable(commandRunner: CommandRunner): Promise<boolean> {
    const result = await commandRunner.run(["biome", "--version"]);
    return result.exitCode === 0;
  },

  async run({ projectDir, commandRunner }: RunOptions): Promise<LintIssue[]> {
    const result = await commandRunner.run(["biome", "ci", "--reporter=rdjson", projectDir], {
      cwd: projectDir,
    });
    // biome exits non-zero when issues are found — parse stdout regardless
    return parseBiomeRdjsonOutput(result.stdout, projectDir);
  },

  generateConfig(_config: ResolvedConfig): string {
    return BIOME_CONFIG_TEMPLATE;
  },
};
