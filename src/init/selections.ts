import type { InitModule } from "@/init/types";

/**
 * Build a selections map from module defaults, honouring CLI `--no-X` disable flags.
 *
 * Each module may declare a `disableFlag` such as `"--no-ruff"`. Commander converts
 * these to camelCase flags (e.g. `noRuff`). If the flag is `true` the module is
 * disabled regardless of its `defaultEnabled` value.
 */
export function applyFlagDisables(
  modules: readonly InitModule[],
  flags: Record<string, unknown>
): Map<string, boolean> {
  const selections = new Map<string, boolean>();
  for (const mod of modules) {
    const flagKey = mod.disableFlag;
    if (flagKey === undefined) {
      selections.set(mod.id, mod.defaultEnabled);
      continue;
    }
    // Convert "--no-foo-bar" → "noFooBar" for Commander flag lookup.
    const camelKey = flagKey
      .replace(/^--/, "")
      .replace(/-([a-z])/g, (_: string, c: string) => c.toUpperCase());
    const disabled = flags[camelKey] === true;
    selections.set(mod.id, !disabled && mod.defaultEnabled);
  }
  return selections;
}
