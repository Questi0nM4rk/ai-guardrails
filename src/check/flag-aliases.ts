/**
 * Flag alias mappings for common CLI tools.
 * Maps short flags to their canonical long forms so rules only need to
 * match one variant.  The engine normalises flags before rule matching.
 */

interface FlagAliasMap {
  readonly [shortFlag: string]: string; // short → long canonical
}

/** Per-command alias tables — only commands whose rules use flag variants. */
const FLAG_ALIASES: Readonly<Record<string, FlagAliasMap>> = {
  rm: { "-r": "--recursive", "-f": "--force" },
  chmod: { "-R": "--recursive" },
  git: {
    "-f": "--force",
    "-n": "--no-verify",
    "-d": "--delete",
    "-D": "--delete --force",
  },
} as const;

/**
 * Normalise a flag list by expanding known short aliases to their
 * canonical long forms.  Unknown flags pass through unchanged.
 */
export function normaliseFlags(cmd: string, flags: readonly string[]): string[] {
  const aliases = FLAG_ALIASES[cmd];
  if (aliases === undefined) return [...flags];

  const result: string[] = [];
  for (const flag of flags) {
    const expanded = aliases[flag];
    if (expanded !== undefined) {
      // An alias may expand to multiple flags (e.g. -D → --delete --force)
      for (const f of expanded.split(" ")) {
        result.push(f);
      }
    } else {
      result.push(flag);
    }
  }
  return result;
}
