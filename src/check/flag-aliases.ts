/**
 * Flag alias resolution for the check engine.
 *
 * Eliminates rule duplication by mapping short/long flag variants
 * (e.g., `-r` <-> `--recursive`) so rules only need one canonical form.
 */

/** Bidirectional alias map: each flag lists its equivalent forms. */
const FLAG_ALIASES: ReadonlyMap<string, readonly string[]> = new Map([
  ["-r", ["--recursive", "-R"]],
  ["--recursive", ["-r", "-R"]],
  ["-R", ["--recursive", "-r"]],
  ["-f", ["--force"]],
  ["--force", ["-f"]],
  ["-d", ["--delete"]],
  ["--delete", ["-d"]],
  ["-n", ["--no-verify"]],
  ["--no-verify", ["-n"]],
]);

/** Multi-flag expansions: compound short flags that expand to multiple flags. */
const FLAG_EXPANSIONS: ReadonlyMap<string, readonly string[]> = new Map([
  ["-D", ["--delete", "--force"]], // git branch -D
]);

/**
 * Returns true if `flags` contains `wanted` or any alias of `wanted`.
 * Handles parameterized flags: `--force-with-lease=refspec` matches `--force-with-lease`.
 */
export function hasFlag(flags: readonly string[], wanted: string): boolean {
  const candidates = new Set<string>([wanted]);
  const aliases = FLAG_ALIASES.get(wanted);
  if (aliases !== undefined) {
    for (const a of aliases) {
      candidates.add(a);
    }
  }

  return flags.some((flag) => {
    if (candidates.has(flag)) return true;
    // Parameterized form: --flag=value matches --flag
    for (const candidate of candidates) {
      if (candidate.startsWith("--") && flag.startsWith(`${candidate}=`)) {
        return true;
      }
    }
    return false;
  });
}

/**
 * Expands compound flags via FLAG_EXPANSIONS (e.g., `-D` -> `["--delete", "--force"]`).
 * Non-expansion flags pass through unchanged.
 */
export function expandFlags(flags: readonly string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const flag of flags) {
    const expansion = FLAG_EXPANSIONS.get(flag);
    const items = expansion !== undefined ? expansion : [flag];
    for (const item of items) {
      if (!seen.has(item)) {
        seen.add(item);
        result.push(item);
      }
    }
  }
  return result;
}
