# AI Guardrails

Pedantic code enforcement for AI-maintained repositories. Ensures consistent
formatting, required type annotations, mandatory documentation, and strict
static analysis across all projects.

**Philosophy**: AI agents need guardrails. This is the fence.

## What It Enforces

| Requirement | Python | TypeScript | C# | Rust | C/C++ | Lua |
|-------------|--------|------------|-----|------|-------|-----|
| Formatting | ruff | biome | dotnet | rustfmt | clang | stylua |
| Types | mypy | tsc | nullable | - | - | - |
| Docs | docstrings | JSDoc | XML | rustdoc | doxygen | - |
| Analysis | ruff | biome | analyzers | clippy | clang-tidy | luacheck |
| Security | bandit | biome | analyzers | - | - | - |

## Quick Start

```bash
# Install globally
git clone https://github.com/Questi0nM4rk/ai-guardrails.git
cd ai-guardrails && ./install.sh

# Initialize in any project
cd /path/to/your/project
ai-guardrails-init          # Auto-detects language, copies configs
pre-commit run --all-files  # Run all checks
```

## Commands

### ai-guardrails-init

Copies pedantic configs to your project based on detected language(s).

```bash
ai-guardrails-init              # Auto-detect
ai-guardrails-init --type rust  # Specific type
ai-guardrails-init --all        # Multi-language project
ai-guardrails-init --force      # Overwrite existing configs
```

**Installed per type:**

| Type | Configs |
|------|---------|
| `python` | `.editorconfig`, `ruff.toml` |
| `node` | `.editorconfig`, `biome.json` |
| `dotnet` | `.editorconfig`, `Directory.Build.props`, `.globalconfig` |
| `rust` | `.editorconfig`, `rustfmt.toml` |
| `cpp` | `.editorconfig`, `.clang-format` |
| `lua` | `.editorconfig`, `stylua.toml` |
| `all` | All of the above |

### ai-hooks-init

Sets up git hooks for the project.

```bash
ai-hooks-init              # Local hooks
ai-hooks-init --global     # Global hooks
ai-hooks-init --pre-commit # Also install pre-commit config
```

### ai-review-tasks

Extracts actionable tasks from CodeRabbit PR reviews.

```bash
gh pr-review review view --pr 1 | ai-review-tasks --pretty
ai-review-tasks --severity major reviews.json
```

## Configs

### EditorConfig (`.editorconfig`)

Universal formatting rules for all editors:

- UTF-8, LF line endings
- 4 spaces for most languages, 2 for JS/TS/YAML/Lua
- 100 char line limit (80 for markdown)
- C# naming conventions (PascalCase public, _camelCase private)

### Python (`ruff.toml`)

- **ALL** ruff rules enabled
- Google-style docstrings required
- Type annotations required (via `flake8-annotations`)
- Complexity limits (mccabe max 10)
- Import sorting (isort style)

### TypeScript/JavaScript (`biome.json`)

- ALL biome rules enabled
- `noExplicitAny: error`
- Naming conventions enforced (PascalCase types, camelCase functions)
- Cognitive complexity limit: 15
- Strict formatting (double quotes, semicolons, trailing commas)

### C# (`.globalconfig` + `Directory.Build.props`)

- `TreatWarningsAsErrors: true`
- `Nullable: enable`
- `AnalysisLevel: latest-All`
- StyleCop, Meziantou, Roslynator, SonarAnalyzer included
- 200+ analyzer rules configured

### Rust (`rustfmt.toml`)

- Edition 2021, 100 char lines
- Imports grouped by std/external/crate
- Comments wrapped at 80 chars
- Doc comment code blocks formatted

### C/C++ (`.clang-format`)

- C++23 standard
- LLVM-based style with modifications
- Braces on same line
- Aligned assignments, declarations, macros
- Includes sorted and regrouped

### Lua (`stylua.toml`)

- 120 char lines, 2 space indent
- Call parentheses always required
- Requires sorted

## Pre-commit Hooks

The included `.pre-commit-config.yaml` runs:

### Security

- gitleaks (secrets detection)
- detect-private-key
- bandit (Python security)

### Formatting

- Language-specific formatters (ruff, biome, clang-format, etc.)
- EditorConfig enforcement
- Trailing whitespace, EOF fixer

### Type Checking

- mypy --strict (Python)
- tsc --strict (TypeScript)
- dotnet build -warnaserror (C#)

### Static Analysis

- ruff ALL rules (Python)
- biome ALL rules (TypeScript)
- clippy pedantic (Rust)
- clang-tidy (C/C++)
- luacheck (Lua)
- shellcheck (Shell)

### Documentation

- cargo doc with `-D missing_docs` (Rust)
- Docstring requirements via ruff (Python)

## Directory Structure

```text
ai-guardrails/
├── bin/
│   ├── ai-guardrails-init    # Project setup
│   ├── ai-hooks-init         # Git hooks setup
│   └── ai-review-tasks       # PR task extraction
├── configs/
│   ├── .editorconfig         # Universal formatting
│   ├── ruff.toml             # Python (pedantic)
│   ├── biome.json            # TypeScript/JS (pedantic)
│   ├── .clang-format         # C/C++ (pedantic)
│   ├── stylua.toml           # Lua
│   ├── rustfmt.toml          # Rust
│   ├── Directory.Build.props # C# build config
│   └── .globalconfig         # C# analyzer rules
├── lib/
│   ├── hooks/                # Git hook scripts
│   └── python/               # Python utilities
├── templates/
│   ├── pre-commit-config.yaml
│   └── settings.json.strict
└── install.sh
```

## Requirements

- Python 3.10+
- [pre-commit](https://pre-commit.com/)
- Language-specific tools (installed automatically by pre-commit):
  - Python: ruff, mypy, bandit
  - TypeScript: biome, tsc
  - Rust: rustfmt, clippy
  - C/C++: clang-format, clang-tidy
  - Lua: stylua, luacheck
  - Shell: shellcheck, shfmt

Optional:

- [gh-pr-review](https://github.com/agynio/gh-pr-review) for PR task extraction

## License

MIT
