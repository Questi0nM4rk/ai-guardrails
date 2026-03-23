# SPEC-001: Architecture

## Status: Draft
## Version: 3.1
## Last Updated: 2026-03-20

---

## Problem

A linting enforcement tool requires I/O, process execution, terminal output,
config loading, language detection, and lint running — all wired together. If
those capabilities are imported directly in domain code, testing requires
filesystem state, real processes, and real terminal output. Coupling also makes
it impossible to swap or extend any one piece without touching all others.

The tool must also express its extension points — new linter runners, new
language plugins, new config generators — without modifying core pipeline code.
Inheritance would make these extension points brittle: adding a field to a base
class forces every subclass to update.

---

## Solution

Pipeline + Plugin architecture with full dependency injection. Every capability
crosses a typed interface boundary. Domain code (runners, generators, steps,
pipelines) receives interfaces via `PipelineContext` — it never constructs or
imports infrastructure directly.

| Concern | Interface | Real impl | Fake impl |
|---------|-----------|-----------|-----------|
| File I/O | `FileManager` | `RealFileManager` | `FakeFileManager` |
| Process execution | `CommandRunner` | `RealCommandRunner` | `FakeCommandRunner` |
| Terminal output | `Console` | `RealConsole` | `FakeConsole` |
| Linter extension | `LinterRunner` | 12 runner files | — |
| Language extension | `LanguagePlugin` | 9 plugin files | — |
| Config generation | `ConfigGenerator` | 8 generator files | — |
| Pipeline step | `StepResult` | step functions | — |

---

## Philosophy

1. **Interfaces at every seam.** Every collaborator is a typed interface, not a
   class reference. WHY: interfaces make the contract explicit and allow swapping
   real implementations with fakes without touching call sites.

2. **Inject, don't construct.** Domain code never calls `new Service()`. All
   dependencies arrive through `PipelineContext`. WHY: construction in domain code
   couples the domain to a specific implementation, breaking testability and making
   future swaps require touching domain files.

3. **Steps never throw.** Every step returns `StepResult` with a typed `status`
   field. WHY: exceptions are invisible to callers — a thrown error bypasses the
   pipeline's sequential control flow and produces uncontrolled output. A
   discriminated union makes every outcome explicit.

4. **Composition over inheritance.** `implements` only — no `extends` except for
   `Error` subclasses. WHY: inheritance creates hidden coupling. A change to a base
   class cascades to all subclasses. Composition keeps each component independently
   testable and replaceable.

5. **Zod at system boundaries only.** Raw JSON from config files and linter stdout
   is Zod-parsed at the entry point. WHY: validating at the boundary converts
   `unknown` to a typed domain object once. Repeating validation inside domain code
   is redundant and slows hot paths.

6. **No barrel files.** Every import names the exact source file. WHY: barrel
   files (`index.ts`) create implicit re-export graphs that make tree-shaking
   unpredictable and obscure where a symbol lives.

7. **Max 200 lines per file, one concern per file.** If you need "and" to describe
   a file, it should be split. WHY: large files with multiple concerns resist
   comprehension and create merge conflicts. Small focused files compose cleanly.

---

## Constraints

### Hard Constraints

- No `any` — use `unknown` + Zod at boundaries
- No `as` casts — use `in`-operator narrowing or Zod parsing
- No `!` non-null assertions — handle `undefined` with early returns or defaults
- No `extends` — composition only (`implements` permitted)
- No direct `import` from `src/infra/` in domain code
- No barrel files (`index.ts`)
- `strict: true`, `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`, `verbatimModuleSyntax` — no exceptions
- Max 200 lines per source file

### Soft Constraints

- Prefer standalone test functions over test classes
- Prefer `as const` for literal objects to prevent accidental widening
- Prefer `Promise.all` for concurrent independent I/O within a step

### Assumptions

| Assumption | If Wrong | Action |
|------------|----------|--------|
| `PipelineContext` shape is stable across commands | New command needs a field not in context | Add to context interface, update all command entry points |
| `StepResult` discriminated union covers all outcomes | New outcome needed (e.g. "partial") | Extend the union, update all `switch` exhaustiveness checks |
| Bun's `Subprocess` API covers all process needs | Bun changes spawn API | Update `RealCommandRunner` only — callers are unaffected |
| `FileManager.glob` with `ignore` is sufficient for detection | Complex exclusion patterns needed | Extend `DetectOptions` with additional filter callbacks |

---

## Module Structure

Actual file tree as of v3.1 (relative to `src/`):

```
src/
  cli.ts                          Entry point — Commander wiring, constructs real infra
  commands/
    check.ts                      `check` command handler
    context.ts                    Shared command context helpers
    generate.ts                   `generate` command handler
    hook.ts                       `hook` command handler
    init.ts                       `init` command handler
    install.ts                    `install` command handler
    report.ts                     `report` command handler
    snapshot.ts                   `snapshot` command handler
    status.ts                     `status` command handler
  config/
    loader.ts                     loadMachineConfig, loadProjectConfig, resolveConfig
    schema.ts                     Zod schemas, ResolvedConfig, buildResolvedConfig
  generators/
    types.ts                      ConfigGenerator interface
    agent-rules.ts                Generator for agent rules
    biome.ts                      Generator for biome.jsonc
    claude-settings.ts            Generator for .claude/settings.json
    codespell.ts                  Generator for .codespellrc
    editorconfig.ts               Generator for .editorconfig
    lefthook.ts                   Generator for lefthook.yml
    markdownlint.ts               Generator for .markdownlint.jsonc
    registry.ts                   All generators list
    ruff.ts                       Generator for ruff.toml
  hooks/
    types.ts                      Hook interfaces
    allow-comment.ts              ai-guardrails-allow comment parser
    dangerous-cmd.ts              Dangerous command detection
    format-stage.ts               Format-and-re-stage hook
    protect-configs.ts            Config file tamper detection
    protect-reads.ts              Sensitive path read protection
    runner.ts                     Hook execution runner
    suppress-comments.ts          Suppression comment detection
  infra/
    command-runner.ts             CommandRunner interface + RealCommandRunner
    console.ts                    Console interface + RealConsole
    file-manager.ts               FileManager interface + RealFileManager
  languages/
    types.ts                      LanguagePlugin, DetectOptions interfaces
    constants.ts                  DEFAULT_IGNORE glob list
    registry.ts                   ALL_PLUGINS list, detectLanguages()
    cpp.ts                        C/C++ plugin
    dotnet.ts                     .NET plugin (stub — no runners yet)
    go.ts                         Go plugin
    lua.ts                        Lua plugin
    python.ts                     Python plugin
    rust.ts                       Rust plugin
    shell.ts                      Shell plugin
    typescript.ts                 TypeScript/JS plugin
    universal.ts                  Universal plugin (always active)
  models/
    audit-record.ts               AuditRecord domain type
    baseline.ts                   BaselineEntry domain type
    lint-issue.ts                 LintIssue, FingerprintOpts, computeFingerprint
    paths.ts                      Well-known path constants
    step-result.ts                StepResult discriminated union + constructors
  pipelines/
    types.ts                      PipelineContext, PipelineResult, Pipeline
    check.ts                      Check pipeline
    generate.ts                   Generate pipeline
    init.ts                       Init pipeline
    install.ts                    Install pipeline
  runners/
    types.ts                      LinterRunner, RunOptions, InstallHint interfaces
    biome.ts                      Biome runner
    clang-tidy.ts                 clang-tidy runner
    clippy.ts                     Clippy runner
    codespell.ts                  Codespell runner
    golangci-lint.ts              golangci-lint runner
    markdownlint.ts               markdownlint-cli2 runner
    pyright.ts                    Pyright runner
    ruff.ts                       Ruff runner
    selene.ts                     Selene runner
    shellcheck.ts                 ShellCheck runner
    shfmt.ts                      shfmt runner
    tsc.ts                        TypeScript compiler runner
  steps/
    check-prerequisites.ts        Verify required tools are available
    check-step.ts                 Run check and compare to baseline
    detect-languages.ts           Run language detection
    generate-configs.ts           Run config generators
    install-prerequisites.ts      Install missing tools
    load-config.ts                Load + resolve config from disk
    report-step.ts                Format and emit lint report
    run-linters.ts                Run all active runners
    setup-agent-instructions.ts   Write agent rules files
    setup-ci.ts                   Write CI workflow files
    setup-hooks.ts                Write lefthook + Claude settings
    snapshot-step.ts              Capture and write baseline
    status-step.ts                Compute new/fixed/baseline counts
    validate-configs.ts           Verify hash headers on managed configs
  templates/                      Static data files (CI YAML, ruff defaults, etc.)
  utils/
    apply-fingerprints.ts         applyFingerprints — reads files, calls fingerprintIssue
    collections.ts                groupBy
    config-merge.ts               Config merging helpers
    deep-merge.ts                 Deep object merge
    detect-project-type.ts        detectNoConsoleLevel from package.json
    errors.ts                     isEnoent helper
    fingerprint.ts                fingerprintIssue — context window + computeFingerprint
    hash.ts                       SHA-256 hash helpers
    ndjson.ts                     parseNdjson
    parse.ts                      safeParseJson
    resolve-tool-path.ts          Resolve local node_modules/.bin before PATH
  writers/
    sarif.ts                      SARIF 2.1 output serializer
    text.ts                       Text output serializer
  check/
    builder-cmd.ts                Command check builder
    builder-path.ts               Path check builder
    engine.ts                     Check rule engine
    engine-helpers.ts             Engine helper functions
    flag-aliases.ts               Flag alias resolution
    output.ts                     Check output formatting
    ruleset.ts                    Rule set management
    types.ts                      Check domain types
    rules/
      groups.ts                   Rule group definitions
      paths.ts                    Path rule definitions
      groups/                     Per-group rule implementations
```

---

## Core Interfaces

### `PipelineContext` (`src/pipelines/types.ts`)

```typescript
export interface PipelineContext {
  projectDir: string;
  config: ResolvedConfig;
  fileManager: FileManager;
  commandRunner: CommandRunner;
  console: Console;
  flags: Record<string, unknown>;
  isTTY: boolean;
  createReadline: () => ReadlineInterface;
}
```

### `PipelineResult` (`src/pipelines/types.ts`)

```typescript
export interface PipelineResult {
  status: "ok" | "error";
  message?: string;
  issueCount?: number;
}
```

### `Pipeline` (`src/pipelines/types.ts`)

```typescript
export interface Pipeline {
  run(ctx: PipelineContext): Promise<PipelineResult>;
}
```

### `FileManager` (`src/infra/file-manager.ts`)

```typescript
export interface FileManager {
  readText(path: string): Promise<string>;
  writeText(path: string, content: string): Promise<void>;
  appendText(path: string, content: string): Promise<void>;
  exists(path: string): Promise<boolean>;
  mkdir(path: string, opts?: { parents?: boolean }): Promise<void>;
  glob(pattern: string, cwd: string, ignore?: readonly string[]): Promise<string[]>;
  isSymlink(path: string): Promise<boolean>;
  delete(path: string): Promise<void>;
}
```

`delete` is idempotent — `ENOENT` is silently swallowed. `glob` accepts an
optional `ignore` list of minimatch patterns applied after scanning.

### `CommandRunner` (`src/infra/command-runner.ts`)

```typescript
export interface RunResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}

export interface CommandRunner {
  run(args: string[], opts?: { cwd?: string; timeout?: number }): Promise<RunResult>;
}
```

`RealCommandRunner` uses `Bun.spawn`. If the executable is not found, it returns
`exitCode: 127` instead of throwing. Timeout kills the subprocess via
`proc.kill()`.

### `Console` (`src/infra/console.ts`)

```typescript
export interface Console {
  info(msg: string): void;
  success(msg: string): void;
  warning(msg: string): void;
  error(msg: string): void;
  step(msg: string): void;
}
```

`RealConsole` writes directly to `process.stdout` with ANSI color codes
(green=success, yellow=warning, red=error, cyan=step). All output goes to
stdout — not stderr — so structured output (SARIF, JSON) can be captured by
redirecting stdout only.

### `LinterRunner` (`src/runners/types.ts`)

```typescript
export interface RunOptions {
  projectDir: string;
  config: ResolvedConfig;
  commandRunner: CommandRunner;
  fileManager: FileManager;
}

export interface InstallHint {
  readonly description: string;
  readonly npm?: string;
  readonly pip?: string;
  readonly brew?: string;
  readonly apt?: string;
  readonly cargo?: string;
  readonly go?: string;
  readonly rustup?: string;
}

export interface LinterRunner {
  readonly id: string;
  readonly name: string;
  readonly configFile: string | null;
  readonly installHint: InstallHint;
  isAvailable(commandRunner: CommandRunner, projectDir?: string): Promise<boolean>;
  run(opts: RunOptions): Promise<LintIssue[]>;
}
```

`configFile` is `null` when the runner does not manage a config file. `isAvailable`
takes an optional `projectDir` so runners like `tsc`, `biome`, and `pyright` can
check `node_modules/.bin/` before falling back to `PATH`.

### `ConfigGenerator` (`src/generators/types.ts`)

```typescript
export interface ConfigGenerator {
  readonly id: string;
  readonly configFile: string;
  readonly languages?: readonly string[];
  generate(config: ResolvedConfig): string;
}
```

`languages` is an optional language gate — if set, the generator only runs when
at least one of those language IDs is detected. `configFile` is relative to the
project root.

### `LanguagePlugin` (`src/languages/types.ts`)

```typescript
export interface DetectOptions {
  projectDir: string;
  fileManager: FileManager;
  ignorePaths?: readonly string[];
}

export interface LanguagePlugin {
  readonly id: string;
  readonly name: string;
  detect(opts: DetectOptions): Promise<boolean>;
  runners(): LinterRunner[];
}
```

### `StepResult` (`src/models/step-result.ts`)

```typescript
export type StepResult =
  | { readonly status: "ok";    readonly message: string }
  | { readonly status: "error"; readonly message: string }
  | { readonly status: "skip";  readonly message: string }
  | { readonly status: "warn";  readonly message: string };
```

Constructor functions `ok()`, `error()`, `skip()`, `warn()` create typed
instances. Steps never throw — they always return one of these variants.

### `LintIssue` + `FingerprintOpts` (`src/models/lint-issue.ts`)

```typescript
export interface LintIssue {
  readonly rule: string;        // "ruff/E501", "biome/noUnusedVariables"
  readonly linter: string;      // "ruff", "biome"
  readonly file: string;        // absolute path
  readonly line: number;        // 1-indexed
  readonly col: number;         // 1-indexed
  readonly message: string;
  readonly severity: "error" | "warning";
  readonly fingerprint: string; // content-stable SHA-256
}

export interface FingerprintOpts {
  rule: string;
  file: string;                 // project-relative path for portable baselines
  lineContent: string;          // content of the flagged line
  contextBefore: string[];      // up to 2 lines before
  contextAfter: string[];       // up to 2 lines after
}
```

`LintIssue.file` is always an absolute path in memory. `FingerprintOpts.file`
is always a project-relative path. Callers of `computeFingerprint` are
responsible for this conversion.

---

## DI Pattern

`cli.ts` is the composition root. It constructs `RealFileManager`,
`RealCommandRunner`, `RealConsole`, and assembles a `PipelineContext`. Every
command handler receives that context and passes it unchanged to the pipeline.
Pipelines pass it to steps. Steps use only the interface methods on
`ctx.fileManager`, `ctx.commandRunner`, and `ctx.console`.

No domain file (`runners/`, `generators/`, `steps/`, `pipelines/`) imports from
`src/infra/` directly. The rule is enforced by code review and the project's own
`ai-guardrails check`.

---

## Design Patterns

### Composition

All extension points use `implements`, not `extends`. A `LinterRunner` is a
plain object literal that satisfies the interface:

```typescript
export const ruffRunner: LinterRunner = {
  id: "ruff",
  name: "Ruff",
  configFile: "ruff.toml",
  installHint: { description: "Python linter and formatter", pip: "pip install ruff" },
  async isAvailable(runner) { ... },
  async run(opts) { ... },
};
```

### Discriminated Unions

`StepResult` and `PipelineResult` use `status` as the discriminant. Switch
exhaustiveness is enforced by TypeScript's `never` type — adding a new variant
without handling it produces a compile error.

### Zod at Boundaries

Raw TOML files (`config.toml`) and linter JSON output are parsed through Zod
schemas before entering domain code. Zod's `.parse()` throws on invalid input
(surfacing config errors to the user). Linter output parsers use `safeParseJson`
+ manual type guards instead of Zod, because linter output is untrusted and
invalid entries are skipped, not fatal.

### Hash Headers

Generated config files include a SHA-256 hash comment as the first line.
`validate-configs` step re-hashes the file content and compares. Any edit
outside `ai-guardrails generate` is detected. This applies to all 8 managed
config files.

---

## Testing Strategy

**Framework:** `bun:test` — `import { describe, expect, test } from "bun:test"`.

**Fakes:** `tests/fakes/FakeFileManager` (in-memory file tree with `seed()`),
`tests/fakes/FakeCommandRunner` (canned responses per args tuple),
`tests/fakes/FakeConsole` (captures messages for assertion).

**Fixtures:** `tests/fixtures/` — static linter output samples (JSON, NDJSON, text).

**Pattern:** `test_<function>_<scenario>_<expected>`.

**Coverage:** 85%+ line coverage on all modules. No suppression without
documented justification.

**Rule:** One test file per source module (`src/runners/ruff.ts` →
`tests/runners/ruff.test.ts`).

---

## Evolution

| Stable While | Revisit If | Impact |
|-------------|------------|--------|
| `PipelineContext` has these 7 fields | New cross-cutting concern (e.g. audit log writer) | Add field to context, update all command entry points, update fakes |
| `StepResult` has 4 variants | New outcome needed | Extend union, update all exhaustiveness checks |
| `FileManager` interface is stable | New I/O primitive needed (e.g. watch) | Add method, update `RealFileManager`, update `FakeFileManager` |
| `LinterRunner.run()` returns `LintIssue[]` | Runners need to return metadata | Add overloaded return type or new interface method |
| Infra lives in `src/infra/` | Restructuring module layout | Update all import paths, update path alias |

---

## Cross-References

- SPEC-000: Overview — philosophy, technology stack, scope
- SPEC-002: Config System — `ResolvedConfig` shape, `buildResolvedConfig`
- SPEC-003: Linter System — all 12 runners, all 9 language plugins
- SPEC-006: Config Generators — `ConfigGenerator` implementations, hash headers
