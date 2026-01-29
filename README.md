# AI Guardrails

Pedantic code enforcement for AI-maintained repositories. Ensures consistent
formatting, required type annotations, mandatory documentation, and strict
static analysis across all projects.

**Philosophy**: AI agents need hard stops. No warnings, no suggestions.
Everything is an error or it's ignored. Black/white only.

## What It Enforces

| Requirement | Python | TypeScript | C# | Rust | C/C++ | Lua |
|-------------|--------|------------|-----|------|-------|-----|
| Formatting | ruff | biome | dotnet | rustfmt | clang | stylua |
| Types | mypy | tsc | nullable | - | - | - |
| Docs | docstrings | JSDoc | XML | rustdoc | doxygen | - |
| Analysis | ruff | biome | analyzers | clippy | clang-tidy | luacheck |
| Security | bandit+semgrep | biome | analyzers | audit | - | - |
| CVE Scan | pip-audit | npm-audit | - | cargo-audit | - | - |

## Quick Start

```bash
# Install globally (framework only)
git clone https://github.com/Questi0nM4rk/ai-guardrails.git
cd ai-guardrails && python3 install.py

# Install with language tools
python3 install.py --all                    # All languages
python3 install.py --python --shell         # Specific languages
python3 install.py --python --node --rust   # Multiple languages

# Initialize in any project
cd /path/to/your/project
ai-guardrails-init          # Auto-detects language, copies configs
pre-commit install          # Install hooks
pre-commit install --hook-type commit-msg  # Commit message validation
pre-commit run --all-files  # Run all checks
```

### Installation Options

```bash
python3 install.py              # Framework only (pyyaml + pre-commit)
python3 install.py --all        # Framework + all language tools
python3 install.py --python     # Framework + Python tools (ruff, mypy, bandit, etc.)
python3 install.py --node       # Framework + Node.js tools (biome)
python3 install.py --rust       # Framework + Rust tools (cargo-audit)
python3 install.py --go         # Framework + Go tools (golangci-lint, govulncheck)
python3 install.py --cpp        # Framework + C/C++ tools (clang-format, clang-tidy)
python3 install.py --lua        # Framework + Lua tools (stylua, luacheck)
python3 install.py --shell      # Framework + Shell tools (shellcheck, shfmt)
```

**Notes:**

- `pyyaml` and `pre-commit` are always installed (required)
- Language tools require their respective toolchains (go, cargo, npm, etc.)
- System package manager (pacman/apt/brew) used where applicable

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

### Python (`ruff.toml`)

**Zero escape routes for AI:**

- ALL rules enabled (800+)
- `from __future__ import annotations` required in every file
- Google-style docstrings mandatory
- Type annotations mandatory (no `Any` allowed)
- Pathlib enforced (no `os.path`)
- Modern syntax enforced (no `typing.Optional`, use `X | None`)
- Relative imports banned
- Complexity limits: 10 cyclomatic, 5 args, 30 statements, 3 nested blocks

### TypeScript/JavaScript (`biome.json`)

**Zero escape routes for AI:**

- ALL rules enabled
- `noExplicitAny: error` (no exceptions)
- `noParameterAssign: error`
- `noDefaultExport: error` (named exports only)
- `noForEach: error` (use for-of)
- `noConsoleLog: error`
- `noBarrelFile: error`
- Kebab-case filenames enforced
- Cognitive complexity limit: 10
- Nested callbacks limit: 3

### C# (`.globalconfig` + `Directory.Build.props`)

- `TreatWarningsAsErrors: true`
- `Nullable: enable`
- `AnalysisLevel: latest-All`
- 200+ analyzer rules at ERROR severity
- StyleCop, Meziantou, Roslynator, SonarAnalyzer included

### Rust (`rustfmt.toml`)

- Edition 2021, 100-char lines
- Imports grouped by std/external/crate
- clippy::pedantic + clippy::nursery enabled
- Missing docs = error

### C/C++ (`.clang-format`)

- C++23 standard
- LLVM-based style with modifications
- clang-tidy with all checks enabled

### Lua (`stylua.toml`)

- 120-char lines, 2-space indent
- Call parentheses always required

### EditorConfig (`.editorconfig`)

- UTF-8, LF line endings everywhere
- Language-specific indent sizes
- C# naming conventions (PascalCase public, _camelCase private)

## Pre-commit Hooks

The included `.pre-commit-config.yaml` runs 40+ checks:

### Security (runs first, fails fast)

- **gitleaks** - Secret detection
- **detect-secrets** - Enhanced secret patterns
- **detect-private-key** - Private key detection
- **semgrep** - SAST security patterns (OWASP)
- **bandit** - Python security linter

### Vulnerability Scanning

- **pip-audit** - Python dependency CVEs
- **npm audit** - Node dependency CVEs
- **cargo audit** - Rust dependency CVEs

### CVE Scanning with pip-audit

The `pip-audit` hook scans Python dependencies for known CVEs. It's
**auto-configured** by `ai-guardrails-init` based on detected dependency
management tool (uv or pip).

#### Auto-Detection

When you run `ai-guardrails-init`, it detects your Python dependency tool:

- **uv detected** (`uv.lock` exists) → Configured with `--locked .`
- **pip detected** (`requirements.txt` or `pyproject.toml`) → Configured
  with `-r requirements.txt` or `--locked .`
- **None detected** → Left disabled

#### Manual Override

Use flags to override auto-detection:

```bash
# Force uv configuration
ai-guardrails-init --pip-audit-uv

# Force pip configuration
ai-guardrails-init --pip-audit-pip

# Disable pip-audit
ai-guardrails-init --no-pip-audit
```

#### Why This Matters

Pre-commit hooks run in **isolated environments**. Without proper
configuration, pip-audit scans the hook's environment instead of your
project dependencies, making CVE scanning ineffective.

#### Manual Configuration

To manually enable/configure pip-audit in `.pre-commit-config.yaml`:

**For uv:**

```yaml
- repo: https://github.com/pypa/pip-audit
  rev: v2.10.0
  hooks:
    - id: pip-audit
      name: "🐍 python · pip-audit CVE scan"
      args: ["--strict", "--progress-spinner", "off", "--locked", "."]
```

**For pip + requirements.txt:**

```yaml
args: ["--strict", "--progress-spinner", "off", "-r", "requirements.txt"]
```

**For pip + pyproject.toml:**

```yaml
args: ["--strict", "--progress-spinner", "off", "--locked", "."]
```

#### Verification

Test that pip-audit scans your actual dependencies:

```bash
pre-commit run pip-audit --all-files
```

You should see your project dependencies being scanned, not the hook
environment.

If pip-audit reports "No packages found", it's scanning the wrong
environment - check your args configuration.

### Commit Message Enforcement

- **conventional-pre-commit** - Requires conventional commit format
- Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore

### Spelling

- **codespell** - Typo detection in code and filenames

### Type Checking

- **mypy --strict** (Python)
- **tsc --strict** (TypeScript)
- **dotnet build -warnaserror** (C#)

### Static Analysis

- **ruff** - ALL rules (Python)
- **biome** - ALL rules (TypeScript/JS)
- **clippy pedantic** (Rust)
- **clang-tidy** (C/C++)
- **luacheck** (Lua)
- **shellcheck** (Shell)

### Formatting

- **ruff-format** (Python)
- **biome** (TypeScript/JS)
- **rustfmt** (Rust)
- **clang-format** (C/C++)
- **stylua** (Lua)
- **shfmt** (Shell)
- **taplo** (TOML)
- **markdownlint** (Markdown)

### Git Hygiene

- No commits to main/master
- No large files (>500KB)
- No merge conflicts
- Executables must have shebangs

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
└── install.py                # Python installer
```

## Requirements

- Python 3.10+
- [pre-commit](https://pre-commit.com/)
- Language-specific tools (installed automatically by pre-commit):
  - Python: ruff, mypy, bandit, pip-audit
  - TypeScript: biome, tsc
  - Rust: rustfmt, clippy, cargo-audit
  - C/C++: clang-format, clang-tidy
  - Lua: stylua, luacheck
  - Shell: shellcheck, shfmt
  - Security: semgrep, gitleaks, detect-secrets

Optional:

- [gh-pr-review](https://github.com/agynio/gh-pr-review) for PR task extraction

## Why This Strict?

AI agents:

- Ignore warnings (only errors stop them)
- Take shortcuts if allowed
- Generate inconsistent code across projects
- Skip documentation if optional
- Use deprecated patterns if not banned

This config removes all gray areas. Every rule is an error. No exceptions.

## License

MIT
