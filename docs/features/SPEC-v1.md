# AI Guardrails — Product Specification v1.0

## Philosophy

> "If you build a structure around agents and people that physically forces them
> to follow the rules of the project, you don't have to be angry at the final
> output and wonder where it went wrong."

AI-native codebases get sloppy. Markdown rules don't force AI agents to do what
you said. `CLAUDE.md` is a suggestion. `ruff.toml` is enforcement.

**Core principles:**

1. **Everything is an error or it's ignored.** No warnings. No "acknowledged."
   Every deviation is registered with a reason, or it blocks.
2. **Structural enforcement > documentation.** External tools that check you
   are better than rules you have to remember.
3. **One setup, every project.** Same rules everywhere means humans and agents
   navigate between projects without re-learning.
4. **Audit trail is the control.** Every exception has a reason. Every reason
   has an owner. Expiring exceptions force re-evaluation.
5. **Config tamper protection.** AI agents cannot weaken their own rules.
   Generated configs are owned by the tool, not the developer.

---

## What ai-guardrails IS

A CLI tool that enforces pedantic code quality on AI-maintained repositories.
Four components:

| Component | What it does |
|-----------|-------------|
| **Config generator** | Merges base templates + exception registry into tool configs |
| **Hook orchestrator** | Generates lefthook config, installs Claude Code hooks |
| **Policy engine** | Exception registry with audit trail, tamper detection |
| **Compliance checker** | Runs all linters, reports unified pass/fail |

**What it is NOT:**

- Not a linter (it configures and orchestrates linters)
- Not a review bot (guardrails-review is separate, optional integration)
- Not a service (zero runtime — runs at commit time, CI time, or on-demand)

---

## Target User

- **Now:** Solo developer managing multiple repos with AI coding agents
- **6 months:** Small team (2-5 devs) adopting guardrails across shared repos
- **12 months:** Open source, community-contributed language packs and profiles

---

## Supported Languages

All detection, config generation, and hook setup for:

| Language | Linter/Formatter | Config file |
|----------|-----------------|-------------|
| Python | ruff | ruff.toml |
| TypeScript/JavaScript | biome | biome.json |
| C#/.NET | roslyn analyzers | Directory.Build.props, .globalconfig |
| Rust | rustfmt + clippy | rustfmt.toml |
| C/C++ | clang-format + clang-tidy | .clang-format, .clang-tidy |
| Lua | stylua | stylua.toml |
| Go | go vet + staticcheck | (go.mod) |
| Shell | shellcheck + shfmt | (args in lefthook.yml) |

Language detection via `configs/languages.yaml` — single source of truth for
detection rules, config mappings, and hook templates.

---

## Architecture

### Pattern: Pipeline + Plugin with Dependency Injection

```
CLI (cyclopts) → Command dataclass → Pipeline → [Step, Step, ...] → Output
```

### Layer diagram

```
┌──────────────────────────────────────────────────┐
│                   CLI Layer                        │
│  cyclopts parses args → validated dataclass        │
│  Dispatches to appropriate pipeline                │
└──────────────┬───────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────┐
│               Pipeline Layer                       │
│  InitPipeline, GeneratePipeline, etc.              │
│  Orchestrates steps in order                       │
│  Handles dry-run, error aggregation                │
└──────────────┬───────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────┐
│               Step Layer (Plugins)                 │
│  DetectLanguages, CopyConfigs, GenerateHooks, ...  │
│  Each step: validate() → execute() → report()     │
└──────────────┬───────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────┐
│             Infrastructure Layer                   │
│  FileManager  — all filesystem ops                 │
│  CommandRunner — all subprocess calls              │
│  ConfigLoader — TOML/YAML/JSON parse + validate    │
│  Console — all user-facing output                  │
└──────────────────────────────────────────────────┘
```

### Key design rules

- **No module-level Path.home()** — inject all paths
- **No direct subprocess.run()** — go through CommandRunner
- **No print()** — go through Console
- **No dict[str, Any] across module boundaries** — dataclasses or TypedDict
- **Max 200 lines per module** — one concern per file
- **All public functions typed** — pyright strict mode

---

## Project Structure

```
ai-guardrails/
├── src/
│   └── ai_guardrails/
│       ├── __init__.py              # version only
│       ├── __main__.py              # python -m ai_guardrails
│       ├── cli.py                   # cyclopts app, command dispatch
│       │
│       ├── commands/                # validated command dataclasses
│       │   ├── install_cmd.py
│       │   ├── init_cmd.py
│       │   ├── generate_cmd.py
│       │   ├── status_cmd.py
│       │   └── check_cmd.py
│       │
│       ├── pipelines/               # pipeline orchestrators
│       │   ├── install_pipeline.py
│       │   ├── init_pipeline.py
│       │   ├── generate_pipeline.py
│       │   ├── status_pipeline.py
│       │   └── check_pipeline.py
│       │
│       ├── steps/                   # individual pipeline steps
│       │   ├── detect_languages.py
│       │   ├── copy_configs.py
│       │   ├── generate_linter_configs.py
│       │   ├── generate_hooks.py
│       │   ├── scaffold_registry.py
│       │   ├── setup_ci.py
│       │   ├── setup_agent_instructions.py
│       │   └── setup_claude_hooks.py
│       │
│       ├── generators/              # config file generators
│       │   ├── base.py              # Generator protocol
│       │   ├── ruff.py
│       │   ├── biome.py
│       │   ├── markdownlint.py
│       │   ├── codespell.py
│       │   ├── editorconfig.py
│       │   ├── lefthook.py
│       │   └── claude_settings.py
│       │
│       ├── hooks/                   # hook implementations (called by lefthook)
│       │   ├── format_stage.py
│       │   ├── suppress_comments.py
│       │   ├── protect_configs.py
│       │   └── dangerous_cmd.py
│       │
│       ├── infra/                   # infrastructure abstractions
│       │   ├── file_manager.py
│       │   ├── command_runner.py
│       │   ├── config_loader.py
│       │   └── console.py
│       │
│       ├── models/                  # domain models
│       │   ├── registry.py          # ExceptionRegistry, FileException
│       │   ├── language.py          # LanguageConfig, DetectionRules
│       │   └── project.py           # ProjectInfo
│       │
│       └── constants.py             # suppression patterns, dangerous commands
│
├── configs/                         # base config templates (package data)
│   ├── languages.yaml               # single source of truth
│   ├── versions.toml                # all pinned tool versions
│   ├── ruff.toml                    # base strict config
│   ├── biome.json
│   ├── rustfmt.toml
│   ├── stylua.toml
│   ├── .clang-format
│   ├── .clang-tidy
│   ├── .editorconfig
│   ├── .markdownlint.jsonc
│   └── .codespellrc
│
├── templates/                       # templates for generated files
│   ├── lefthook/                    # hook templates per language
│   │   ├── base.yaml
│   │   ├── python.yaml
│   │   ├── node.yaml
│   │   ├── dotnet.yaml
│   │   ├── rust.yaml
│   │   ├── cpp.yaml
│   │   ├── lua.yaml
│   │   ├── go.yaml
│   │   └── shell.yaml
│   ├── workflows/
│   │   └── check.yml
│   ├── claude-settings.json         # CC hooks + permissions template
│   ├── guardrails-exceptions.toml   # registry scaffold
│   └── CLAUDE.md.guardrails         # agent instructions append
│
├── schemas/                         # JSON schemas for validation
│   └── guardrails-exceptions.schema.json
│
├── tests/
│   ├── conftest.py                  # FakeFileManager, FakeCommandRunner
│   ├── test_cli.py
│   ├── steps/
│   ├── generators/
│   ├── hooks/
│   └── infra/
│
├── pyproject.toml
├── CLAUDE.md
└── README.md
```

---

## Commands

### `ai-guardrails install`

**Scope:** Global, once per machine. Updates via `ai-guardrails install --upgrade`.

**What it does:**

1. Verifies prerequisites (Python 3.11+, git, lefthook)
2. Reports missing optional tools (ruff, biome, etc.) with install commands
3. Creates `~/.ai-guardrails/config.toml` with global preferences
4. Installs Claude Code PreToolUse hooks into `~/.claude/settings.json`

**Global config (`~/.ai-guardrails/config.toml`):**

```toml
[install]
version = "1.0.0"
installed_at = "2026-03-01T12:00:00Z"

[preferences]
default_languages = []  # empty = auto-detect
```

**Claude Code global hooks installed:**

- `dangerous-command-check` — blocks rm -rf /, --no-verify, etc.
- `protect-generated-configs` — blocks direct edits to generated files

**Prerequisites checked:**

| Tool | Required | Check | Install hint |
|------|----------|-------|-------------|
| Python 3.11+ | Yes | `python3 --version` | System package manager |
| git | Yes | `git --version` | System package manager |
| lefthook | Yes | `lefthook --version` | `brew install lefthook` or `go install` |
| uv | Recommended | `uv --version` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| ruff | For Python | `ruff --version` | `uv tool install ruff` |
| biome | For Node | `biome --version` | `npm i -g @biomejs/biome` |

### `ai-guardrails init`

**Scope:** Per-project, interactive with confirmation.

**Flow:**

```
1. Detect languages (from languages.yaml rules)
2. Show what will be created
3. Ask Y/N confirmation
4. Copy base configs (.editorconfig, .markdownlint.jsonc, .codespellrc)
5. Copy language-specific configs (ruff.toml, biome.json, etc.)
6. Scaffold .guardrails-exceptions.toml (exception registry)
7. Generate all tool configs from registry
8. Generate lefthook.yml from language templates
9. Generate .claude/settings.json (project-level CC hooks)
10. Generate CI workflow (.github/workflows/check.yml)
11. Append guardrails section to CLAUDE.md (+ symlink AGENTS.md)
12. Run lefthook install
13. Show summary
```

**What gets committed to the project:**

```
project/
├── .claude/
│   └── settings.json              # CC project-level hooks + permissions
├── .github/
│   └── workflows/
│       └── check.yml              # CI workflow
├── .codespellrc
├── .editorconfig
├── .guardrails-exceptions.toml    # THE registry
├── .markdownlint.jsonc
├── .secrets.baseline              # detect-secrets baseline
├── AGENTS.md                      # symlink → CLAUDE.md
├── CLAUDE.md                      # agent instructions (appended)
├── lefthook.yml                   # hook config
├── ruff.toml                      # generated (Python)
├── biome.json                     # generated (Node)
├── Directory.Build.props          # copied (C#)
├── .globalconfig                  # copied (C#)
├── rustfmt.toml                   # copied (Rust)
├── stylua.toml                    # copied (Lua)
├── .clang-format                  # copied (C++)
└── .clang-tidy                    # copied (C++)
```

**No `.ai-guardrails/` directory in projects.** No gitignored files. No shell
shims. No Python runtime copies.

**Flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--force` | false | Overwrite existing configs (backs up to .bak) |
| `--type LANG` | auto | Skip detection, use specified language |
| `--all` | false | Install configs for all languages |
| `--no-hooks` | false | Skip lefthook setup |
| `--no-ci` | false | Skip CI workflow |
| `--no-agent-instructions` | false | Skip CLAUDE.md/AGENTS.md |
| `--dry-run` | false | Show what would be done, change nothing |

### Edge cases for `init`

**Re-init on existing project (no `--force`):**

- Existing configs are SKIPPED with a message: `"ruff.toml exists (use --force)"`.
- `.guardrails-exceptions.toml` is NEVER overwritten — it's user data.
- CLAUDE.md is only APPENDED to if the guardrails section is missing.

**Re-init with `--force`:**

- Existing generated configs (ruff.toml, lefthook.yml, etc.) are backed up to
  `.bak` and regenerated from the registry.
- `.guardrails-exceptions.toml` is PRESERVED (never overwritten with `--force`).
- CLAUDE.md guardrails section is replaced if already present.

**Partial failure:**

- Init is NOT atomic. If step 8 fails, steps 1-7 remain.
- This is acceptable — each step is idempotent. Re-running `init` picks up
  where it left off (existing files are skipped or regenerated).
- No rollback mechanism needed.

**Monorepo with multiple languages:**

- Detection finds all languages present (e.g., Python + Node).
- All relevant configs are generated (ruff.toml + biome.json).
- lefthook.yml includes hooks for all detected languages.
- Language-specific hooks only fire on matching file globs.

### `ai-guardrails generate`

**Scope:** Per-project, regenerates all tool configs from exception registry.

**What it does:**

1. Read `.guardrails-exceptions.toml`
2. Read `configs/languages.yaml` (from package data)
3. Detect languages — always re-detects from filesystem (no cache).
   Override with `--languages python,node` flag.
4. For each detected language, merge base config + exceptions → output config
5. Generate lefthook.yml from language templates
6. Validate generated configs (TOML syntax, rule ID validity)
7. Report what changed

**Exception registry format (`.guardrails-exceptions.toml`):**

```toml
[metadata]
created_by = "ai-guardrails init"
created_at = "2026-03-01"

[global]
# Exceptions applied to ALL tools
codespell_ignore_words = ["uint", "crate"]

[[exceptions]]
tool = "ruff"
rule = "T201"
reason = "CLI tool — print() is expected output"

[[exceptions]]
tool = "ruff"
rule = "S101"
reason = "assert is acceptable in tests"
scope = "tests/**/*.py"

[[exceptions]]
tool = "ruff"
rule = "PLR0913"
reason = "init entrypoint has many keyword args by design"
scope = "src/ai_guardrails/pipelines/init_pipeline.py"
expires = "2026-06-01"

[[file_exceptions]]
glob = "tests/**/*.py"
tool = "ruff"
rules = ["S101", "PLR2004", "ARG001", "D100", "D103", "SLF001"]
reason = "Test files: asserts, magic values, unused args, no docstrings"

[custom]
# Escape hatch: raw config merged into generated output
[custom.ruff]
# Merged directly into ruff.toml [lint] section
"lint.pylint.max-args" = 7  # override default 5 for this project
```

**Tamper protection:**

Generated configs include a hash comment:

```toml
# ai-guardrails:hash:sha256:abc123def456
# Generated from .guardrails-exceptions.toml — do not edit directly.
# Run: ai-guardrails generate
```

`ai-guardrails generate --check` exits non-zero if any generated config
doesn't match the hash (used in CI and lefthook).

### `ai-guardrails status` (future, simple first)

**MVP:** Show detected languages, exception count, config freshness.

**Endgoal:** Compliance score, exception summary (with expiring-soon warnings),
tool versions with drift detection, config freshness, hook installation status.

### `ai-guardrails check` (future)

**MVP:** Run all configured linters via lefthook in one command.

**Endgoal:** Unified pass/fail with structured output (JSON, SARIF).

---

## Hook Architecture

### Enforcement layers

ai-guardrails enforces at THREE levels, each catching different things:

| Layer | When | What it catches | Mechanism |
|-------|------|-----------------|-----------|
| **Claude Code hooks** | Before tool execution | AI agent editing generated configs, running dangerous commands | PreToolUse hooks + permissions deny list |
| **Lefthook (git hooks)** | At commit time | Lint errors, suppression comments, config tampering, secrets | lefthook.yml commands |
| **CI** | At push/PR time | Everything lefthook catches + cross-file analysis | `lefthook run pre-commit` or `ai-guardrails check` |

CC hooks and lefthook hooks may check the same thing (e.g., suppress_comments).
This is intentional — defense in depth. CC hooks catch problems before they're
written to disk. Lefthook catches problems from any source (human, Copilot,
Cursor, manual edits).

### Lefthook as hook runner

ai-guardrails generates `lefthook.yml` from language templates. Hooks call
tools directly — no shell shims, no pre-commit abstraction layer.

**Generated lefthook.yml example (Python project):**

```yaml
# ai-guardrails:hash:sha256:abc123
# Generated — do not edit. Run: ai-guardrails generate
pre-commit:
  # Phase 1: Format and auto-fix (SERIAL — must complete before checks)
  commands:
    format-and-stage:
      glob: "*.py"
      run: ruff format {staged_files} && ruff check --fix {staged_files} && git add {staged_files}
      stage_fixed: true
      priority: 1

  # Phase 2: All checks (PARALLEL — run after formatting)
    ruff-check:
      glob: "*.py"
      run: ruff check {staged_files}
      priority: 2
    suppress-comments:
      glob: "*.{py,js,ts,rs,cs,go,lua,sh}"
      run: python -m ai_guardrails.hooks.suppress_comments {staged_files}
      priority: 2
    protect-configs:
      glob: "ruff.toml|biome.json|lefthook.yml|.editorconfig"
      run: python -m ai_guardrails.hooks.protect_configs {staged_files}
      priority: 2
    gitleaks:
      run: gitleaks detect --staged --no-banner
      priority: 2
    detect-secrets:
      glob: "!.secrets.baseline"
      run: detect-secrets-hook --baseline .secrets.baseline {staged_files}
      priority: 2
    codespell:
      glob: "*.{py,md,txt,yaml,yml,toml,json}"
      run: codespell --check-filenames {staged_files}
      priority: 2
    markdownlint:
      glob: "*.md"
      run: markdownlint-cli2 {staged_files}
      priority: 2
    validate-configs:
      run: python -m ai_guardrails generate --check
      priority: 2

commit-msg:
  commands:
    conventional:
      run: >-
        echo "{1}" | grep -qE
        "^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?!?:"
```

**Hook execution ordering:** Lefthook `priority` ensures format-and-stage
(priority 1) completes before all check commands (priority 2) run in parallel.
This prevents race conditions where checkers see pre-formatted code.

### Claude Code hooks (project-level)

Generated `.claude/settings.json`:

```json
{
  "permissions": {
    "deny": [
      "Edit(ruff.toml)",
      "Edit(biome.json)",
      "Edit(lefthook.yml)",
      "Edit(.editorconfig)",
      "Edit(.markdownlint.jsonc)",
      "Edit(.codespellrc)",
      "Bash(* --no-verify *)",
      "Bash(git commit * -n *)",
      "Bash(git push --force *)",
      "Bash(git push * --force *)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python -m ai_guardrails.hooks.dangerous_cmd"
          }
        ]
      }
    ]
  }
}
```

**Permission deny rules** handle the simple pattern matching (block edits to
generated files, block --no-verify). **PreToolUse hooks** handle the contextual
checks (dangerous-command-check with smart pattern analysis).

### Claude Code hooks (global, from `install`)

`~/.claude/settings.json` gets:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python -m ai_guardrails.hooks.dangerous_cmd"
          }
        ]
      }
    ]
  }
}
```

Global hooks are the safety net. Project-level hooks add project-specific
deny rules for generated config files.

---

## Exception Registry Design

### Format: TOML with JSON Schema validation

**Schema** (`schemas/guardrails-exceptions.schema.json`) provides:

- Editor autocomplete (VS Code, JetBrains)
- CI validation (`ai-guardrails generate --check` validates against schema)
- Type safety for all fields

### Exception types

| Type | Scope | Example |
|------|-------|---------|
| Global rule exception | All files | `rule = "T201"` (allow print) |
| Scoped rule exception | File pattern | `scope = "tests/**"`, `rule = "S101"` |
| File exception | Multiple rules for a glob | `glob = "tests/**"`, `rules = [...]` |
| Custom override | Raw config merge | `[custom.ruff]` section |

### Required fields

| Field | Required | Description |
|-------|----------|-------------|
| `tool` | Yes | Which tool this exception is for |
| `rule` | Yes (for [[exceptions]]) | Rule ID being suppressed |
| `reason` | Yes | Why this exception exists |
| `scope` | No | File glob pattern (omit = all files) |
| `expires` | No | ISO date after which exception is invalid |
| `owner` | No | Who approved this exception |

### Audit trail

The registry file IS the audit trail. Every exception has a documented reason.
Git history shows who added it and when. Expiring exceptions are flagged by
`ai-guardrails status`.

---

## Tool Version Pinning

All external tool versions are pinned in `configs/versions.toml`:

```toml
[tools]
ruff = ">=0.8"
biome = ">=2.0"
gitleaks = ">=8.20"
lefthook = ">=1.11"
```

Generators use these versions to:

- Select the correct config schema (biome v1 vs v2)
- Pin hook revisions in lefthook.yml
- Warn when installed tool version doesn't match

When a tool releases a breaking version (e.g., biome v3), the generator gets a
new codepath. `ai-guardrails init --upgrade` regenerates configs for the new
version. Old projects keep working until they upgrade.

Each generator is responsible for detecting the installed tool version and
generating compatible config. If the tool isn't installed, the generator uses
the pinned version as the target schema.

---

## Distribution

### Primary: `uv tool install`

```bash
uv tool install ai-guardrails
ai-guardrails install          # global setup
cd my-project && ai-guardrails init   # per-project
```

### Future: Homebrew / binary

```bash
brew install ai-guardrails     # macOS/Linux
```

### CI: pip in ephemeral environments

```bash
pip install ai-guardrails      # CI runners only
```

### Prerequisites

| Tool | Required by | Installed by user |
|------|------------|-------------------|
| Python 3.11+ | ai-guardrails itself | System package manager |
| git | hooks, CI | System package manager |
| lefthook | hook runner | `brew install lefthook` / `go install` / `npm i -g` |
| uv | Python project management | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

Tool-specific prerequisites (ruff, biome, etc.) checked at init time with
install hints.

---

## Dependencies

### Runtime

| Package | Version | Purpose |
|---------|---------|---------|
| cyclopts | >=4.0 | CLI framework |
| tomlkit | >=0.12 | TOML read/write preserving comments |
| pyyaml | >=6.0 | YAML read (languages.yaml, lefthook templates) |
| tomli-w | >=1.0 | TOML write (fast, for generation) |
| jsonschema | >=4.0 | Registry validation against JSON schema |

### Dev

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=8.0 | Testing |
| pytest-cov | >=4.0 | Coverage |
| ruff | >=0.4 | Lint + format |
| pyright | >=1.1 | Type checking |

### Removed from current

| Package | Why removed |
|---------|------------|
| pyinfra | Was used for install.py. Replaced by pure Python. |

---

## Testing Strategy

### Approach: New tests from spec, informed by old test context

Each module in `src/ai_guardrails/` gets a parallel test file.
Infrastructure fakes (not mocks) at the boundary.

### Fakes

```python
# tests/conftest.py

class FakeFileManager:
    """In-memory filesystem."""
    files: dict[Path, str]
    copied: list[tuple[Path, Path]]

class FakeCommandRunner:
    """Predetermined subprocess results."""
    responses: dict[str, CompletedProcess]
    calls: list[list[str]]

class FakeConsole:
    """Captured output."""
    lines: list[str]
```

### Coverage

- Target: 85%+ on all modules
- No `# pragma: no cover` without documented justification
- No file exclusions in coverage config
- CI enforces coverage threshold

### Test naming

`test_{function_name}_{scenario}_{expected}`

Example: `test_detect_languages_dotnet_project_returns_dotnet`

---

## CI Workflow

Generated `.github/workflows/check.yml`:

```yaml
name: AI Guardrails Check
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv tool install ai-guardrails
      - run: lefthook run pre-commit  # or ai-guardrails check
```

No `SKIP=` hacks. No gitignored dependencies. Everything needed is either
installed globally (ruff, lefthook) or committed to the repo (configs).

---

## Upgrade Path

### `ai-guardrails init --upgrade`

1. Reads existing `.guardrails-exceptions.toml` (preserves user exceptions)
2. Regenerates all tool configs with latest templates
3. Updates lefthook.yml with latest hook versions
4. Updates CI workflow template
5. Shows diff of what changed before applying
6. Asks Y/N confirmation

### `ai-guardrails install --upgrade`

1. Updates the `ai-guardrails` CLI to latest version
2. Updates global Claude Code hooks
3. Updates `~/.ai-guardrails/config.toml` version marker

---

## Multi-repo (future phases)

### Phase 1: Per-repo manual

`ai-guardrails init --upgrade` in each repo.

### Phase 2: Org scan

`ai-guardrails org scan ~/Projects` — finds all repos with
`.guardrails-exceptions.toml`, shows version drift, offers batch upgrade.

### Phase 3: Auto PRs

`ai-guardrails org upgrade --pr` — creates upgrade PRs in each drifted repo.
Like Renovate/Dependabot for guardrails configs.

---

## Competitive Positioning

### What no competitor does

1. **Auditable exception registry** with reason + expiry + scope
2. **Config tamper protection** — AI agents can't weaken their own rules
3. **AI agent hook integration** — Claude Code PreToolUse enforcement
4. **Generated-config ownership** — tool configs are derived, not hand-edited
5. **Multi-language from one source** — single exception registry drives
   ruff.toml, biome.json, lefthook.yml, and more

### Closest competitors

| Tool | Gap ai-guardrails fills |
|------|------------------------|
| trunk.io | No exception registry. Flexible where we're opinionated. |
| MegaLinter | CI-only, no local hooks, no policy engine. |
| pre-commit | Hook runner only. No config generation, no policy. |
| lefthook | Hook runner only. We generate lefthook.yml. |

---

## Implementation Order

### MVP: Install + Init + Generate

1. **Infrastructure layer** — FileManager, CommandRunner, ConfigLoader, Console
2. **Models** — ExceptionRegistry, LanguageConfig, ProjectInfo
3. **Generators** — ruff, lefthook, editorconfig, markdownlint, codespell
4. **Steps** — DetectLanguages, CopyConfigs, ScaffoldRegistry, GenerateConfigs
5. **Pipelines** — InstallPipeline, InitPipeline, GeneratePipeline
6. **CLI** — cyclopts app with install, init, generate commands
7. **Hooks** — suppress_comments, protect_configs, dangerous_cmd
8. **Templates** — lefthook per-language, CI workflow, CC settings

### Post-MVP

- `status` command (compliance + freshness)
- `check` command (unified lint runner)
- `comments` command (PR thread management)
- JSON schema for exception registry
- Multi-repo org scan
- Additional generators (biome, claude-settings)

---

## Generator Inventory

### Generators that merge exceptions from registry

| Generator | Output | Format | Base config | Merge algorithm |
|-----------|--------|--------|-------------|----------------|
| **ruff** | `ruff.toml` | TOML | `configs/ruff.toml` | Base + global ignores union + per-file-ignores append |
| **biome** | `biome.json` | JSON | `configs/biome.json` | Base + overrides array for file exceptions |
| **markdownlint** | `.markdownlint.jsonc` | JSONC | `configs/.markdownlint.jsonc` | Base + rule disables |
| **codespell** | `.codespellrc` | INI | None (scratch) | Generated from `[global.codespell]` registry section |
| **allowlist** | `.suppression-allowlist` | Text | None (scratch) | Generated from `[[inline_suppressions]]` entries |
| **lefthook** | `lefthook.yml` | YAML | `templates/lefthook/base.yaml` | Base + per-language hook templates merged |
| **claude-settings** | `.claude/settings.json` | JSON | `templates/claude-settings.json` | Template + dynamic deny rules from GENERATED_CONFIGS |
| **ci-workflow** | `.github/workflows/check.yml` | YAML | `templates/workflows/check.yml` | Template + language-conditional steps |

### Generators that copy base configs (no exception merge)

| Generator | Output | Language | Notes |
|-----------|--------|----------|-------|
| **editorconfig** | `.editorconfig` | Universal | Identical across all projects |
| **clang-format** | `.clang-format` | C/C++ | Could gain exception support later |
| **clang-tidy** | `.clang-tidy` | C/C++ | Could gain exception support later |
| **rustfmt** | `rustfmt.toml` | Rust | Simple config, copy is sufficient |
| **stylua** | `stylua.toml` | Lua | Simple config, copy is sufficient |
| **dotnet** | `Directory.Build.props`, `.globalconfig` | C#/.NET | XML — not worth generating |

### Generator protocol

```python
class Generator(Protocol):
    """All generators implement this interface."""

    name: str  # e.g., "ruff", "biome"
    output_files: list[str]  # e.g., ["ruff.toml"]

    def generate(
        self,
        registry: ExceptionRegistry,
        languages: list[str],
        project_dir: Path,
    ) -> dict[Path, str]:
        """Return {relative_path: content} for files to write."""
        ...

    def check(
        self,
        registry: ExceptionRegistry,
        project_dir: Path,
    ) -> list[str]:
        """Return list of stale/missing config descriptions (empty = fresh)."""
        ...
```

### Config merge function

```python
def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Override wins on conflicts."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
```

### Library stack for generation

| Concern | Library | Import cost | New dep? |
|---------|---------|------------|----------|
| TOML read | `tomllib` (stdlib 3.11+) | 0ms | No |
| TOML write | `tomli-w` | ~2ms | No (existing) |
| TOML roundtrip | `tomlkit` (only for pyproject.toml edits) | ~5-10ms | No (existing) |
| JSON | `json` (stdlib) | 0ms | No |
| YAML | `pyyaml` | ~5-10ms | No (existing) |
| Validation | `@dataclass` + manual checks | 0ms | No |

Total generation import overhead: ~12-17ms. No new dependencies.

---

## Hook Inventory

### Enforcement hooks (called by lefthook or Claude Code)

| Hook | Module | Layer | What it enforces |
|------|--------|-------|-----------------|
| **dangerous_cmd** | `hooks/dangerous_cmd.py` | CC PreToolUse (Bash matcher) | Blocks `rm -rf /`, `--no-verify`, force push, fork bombs, etc. (19 patterns in 4 categories) |
| **protect_configs** | `hooks/protect_configs.py` | CC PreToolUse (Write\|Edit matcher) | Blocks AI editing files with `AUTO-GENERATED` header |
| **suppress_comments** | `hooks/suppress_comments.py` | lefthook pre-commit | Blocks `# noqa`, `// @ts-ignore`, `#pragma warning disable`, `#[allow(`, `//nolint`, etc. (20+ patterns across 8 languages). Test files exempt. |
| **config_ignore** | `hooks/config_ignore.py` | lefthook pre-commit | Blocks adding ignore/disable patterns to config files via diff analysis |
| **format_stage** | `hooks/format_stage.py` | lefthook pre-commit (priority 1) | Auto-formats staged files per language (ruff, biome, shfmt, clang-format, etc.), re-stages changed files |

### Validation hooks (called by lefthook)

| Hook | Invocation | What it checks |
|------|-----------|---------------|
| **validate-configs** | `ai-guardrails generate --check` | Generated configs match registry (hash comparison) |
| **conventional-commit** | `grep -qE "^(feat\|fix\|...):"` | Commit message follows conventional format |
| **gitleaks** | `gitleaks detect --staged` | No secrets in staged files |
| **detect-secrets** | `detect-secrets-hook --baseline` | No new secrets vs baseline |
| **codespell** | `codespell {staged_files}` | No typos |
| **markdownlint** | `markdownlint-cli2 {staged_files}` | Markdown formatting |

### Claude Code permission deny rules (project-level)

Generated into `.claude/settings.json` — no hook code needed, CC enforces natively:

```
Edit(ruff.toml), Edit(biome.json), Edit(lefthook.yml), Edit(.editorconfig),
Edit(.markdownlint.jsonc), Edit(.codespellrc),
Bash(* --no-verify *), Bash(git commit * -n *),
Bash(git push --force *), Bash(git push * --force *)
```

### Shell shims: DELETED in v1

No more `.sh` wrapper scripts. All hooks are invoked as:

- `python -m ai_guardrails.hooks.<name>` (by lefthook)
- `python -m ai_guardrails.hooks.<name>` (by CC PreToolUse `command`)

---

## Related Documents

| Document | What it covers | Relationship |
|----------|---------------|-------------|
| [ADR-002](../ADR-002-greenfield-architecture.md) | DONTs / lessons learned, competitive landscape | **Superseded** by this spec for architecture + features. DONTs section still authoritative. |
| [Interactive init](interactive-init.md) | Detailed UX for init prompts | **Subsumed** — init UX defined here, interactive-init has extra detail on prompt defaults and branch protection. |
| `configs/languages.yaml` | Language detection rules | **Source of truth** — spec references it, generators consume it. |
