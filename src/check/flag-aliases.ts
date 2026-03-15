/**
 * Flag alias resolution for command rules.
 *
 * FLAG_ALIASES maps a canonical flag to its short/long equivalents.
 * FLAG_EXPANSIONS maps compound short flags (like -D) to the flags they imply.
 *
 * hasFlag() checks whether a wanted flag is present among expanded flags,
 * accounting for aliases. expandFlags() normalizes a flag list by adding
 * alias-equivalent forms.
 */

/** Maps each flag to its aliases (bi-directional). */
const FLAG_ALIASES: ReadonlyMap<string, readonly string[]> = new Map([
  ["-r", ["--recursive"]],
  ["--recursive", ["-r", "-R"]],
  ["-R", ["--recursive"]],
  ["-f", ["--force"]],
  ["--force", ["-f"]],
  ["-d", ["--delete"]],
  ["--delete", ["-d"]],
  ["-n", ["--no-verify"]],
  ["--no-verify", ["-n"]],
]);

/** Maps compound flags to the canonical flags they expand into. */
const FLAG_EXPANSIONS: ReadonlyMap<string, readonly string[]> = new Map([
  ["-D", ["--delete", "--force"]],
]);

/**
 * Expand a list of flags by applying FLAG_EXPANSIONS and FLAG_ALIASES.
 * The result contains every original flag plus all alias equivalents.
 */
export function expandFlags(flags: readonly string[]): string[] {
  const result = new Set<string>();

  for (const flag of flags) {
    result.add(flag);

    // Expand compound flags (e.g. -D -> --delete, --force)
    const expansion = FLAG_EXPANSIONS.get(flag);
    if (expansion !== undefined) {
      for (const f of expansion) {
        result.add(f);
      }
    }
  }

  // Now add aliases for everything in the set (iterate over a snapshot)
  const snapshot = [...result];
  for (const flag of snapshot) {
    const aliases = FLAG_ALIASES.get(flag);
    if (aliases !== undefined) {
      for (const alias of aliases) {
        result.add(alias);
      }
    }
  }

  return [...result];
}

/**
 * Check whether a wanted flag is present in a list of expanded flags.
 * Uses startsWith to handle parameterized forms like --force-with-lease=refspec.
 */
export function hasFlag(expanded: readonly string[], wanted: string): boolean {
  return expanded.some((f) => f === wanted || f.startsWith(`${wanted}=`));
}
