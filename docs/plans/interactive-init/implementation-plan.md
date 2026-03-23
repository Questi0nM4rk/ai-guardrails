# Interactive Init — Implementation Plan

## Decisions

- **Full replacement** of init.ts + install.ts with modular system
- **All config prompts visible** — no hidden "advanced" section
- **Tool installation included** — missing linters prompted per-tool
- **`--yes` flag** for backward compat (accepts all defaults, non-interactive)
- **Existing generators/steps reused** — modules wrap them, not replace

## Architecture

```
src/init/
  types.ts              # InitModule, InitContext, InitCategory, InitModuleResult
  registry.ts           # ALL_INIT_MODULES array
  wizard.ts             # Interactive prompt loop (askYesNo, askChoice, askText)
  runner.ts             # Execute modules in dependency order
  prompt.ts             # Low-level prompt helpers (askYesNo, askChoice, askText, askMultiSelect)
  modules/
    ruff-config.ts
    biome-config.ts
    editorconfig.ts
    markdownlint-config.ts
    codespell-config.ts
    lefthook.ts
    claude-settings.ts
    agent-rules.ts
    github-actions.ts
    baseline.ts
    tool-install.ts     # Per-tool installation prompts
```

## Phases

### Phase 1: Core framework (types + prompt + runner)

**Files:**
- `src/init/types.ts` — interfaces
- `src/init/prompt.ts` — readline-based prompt helpers
- `src/init/runner.ts` — dependency-aware module executor
- `src/init/registry.ts` — empty registry (populated in phase 2)

**Types:**
```typescript
interface InitModule {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly category: InitCategory;
  readonly defaultEnabled: boolean;
  readonly disableFlag?: string;
  readonly dependsOn?: readonly string[];
  detect(ctx: InitContext): Promise<boolean>;
  execute(ctx: InitContext): Promise<InitModuleResult>;
}

type InitCategory =
  | "profile"
  | "language-config"
  | "universal-config"
  | "hooks"
  | "agent"
  | "ci"
  | "tools"
  | "baseline"
  | "config";

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
  selections: Map<string, boolean>;
  isTTY: boolean;
  createReadline: () => ReadlineInterface;
  flags: Record<string, unknown>;
}
```

**Prompt helpers:**
```typescript
async function askYesNo(rl: ReadlineInterface, question: string, defaultYes: boolean): Promise<boolean>
async function askChoice<T extends string>(rl: ReadlineInterface, question: string, choices: readonly T[], defaultChoice: T): Promise<T>
async function askText(rl: ReadlineInterface, question: string, defaultValue: string): Promise<string>
async function askCommaSeparated(rl: ReadlineInterface, question: string): Promise<string[]>
```

**Runner:**
- Topological sort by `dependsOn`
- Skip modules where `selections.get(id) !== true`
- Log each module execution via `ctx.console`

### Phase 2: All 10 modules

Each module wraps existing generator/step functionality.

**Module 1: profile-selection** (category: "profile")
- Always applicable, always first
- Prompts: strict/standard/minimal choice
- Writes .ai-guardrails/config.toml
- All other modules depend on this

**Module 2: ruff-config** (category: "language-config")
- detect: Python in languages
- execute: ruffGenerator.generate() → ruff.toml
- Uses config merge strategy

**Module 3: biome-config** (category: "language-config")
- detect: TypeScript in languages
- execute: biomeGenerator.generate() → biome.jsonc
- Detects biome version + noConsole level before generating

**Module 4: editorconfig** (category: "universal-config")
- detect: always true
- execute: editorconfigGenerator.generate() → .editorconfig

**Module 5: markdownlint-config** (category: "universal-config")
- detect: always true
- execute: markdownlintGenerator.generate() → .markdownlint.jsonc

**Module 6: codespell-config** (category: "universal-config")
- detect: always true
- execute: codespellGenerator.generate() → .codespellrc

**Module 7: lefthook** (category: "hooks")
- detect: always true
- execute: lefthookGenerator → lefthook.yml + `lefthook install`
- dependsOn: profile-selection (needs config for ignore_paths)

**Module 8: claude-settings** (category: "hooks")
- detect: always true (Claude Code is the primary consumer)
- execute: claudeSettingsGenerator → .claude/settings.json

**Module 9: agent-rules** (category: "agent")
- detect: any AI tool detected (Claude, Cursor, Windsurf, Copilot, Cline)
- execute: agentRulesGenerator → .ai-guardrails/agent-rules/base.md + symlinks

**Module 10: github-actions** (category: "ci")
- detect: .git directory exists
- execute: setupCiStep → .github/workflows/ai-guardrails.yml

**Module 11: tool-install** (category: "tools")
- detect: any missing runner tools
- execute: per-tool install prompts (npm/pip/brew/apt)
- dependsOn: profile-selection (needs languages detected)

**Module 12: baseline** (category: "baseline")
- detect: always true
- execute: run all linters, write .ai-guardrails/baseline.json
- dependsOn: all config modules (needs configs generated first)

**Module 13: config-tuning** (category: "config")
- detect: always true, runs as part of profile-selection
- Prompts: line_length, indent_width, ignore_rules, ignore_paths
- Actually this should be part of the profile-selection module or right after it

Actually — config tuning (line_length, indent_width, ignore_rules, ignore_paths, managed_files, disabled_groups) should be separate prompts AFTER profile selection but BEFORE generators run. Let me restructure:

**Revised module order:**
1. profile-selection → writes config.toml with profile
2. config-tuning → prompts for line_length, indent_width, ignore rules/paths → updates config.toml
3. language configs (ruff, biome) → depend on config-tuning
4. universal configs (editorconfig, markdownlint, codespell) → depend on config-tuning
5. hooks (lefthook, claude-settings) → depend on config-tuning
6. agent rules → no deps beyond detection
7. CI → no deps
8. tool install → depends on language detection
9. baseline → depends on all configs + tool install

### Phase 3: Rewrite init.ts pipeline

Replace the monolithic `initPipeline` with:

```typescript
export const initPipeline: Pipeline = {
  async run(ctx: PipelineContext): Promise<PipelineResult> {
    // 1. Check config exists (--force / --upgrade)
    // 2. Detect languages
    // 3. Build InitContext
    // 4. Filter applicable modules
    // 5. If interactive: run wizard (per-module y/n prompts)
    //    If --yes: all defaults on
    //    If --no-X flags: override specific modules off
    // 6. Execute selected modules via runner
    // 7. Show summary
  },
};
```

The install pipeline becomes a thin wrapper that calls the same module
runner with all modules enabled (for `ai-guardrails install` command).

### Phase 4: Wizard UI

The wizard groups modules by category and prompts:

```
AI Guardrails Setup
═══════════════════

Detected: TypeScript, Python
Tools: Claude Code, Cursor

── Profile ─────────────────────────────────
? Enforcement profile [strict/standard/minimal]: standard

── Config ──────────────────────────────────
? Line length (60-200, default 88): 88
? Indent width [2/4]: 2
? Rules to ignore (comma-separated, empty to skip):
? Additional paths to exclude (comma-separated, empty to skip):

── Language Configs ────────────────────────
? Generate ruff.toml (Python)?              [Y/n]
? Generate biome.jsonc (TypeScript)?        [Y/n]

── Universal Configs ───────────────────────
? Generate .editorconfig?                   [Y/n]
? Generate .markdownlint.jsonc?             [Y/n]
? Generate .codespellrc?                    [Y/n]

── Pre-commit Hooks ────────────────────────
? Install lefthook pre-commit hooks?        [Y/n]

── AI Agent Hooks ──────────────────────────
? Generate .claude/settings.json?           [Y/n]

── Agent Instructions ──────────────────────
? Generate agent rule files?                [Y/n]
  (Detected: Claude Code, Cursor)

── CI ──────────────────────────────────────
? Generate GitHub Actions workflow?         [Y/n]

── Tools ───────────────────────────────────
? Install ruff (Python linter)?             [Y/n]
? Install pyright (Python type checker)?    [Y/n]

── Baseline ────────────────────────────────
? Capture initial baseline snapshot?        [Y/n]

═══════════════════════════════════════════

✓ Config: .ai-guardrails/config.toml
✓ Generated: ruff.toml
✓ Generated: biome.jsonc
✓ Generated: .editorconfig
...
✓ Baseline: 12 issues captured

Done! Run `ai-guardrails check` to verify.
```

### Phase 5: Tests

- Unit tests for each prompt helper (askYesNo, askChoice, askText)
- Unit tests for runner (topological sort, skip disabled)
- Integration test: wizard with FakeReadline (pre-programmed answers)
- Each module: test detect() and execute() with fakes
- Backward compat: `--yes` produces same output as current init

### Phase 6: CLI flag updates

Update `src/commands/init.ts` and `src/cli.ts`:

```
ai-guardrails init
  --yes                     Accept all defaults
  --profile <p>             Preselect profile
  --force                   Overwrite existing
  --upgrade                 Refresh generated files
  --interactive             Force interactive mode
  --config-strategy <s>     merge|replace|skip
  --no-hooks                Skip lefthook
  --no-ci                   Skip CI workflow
  --no-agent-rules          Skip agent rules
  --no-agent-hooks          Skip .claude/settings.json
  --no-baseline             Skip baseline snapshot
  --no-editorconfig         Skip .editorconfig
  --no-markdownlint         Skip .markdownlint.jsonc
  --no-codespell            Skip .codespellrc
  --no-ruff                 Skip ruff.toml
  --no-biome                Skip biome.jsonc
```

Each `--no-X` flag maps to setting `selections.set(moduleId, false)` before the wizard runs.

## Execution Strategy

6 phases, sequential. Each phase is a PR.

Phase 1 + 2 can be parallelized (framework + modules are independent).
Phase 3 depends on 1 + 2.
Phase 4 depends on 3.
Phase 5 parallel with 4.
Phase 6 parallel with 4.

```
Phase 1 (framework) ─┐
Phase 2 (modules)    ─┤── merge ──→ Phase 3 (rewrite init) → Phase 4 (wizard UI)
                      │
Phase 5 (tests) ──────┘ (can start after 1+2, iterate with 3+4)
Phase 6 (CLI flags) ──── (parallel with 4)
```
