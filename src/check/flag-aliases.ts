/**
 * Flag alias resolution for the check engine.
 *
 * Eliminates rule duplication by mapping short/long flag variants
 * (e.g., `-r` <-> `--recursive`) so rules only need one canonical form.
 */

/**
 * Alias groups: each array lists all equivalent forms of the same flag.
 * The bidirectional lookup map is derived automatically — adding a new
 * alias only requires editing a single group, not every permutation.
 */
const FLAG_GROUPS: readonly (readonly string[])[] = [
  ["-r", "--recursive", "-R"],
  ["-f", "--force"],
  ["-d", "--delete"],
  ["-n", "--no-verify"],
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
  ["-D", ["--delete", "--force"]], // git branch -D
]);

/**
 * Returns true if `flags` contains `wanted` or any alias of `wanted`.
 * Handles parameterized flags: `--force-with-lease=refspec` matches `--force-with-lease`.
 *
 * **Precondition:** compound flags (e.g. `-D`) must be pre-expanded via `expandFlags`
 * before passing to this function. Without expansion, compound flags are not matched
 * against their constituent parts.
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
 * Non-expansion flags pass through unchanged. Deduplicates the result.
 *
 * Call this before `hasFlag` to ensure compound flags are resolved.
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
