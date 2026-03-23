# SPEC-005: Hook System

## Status: Draft
## Version: 3.1
## Last Updated: 2026-03-20

---

## Problem

AI coding agents execute shell commands, edit files, and read sensitive paths.
No runtime gating exists at the tool-call level — an agent can run
`git push --force`, overwrite `biome.jsonc`, or read `.env` and the developer
only finds out after the fact.

Pre-commit hooks catch many issues but they run after the agent has already
done the damage. The gap between "agent acts" and "pre-commit runs" is where
dangerous changes slip through: a force push has no staged files to check.

Additionally, inline lint suppressions (`// @ts-ignore`, `# noqa`) are agent
escape hatches inserted at write time. Pre-commit must detect them before the
commit lands.

---

## Solution

Two complementary layers:

**Layer 1 — Claude Code PreToolUse hooks:** Three hooks registered in
`.claude/settings.json` intercept tool calls before execution. The hook binary
reads a JSON payload from stdin, evaluates it against a rule set compiled from
the project's `.ai-guardrails/config.toml`, and writes a decision JSON to
stdout (allow/ask) or exits 2 (deny).

**Layer 2 — lefthook pre-commit hooks:** Two hooks run at `git commit` time.
`format-stage` auto-formats staged files and re-stages them. `suppress-comments`
scans staged files for inline linter suppressions using a two-pass AST-aware
scanner.

The rule engine (`src/check/`) is shared by Layer 1 hooks. It parses shell
commands into an AST using `@questi0nm4rk/shell-ast` and applies typed rule
objects. Rule groups are modular and user-disableable via `config.toml`.

---

## Philosophy

1. **AST-based command parsing, not string matching.**
   WHY: String matching produces false positives and false negatives. `rm -rf`
   and `rm -r -f` are the same command — a string match treats them differently.
   An AST parser understands flag equivalence, flag expansion, and shell quoting.

2. **Rules are typed objects, not regex strings.**
   WHY: A `CallRule` with `cmd`, `flags`, `noFlags`, `sub`, and `hasDdash` fields
   encodes intent explicitly. A regex encodes implementation. Typed rules are
   reviewable, testable, and composable.

3. **Inline suppressions must have a reason or they are blocked.**
   WHY: Bare `# noqa` is an escape hatch with no accountability. The
   `ai-guardrails-allow: rule "reason"` syntax forces a justification that is
   visible in code review and searchable in the codebase.

4. **Hook input is validated at the Zod boundary.**
   WHY: Claude Code controls the JSON shape. If the API changes, the Zod schema
   catches the mismatch immediately at parse time rather than producing undefined
   behavior in rule evaluation.

5. **Rule groups are independently disableable.**
   WHY: Some teams have legitimate uses for `git reset --hard` in scripts. Forcing
   a deny is paternalistic. The right model is configurable, not hardcoded.

6. **The binary existence guard prevents hook failure on unconfigured repos.**
   WHY: `.claude/settings.json` is committed to the repo. If someone clones the
   repo without building the binary, hooks should silently pass rather than
   blocking all tool use with a confusing error.

---

## Constraints

### Hard Constraints

- Claude Code PreToolUse hooks must write decision JSON to stdout and exit 0
  (allow/ask) or exit 2 (deny) — never exit 1
- Stdin must be read fully before any processing (streaming partial reads
  would produce invalid JSON)
- The check engine must not throw — parse failures default to `allow`
- `MAX_RECURSE_DEPTH = 5` for inline script recursion (bash -c / eval chains)
- `suppress-comments` receives file paths as CLI args, not stdin

### Soft Constraints

- Prefer `@questi0nm4rk/shell-ast` over manual shell tokenization
- Flag alias groups must be defined once; bidirectional maps are derived
- Suppressions patterns must be language-specific, not generic regexes

### Assumptions

| Assumption | If Wrong | Action |
|------------|----------|--------|
| Claude Code PreToolUse sends full JSON payload before closing stdin | Streaming protocol added | Switch to line-based JSON reading |
| `@questi0nm4rk/shell-ast` covers POSIX shell plus bash extensions | Parser gaps | Add fallback allow on parse failure (already implemented) |
| `-n` is not aliased globally because it means different things per subcommand | git changes flag semantics | Add sub-scoped explicit rules |
| `[ ! -f ./dist/ai-guardrails ] && exit 0` guard works in all shells | Exotic shell in hook env | Test guard in dash and busybox sh |

---

## 1. Hook Types

Five hooks are registered and dispatched through `ai-guardrails hook <name>`.

| Hook | Trigger | Caller | Input | Decision |
|------|---------|--------|-------|----------|
| `dangerous-cmd` | PreToolUse: Bash | Claude Code | stdin JSON (tool_input.command) | allow/ask/deny |
| `protect-configs` | PreToolUse: Edit, Write, NotebookEdit | Claude Code | stdin JSON (tool_input.file_path) | allow/ask |
| `protect-reads` | PreToolUse: Read | Claude Code | stdin JSON (tool_input.file_path) | allow/ask |
| `suppress-comments` | pre-commit | lefthook | CLI args (staged file paths) | exit 0/1 |
| `format-stage` | pre-commit | lefthook | none (reads git staged files) | exit 0/1 |

### Hook Input Protocol (Claude Code hooks)

Claude Code writes a JSON payload to the hook's stdin:

```typescript
export interface HookInput {
  session_id: string;
  transcript_path: string;
  cwd: string;
  hook_event_name: "PreToolUse" | "PostToolUse" | "Notification" | "Stop" | string;
  tool_name: string;
  tool_input: Record<string, unknown>;
}
```

`readHookInput()` in `src/hooks/runner.ts` reads stdin fully, parses JSON,
and validates with Zod. On parse failure or schema mismatch: writes error to
stderr, exits 2.

### Hook Output Protocol (Claude Code hooks)

The `toHookOutput(result, label)` function in `src/check/output.ts` translates
a `CheckResult` to the wire protocol:

```typescript
export function toHookOutput(result: CheckResult, label: string): never {
  if (result.decision === "allow") {
    process.exit(0);
  }
  if (result.decision === "ask") {
    process.stdout.write(
      JSON.stringify({
        permissionDecision: "ask",
        reason: `[${label}] ${result.reason}`,
      })
    );
    process.exit(0);
  }
  process.stderr.write(`[${label}] ${result.reason}\n`);
  process.exit(2);
}
```

- `allow` → exit 0, no stdout
- `ask` → JSON to stdout with `permissionDecision: "ask"`, exit 0
- `deny` → reason to stderr, exit 2

### dangerous-cmd

Reads `tool_input.command`, calls `isDangerous(command)`. If the check engine
returns a non-null `CheckResult`, calls `toHookOutput`. If the engine returns
null (allow), exits 0.

Covers: Bash tool calls only. File-write redirects (`cmd > .env`) are also
caught here via `checkRedirectsAgainstPathRules`.

### protect-configs

Handles `Edit`, `Write`, `NotebookEdit` tool names only. Ignores `Bash` (that
is `dangerous-cmd`'s domain). Extracts the path from `tool_input.file_path`,
`tool_input.notebook_path`, or `tool_input.path` (in priority order). Evaluates
with `event.type = "write"` against path rules.

Decision is always allow or ask — never deny. User can proceed after
confirmation.

### protect-reads

Handles `Read` tool name only. Extracts `tool_input.file_path`. Evaluates with
`event.type = "read"` against path rules.

Protected read paths (`.env`, `.ssh/`, `.gnupg/`) trigger ask, not deny —
reads are less destructive than writes.

### suppress-comments

Receives staged file paths as positional CLI arguments (passed by lefthook as
`{staged_files}`). For each file: reads content, calls `scanFile()`, collects
`Finding[]`. Writes all findings to stderr and exits 1 if any are found.

Exits 0 if no files, no matching extensions, or all patterns match lines with
valid `ai-guardrails-allow` annotations.

### format-stage

Reads staged file paths from `git diff --cached --name-only`. For each
formatter glob, filters matching files, runs the formatter binary via
`spawnSync`. On success, re-stages formatted files with `git add`. On formatter
failure, writes a descriptive error to stderr but does not exit 1 (the commit
proceeds with unformatted files rather than blocking).

Formatters:

| Glob | Command |
|------|---------|
| `**/*.py` | `ruff format` |
| `**/*.{ts,tsx,js,jsx}` | `biome format --write` |
| `**/*.rs` | `rustfmt` |
| `**/*.go` | `gofmt -w` |
| `**/*.lua` | `stylua` |
| `**/*.{c,cpp,cc,h,hpp}` | `clang-format -i` |

---

## 2. Check Engine

The check engine in `src/check/engine.ts` evaluates a `ToolEvent` against a
`RuleSet` and returns a `CheckResult`.

```typescript
export type ToolEvent =
  | { type: "bash"; command: string }
  | { type: "write"; path: string }
  | { type: "read"; path: string };

export type CheckResult =
  | { decision: "allow" }
  | { decision: "ask"; reason: string }
  | { decision: "deny"; reason: string };
```

`evaluate(event, ruleset)` dispatches:
- `bash` events → `evaluateCommand()`
- `write` / `read` events → `evaluatePath()`

### evaluateCommand()

1. Parse the command string with `@questi0nm4rk/shell-ast`. On parse failure:
   return `{ decision: "allow" }`.
2. Check all `redirect` rules via `hasWriteRedirect()`.
3. Check redirect targets against path rules via `checkRedirectsAgainstPathRules()`.
4. Check pipe patterns via `findPipeViolations()`.
5. Extract all `CallExprNode[]` with `findCalls()`.
6. Check tee/cp/mv/sed-i argument destinations via `checkWriteArgCommands()`.
7. For each call: unwrap with `unwrapCall()`, expand flags with `expandFlags()`.
   - If `recurse` rule is active and command is an inline shell (`bash`, `sh`,
     `dash`, `zsh`, `ksh`, `eval`, `exec`): extract inline script,
     recurse up to `MAX_RECURSE_DEPTH = 5`.
   - Match `call` rules: check `cmd`, `sub`, `flags`, `noFlags`, `args`, `hasDdash`.
8. Return `{ decision: "allow" }` if no rule matches.

### evaluatePath()

Iterates path rules in order. Returns the first rule whose `pattern.test(path)`
is true and whose `event` matches (`"write"`, `"read"`, or `"both"`). Returns
`{ decision: "allow" }` if no rule matches.

---

## 3. Rule Groups

Six rule groups are registered in `ALL_RULE_GROUPS` (ordered by precedence):

| ID | Name | Rule Type | Patterns |
|----|------|-----------|----------|
| `destructive-rm` | Destructive rm | CallRule | `rm` with `--recursive` + `--force` flags |
| `git-force-push` | Git force push | CallRule | `git push` with `--force` but not `--force-with-lease` |
| `git-destructive` | Git destructive operations | CallRule | `git reset --hard`, `git checkout --`, `git restore --`, `git clean --force`, `git branch -D` |
| `git-bypass-hooks` | Git bypass hooks | CallRule | `git commit --no-verify`, `git commit -n` |
| `chmod-world-writable` | Chmod world-writable | CallRule | `chmod -R 777`, `chmod -R a+rwx` |
| `remote-code-exec` | Remote code execution | PipeRule | `curl\|wget` piped into any shell |

Every group has a `denyGlobs` array used to populate `.claude/settings.json`
`permissions.deny` — these are Claude Code's static deny patterns, a first-layer
safety net independent of the hook engine's AST evaluation.

Groups are disabled via `config.toml` `[hooks] disabled_groups = ["git-force-push"]`.
The `recurseRule` is always active (injected by `buildRuleSet`) regardless of
disabled groups.

### Default Path Rules

Path rules are defined in `src/check/rules/paths.ts`:

| Pattern | Event | Decision | Reason |
|---------|-------|----------|--------|
| `\.(env|env\.\w+)$` | both | ask | `.env` file (contains secrets) |
| `/\.ssh/` | read | ask | SSH directory |
| `/\.gnupg/` | read | ask | GPG directory |
| `biome\.jsonc?$` | write | ask | biome config (managed) |
| `\.claude/settings(\.local)?\.json$` | write | ask | Claude settings |
| `\.(github\|gitlab)/(workflows\|ci)/` | write | ask | CI pipeline config |
| `package\.json$` | write | ask | package.json |
| `Cargo\.toml$` | write | ask | Cargo.toml |
| `pyproject\.toml$` | write | ask | pyproject.toml |
| `tsconfig(\.\w+)?\.json$` | write | ask | tsconfig |

Additionally, `DEFAULT_MANAGED_FILES` adds `protectWrite` rules for common tool
config files (`.gitignore`, `.eslintrc*`, `.prettierrc*`, `lefthook.yml`).

User-configured paths from `config.toml` `[hooks]` section are appended after
defaults:
- `managed_files` → `protectWrite` per-filename rules
- `managed_paths` → `protectWrite` per-path rules
- `protected_read_paths` → `protectRead` per-path rules

All pattern strings are run through `escapeRegExp()` before constructing
`RegExp` objects to prevent ReDoS from user-provided path strings.

---

## 4. Flag Alias System

Flag aliases are defined in `src/check/flag-aliases.ts` as `FLAG_GROUPS`:

```typescript
const FLAG_GROUPS: readonly (readonly string[])[] = [
  ["-r", "--recursive", "-R"],
  ["-f", "--force"],
  ["-d", "--delete"],
];
```

A bidirectional alias map is derived at module load time. `expandFlags(flags)`
applies both compound expansions and alias closure:

- `FLAG_EXPANSIONS`: compound flags → multiple canonical flags. Example:
  `-D` → `["--delete", "--force"]`
- `FLAG_ALIASES`: bidirectional equivalence. Example: `-r` → `["--recursive", "-R"]`

`hasFlag(expanded, wanted)` checks whether a wanted flag appears in the
expanded set, using `startsWith` to match parameterized forms like
`--force-with-lease=refspec`.

`-n` is explicitly excluded from alias groups. It means `--no-verify` for
`git commit`, `--dry-run` for `git push`, and `--no-checkout` for `git clone`.
Commands requiring `-n` matching use explicit sub-scoped rules.

---

## 5. Suppress-Comments Scanner

`scanFile(filePath, content)` in `src/hooks/suppress-comments.ts` implements
a two-pass scanner:

**Pass 1:** Language-specific pattern matching. Maps file extension to language,
then tests each line against `SUPPRESSION_PATTERNS[lang]`. Patterns are exact
match against the full line text.

Supported languages and their suppression patterns:

| Language | Extensions | Patterns |
|----------|-----------|---------|
| python | `.py` | `# noqa`, `# type: ignore`, `# pragma: no cover`, `# pylint: disable` |
| typescript | `.ts`, `.tsx`, `.js`, `.jsx` | `// @ts-ignore`, `// @ts-nocheck`, `eslint-disable`, `/* tslint:disable`, `nosemgrep` |
| rust | `.rs` | `#[allow(`, `#![allow(` |
| go | `.go` | `//nolint`, `// nolint` |
| csharp | `.cs` | `#pragma warning disable`, `[SuppressMessage` |
| lua | `.lua` | `-- luacheck: ignore`, `-- luacheck: disable` |
| shell | `.sh`, `.bash`, `.zsh`, `.ksh` | `# shellcheck disable` |
| cpp | `.c`, `.cpp`, `.cc`, `.h`, `.hpp` | `// NOLINT`, `#pragma diagnostic ignored`, `#pragma GCC diagnostic ignored` |

**Pass 2:** Generic keyword scanner on the comment portion only.
`extractComment(line, lang)` extracts the comment text using language-aware
comment markers (handles `//`, `/* */`, `#`, `--`). The generic pattern
`\b(nolint|nocheck|nosemgrep|NOLINT|pragma ignore)\b` is tested against the
extracted comment only — not the full line — to avoid false positives from
code like `const NOLINT_MAP = {}`.

**Allow annotations:** Before scanning, `parseAllowComments(lines)` extracts
all `ai-guardrails-allow:` annotations. Lines with valid annotations are
excluded from both passes.

```typescript
export interface AllowComment {
  rule: string;
  reason: string;
  line: number; // 1-indexed
}
```

Allow pattern: `(?:#|\/\/|--)[ \t]*ai-guardrails-allow:[ \t]*([\w/-]+)[ \t]+"([^"]+)"`.
Both rule ID and quoted reason are required — annotations without a quoted
reason are not recognized and will be flagged if they also contain a
suppression keyword.

---

## Testing Strategy

- Unit tests for `evaluate()` cover each rule type: call, pipe, redirect, recurse, path
- Unit tests for `expandFlags()` verify alias closure, compound expansion, and `hasFlag()`
- Unit tests for `scanFile()` use fixture files with known suppression patterns
- Unit tests for `parseAllowComments()` verify the allow pattern parser
- Unit tests for `extractComment()` cover each language's comment marker
- `readHookInput()` is tested with valid JSON, invalid JSON, and wrong schema
- `toHookOutput()` is tested for each decision variant
- Integration: `runDangerousCmd()` / `runProtectConfigs()` / `runProtectReads()` tested
  with fake stdin injection
- `runFormatStage()` tested with `FakeCommandRunner`-equivalent spawnSync substitution
- Coverage target: 85%+ on all check/ and hooks/ modules

---

## Evolution

| Stable While | Revisit If | Impact |
|-------------|------------|--------|
| `@questi0nm4rk/shell-ast` is the AST library | Replacing with mvdan/sh bindings | evaluateCommand(), all engine-helpers |
| Six rule groups are the full set | Adding new rule categories | groups.ts, ALL_RULE_GROUPS, claude-settings generator |
| Flag alias groups cover `-r/-f/-d` | New flags need aliasing | flag-aliases.ts, FLAG_GROUPS |
| `ai-guardrails-allow` is the allow syntax | Changing allow annotation format | allow-comment.ts, suppress-comments.ts |
| Claude Code PreToolUse JSON schema | Claude Code API version change | runner.ts Zod schema, types.ts interfaces |
| All decisions default to `ask` (not `deny`) | Switching to deny-first policy | All hook output calls, toHookOutput() |

---

## Cross-References

- SPEC-000: Overview — three-ring defense model, philosophy principles 1-5
- SPEC-001: Architecture — `PipelineContext`, infra injection, composition model
- SPEC-002: Config System — `HooksConfig`, `ProjectConfigSchema` `[hooks]` section
- SPEC-004: CLI Commands — `hook` dispatcher, command registration
- SPEC-006: Config Generators — `claudeSettingsGenerator` emits deny globs and hook registrations
