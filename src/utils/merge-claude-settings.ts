export interface HookEntry {
  readonly type: string;
  readonly command: string;
}

export interface PreToolUseEntry {
  readonly matcher: string;
  readonly hooks: readonly HookEntry[];
}

interface MutablePreToolUseEntry {
  readonly matcher: string;
  hooks: HookEntry[];
}

interface ClaudeSettingsHooks {
  readonly PreToolUse?: readonly PreToolUseEntry[];
  readonly [key: string]: unknown;
}

export interface ClaudeSettings {
  readonly permissions?: { readonly deny?: string[] };
  readonly hooks?: ClaudeSettingsHooks;
  readonly [key: string]: unknown;
}

/**
 * Merge ai-guardrails hooks into an existing settings object.
 * Preserves all existing entries. Adds hooks only if not already present.
 * Deduplicates by matching on the hook command string.
 */
export function mergeHooks(
  existing: ClaudeSettings,
  guardrailsHooks: readonly PreToolUseEntry[]
): ClaudeSettings {
  // Build a mutable working copy so we can accumulate merges.
  const workingPTU: MutablePreToolUseEntry[] = (existing.hooks?.PreToolUse ?? []).map(
    (e) => ({ matcher: e.matcher, hooks: [...e.hooks] })
  );

  for (const entry of guardrailsHooks) {
    const existingMatcher = workingPTU.find((e) => e.matcher === entry.matcher);
    if (existingMatcher !== undefined) {
      const existingCommands = new Set(existingMatcher.hooks.map((h) => h.command));
      for (const hook of entry.hooks) {
        if (!existingCommands.has(hook.command)) {
          existingMatcher.hooks.push(hook);
          existingCommands.add(hook.command);
        }
      }
    } else {
      workingPTU.push({ matcher: entry.matcher, hooks: [...entry.hooks] });
    }
  }

  return {
    ...existing,
    hooks: { ...existing.hooks, PreToolUse: workingPTU },
  };
}
