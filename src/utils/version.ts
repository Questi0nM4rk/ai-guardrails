import pkg from "../../package.json";

/**
 * Compare two semver strings (X.Y.Z only). Returns true if a < b.
 *
 * Only handles strict X.Y.Z — no pre-release, no build metadata, no calver.
 * The Zod regex /^\d+\.\d+\.\d+$/ on config.toml enforces this at parse time.
 * Missing parts default to 0 via ?? 0, so "3.1" (if it somehow passes
 * validation) is treated as "3.1.0".
 *
 * We roll our own instead of importing `semver` npm package because:
 * - The comparison is 6 lines, not worth a dependency
 * - We explicitly reject pre-release (semver package would parse it)
 * - The Zod schema is the primary validator — this is just a comparator
 */
export function semverLt(a: string, b: string): boolean {
  const pa = a.split(".").map(Number);
  const pb = b.split(".").map(Number);
  for (let i = 0; i < 3; i++) {
    if ((pa[i] ?? 0) < (pb[i] ?? 0)) return true;
    if ((pa[i] ?? 0) > (pb[i] ?? 0)) return false;
  }
  return false;
}

/**
 * Get the installed ai-guardrails version from package.json.
 * Bun embeds this at compile time.
 */
export function getVersion(): string {
  return pkg.version;
}
