# Interactive Init — Feature Design

## Concept

`ai-guardrails init` becomes a guided wizard. Every feature gets a y/n prompt.
User sees what will be created, confirms each module, and the tool only installs
what they approved. Non-interactive mode (`--yes`) accepts all defaults.

## Init Flow

```
ai-guardrails init

  AI Guardrails Setup
  ═══════════════════

  Detected languages: TypeScript, Python
  Detected tools: Claude Code, Cursor

  ── Profile ──────────────────────────────────
  ? Select enforcement profile:
    > standard (recommended)
      strict
      minimal

  ── Language Configs ─────────────────────────
  ? Generate ruff.toml for Python?              [Y/n]
  ? Generate biome.jsonc for TypeScript?        [Y/n]

  ── Universal Configs ────────────────────────
  ? Generate .editorconfig?                     [Y/n]
  ? Generate .markdownlint.jsonc?               [Y/n]
  ? Generate .codespellrc?                      [Y/n]

  ── Pre-commit Hooks ─────────────────────────
  ? Install lefthook pre-commit hooks?          [Y/n]
    Includes: biome-fix, ruff-fix, gitleaks,
    codespell, markdownlint, suppress-comments,
    no-commits-to-main, conventional-commits

  ── AI Agent Hooks (Claude Code) ─────────────
  ? Generate .claude/settings.json with
    PreToolUse safety hooks?                    [Y/n]
    Includes: dangerous-cmd blocker,
    config protection, read protection

  ── AI Agent Rules ───────────────────────────
  ? Generate agent instruction files?           [Y/n]
    Detected: Claude Code, Cursor
    Creates: .ai-guardrails/agent-rules/base.md
             .cursorrules (symlink)

  ── CI Pipeline ──────────────────────────────
  ? Generate GitHub Actions workflow?           [Y/n]
    Creates: .github/workflows/ai-guardrails.yml

  ── Baseline ─────────────────────────────────
  ? Capture initial baseline snapshot?          [Y/n]
    Runs all linters, saves current state so
    future checks only fail on NEW issues

  ── Config Tuning ────────────────────────────
  ? Line length (default: 88):                  [88]
  ? Indent width:
    > 2 (recommended for web)
      4

  ? Rules to ignore (comma-separated, or empty):
    Example: ruff/E501, biome/noConsole
    >

  ? Paths to exclude from checks:
    Default: node_modules/**, .venv/**, dist/**
    Additional (comma-separated, or empty):
    >

  ── Hook Config ──────────────────────────────
  ? Additional files to protect from AI edits:
    Default: .env*, package.json, tsconfig.json
    Additional (comma-separated, or empty):
    >

  ? Disable any dangerous-command rule groups?
    [ ] destructive-rm
    [ ] git-force-push
    [ ] git-destructive
    [ ] git-bypass-hooks
    [ ] chmod-world-writable
    [ ] remote-code-exec

  ═══════════════════════════════════════════════

  Summary:
    Profile:        standard
    Languages:      TypeScript, Python
    Configs:        ruff.toml, biome.jsonc, .editorconfig,
                    .markdownlint.jsonc, .codespellrc
    Pre-commit:     lefthook (8 hooks)
    Claude hooks:   dangerous-cmd, protect-configs, protect-reads
    Agent rules:    base.md + .cursorrules
    CI:             GitHub Actions
    Baseline:       yes (snapshot after setup)

  ? Proceed with installation?                  [Y/n]

  ✓ Config written: .ai-guardrails/config.toml
  ✓ Generated: ruff.toml
  ✓ Generated: biome.jsonc
  ...
  ✓ Hooks installed (lefthook)
  ✓ Baseline captured: 12 issues
  ✓ Done! Run `ai-guardrails check` to verify.
```

## Feature Modules (y/n toggleable)

### Module 1: Profile Selection
- strict / standard / minimal
- Affects rule severity across all linters
- Default: standard

### Module 2: Language-Specific Configs
- Per-detected-language generator toggle
- `ruff.toml` (Python) — y/n
- `biome.jsonc` (TypeScript) — y/n
- Future: per-language strictness variants

### Module 3: Universal Configs
- `.editorconfig` — y/n (default: y)
- `.markdownlint.jsonc` — y/n (default: y)
- `.codespellrc` — y/n (default: y)

### Module 4: Pre-commit Hooks (lefthook)
- All-or-nothing toggle for now
- Future: per-hook toggles (gitleaks y/n, codespell y/n, etc.)
- Creates `lefthook.yml` + runs `lefthook install`
- Default: y

### Module 5: AI Agent Hooks (Claude Code PreToolUse)
- `.claude/settings.json` with deny globs + PreToolUse hooks
- dangerous-cmd blocker
- protect-configs blocker
- protect-reads blocker
- Default: y

### Module 6: Agent Instruction Files
- `.ai-guardrails/agent-rules/base.md`
- Tool-specific symlinks (Cursor, Windsurf, Copilot, Cline)
- Only for detected tools
- Default: y

### Module 7: CI Workflow
- `.github/workflows/ai-guardrails.yml`
- Future: GitLab CI, Bitbucket Pipelines
- Default: y

### Module 8: Initial Baseline
- Run all linters, capture baseline snapshot
- `.ai-guardrails/baseline.json`
- Makes `check` pass immediately (all existing issues baselined)
- Default: y (new addition — not currently part of init)

### Module 9: Config Tuning
- line_length (number, default 88)
- indent_width (2 or 4, default 2)
- ignore rules (comma-separated)
- ignore_paths (comma-separated, added to defaults)

### Module 10: Hook Config
- Additional managed_files
- Additional managed_paths
- Additional protected_read_paths
- disabled_groups selection

## CLI Flags

```
ai-guardrails init
  --yes                     Accept all defaults (non-interactive)
  --profile <p>             Preselect profile
  --no-hooks                Skip pre-commit hooks
  --no-ci                   Skip CI workflow
  --no-agent-rules          Skip agent instruction files
  --no-agent-hooks          Skip .claude/settings.json (NEW)
  --no-baseline             Skip initial baseline (NEW)
  --no-editorconfig         Skip .editorconfig (NEW)
  --no-markdownlint         Skip .markdownlint.jsonc (NEW)
  --no-codespell            Skip .codespellrc (NEW)
  --config-strategy <s>     merge|replace|skip
  --force                   Overwrite all
  --interactive             Force interactive mode
```

## Implementation Architecture

### Current: monolithic pipeline
```
init → detect → check-prereqs → install-prereqs → install pipeline (all steps)
```

### New: modular pipeline with feature flags
```
init → detect → prompt (interactive) → build feature set → install pipeline (selected steps)
```

The prompt step produces a `FeatureSet` object:
```typescript
interface FeatureSet {
  profile: Profile;
  languages: LanguagePlugin[];      // detected, confirmed by user
  generators: {
    ruff: boolean;
    biome: boolean;
    editorconfig: boolean;
    markdownlint: boolean;
    codespell: boolean;
  };
  hooks: {
    lefthook: boolean;
    claudeSettings: boolean;        // .claude/settings.json
  };
  agentRules: boolean;
  ci: boolean;
  baseline: boolean;
  config: {
    lineLength: number;
    indentWidth: 2 | 4;
    ignoreRules: string[];
    ignorePaths: string[];
    managedFiles: string[];
    disabledGroups: string[];
  };
}
```

Each step in the install pipeline checks the relevant FeatureSet field before running.

## Prompt Implementation

Use the existing `ctx.createReadline()` abstraction (from #152). Each prompt
is a function that reads a line and returns a parsed value. No external TUI
library — just simple stdin/stdout questions.

```typescript
async function askYesNo(rl: ReadlineInterface, question: string, defaultYes: boolean): Promise<boolean>
async function askChoice(rl: ReadlineInterface, question: string, options: string[], defaultIdx: number): Promise<string>
async function askText(rl: ReadlineInterface, question: string, defaultValue: string): Promise<string>
async function askMultiSelect(rl: ReadlineInterface, question: string, options: string[]): Promise<string[]>
```

## Non-interactive Mode

`--yes` or non-TTY: skip all prompts, use defaults. Every feature ON with
standard profile. Equivalent to current behavior.

## Phases

### Phase 1: FeatureSet type + prompt functions
- Define FeatureSet interface
- Implement askYesNo, askChoice, askText
- Wire into init pipeline

### Phase 2: Per-generator toggles
- Each generator checks FeatureSet before running
- CLI flags for --no-editorconfig etc.

### Phase 3: Baseline as init step
- Add baseline capture after all configs generated
- Prompt: "Capture initial baseline?"

### Phase 4: Hook config prompts
- managed_files, protected_read_paths, disabled_groups
- Written to config.toml
