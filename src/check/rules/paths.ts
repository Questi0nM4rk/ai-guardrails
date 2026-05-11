import type { HookModule, Rule } from "@questi0nm4rk/hook-kit";
import { createModule, path, redirect } from "@questi0nm4rk/hook-kit";

const LABEL = "[ai-guardrails]";

interface ProtectedPath {
  pattern: RegExp;
  event: "write" | "read";
  reason: string;
}

const PROTECTED_PATHS: readonly ProtectedPath[] = [
  {
    pattern: /\.(env|env\.\w+)$/,
    event: "write",
    reason: "Writing to .env file (contains secrets)",
  },
  {
    pattern: /\.(env|env\.\w+)$/,
    event: "read",
    reason: "Reading .env file (contains secrets)",
  },
  { pattern: /\/\.ssh\//, event: "read", reason: "Reading SSH directory" },
  { pattern: /\/\.gnupg\//, event: "read", reason: "Reading GPG directory" },
  {
    pattern: /biome\.jsonc?$/,
    event: "write",
    reason: "Writing to biome config (managed by ai-guardrails)",
  },
  {
    pattern: /\.claude\/settings(\.local)?\.json$/,
    event: "write",
    reason: "Writing to Claude settings",
  },
  {
    pattern: /\.(github|gitlab)\/(workflows|ci)\//,
    event: "write",
    reason: "Writing to CI pipeline config",
  },
  { pattern: /package\.json$/, event: "write", reason: "Writing to package.json" },
  { pattern: /Cargo\.toml$/, event: "write", reason: "Writing to Cargo.toml" },
  { pattern: /pyproject\.toml$/, event: "write", reason: "Writing to pyproject.toml" },
  { pattern: /tsconfig(\.\w+)?\.json$/, event: "write", reason: "Writing to tsconfig" },
];

// Exact filenames added as additional write protections by ruleset.ts.
// Files already covered by PROTECTED_PATHS are omitted to avoid duplicates.
export const DEFAULT_MANAGED_FILES: readonly string[] = [
  ".gitignore",
  ".eslintrc",
  ".eslintrc.js",
  ".eslintrc.json",
  ".prettierrc",
  ".prettierrc.js",
  ".prettierrc.cjs",
  ".prettierrc.json",
  ".prettierrc.yaml",
  ".prettierrc.yml",
  ".prettierignore",
  "lefthook.yml",
];

function toRules(paths: readonly ProtectedPath[], event: "write" | "read"): Rule[] {
  return paths
    .filter((p) => p.event === event)
    .map((p) =>
      event === "write"
        ? path(p.pattern).onWrite().escalate(p.reason, LABEL)
        : path(p.pattern).onRead().escalate(p.reason, LABEL)
    );
}

function toRedirectRules(paths: readonly ProtectedPath[]): Rule[] {
  return paths
    .filter((p) => p.event === "write")
    .map((p) => redirect(p.pattern).escalate(p.reason, LABEL));
}

export const defaultWriteModule: HookModule = createModule(
  {
    id: "ai-guardrails-paths-write",
    name: "ai-guardrails write protection",
    events: ["PreToolUse"],
    matchers: ["Edit", "Write", "NotebookEdit"],
  },
  toRules(PROTECTED_PATHS, "write")
);

export const defaultReadModule: HookModule = createModule(
  {
    id: "ai-guardrails-paths-read",
    name: "ai-guardrails read protection",
    events: ["PreToolUse"],
    matchers: ["Read"],
  },
  toRules(PROTECTED_PATHS, "read")
);

export const defaultRedirectModule: HookModule = createModule(
  {
    id: "ai-guardrails-redirects",
    name: "ai-guardrails Bash redirect protection",
    events: ["PreToolUse"],
    matchers: ["Bash"],
  },
  toRedirectRules(PROTECTED_PATHS)
);
