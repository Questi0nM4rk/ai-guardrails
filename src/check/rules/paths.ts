import { protectRead, protectWrite } from "@/check/builder-path";
import type { PathRule } from "@/check/types";

export const DEFAULT_MANAGED_FILES: string[] = [
  ".env",
  ".env.local",
  ".env.production",
  ".env.staging",
  ".env.development",
  "biome.jsonc",
  ".gitignore",
  ".eslintrc",
  ".eslintrc.js",
  ".eslintrc.json",
  ".prettier*",
  "tsconfig.json",
  "tsconfig.*.json",
  "package.json",
  "Cargo.toml",
  "pyproject.toml",
  "lefthook.yml",
  ".claude/settings.json",
  ".claude/settings.local.json",
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
];
