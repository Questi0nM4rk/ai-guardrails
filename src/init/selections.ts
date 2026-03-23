import type { InitModule } from "@/init/types";

/**
 * Build a selections map from module defaults, honouring CLI `--no-X` disable flags.
 *
 * Each module may declare a `disableFlag` such as `"--no-ruff"`. Commander's negation
 * flag syntax strips the `--no-` prefix and stores the positive camelCase key with a
 * `false` value when the flag is supplied. For example, `--no-agent-hooks` causes
 * Commander to store `flags.agentHooks = false`.
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
    // Convert "--no-foo-bar" → "fooBar" (strip "--no-", then camelCase the rest).
    const camelKey = flagKey
      .replace(/^--no-/, "")
      .replace(/-([a-z])/g, (_: string, c: string) => c.toUpperCase());
    // Commander sets flags[camelKey] = false when --no-X is supplied.
    const disabled = flags[camelKey] === false;
    selections.set(mod.id, !disabled && mod.defaultEnabled);
  }
  return selections;
}
