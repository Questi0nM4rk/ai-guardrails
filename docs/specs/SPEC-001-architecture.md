# SPEC-001: Architecture

## Status: Draft

---

## Module Structure

```
src/
  cli.ts                        # Entry: registers all commands, wires DI
  commands/                     # One file per CLI command
    install.ts
    init.ts
    generate.ts
    check.ts
    snapshot.ts
    status.ts
    report.ts
    hook.ts                     # Subcommand dispatcher for hook runners
  runners/                      # One file per linter tool
    types.ts                    # LinterRunner interface + shared types
    ruff.ts
    mypy.ts
    shellcheck.ts
    clippy.ts
    biome.ts
    go-vet.ts
    staticcheck.ts
    clang-tidy.ts
    luacheck.ts
    codespell.ts
    markdownlint.ts
  languages/                    # One file per language plugin
    types.ts                    # LanguagePlugin interface
    registry.ts                 # Discover + instantiate plugins from project
    python.ts                   # Composes: ruff + mypy + codespell
    shell.ts                    # Composes: shellcheck
    typescript.ts               # Composes: biome
    rust.ts                     # Composes: clippy
    go.ts                       # Composes: go-vet + staticcheck
    cpp.ts                      # Composes: clang-tidy
    dotnet.ts                   # Composes: dotnet-build (analyzers at build)
    lua.ts                      # Composes: luacheck
    universal.ts                # Always active: codespell + markdownlint
  generators/                   # Config file generators (one per output file)
    types.ts                    # Generator interface
    registry.ts                 # Default generator list
    ruff.ts                     # → ruff.toml
    mypy.ts                     # → mypy.ini
    biome.ts                    # → biome.json
    editorconfig.ts             # → .editorconfig
    markdownlint.ts             # → .markdownlint.jsonc
    lefthook.ts                 # → lefthook.yml
    codespell.ts                # → .codespellrc
    claude-settings.ts          # → .claude/settings.json
    agent-rules.ts              # → AGENTS.md, .cursorrules, .windsurfrules, copilot-instructions.md
  config/                       # Config system
    schema.ts                   # Zod schemas — MachineConfig, ProjectConfig, ResolvedConfig
    loader.ts                   # Load + merge machine → project → resolved
    defaults.ts                 # Per-language default ignore lists
  models/                       # Domain types (pure data, no methods)
    lint-issue.ts               # LintIssue + fingerprint computation
    baseline.ts                 # BaselineEntry, BaselineStatus
    step-result.ts              # StepResult discriminated union
    audit-record.ts             # AuditRecord for .guardrails-audit.jsonl
  pipelines/                    # Command orchestration
    types.ts                    # Pipeline, PipelineContext, Step interfaces
    init-pipeline.ts
    generate-pipeline.ts
    check-pipeline.ts
    snapshot-pipeline.ts
    status-pipeline.ts
    install-pipeline.ts
    report-pipeline.ts
  steps/                        # Reusable pipeline steps
    detect-languages.ts
    load-config.ts
    generate-configs.ts
    generate-agent-rules.ts
    check-step.ts
    snapshot-step.ts
    setup-hooks.ts
    setup-ci.ts
    setup-agent-instructions.ts
    validate-configs.ts
    status-step.ts
    report-step.ts
  hooks/                        # Hook implementations (invoked via `ai-guardrails hook`)
    dangerous-cmd.ts            # PreToolUse: blocks rm -rf, force-push, etc.
    protect-configs.ts          # PreToolUse: blocks edits to managed config files
    suppress-comments.ts        # Pre-commit: detects noqa/ts-ignore/etc.
    format-stage.ts             # Pre-commit: auto-format + re-stage
    allow-comment.ts            # Parser: ai-guardrails-allow: RULE "reason"
  writers/                      # Output serializers
    sarif.ts                    # LintIssue[] → SARIF 2.1.0 JSON
    text.ts                     # LintIssue[] → human-readable text
  infra/                        # Infrastructure (injected, never imported directly in domain)
    file-manager.ts             # FileManager interface + real impl
    command-runner.ts           # CommandRunner interface + real impl
    console.ts                  # Console interface + real impl
  utils/                        # Pure functions, no side effects
    hash.ts                     # SHA-256, hash headers, verify
    fingerprint.ts              # Content-stable LintIssue fingerprinting
    glob.ts                     # Glob matching helpers (wraps Bun built-in)
    toml.ts                     # TOML read/write helpers
  templates/                    # Static data files (not compiled)
    defaults/
      ruff.toml                 # Battle-tested Python ruff defaults
      mypy.ini                  # mypy strict defaults
      biome.json                # biome defaults
    workflows/
      check.yml                 # GitHub Actions CI template
    agent-rules/
      base.md                   # Agent instructions base
      claude-additions.md
      cursor-additions.md
      windsurf-additions.md
      copilot-additions.md
    config/
      machine-default.toml      # Scaffold for ~/.ai-guardrails/config.toml
      project-default.toml      # Scaffold for .ai-guardrails/config.toml
```

---

## Confirmed Library Stack

Based on research (March 2026):

| Purpose | Library | Version | Notes |
|---------|---------|---------|-------|
| CLI framework | `@commander-js/extra-typings` | v13+ | Type-safe subcommands; zero native deps; Bun full compat |
| Interactive prompts | `@clack/prompts` | 1.0.0-alpha.1+ | Best DX; Bun compat (avoid Bun 1.3.2 on Linux); use Bun native iterator for simple Y/N |
| TOML read | `smol-toml` | v1.5.1+ | Only maintained TS TOML with stringify; Bun built-in has read-only |
| TOML write | `smol-toml` | v1.5.1+ | `stringify()` — do not use Bun built-in (no stringify) |
| Config validation | `zod` | v3+ | smol-toml returns plain objects; Zod validates them |
| Glob matching | `minimatch` | v10+ | For `isAllowed(rule, filePath)` in ResolvedConfig |
| Hook runner (generated) | lefthook | v2.1.x | Still best for generated configs; `stage_fixed: true` replaces lint-staged |
| Claude Code hooks runtime | `bun run hook.ts` | — | 8–15ms startup vs 200–400ms for `npx tsx` |
| Hook target projects | `node script.js` | — | Cannot assume Bun in target projects |

### Bun built-in TOML caveat

`import config from "./config.toml"` (Bun built-in) supports **read only**. There is no
`TOML.stringify()` in Bun as of 1.2.x (GitHub issue #22219, Aug 2025). Use smol-toml for
all TOML write operations.

### Y/N prompts without deps

For simple Y/N, Bun exposes `console` as an AsyncIterable — zero-dep fallback:
```typescript
async function confirm(question: string, defaultValue = false): Promise<boolean> {
  const hint = defaultValue ? "[Y/n]" : "[y/N]";
  process.stdout.write(`${question} ${hint} `);
  for await (const line of console) {
    if (line === "") return defaultValue;
    return line.toLowerCase().startsWith("y");
  }
  return defaultValue;
}
```
Use `@clack/prompts select` when arrow-key navigation is needed.

---

## Core Interfaces

### LinterRunner

```typescript
// runners/types.ts

export interface RunOptions {
  projectDir: string;
  config: ResolvedConfig;
  commandRunner: CommandRunner;
}

export interface LinterRunner {
  /** Stable identifier: "ruff", "mypy", "shellcheck", etc. */
  readonly id: string;

  /** Human-readable name for output */
  readonly name: string;

  /** Config file this runner reads, relative to project root. null = no config file. */
  readonly configFile: string | null;

  /** Check if the tool binary is reachable */
  isAvailable(commandRunner: CommandRunner): Promise<boolean>;

  /** Run the linter, return normalized issues */
  run(opts: RunOptions): Promise<LintIssue[]>;

  /** Generate the config file content for this runner. null = runner has no managed config. */
  generateConfig(config: ResolvedConfig): string | null;
}
```

### LanguagePlugin

```typescript
// languages/types.ts

export interface DetectOptions {
  projectDir: string;
  fileManager: FileManager;
}

export interface LanguagePlugin {
  /** Stable identifier: "python", "typescript", "rust", etc. */
  readonly id: string;

  /** Human-readable name */
  readonly name: string;

  /** Ordered list of runners this language uses */
  readonly runners: readonly LinterRunner[];

  /** Return true if this language is present in the project */
  detect(opts: DetectOptions): Promise<boolean>;
}
```

### Generator

```typescript
// generators/types.ts

export interface GeneratorIssue {
  file: string;
  message: string;
}

export interface Generator {
  /** Stable identifier: "ruff", "editorconfig", "lefthook", etc. */
  readonly id: string;

  /** Output file path relative to project root */
  readonly outputFile: string;

  /** Generate file content from resolved config */
  generate(config: ResolvedConfig, projectDir: string): string;

  /** Verify the on-disk file is fresh (matches what generate() would produce) */
  verify(projectDir: string, config: ResolvedConfig): Promise<GeneratorIssue[]>;
}
```

### Pipeline + Step

```typescript
// pipelines/types.ts

export interface PipelineContext {
  projectDir: string;
  languages: readonly LanguagePlugin[];
  config: ResolvedConfig;
  fileManager: FileManager;
  commandRunner: CommandRunner;
  console: Console;
  // Command-specific flags passed through
  flags: Record<string, unknown>;
}

export type StepResult =
  | { status: "ok"; message: string }
  | { status: "error"; message: string }
  | { status: "skip"; message: string }
  | { status: "warn"; message: string };

export interface Step {
  readonly name: string;
  execute(ctx: PipelineContext): Promise<StepResult>;
}

export interface Pipeline {
  run(ctx: PipelineContext): Promise<StepResult[]>;
}
```

### Infrastructure (injected via DI)

```typescript
// infra/file-manager.ts
export interface FileManager {
  readText(path: string): Promise<string>;
  writeText(path: string, content: string): Promise<void>;
  appendText(path: string, content: string): Promise<void>;
  exists(path: string): Promise<boolean>;
  mkdir(path: string, opts?: { parents?: boolean }): Promise<void>;
  glob(pattern: string, cwd: string): Promise<string[]>;
  isSymlink(path: string): Promise<boolean>;
}

// infra/command-runner.ts
export interface RunResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}

export interface CommandRunner {
  run(args: string[], opts?: { cwd?: string; timeout?: number }): Promise<RunResult>;
}

// infra/console.ts
export interface Console {
  info(msg: string): void;
  success(msg: string): void;
  warning(msg: string): void;
  error(msg: string): void;
  step(msg: string): void;
}
```

---

## Key Design Patterns

### 1. Composition over inheritance — always

Language plugins compose runner instances. Generators are standalone. Nothing
extends anything. `implements` only, never `extends` (except for Error subclasses).

```typescript
// languages/python.ts
export const pythonPlugin: LanguagePlugin = {
  id: "python",
  name: "Python",
  runners: [ruffRunner, mypyRunner],
  async detect({ projectDir, fileManager }) {
    return (
      (await fileManager.exists(join(projectDir, "pyproject.toml"))) ||
      (await fileManager.glob("**/*.py", projectDir)).length > 0
    );
  },
};
```

### 2. Dependency injection via function parameters

No IoC container. No `new Service()` inside domain code. Context carries all
infrastructure. Domain functions are pure given their context.

### 3. Discriminated unions over class hierarchies

```typescript
type StepResult =
  | { status: "ok"; message: string }
  | { status: "error"; message: string }
  | { status: "skip"; message: string };

// Exhaustive switch — compiler enforces all cases handled
switch (result.status) {
  case "ok": ...
  case "error": ...
  case "skip": ...
}
```

### 4. Zod at boundaries only

Config loading and external tool output parsing are the only places Zod
validates. Internal domain types are plain TypeScript interfaces — fully typed
at compile time, no runtime overhead.

### 5. Runners are async, pipelines are sequential

Each step runs to completion before the next starts. Parallelism within a step
(e.g. running ruff and mypy concurrently for Python) is the step's internal
responsibility using `Promise.all`.

### 6. Hash headers for tamper detection

Every generated config file starts with:
```
# ai-guardrails:sha256=<hex>
```
The hash covers the file content below the header. `verify()` recomputes and
compares. Any edit breaks the hash — detected by `generate --check` and CI.

---

## Testing Architecture

```
tests/
  runners/            # Unit: each runner's output parser with fixture data
  languages/          # Unit: detection logic with fake file trees
  generators/         # Unit: generated output matches snapshots
  config/             # Unit: schema validation, merge logic
  pipelines/          # Integration: full pipeline with FakeCommandRunner + FakeFileManager
  hooks/              # Unit: each hook's decision logic
  utils/              # Unit: hash, fingerprint, glob
  fixtures/           # Static linter output samples (JSON/text files)
    ruff-output.json
    mypy-output.txt
    shellcheck-output.json
    clippy-output.json
    biome-output.json
    go-vet-output.txt
    luacheck-output.txt
```

**Fakes (not mocks):**
- `FakeFileManager` — in-memory tree, `seed(path, content)` for setup
- `FakeCommandRunner` — register canned responses per args tuple
- `FakeConsole` — captures messages for assertion

**Snapshot testing for generators:**
Generated config content is snapshot-tested. Changes to templates require
explicit snapshot updates (`bun test --update-snapshots`).

---

## Skills + MCPs for Implementation

| Need | Tool |
|------|------|
| TypeScript/Bun/Zod docs | `context7` MCP |
| Parallel feature branches | `EnterWorktree` + git worktrees |
| TDD workflow enforcement | `tdd` skill |
| Post-implementation review | `code-review` skill |
| Learning from failures | `reflections` skill |
| PR creation + status | GitHub MCP |
| Research (library choices, API changes) | `Explore` subagent (preserves main context) |
