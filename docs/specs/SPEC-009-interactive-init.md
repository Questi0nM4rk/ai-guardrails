# SPEC-009: Interactive Init System

## Status: Draft
## Version: 3.1
## Depends on: SPEC-001 (Architecture), SPEC-002 (Config), SPEC-004 (Commands)

---

## Problem

`ai-guardrails init` is monolithic — it runs everything or nothing. Users can
disable hooks/CI/agent-rules with flags, but there's no way to selectively
configure individual generators, choose which universal configs to install,
or customize the setup interactively. The only customization is profile
selection and ignore rules.

Teams adopting ai-guardrails need granular control over what gets installed.
A TypeScript-only project doesn't want ruff.toml. A project already using
Prettier doesn't want .editorconfig. A team not using Claude Code doesn't
want .claude/settings.json.

---

## Solution

Replace the monolithic init/install pipeline with a modular system where
every action is an **InitModule**. Each module is self-contained: it knows
what it does, how to detect if it's applicable, and how to execute. The
interactive wizard prompts for each applicable module. Non-interactive mode
(`--yes`) accepts all defaults for backward compatibility.

---

## InitModule Interface

```typescript
interface InitModule {
  /** Stable identifier used for selections and CLI flags */
  readonly id: string;
  /** Human-readable name shown in prompts */
  readonly name: string;
  /** One-line description shown in prompts */
  readonly description: string;
  /** Category for grouping in the wizard */
  readonly category: InitCategory;
  /** Default state when user hits Enter (or --yes) */
  readonly defaultEnabled: boolean;
  /** CLI flag that disables this module */
  readonly disableFlag?: string;
  /** Module IDs that must execute before this one */
  readonly dependsOn?: readonly string[];
  /** Check if this module is applicable to the project */
  detect(ctx: InitContext): Promise<boolean>;
  /** Execute the module's action */
  execute(ctx: InitContext): Promise<InitModuleResult>;
}
```

---

## Categories

Modules are grouped by category in the wizard. Categories display in this order:

| Order | Category | Label | Example Modules |
|-------|----------|-------|-----------------|
| 1 | `profile` | Profile & Config | profile-selection, config-tuning |
| 2 | `language-config` | Language Configs | ruff-config, biome-config |
| 3 | `universal-config` | Universal Configs | editorconfig, markdownlint, codespell |
| 4 | `hooks` | Hooks | lefthook, claude-settings |
| 5 | `agent` | Agent Instructions | agent-rules |
| 6 | `ci` | CI Pipeline | github-actions |
| 7 | `tools` | Tool Installation | tool-install |
| 8 | `baseline` | Baseline | baseline |

---

## Module Registry

All modules are registered in a flat array. Order in the array determines
display order within a category. Detection and dependency resolution are
handled by the framework.

```typescript
const ALL_INIT_MODULES: readonly InitModule[] = [
  profileSelectionModule,     // profile
  configTuningModule,         // profile
  ruffConfigModule,           // language-config
  biomeConfigModule,          // language-config
  editorconfigModule,         // universal-config
  markdownlintConfigModule,   // universal-config
  codespellConfigModule,      // universal-config
  lefthookModule,             // hooks
  claudeSettingsModule,       // hooks
  agentRulesModule,           // agent
  githubActionsModule,        // ci
  toolInstallModule,          // tools
  baselineModule,             // baseline
];
```

---

## Module Specifications

### profile-selection

| Field | Value |
|-------|-------|
| id | `profile-selection` |
| category | `profile` |
| detect | Always true |
| defaultEnabled | true |
| dependsOn | none |

**Prompts:**
- Choice: strict / standard / minimal (default: standard)

**Execute:**
- Writes `.ai-guardrails/config.toml` with selected profile

---

### config-tuning

| Field | Value |
|-------|-------|
| id | `config-tuning` |
| category | `profile` |
| detect | Always true |
| defaultEnabled | true |
| dependsOn | `profile-selection` |

**Prompts:**
- Number: line_length (60-200, default: 88)
- Choice: indent_width (2 or 4, default: 2)
- Comma-separated: rules to ignore (empty to skip)
- Comma-separated: additional paths to exclude (empty to skip)

**Execute:**
- Updates `.ai-guardrails/config.toml` with tuning values

---

### ruff-config

| Field | Value |
|-------|-------|
| id | `ruff-config` |
| category | `language-config` |
| detect | Python detected |
| defaultEnabled | true |
| disableFlag | `--no-ruff` |
| dependsOn | `config-tuning` |

**Execute:**
- Calls `ruffGenerator.generate(config)` → writes `ruff.toml`
- Uses config merge strategy

---

### biome-config

| Field | Value |
|-------|-------|
| id | `biome-config` |
| category | `language-config` |
| detect | TypeScript detected |
| defaultEnabled | true |
| disableFlag | `--no-biome` |
| dependsOn | `config-tuning` |

**Execute:**
- Detects biome version + noConsole level
- Calls `biomeGenerator.generate(config)` → writes `biome.jsonc`
- Uses config merge strategy

---

### editorconfig

| Field | Value |
|-------|-------|
| id | `editorconfig` |
| category | `universal-config` |
| detect | Always true |
| defaultEnabled | true |
| disableFlag | `--no-editorconfig` |
| dependsOn | `config-tuning` |

**Execute:**
- Calls `editorconfigGenerator.generate(config)` → writes `.editorconfig`

---

### markdownlint-config

| Field | Value |
|-------|-------|
| id | `markdownlint-config` |
| category | `universal-config` |
| detect | Always true |
| defaultEnabled | true |
| disableFlag | `--no-markdownlint` |
| dependsOn | `config-tuning` |

**Execute:**
- Calls `markdownlintGenerator.generate(config)` → writes `.markdownlint.jsonc`

---

### codespell-config

| Field | Value |
|-------|-------|
| id | `codespell-config` |
| category | `universal-config` |
| detect | Always true |
| defaultEnabled | true |
| disableFlag | `--no-codespell` |
| dependsOn | `config-tuning` |

**Execute:**
- Calls `codespellGenerator.generate(config)` → writes `.codespellrc`

---

### lefthook

| Field | Value |
|-------|-------|
| id | `lefthook` |
| category | `hooks` |
| detect | Always true |
| defaultEnabled | true |
| disableFlag | `--no-hooks` |
| dependsOn | `config-tuning` |

**Execute:**
- Calls `lefthookGenerator` → writes `lefthook.yml`
- Runs `lefthook install`

---

### claude-settings

| Field | Value |
|-------|-------|
| id | `claude-settings` |
| category | `hooks` |
| detect | Always true |
| defaultEnabled | true |
| disableFlag | `--no-agent-hooks` |
| dependsOn | `config-tuning` |

**Execute:**
- Calls `claudeSettingsGenerator.generate(config)` → writes `.claude/settings.json`

---

### agent-rules

| Field | Value |
|-------|-------|
| id | `agent-rules` |
| category | `agent` |
| detect | Any AI tool detected (Claude, Cursor, Windsurf, Copilot, Cline) |
| defaultEnabled | true |
| disableFlag | `--no-agent-rules` |
| dependsOn | none |

**Execute:**
- Calls `setupAgentInstructionsStep` → writes `base.md` + tool symlinks

---

### github-actions

| Field | Value |
|-------|-------|
| id | `github-actions` |
| category | `ci` |
| detect | `.git` directory exists |
| defaultEnabled | true |
| disableFlag | `--no-ci` |
| dependsOn | none |

**Execute:**
- Calls `setupCiStep` → writes `.github/workflows/ai-guardrails.yml`

---

### tool-install

| Field | Value |
|-------|-------|
| id | `tool-install` |
| category | `tools` |
| detect | Any runner tool missing |
| defaultEnabled | true |
| dependsOn | `profile-selection` |

**Prompts (per missing tool):**
- Y/N: Install <tool>? Shows install command.

**Execute:**
- Runs install command for each approved tool

---

### baseline

| Field | Value |
|-------|-------|
| id | `baseline` |
| category | `baseline` |
| detect | Always true |
| defaultEnabled | true |
| disableFlag | `--no-baseline` |
| dependsOn | all config modules, `tool-install` |

**Execute:**
- Runs all linters → writes `.ai-guardrails/baseline.json`
- Reports issue count

---

## Wizard Flow

```
ai-guardrails init

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
  ? Generate ruff.toml (Python)?           [Y/n]
  ? Generate biome.jsonc (TypeScript)?     [Y/n]

  ── Universal Configs ─────────────────────
  ? Generate .editorconfig?                [Y/n]
  ? Generate .markdownlint.jsonc?          [Y/n]
  ? Generate .codespellrc?                 [Y/n]

  ── Hooks ─────────────────────────────────
  ? Install lefthook pre-commit hooks?     [Y/n]
  ? Generate .claude/settings.json?        [Y/n]

  ── Agent Instructions ────────────────────
  ? Generate agent rule files?             [Y/n]

  ── CI Pipeline ───────────────────────────
  ? Generate GitHub Actions workflow?      [Y/n]

  ── Tools ─────────────────────────────────
  ? Install ruff?                          [Y/n]
  ? Install pyright?                       [Y/n]

  ── Baseline ──────────────────────────────
  ? Capture initial baseline?              [Y/n]

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

## Non-Interactive Mode

`--yes` or non-TTY: skip all prompts, use `defaultEnabled` for each module.
Equivalent to current `init` behavior. Every feature ON with standard profile.

`--no-X` flags: override specific modules off before wizard runs.

---

## CLI Flags (updated from SPEC-004)

```
ai-guardrails init
  --yes                Accept all defaults (non-interactive)
  --profile <p>        Preselect profile
  --force              Overwrite existing managed files
  --upgrade            Refresh generated files, preserve config.toml
  --interactive        Force interactive mode
  --config-strategy    merge|replace|skip
  --no-hooks           Skip lefthook
  --no-ci              Skip CI workflow
  --no-agent-rules     Skip agent instruction files
  --no-agent-hooks     Skip .claude/settings.json
  --no-baseline        Skip initial baseline
  --no-editorconfig    Skip .editorconfig
  --no-markdownlint    Skip .markdownlint.jsonc
  --no-codespell       Skip .codespellrc
  --no-ruff            Skip ruff.toml
  --no-biome           Skip biome.jsonc
```

---

## Module File Structure

```
src/init/
  types.ts             # InitModule, InitContext, InitCategory, InitModuleResult
  registry.ts          # ALL_INIT_MODULES
  wizard.ts            # Interactive prompt flow grouped by category
  runner.ts            # Dependency-aware module executor (topological sort)
  prompt.ts            # Low-level: askYesNo, askChoice, askText, askCommaSeparated
  modules/
    profile-selection.ts
    config-tuning.ts
    ruff-config.ts
    biome-config.ts
    editorconfig.ts
    markdownlint-config.ts
    codespell-config.ts
    lefthook.ts
    claude-settings.ts
    agent-rules.ts
    github-actions.ts
    tool-install.ts
    baseline.ts
```

---

## Dependency Graph

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

agent-rules (independent)
github-actions (independent)

tool-install (depends on: profile-selection)

baseline (depends on: ALL config modules + tool-install)
```

---

## Migration Path

1. Existing generators in `src/generators/` stay untouched — modules call them
2. Existing steps in `src/steps/` stay untouched — modules call them
3. New `src/init/` directory wraps existing functionality
4. `src/pipelines/init.ts` rewritten to use module system
5. `src/pipelines/install.ts` becomes thin wrapper (all modules enabled)
6. `--yes` produces identical output to current behavior (backward compat)

---

## Test Strategy

| Test | What |
|------|------|
| `prompt.test.ts` | askYesNo, askChoice, askText with FakeReadline |
| `runner.test.ts` | Topological sort, skip disabled, dependency chain |
| `wizard.test.ts` | Integration: wizard with pre-programmed answers |
| `modules/*.test.ts` | Each module: detect + execute with fakes |
| `init-pipeline.test.ts` | End-to-end: --yes produces backward-compat output |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Init completed successfully |
| 1 | Init failed (config error, write failure) |
| 2 | Config already exists (use --force/--upgrade) |

---

## Success Criteria

- [ ] Every generator/step is wrapped by an InitModule
- [ ] Wizard prompts for each applicable module
- [ ] `--yes` produces identical output to current init
- [ ] Each `--no-X` flag disables exactly one module
- [ ] Adding a new init feature = adding one module file + registry entry
- [ ] All existing init tests pass (backward compat)
- [ ] 13 modules, each with detect + execute tests
