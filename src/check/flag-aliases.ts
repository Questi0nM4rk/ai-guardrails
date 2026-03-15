/**
 * Flag alias resolution for command rules.
 *
 * Alias groups define equivalent flag forms (e.g. ["-r", "--recursive", "-R"]).
 * The bidirectional lookup map is derived automatically — adding a new alias
 * only requires editing a single group, not every permutation.
 *
 * Note: `-n` is intentionally excluded. It means `--no-verify` for `git commit`
 * but `--dry-run` for `git push` and `--no-checkout` for `git clone`. Commands
 * that need `-n` matching should use explicit rules with `sub` scoping.
 *
 * FLAG_EXPANSIONS maps compound short flags (like -D) to the flags they imply.
 */

/**
 * Each array lists all equivalent forms of the same flag.
 * The bidirectional alias map is computed from these groups.
 */
const FLAG_GROUPS: readonly (readonly string[])[] = [
  ["-r", "--recursive", "-R"],
  ["-f", "--force"],
  ["-d", "--delete"],
];

/** Derived bidirectional alias map from FLAG_GROUPS. */
const FLAG_ALIASES: ReadonlyMap<string, readonly string[]> = (() => {
  const map = new Map<string, string[]>();
  for (const group of FLAG_GROUPS) {
    for (const flag of group) {
      map.set(
        flag,
        group.filter((f) => f !== flag)
      );
    }
  }
  return map;
})();

/** Compound flag expansions: one flag expands to multiple canonical flags. */
const FLAG_EXPANSIONS: ReadonlyMap<string, readonly string[]> = new Map([
  ["-D", ["--delete", "--force"]],
]);

/**
 * Expand a list of flags by applying FLAG_EXPANSIONS and FLAG_ALIASES.
 * The result contains every original flag (including compound flags like `-D`)
 * plus their expansions and all alias equivalents, with full transitivity
 * through the alias graph.
 */
export function expandFlags(flags: readonly string[]): string[] {
  const result = new Set<string>();

  for (const flag of flags) {
    result.add(flag);

    const expansion = FLAG_EXPANSIONS.get(flag);
    if (expansion !== undefined) {
      for (const f of expansion) {
        result.add(f);
      }
    }
  }

  // Add aliases — iterate until no new entries
  let prevSize = 0;
  while (result.size !== prevSize) {
    prevSize = result.size;
    for (const flag of [...result]) {
      const aliases = FLAG_ALIASES.get(flag);
      if (aliases !== undefined) {
        for (const alias of aliases) {
          result.add(alias);
        }
      }
    }
  }

  return [...result];
}

/**
 * Check whether a wanted flag is present in a list of expanded flags.
 * Uses startsWith to handle parameterized forms like --force-with-lease=refspec.
 *
 * **Precondition:** compound flags (e.g. `-D`) must be pre-expanded via `expandFlags`
 * before passing to this function.
 */
export function hasFlag(expanded: readonly string[], wanted: string): boolean {
  return expanded.some((f) => f === wanted || f.startsWith(`${wanted}=`));
}
