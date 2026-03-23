# SPEC-008: Interactive Init

## Status: Draft — NOT YET IMPLEMENTED
## Version: 3.1
## Last Updated: 2026-03-20
## Depends on: SPEC-000 (Overview), SPEC-001 (Architecture), SPEC-002 (Config), SPEC-004 (CLI Commands), SPEC-006 (Config Generators)

> **This spec describes a planned feature. No code in `src/init/` exists yet.**
> The current `src/pipelines/init.ts` is the monolithic implementation this
> spec replaces. See the Migration Path section for backward-compat guarantees.

---

## Problem

`ai-guardrails init` is monolithic. It runs everything or nothing. The only
customization available today is profile selection and ignore rules. Users
cannot selectively configure which generators run, which universal configs
are installed, or skip components they don't need.

Specifically:

- A TypeScript-only project does not want `ruff.toml` generated (Python config)
- A project already using Prettier does not want `.editorconfig` overwriting its settings
- A team not using Claude Code does not want `.claude/settings.json` created
- A project using GitLab CI, not GitHub Actions, gets a GitHub workflow it will never use
- There is no way to capture an initial baseline as part of init

Adding a new init feature today means modifying `init.ts` or `install.ts`
directly — monolithic files that are hard to test in isolation. Feature flags
accumulate as boolean guards inside a single execution path.

---

## Solution

Replace the monolithic init/install pipeline with a modular system where every
action is an **InitModule**. Each module is self-contained: it declares its
category, whether it's applicable to the project, its default state, and how
to execute. The interactive wizard iterates over applicable modules grouped
by category and prompts for each one. Non-interactive mode (`--yes`) accepts
all defaults without prompting.

The module system is additive. Adding a new init feature means adding one file
in `src/init/modules/` and one line in the registry. No other files change.

---

## Philosophy

1. **One concern per module.** Each `InitModule` does exactly one thing. It
   generates one config file, installs one hook system, or sets up one CI provider.
   WHY: Monolithic functions fail partially and leave the project in an undefined
   state. A module-per-concern makes partial failure recoverable — the failed
   module is reported, others succeed.

2. **Detect before prompt.** Modules that are not applicable to the project are
   never shown in the wizard. The wizard does not ask about Python configs in a
   TypeScript project.
   WHY: Irrelevant prompts erode trust in the wizard. If users see options they
   don't understand, they will skip the wizard entirely and use `--yes`. The
   wizard should only surface decisions that matter for this project.

3. **Defaults that are always right.** Every module has `defaultEnabled: true`
   or `false`. The defaults are chosen so that `--yes` (accept all defaults)
   produces a sensible, complete setup for any project type.
   WHY: Most users will hit Enter for most prompts. Defaults represent the
   "recommended by the tool" choice. Defaults that require manual correction
   are UX failures.

4. **Topology enforced, not documented.** Module dependencies are declared in
   `dependsOn` and enforced by topological sort in the runner. A module cannot
   execute before its dependencies.
   WHY: If dependency order is only documented, it will be violated by future
   modules. The runner enforces the order structurally — declaring a dependency
   is sufficient, no human needs to remember the execution order.

5. **Backward compatibility is non-negotiable.** `--yes` must produce identical
   output to the current `init` command. Every existing `--no-X` flag must still
   work. No existing CI pipeline that calls `ai-guardrails init --yes` should
   break.
   WHY: Tooling that breaks existing workflows gets ripped out. Backward compat
   is a social contract with all existing adopters.

6. **Under 30 seconds, end to end.** The interactive wizard — from launch to
   "Done!" — must complete within 30 seconds of user input on a standard laptop
   with a warm network. Each module runs only what it needs; the baseline
   module is the only step that touches the network (prerequisite installs).
   Non-interactive mode (`--yes`) must complete in under 10 seconds.
   WHY: A setup wizard that takes minutes gets abandoned halfway through. Speed
   is a UX requirement, not a nice-to-have.

7. **Per-file conflict detection before overwrite.** Before any module writes a
   file, it checks whether that file already exists. If it does, the module
   prompts once per file: `"biome.jsonc exists. Merge? [Y/n]"`. The default
   (`Y`) merges the guardrails config into the existing file without losing
   user customization. The user can also choose `n` (skip this file) or is
   offered `r` (replace entirely) only if `--force` is active.
   WHY: Silently overwriting user config is the fastest way to lose trust.
   Per-file prompts give users control over each generated file individually,
   without requiring them to know the `--config-strategy` flag in advance.

6. **Existing generators and steps are not replaced.** Modules wrap them. The
   `src/generators/` and `src/steps/` directories are stable. Only the
   orchestration layer changes.
   WHY: Generators are well-tested, battle-tested, and snapshot-tested. Rewriting
   them to fit a new architecture is unnecessary risk. The module interface is
   an orchestration boundary, not a reimplementation boundary.

---

## Constraints

### Hard Constraints

- No new `src/init/` code exists until implementation starts — this spec is design only
- `--yes` produces output identical to current `ai-guardrails init` behavior
- Each `--no-X` flag disables exactly one module
- Modules may not import from other modules (only from generators and steps)
- Module `id` values are stable after shipping — they are CLI-facing identifiers
- `dependsOn` references must be resolvable in `ALL_INIT_MODULES` at startup
- The runner uses topological sort — circular `dependsOn` chains are a startup error
- Total interactive wizard time must not exceed 30 seconds (excluding user think time)
- Non-interactive (`--yes`) must complete in under 10 seconds
- Every module that writes a file must check for existence and prompt before overwrite
  (format: `"<filename> exists. Merge? [Y/n]"`, default Y = merge)

### Soft Constraints

- Prefer readline-based prompts over third-party prompt libraries
- Module `execute()` returns `InitModuleResult`, never throws
- Wizard groups modules by category in the display order defined in this spec
- Each module file stays under 200 lines
- Conflict resolution prompt uses three options: Merge (Y), Skip (n), Replace (r, only with --force)

### Assumptions

| Assumption | If Wrong | Action |
|------------|----------|--------|
| Node readline is sufficient for wizard prompts | Windows terminal incompatibility | Evaluate `enquirer` or `@inquirer/prompts` as readline wrapper |
| 13 modules covers all init scenarios | New init feature does not fit any module | Add a new module file and category if needed, update this spec — 13 is correct for v3.1 |
| Topological sort is sufficient for dependency management | Circular dependencies introduced by future module | Detect cycle at startup, fail with clear error listing the cycle |
| `--yes` flag is the right backward-compat path | Some CI pipelines use flags incompatible with `--yes` | Audit all known usages, add alias if needed |
| Generators stay stable during implementation | Generator signature changes | Update module wrappers, not the generators themselves |

---

## 1. InitModule Interface

```typescript
// src/init/types.ts

interface InitModule {
  /** Stable identifier used for selections and CLI flags. Never change after shipping. */
  readonly id: string;

  /** Human-readable name shown in wizard prompts */
  readonly name: string;

  /** One-line description shown in prompts */
  readonly description: string;

  /** Category for grouping in the wizard */
  readonly category: InitCategory;

  /** Default state when user hits Enter (or --yes) */
  readonly defaultEnabled: boolean;

  /** CLI flag that disables this module (e.g., "--no-hooks") */
  readonly disableFlag?: string;

  /** Other module IDs that must execute before this one */
  readonly dependsOn?: readonly string[];

  /** Check if this module is applicable to the project */
  detect(ctx: InitContext): Promise<boolean>;

  /** Execute the module's action */
  execute(ctx: InitContext): Promise<InitModuleResult>;
}

type InitCategory =
  | "profile"           // profile selection, config tuning
  | "language-config"   // ruff.toml, biome.jsonc
  | "universal-config"  // .editorconfig, .markdownlint.jsonc, .codespellrc
  | "hooks"             // lefthook, claude-settings
  | "agent"             // agent-rules, tool-specific symlinks
  | "ci"                // GitHub Actions, GitLab CI
  | "tools"             // per-tool installation prompts
  | "baseline";         // initial snapshot

interface InitModuleResult {
  status: "ok" | "skipped" | "error";
  message: string;
  filesCreated?: readonly string[];
  filesModified?: readonly string[];
}

interface InitContext {
  projectDir: string;
  fileManager: FileManager;
  commandRunner: CommandRunner;
  console: Console;
  config: ResolvedConfig;
  languages: LanguagePlugin[];
  selections: Map<string, boolean>;  // module ID → enabled
  isTTY: boolean;
  createReadline: () => ReadlineInterface;
  flags: Record<string, unknown>;
}
```

---

## 2. Module Registry

All modules are registered in a flat array. Order within the array determines
display order within a category.

```typescript
// src/init/registry.ts

export const ALL_INIT_MODULES: readonly InitModule[] = [
  profileSelectionModule,    // profile
  configTuningModule,        // profile
  ruffConfigModule,          // language-config
  biomeConfigModule,         // language-config
  editorconfigModule,        // universal-config
  markdownlintConfigModule,  // universal-config
  codespellConfigModule,     // universal-config
  lefthookModule,            // hooks
  claudeSettingsModule,      // hooks
  agentRulesModule,          // agent
  githubActionsModule,       // ci
  toolInstallModule,         // tools
  baselineModule,            // baseline
];
```

### Module Specifications (13 modules)

| Module ID | Category | detect() | defaultEnabled | disableFlag | dependsOn |
|-----------|----------|----------|----------------|-------------|-----------|
| `profile-selection` | `profile` | always true | true | — | none |
| `config-tuning` | `profile` | always true | true | — | `profile-selection` |
| `ruff-config` | `language-config` | Python detected | true | `--no-ruff` | `config-tuning` |
| `biome-config` | `language-config` | TypeScript detected | true | `--no-biome` | `config-tuning` |
| `editorconfig` | `universal-config` | always true | true | `--no-editorconfig` | `config-tuning` |
| `markdownlint-config` | `universal-config` | always true | true | `--no-markdownlint` | `config-tuning` |
| `codespell-config` | `universal-config` | always true | true | `--no-codespell` | `config-tuning` |
| `lefthook` | `hooks` | always true | true | `--no-hooks` | `config-tuning` |
| `claude-settings` | `hooks` | always true | true | `--no-agent-hooks` | `config-tuning` |
| `agent-rules` | `agent` | any AI tool detected | true | `--no-agent-rules` | none |
| `github-actions` | `ci` | `.git` directory exists | true | `--no-ci` | none |
| `tool-install` | `tools` | any runner missing | true | — | `profile-selection` |
| `baseline` | `baseline` | always true | true | `--no-baseline` | all config modules + `tool-install` |

### Module Details

**profile-selection**: Prompts for strict / standard / minimal (default: standard).
Writes `.ai-guardrails/config.toml`. All other modules that generate configs
depend on this running first so `config.profile` is set.

**config-tuning**: Prompts for `line_length` (60–200, default: 88),
`indent_width` (2 or 4, default: 2), rules to ignore (comma-separated),
and paths to exclude (comma-separated). Updates the config file written by
`profile-selection`.

**ruff-config**: Calls `ruffGenerator.generate(config)` → writes `ruff.toml`.
Respects `configStrategy` (merge / replace / skip).

**biome-config**: Detects biome version via `getBiomeVersion()` and `noConsole`
level via `detectNoConsoleLevel()`. Calls `biomeGenerator.generate(config)` →
writes `biome.jsonc`.

**editorconfig**, **markdownlint-config**, **codespell-config**: Call the
corresponding generator → write the config file.

**lefthook**: Generates `lefthook.yml` then runs `lefthook install` via
`commandRunner`.

**claude-settings**: Generates `.claude/settings.json` with PreToolUse hooks
pointing at the binary.

**agent-rules**: Detects AI tool markers (`.claude/`, `.cursor/`, `.codeium/`,
`.github/copilot-instructions.md`, `.clinerules`). Calls `setupAgentInstructionsStep`.

**github-actions**: Checks for `.git/` directory. Calls `setupCiStep` →
writes `.github/workflows/ai-guardrails.yml`.

**tool-install**: Runs `checkPrerequisites` to find missing tools. For each
missing tool, prompts Y/N with the install command. Runs approved installs.
In non-interactive mode, installs all missing tools if platform supports it.

**baseline**: Runs the full linter collection (same as `snapshotStep`). Writes
`.ai-guardrails/baseline.json`. Reports count: "Baseline: N issues captured."
This must be the last module to execute so all configs are in place.

---

## 3. Wizard Flow

### Category Display Order

```
1. profile          → "Profile & Config"
2. language-config  → "Language Configs"
3. universal-config → "Universal Configs"
4. hooks            → "Pre-commit & Agent Hooks"
5. agent            → "Agent Instructions"
6. ci               → "CI Pipeline"
7. tools            → "Tool Installation"
8. baseline         → "Baseline"
```

### Prompt Helpers (src/init/prompt.ts)

```typescript
async function askYesNo(
  rl: ReadlineInterface,
  question: string,
  defaultYes: boolean
): Promise<boolean>

async function askChoice<T extends string>(
  rl: ReadlineInterface,
  question: string,
  choices: readonly T[],
  defaultChoice: T
): Promise<T>

async function askText(
  rl: ReadlineInterface,
  question: string,
  defaultValue: string
): Promise<string>

async function askCommaSeparated(
  rl: ReadlineInterface,
  question: string
): Promise<string[]>

/** Per-file conflict prompt. Returns "merge" | "skip" | "replace".
 *  "replace" is only offered if force === true. */
async function askFileConflict(
  rl: ReadlineInterface,
  filename: string,
  force: boolean
): Promise<"merge" | "skip" | "replace">
```

`askFileConflict` prompts: `"<filename> exists. Merge? [Y/n]"` in standard
mode; `"<filename> exists. [M]erge / [s]kip / [r]eplace:"` when `force` is
true. Default is always merge. Modules call this before calling any generator
`generate()` method when the output file already exists.

### Example Wizard Session

```
AI Guardrails Setup
═══════════════════

Detected: TypeScript, Python
Tools: Claude Code, Cursor

── Profile & Config ──────────────────────
? Enforcement profile [strict/standard/minimal]: standard
? Line length (60-200): 88
? Indent width [2/4]: 2
? Rules to ignore (comma-separated):
? Paths to exclude (comma-separated):

── Language Configs ──────────────────────
? Generate ruff.toml (Python)?              [Y/n]
? Generate biome.jsonc (TypeScript)?        [Y/n]

── Universal Configs ─────────────────────
? Generate .editorconfig?                   [Y/n]
? Generate .markdownlint.jsonc?             [Y/n]
? Generate .codespellrc?                    [Y/n]

── Pre-commit & Agent Hooks ──────────────
? Install lefthook pre-commit hooks?        [Y/n]
? Generate .claude/settings.json?           [Y/n]

── Agent Instructions ────────────────────
? Generate agent rule files?                [Y/n]
  (Detected: Claude Code, Cursor)

── CI Pipeline ───────────────────────────
? Generate GitHub Actions workflow?         [Y/n]

── Tool Installation ─────────────────────
? Install ruff (Python linter)?             [Y/n]
? Install pyright (Python type checker)?    [Y/n]

── Baseline ──────────────────────────────
? Capture initial baseline snapshot?        [Y/n]

═════════════════════════════════════════

✓ Config: .ai-guardrails/config.toml
✓ ruff.toml
✓ biome.jsonc
✓ .editorconfig
✓ lefthook.yml (8 hooks installed)
✓ .claude/settings.json
✓ Baseline: 12 issues captured

Done! Run `ai-guardrails check` to verify.
```

---

## 4. Dependency Graph

```
profile-selection
    │
config-tuning
    │
    ├── ruff-config
    ├── biome-config
    ├── editorconfig
    ├── markdownlint-config
    ├── codespell-config
    ├── lefthook
    └── claude-settings

agent-rules    (no config deps — independent)
github-actions (no config deps — independent)

tool-install   (depends on: profile-selection)

baseline       (depends on: ruff-config, biome-config, editorconfig,
                markdownlint-config, codespell-config, lefthook,
                claude-settings, tool-install)
```

The runner performs a topological sort over `dependsOn` declarations. Circular
dependencies are detected at startup with a clear error. Modules with no `dependsOn`
may execute in any order relative to each other.

### Runner (src/init/runner.ts)

```typescript
async function executeModules(
  modules: readonly InitModule[],
  selections: Map<string, boolean>,
  ctx: InitContext
): Promise<InitModuleResult[]>
```

1. Topological sort of `modules` by `dependsOn`
2. For each module in sorted order: skip if `selections.get(mod.id) !== true`
3. Call `mod.execute(ctx)`
4. Log result via `ctx.console`
5. Collect results; continue even if a module errors (non-fatal by default)

---

## 5. CLI Flag Mapping

Updated init flags (extending current SPEC-004 flags):

```
ai-guardrails init
  --yes                   Accept all defaults (non-interactive)
  --profile <p>           Preselect profile (strict | standard | minimal)
  --force                 Overwrite existing managed files
  --upgrade               Refresh generated files, preserve config.toml
  --interactive           Force interactive mode even in non-TTY
  --config-strategy <s>   merge | replace | skip (default: merge)
  --no-hooks              Disable lefthook module
  --no-ci                 Disable github-actions module
  --no-agent-rules        Disable agent-rules module
  --no-agent-hooks        Disable claude-settings module
  --no-baseline           Disable baseline module
  --no-editorconfig       Disable editorconfig module
  --no-markdownlint       Disable markdownlint-config module
  --no-codespell          Disable codespell-config module
  --no-ruff               Disable ruff-config module
  --no-biome              Disable biome-config module
```

Each `--no-X` flag maps to `selections.set(moduleId, false)` before the
wizard runs. The wizard never prompts for a module that has been pre-disabled.

---

## 6. Migration Path

The migration preserves backward compatibility at every step.

### What stays

- `src/generators/` — untouched; modules call generators, not replace them
- `src/steps/` — untouched; modules call steps, not replace them
- All existing `ai-guardrails init` CLI flags continue to work
- `--yes` produces identical output to current behavior

### What changes

| File | Change |
|------|--------|
| `src/pipelines/init.ts` | Rewritten to use module system |
| `src/pipelines/install.ts` | Becomes thin wrapper (all modules enabled) |
| `src/cli.ts` | New `--yes`, `--no-baseline`, `--no-ruff`, `--no-biome` flags added |
| New: `src/init/types.ts` | `InitModule`, `InitContext`, `InitCategory`, `InitModuleResult` |
| New: `src/init/registry.ts` | `ALL_INIT_MODULES` |
| New: `src/init/wizard.ts` | Interactive prompt loop grouped by category |
| New: `src/init/runner.ts` | Topological sort + module executor |
| New: `src/init/prompt.ts` | `askYesNo`, `askChoice`, `askText`, `askCommaSeparated` |
| New: `src/init/modules/*.ts` | 13 module files |

### Phased Delivery

| Phase | Content | Deliverable |
|-------|---------|-------------|
| 1 | Core framework (types, prompt, runner, empty registry) | Mergeable in isolation, no behavior change |
| 2 | 13 module files | Each module tested independently |
| 3 | Rewrite `init.ts` pipeline | Full replacement, backward-compat tested |
| 4 | Wizard UI (grouped prompts, summary) | Requires Phase 3 |
| 5 | Tests (unit + integration) | Parallel with Phase 4 |
| 6 | CLI flag additions | Parallel with Phase 4 |

Phases 1 and 2 can be developed in parallel. Phase 3 requires both to complete.

---

## Testing Strategy

| Test file | Coverage |
|-----------|----------|
| `tests/init/prompt.test.ts` | `askYesNo`, `askChoice`, `askText` with `FakeReadline` |
| `tests/init/runner.test.ts` | Topological sort correct order, skip disabled modules, dependency chain |
| `tests/init/wizard.test.ts` | Integration: wizard with pre-programmed answers produces expected selections |
| `tests/init/modules/profile-selection.test.ts` | detect always true, execute writes config.toml |
| `tests/init/modules/ruff-config.test.ts` | detect false for non-Python, execute calls generator |
| `tests/init/modules/baseline.test.ts` | execute runs linters, writes baseline.json |
| `tests/init/modules/*.test.ts` | Each of the 13 modules: detect + execute with fakes |
| `tests/pipelines/init.test.ts` | `--yes` produces same output as current init (backward-compat) |

**FakeReadline:** A test double that feeds pre-programmed responses to readline
prompts. Required for wizard integration tests.

**FakeFileManager seeding:** Each module test seeds the fake filesystem with
prerequisite state (e.g., Python detected = `requirements.txt` present).

---

## Evolution

| Stable While | Revisit If | Impact |
|-------------|------------|--------|
| 13-module registry | New init feature needed | Add one module file + registry entry — no other changes |
| Category display order | UX research shows different grouping preferred | Update `wizard.ts` category order, update this spec |
| `dependsOn` string IDs | Module renamed after shipping | Never rename a module ID — add an alias instead |
| readline-based prompts | Windows terminal issues reported | Evaluate `@inquirer/prompts`, update `prompt.ts` only |
| `--yes` backward compat | Major version bump (v4.0) | Acceptable break — document in migration guide |
| Phase delivery order | Resource constraints | Phases are independent PRs, order can shift |

---

## Cross-References

- SPEC-000: Philosophy principles 6 (composition over inheritance), technology stack
- SPEC-001: `PipelineContext`, `StepResult`, `FileManager`, `CommandRunner`, `Console` interfaces
- SPEC-002: `ResolvedConfig`, profiles, `isAllowed()` — consumed by modules via `InitContext.config`
- SPEC-004: Current init flags, exit codes — this spec extends them
- SPEC-006: Config generators called by modules (`ruffGenerator`, `biomeGenerator`, etc.)
- SPEC-007: `snapshotStep` called by the `baseline` module
