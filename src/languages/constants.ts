/** Directories excluded from glob-based language detection (always applied) */
export const DEFAULT_IGNORE: readonly string[] = [
  "node_modules/**",
  ".venv/**",
  "venv/**",
  "vendor/**",
  "dist/**",
  "build/**",
  "target/**",
  ".git/**",
  "__pycache__/**",
];
