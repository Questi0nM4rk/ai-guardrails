import { protectRead, protectWrite } from "@/check/builder-path";
import type { PathRule } from "@/check/types";

// Exact filenames only — no globs. Wildcard patterns belong in DEFAULT_PATH_RULES as regex.
// Files already covered by DEFAULT_PATH_RULES are omitted to avoid duplicate rules.
export const DEFAULT_MANAGED_FILES: string[] = [
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

export const DEFAULT_PATH_RULES: PathRule[] = [
  protectWrite(/\.(env|env\.\w+)$/, "Writing to .env file (contains secrets)"),
  protectRead(/\.(env|env\.\w+)$/, "Reading .env file (contains secrets)"),
  protectRead(/\/\.ssh\//, "Reading SSH directory"),
  protectRead(/\/\.gnupg\//, "Reading GPG directory"),
  protectWrite(/biome\.jsonc?$/, "Writing to biome config (managed by ai-guardrails)"),
  protectWrite(/\.claude\/settings(\.local)?\.json$/, "Writing to Claude settings"),
  protectWrite(/\.(github|gitlab)\/(workflows|ci)\//, "Writing to CI pipeline config"),
  protectWrite(/package\.json$/, "Writing to package.json"),
  protectWrite(/Cargo\.toml$/, "Writing to Cargo.toml"),
  protectWrite(/pyproject\.toml$/, "Writing to pyproject.toml"),
  protectWrite(/tsconfig(\.\w+)?\.json$/, "Writing to tsconfig"),
];
