# Phase 4 — Hook Rewrites + protect-reads

## Deliverables

Rewrite `src/hooks/dangerous-cmd.ts`, `src/hooks/protect-configs.ts`,
add `src/hooks/runner.ts` `ask()` function, and create new `src/hooks/protect-reads.ts`.

## `src/hooks/runner.ts` — add `ask()`

Current `runner.ts` has `allow()` and `deny()`. Add:

```typescript
export function ask(reason: string): never {
  process.stdout.write(JSON.stringify({ permissionDecision: "ask", reason }));
  process.exit(0);
}
```

Note: `toHookOutput` in `output.ts` handles this internally, but `ask()` in runner.ts
allows direct use from hooks that don't go through the engine (e.g. format-stage, allow-comment).

## `src/hooks/dangerous-cmd.ts` — rewrite

```typescript
import { evaluate } from "@/check/engine";
import { toHookOutput } from "@/check/output";
import { buildRuleSet, loadHookConfig } from "@/check/ruleset";
import { allow } from "@/hooks/runner";
import { readHookInput, extractBashCommand } from "@/hooks/types";

export async function isDangerous(command: string): Promise<string | null> {
  const config = await loadHookConfig();
  const ruleset = buildRuleSet(config);
  const result = await evaluate({ type: "bash", command }, ruleset);
  if (result.decision === "allow") return null;
  return result.reason;
}

export async function runDangerousCmd(): Promise<never> {
  const input = await readHookInput();
  const command = extractBashCommand(input.tool_input);
  const config = await loadHookConfig();
  const ruleset = buildRuleSet(config);
  const result = await evaluate({ type: "bash", command }, ruleset);
  toHookOutput(result, "dangerous-cmd");
}
```

## `src/hooks/protect-configs.ts` — fix + rewrite

**Current bug**: The hook extracts `file_path` from `tool_input` but then runs the regex
against the Bash command rather than the path. Edit/Write events are never actually
checked against `file_path`.

**Rewrite**:

```typescript
import { evaluate } from "@/check/engine";
import { toHookOutput } from "@/check/output";
import { buildRuleSet, loadHookConfig } from "@/check/ruleset";
import { readHookInput } from "@/hooks/types";

export async function runProtectConfigs(): Promise<never> {
  const input = await readHookInput();
  const toolName = input.tool_name;

  if (toolName === "Bash") {
    // Bash tool — check command for redirect-based writes to config files
    const command = input.tool_input.command as string;
    const config = await loadHookConfig();
    const ruleset = buildRuleSet(config);
    const result = await evaluate({ type: "bash", command }, ruleset);
    toHookOutput(result, "protect-configs");
  }

  if (toolName === "Edit" || toolName === "Write" || toolName === "NotebookEdit") {
    // File write tool — check file_path directly
    const path = (input.tool_input.file_path ?? input.tool_input.path ?? "") as string;
    const config = await loadHookConfig();
    const ruleset = buildRuleSet(config);
    const result = await evaluate({ type: "write", path }, ruleset);
    toHookOutput(result, "protect-configs");
  }

  // Unknown tool — allow
  process.exit(0);
}
```

## `src/hooks/protect-reads.ts` — new hook

```typescript
import { evaluate } from "@/check/engine";
import { toHookOutput } from "@/check/output";
import { buildRuleSet, loadHookConfig } from "@/check/ruleset";
import { readHookInput } from "@/hooks/types";

export async function runProtectReads(): Promise<never> {
  const input = await readHookInput();
  const toolName = input.tool_name;

  if (toolName === "Read") {
    const path = (input.tool_input.file_path ?? "") as string;
    const config = await loadHookConfig();
    const ruleset = buildRuleSet(config);
    const result = await evaluate({ type: "read", path }, ruleset);
    toHookOutput(result, "protect-reads");
  }

  process.exit(0);
}
```

## Entry Points

Add `protect-reads` to `src/cli.ts` hook subcommands:

```typescript
hookCmd
  .command("protect-reads")
  .description("PreToolUse hook: ask before reading sensitive files")
  .action(() => void runProtectReads());
```

## Tests

`tests/hooks/protect-configs.test.ts`:

- Edit event with `.env` path → ask
- Write event with `biome.jsonc` path → ask
- Write event with `src/main.ts` → allow
- Bash with redirect to `.env` (`cat secret > .env`) → ask
- Bash with safe command → allow

`tests/hooks/protect-reads.test.ts`:

- Read event with `.ssh/id_rsa` path → ask
- Read event with `README.md` → allow

`tests/hooks/dangerous-cmd.test.ts` — update to use new engine (same inputs, same expected results):

- `rm -rf /path` → not null (ask)
- `git push --force-with-lease` → null (allow)
- All 42 existing tests pass

## Acceptance Criteria

- [ ] `protect-configs.ts` checks `file_path` for Edit/Write events
- [ ] `protect-reads.ts` exists and is wired to CLI
- [ ] `ask()` added to `runner.ts`
- [ ] All hook tests pass
- [ ] `bun run typecheck` passes
- [ ] `shell-quote` removed; `dangerous-patterns.ts` deleted or updated (no remaining import sites)
