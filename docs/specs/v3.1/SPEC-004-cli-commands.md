# SPEC-004: CLI Commands

## Status: Draft
## Version: 3.1
## Last Updated: 2026-03-20

---

## Problem

A multi-purpose tool with a pipeline-based architecture needs a consistent,
discoverable CLI surface. Every command must produce deterministic exit codes
so that CI pipelines, pre-commit hooks, and shell scripts can branch on
outcomes without parsing output text. Flags must map to pipeline behavior
without leaking implementation details to the user.

---

## Solution

A single binary — `ai-guardrails` — registered with Commander.js. All
subcommands delegate to a pipeline via a thin adapter. The adapter pattern
means command files contain no business logic: they build a `PipelineContext`
from global options and flags, run the pipeline, and map `PipelineResult` to
an exit code.

Global options (`--project-dir`, `--quiet`, `--no-color`) are declared on the
root program and accessed via `.optsWithGlobals()` or the `getProjectDir()`
helper. All commands share these options without redeclaring them.

---

## Philosophy

1. **Commands are thin adapters, not business logic containers.**
   WHY: If commands contain business logic, that logic cannot be tested without
   invoking the CLI. Pipelines are testable in isolation. Commands just wire them.

2. **Exit code semantics are contractual, not incidental.**
   WHY: CI pipelines branch on exit codes. `check` returning 1 for "issues found"
   vs 2 for "tool error" is a stable API contract. Changing it is a breaking change.

3. **Every command surfaces errors on stderr, success on stdout.**
   WHY: Machine consumers (CI, scripts) redirect stderr to a log and stdout to
   a pipe. Mixing them makes parsing impossible.

4. **Flags that control optional pipeline steps use `--no-*` negation.**
   WHY: Opt-in steps would require users to discover them. Opt-out steps work
   by default and are disabled explicitly — the safer default.

5. **The `hook` command is an internal dispatcher, not a user command.**
   WHY: Hooks are invoked by lefthook and Claude Code, not humans. The CLI
   exposes them through the same binary for simplicity, but their interface is
   defined by the caller, not the user.

---

## Constraints

### Hard Constraints

- All exit codes are defined in this spec and must not change without a
  version bump
- `--project-dir` defaults to `process.cwd()` and must be respected by every
  command
- Hook subcommands must read JSON from stdin (Claude Code protocol)
- `check` exit code 1 means lint issues found; exit code 2 means tool error
- `generate --check` must exit non-zero when any config fails validation

### Soft Constraints

- Prefer Commander.js `Option` with `.choices()` for constrained string flags
- Prefer early exit (`process.exit()`) over returning from async functions

### Assumptions

| Assumption | If Wrong | Action |
|------------|----------|--------|
| Commander.js `.optsWithGlobals()` merges parent options correctly | Commander API changes | Redeclare global options per command |
| `process.stdin.isTTY` reliably detects interactive mode | Bun changes TTY semantics | Add explicit `--interactive` flag (already exists as fallback) |
| Exit code 2 is universally understood as "tool/config error" | Shell convention differs | Document exit codes explicitly in `--help` output |

---

## 1. Commands

All commands are registered on the root `Command` instance from
`@commander-js/extra-typings`. Every command delegates to a pipeline or step
function — no business logic lives in command files.

| Command | Description | Pipeline/Step | Exit Codes |
|---------|-------------|---------------|------------|
| `install` | One-time machine setup | `installPipeline` | 0 = ok, 2 = error |
| `init` | Per-project setup | `initPipeline` | 0 = ok, 2 = error |
| `generate` | Regenerate all managed config files | `generatePipeline` | 0 = ok, 1 = error |
| `check` | Hold-the-line enforcement | `checkPipeline` | 0 = ok, 1 = issues, 2 = tool error |
| `snapshot` | Capture current lint state as baseline | `snapshotStep` | 0 = ok, 2 = error |
| `status` | Project health dashboard | `statusStep` | 0 = always (informational) |
| `report` | Show recent check run history | audit log reader | 0 = always (informational) |
| `allow` | Register a permanent per-glob rule exception | `allowStep` | 0 = ok, 2 = error |
| `query` | Inspect active allow entries for a rule | `queryStep` | 0 = always (informational) |
| `hook` | Internal hook dispatcher | `runHook` dispatcher | per-hook (see §5) |
| `branch` | Create a protected branch matching a configured pattern | `branchStep` | 0 = ok, 2 = error |
| `completion` | Generate shell completion script | completion generator | 0 = always |

### install

```
ai-guardrails install [--upgrade]
```

Runs `installPipeline`: detect languages, load config, generate configs,
validate configs, install hooks, set up CI, set up agent instructions.

Flags:

| Flag | Type | Default | Effect |
|------|------|---------|--------|
| `--upgrade` | boolean | false | Overwrite existing machine config files |

On pipeline error: writes `Error: <message>` to stderr, exits 2.

### init

```
ai-guardrails init [options]
```

Runs `initPipeline`: check existing config, prompt profile/ignore rules in
interactive mode, write `config.toml`, detect languages, check prerequisites,
install prerequisites, then delegates to `installPipeline`.

Flags:

| Flag | Type | Default | Effect |
|------|------|---------|--------|
| `--profile <profile>` | `strict\|standard\|minimal` | `standard` | Profile when non-interactive |
| `--force` | boolean | false | Overwrite existing `.ai-guardrails/config.toml` |
| `--upgrade` | boolean | false | Refresh generated files, preserve `config.toml` |
| `--no-hooks` | boolean | hooks on | Skip lefthook installation |
| `--no-ci` | boolean | CI on | Skip CI workflow generation |
| `--no-agent-rules` | boolean | agent rules on | Skip AGENTS.md and IDE rule files |
| `--interactive` | boolean | auto-detect TTY | Force interactive prompts even in non-TTY |
| `--config-strategy <strategy>` | `merge\|replace\|skip` | `merge` | How to handle existing language configs |

Interactive mode is active when `process.stdin.isTTY === true` or
`--interactive` is passed. Non-interactive mode uses `--profile` flag (default:
`standard`) and skips prompts.

Guard: if `config.toml` already exists and neither `--force` nor `--upgrade`
is passed, the pipeline returns an error immediately.

On pipeline error: writes `Error: <message>` to stderr, exits 2.

### generate

```
ai-guardrails generate [--check]
```

Without `--check`: detects languages, loads config, runs `generateConfigsStep`
with default strategy `merge`.

With `--check`: detects languages, loads config, runs `validateConfigsStep`
against all generators. Used in CI to assert configs are fresh and untampered.

Flags:

| Flag | Type | Default | Effect |
|------|------|---------|--------|
| `--check` | boolean | false | Validate mode: exit 1 if stale/tampered |

On pipeline error: writes `Error: <message>` to stderr, exits 1.

### check

```
ai-guardrails check [--baseline <path>] [--format <format>] [--strict]
```

Runs `checkPipeline`: detect languages, load config, run all applicable
linters, compare against baseline, report results.

Exit codes are differentiated within the error path:
- `issueCount > 0` → exit 1 (new issues found)
- `issueCount === 0` (tool/config error) → exit 2

Flags:

| Flag | Type | Default | Effect |
|------|------|---------|--------|
| `--baseline <path>` | string | `.ai-guardrails/baseline.json` | Custom baseline file path |
| `--format <format>` | `text\|sarif` | `text` | Output format |
| `--strict` | boolean | false | Ignore baseline — all issues are new |

On success: exits 0.

### snapshot

```
ai-guardrails snapshot [--baseline <path>]
```

Detects languages, loads config, runs all linters, writes current issue set
to baseline file. Does not fail on issues — the point is to capture the
current state.

Flags:

| Flag | Type | Default | Effect |
|------|------|---------|--------|
| `--baseline <path>` | string | `.ai-guardrails/baseline.json` | Custom output path |

On error: writes `Error: <message>` to stderr, exits 2.

### status

```
ai-guardrails status
```

Detects languages, loads config, runs `statusStep` which reports health
metrics: detected languages, config freshness, hook installation status,
baseline age. Never exits non-zero — purely informational.

No flags beyond globals.

### report

```
ai-guardrails report [--last <n>]
```

Reads `.ai-guardrails/audit.jsonl` (append-only JSONL, one record per `check`
run). Validates each line with Zod (`auditRecordSchema`). Skips malformed
lines. Displays the last N records.

Each record format: `<timestamp>  <status>  <newIssueCount> new, <issueCount> total`.

Flags:

| Flag | Type | Default | Effect |
|------|------|---------|--------|
| `--last <n>` | number | 10 | Number of recent runs to display |

If no audit log exists: prints info message, exits 0.

### hook

```
ai-guardrails hook <hook-name> [args...]
```

Internal dispatcher. Not intended for direct user invocation. Dispatches to
one of five hook implementations:

| hook-name | Implementation | Caller |
|-----------|----------------|--------|
| `dangerous-cmd` | `runDangerousCmd()` | Claude Code PreToolUse on Bash |
| `protect-configs` | `runProtectConfigs()` | Claude Code PreToolUse on Edit/Write/NotebookEdit |
| `protect-reads` | `runProtectReads()` | Claude Code PreToolUse on Read |
| `suppress-comments` | `runSuppressComments(args)` | lefthook pre-commit |
| `format-stage` | `runFormatStage()` | lefthook pre-commit |

Unknown hook names: writes error to stderr, exits 1.

`suppress-comments` receives staged file paths as positional `args`.
All other hooks receive no arguments (they read stdin for Claude Code hooks or
enumerate staged files internally).

### allow

```
ai-guardrails allow <rule> <glob> "<reason>"
```

Registers a permanent exception for `<rule>` on files matching `<glob>`.
Writes an `AllowEntry` to `.ai-guardrails/config.toml` under the `[[allow]]`
table array. Fails if the entry already exists (same rule + glob) unless
`--force` is passed.

Arguments:

| Argument | Description |
|----------|-------------|
| `<rule>` | Rule identifier: `linter/RULE_CODE` (e.g. `ruff/E501`) |
| `<glob>` | File glob pattern (e.g. `tests/**`, `src/generated/**`) |
| `<reason>` | Non-empty quoted string explaining the exception |

Flags:

| Flag | Type | Default | Effect |
|------|------|---------|--------|
| `--force` | boolean | false | Overwrite existing entry for the same rule + glob |

On success: prints `Allow registered: <rule> on <glob>`, exits 0.
On error (duplicate, invalid format, write failure): writes error to stderr, exits 2.

The entry is immediately active — `checkStep` and `snapshotStep` call
`config.isAllowed(rule, filePath)` which reads the updated config.

### query

```
ai-guardrails query <rule>
```

Reads `.ai-guardrails/config.toml` and prints all `[[allow]]` entries matching
`<rule>`. If `<rule>` contains no `/`, matches any rule with that suffix
(e.g. `query E501` matches `ruff/E501`). Output is human-readable text.

```
Rule: ruff/E501
  glob:   tests/**
  reason: Test fixtures use long lines for readability
  added:  2026-03-21
```

No flags beyond globals. Always exits 0 (informational).

### branch

```
ai-guardrails branch <name> [--from <base>] [--push] [--dry-run]
```

Creates a new Git branch whose name is guaranteed to match a protected pattern
from the repository ruleset created by `github-protected-patterns` during init.
If the name doesn't match any configured pattern, the command warns and asks
for confirmation before continuing.

**Why this command exists:** The GitHub Rulesets API protects branches
automatically when they're pushed — no re-running `init` needed. But
developers don't always know what patterns are active. Running
`ai-guardrails branch release/v2` creates the branch, validates the name
against known patterns, pushes it, and confirms the ruleset is enforcing.
This replaces the error-prone workflow of `git checkout -b`, pushing, then
manually checking GitHub settings.

**Pattern resolution:**

The command reads the active ruleset name `"ai-guardrails protected branches"`
via `gh api repos/{owner}/{repo}/rulesets` and extracts the `ref_name.include`
patterns. If no ruleset is found (init not run, or `--no-protected-patterns`
was used), the command warns and falls back to create the branch without
pattern validation.

**Name suggestion:**

If `<name>` is provided without a prefix and no pattern matches, the command
suggests the closest matching pattern:

```
"dev" does not match any protected pattern.
Protected patterns: release/*, hotfix/*, v*

Suggestions:
  release/dev
  hotfix/dev

Create as "release/dev"? [Y/n]
```

If `<name>` already matches a pattern, no prompt is shown.

**Flags:**

| Flag | Type | Default | Effect |
|------|------|---------|--------|
| `--from <base>` | string | current HEAD | Base branch/commit for the new branch |
| `--push` | boolean | true | Push to origin after creating locally |
| `--dry-run` | boolean | false | Print what would happen, make no changes |

**Execution steps:**

1. Read active rulesets from GitHub API (skip if not authenticated)
2. Validate `<name>` against extracted patterns
3. If no match: print warning + suggestion prompt
4. `git checkout -b <name> [--from <base>]`
5. If `--push`: `git push -u origin <name>`
6. If authenticated: verify ruleset is active on the pushed branch via
   `gh api repos/{owner}/{repo}/branches/<name>/protection`
7. Print confirmation: `Branch <name> created and protected by ruleset "ai-guardrails protected branches"`

**Exit codes:**

| Code | Meaning |
|------|---------|
| 0 | Branch created (and pushed if `--push`) |
| 2 | Git error, branch already exists, or user aborted name prompt |

**Example:**

```
$ ai-guardrails branch release/v2
✓ "release/v2" matches pattern release/*
✓ Branch created: release/v2
✓ Pushed to origin/release/v2
✓ Protected by ruleset: required PRs, CI, 1 review, no force-push
```

```
$ ai-guardrails branch dev
⚠ "dev" does not match any protected pattern.
  Protected patterns: release/*, hotfix/*, v*
  Suggestion: release/dev
Create as "release/dev"? [Y/n] y
✓ Branch created: release/dev
✓ Pushed to origin/release/dev
✓ Protected by ruleset: required PRs, CI, 1 review, no force-push
```

### completion

```
ai-guardrails completion <shell>
```

Generates a shell completion script for the specified shell.
Shell: `bash | zsh | fish`. Writes the script to stdout. Always exits 0.

Usage:

```sh
# bash
source <(ai-guardrails completion bash)

# zsh (add to .zshrc)
ai-guardrails completion zsh > "${fpath[1]}/_ai-guardrails"

# fish
ai-guardrails completion fish | source
```

The completion covers all subcommands, all flags, and choices for constrained
string flags (`--profile`, `--format`, `--config-strategy`).

> **Distribution note:** npm publish installs the completion script to
> `node_modules/.bin/ai-guardrails`. Users who install via npm can source
> completions the same way; the binary path is resolved via PATH.

---

## 2. Global Options

Declared on the root `Command` instance. Inherited by all subcommands via
Commander's option propagation.

| Option | Type | Default | Effect |
|--------|------|---------|--------|
| `--project-dir <dir>` | string | `process.cwd()` | Override working directory for all file I/O |
| `--quiet` | boolean | false | Suppress info/success output (stderr errors still shown) |
| `--no-color` | boolean | color on | Disable ANSI color codes in output |

The `getProjectDir()` helper reads `program.getOptionValue("projectDir")` and
falls back to `process.cwd()` if the value is not a string.

---

## 3. Flag Mapping

Flags are passed as `Record<string, unknown>` through `PipelineContext.flags`.
Pipelines access them with explicit type-narrowing:

```typescript
const force = ctx.flags.force === true;
const format: ReportFormat = ctx.flags.format === "sarif" ? "sarif" : "text";
const baseline = typeof ctx.flags.baseline === "string"
  ? ctx.flags.baseline
  : undefined;
```

Commander's `--no-*` negation flags arrive as the positive key set to `false`:
`--no-hooks` → `ctx.flags.hooks === false`, accessed as `ctx.flags.noHooks === true`
after Commander's camelCase transformation.

The `--config-strategy` flag is validated with `ConfigStrategySchema.safeParse()`
in the install pipeline. Invalid values produce a descriptive error:
`Invalid --config-strategy value "foo". Must be one of: merge, replace, skip.`

---

## 4. Exit Code Semantics

| Code | Meaning | Commands |
|------|---------|----------|
| 0 | Success, no issues | All commands |
| 1 | Lint issues found / generate validation failed | `check`, `generate` |
| 2 | Tool error, config error, hook deny | All commands, hook dispatcher |

The distinction between 1 and 2 in `check` is implemented in `commands/check.ts`:

```typescript
if (result.status === "error") {
  const issueCount = result.issueCount ?? 0;
  if (issueCount === 0) {
    process.stderr.write(`Error: ${result.message ?? "unknown error"}\n`);
    process.exit(2);
  }
  process.exit(1);
}
```

`issueCount > 0` means the pipeline completed successfully but found new
issues — `checkPipeline` populates `PipelineResult.issueCount` from
`newIssueCount` returned by `checkStep`.

`issueCount === 0` with status `"error"` means the pipeline itself failed
(tool not found, config parse error, etc.).

The `status` command and `report` command always exit 0 — they are
informational and must not block scripts.

---

## 5. PipelineContext Construction

Every command constructs a `PipelineContext` via `buildContext(projectDir, flags)`:

```typescript
export function buildContext(
  projectDir: string,
  flags: Record<string, unknown> = {}
): PipelineContext {
  const machine = MachineConfigSchema.parse({});
  const project = ProjectConfigSchema.parse({});
  const config = buildResolvedConfig(machine, project);

  return {
    projectDir,
    config,
    fileManager: new RealFileManager(),
    commandRunner: new RealCommandRunner(),
    console: new RealConsole(),
    flags,
    isTTY: process.stdin.isTTY === true,
    createReadline: () =>
      createInterface({ input: process.stdin, output: process.stdout }),
  };
}
```

The context provides real infrastructure implementations. Tests substitute
fakes (`FakeFileManager`, `FakeCommandRunner`, `FakeConsole`) by constructing
`PipelineContext` directly without going through `buildContext`.

---

## Testing Strategy

- Each command is tested via its pipeline, not the CLI adapter directly
- Exit code behavior is tested by asserting `process.exit` is called with the
  correct code in error scenarios
- Flag-to-pipeline mapping is tested by constructing `PipelineContext` with
  known flags and asserting downstream behavior
- The `hook` dispatcher is tested with each valid hook name and one unknown name
- Snapshot tests: none (commands produce no deterministic output)
- Coverage target: 85%+ on all command files

---

## Evolution

| Stable While | Revisit If | Impact |
|-------------|------------|--------|
| Commander.js is the CLI library | Switching to yargs or args | All command registrations, global options |
| Exit code 1/2 split in `check` | Adding more exit code distinctions | CI scripts, SPEC-000 MVP table |
| `PipelineContext` carries `flags: Record<string, unknown>` | Adding typed flag interfaces | All command-to-pipeline adapters |
| `hook` dispatches by string name | Adding hook config schemas | hook.ts dispatcher, hook implementations |
| `allow` writes to project config.toml | Allow entries need machine-level scope | Add machine allow support, update SPEC-002 |
| `completion` covers bash/zsh/fish | Adding PowerShell completion | Add `powershell` branch in completion generator |

---

## Cross-References

- SPEC-000: Overview — three-ring defense model, MVP scope
- SPEC-001: Architecture — `PipelineContext`, `Pipeline`, `PipelineResult` interfaces
- SPEC-002: Config System — `ConfigStrategy`, `ProjectConfigSchema`, `buildResolvedConfig`
- SPEC-005: Hook System — hook implementations invoked by the `hook` dispatcher
- SPEC-006: Config Generators — generators invoked by `generate` and `init`
- SPEC-008: Interactive Init — `github-protected-patterns` module that creates the ruleset `branch` reads
