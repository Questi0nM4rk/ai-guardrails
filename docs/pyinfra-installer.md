# pyinfra Installer - Design Philosophy

## Why pyinfra?

The original bash installer grew to 548 lines with 8 language-specific
sub-installers totaling 613 lines. This posed several problems:

1. **Duplication**: ~33% code duplication across installers (color output, package manager detection, error handling)
2. **Testability**: Bash scripts are hard to unit test
3. **Maintainability**: Complex case statements for package manager detection
4. **Idempotency**: Manual checks required to avoid reinstalling existing tools

**pyinfra** solves these problems:

| Feature | Benefit |
|---------|---------|
| Built-in operations | apt, pacman, brew, dnf, pip, pipx, npm, cargo all included |
| @local connector | Runs on local machine via subprocess |
| Idempotent | Only makes changes when needed |
| Pure Python | Full IDE support, type hints, testable |
| @deploy decorator | Package reusable deploy functions |

## Architecture Principles

### 1. Modular Deploy Functions

Each language gets its own module with a single `@deploy` decorated function:

```text
lib/installers/
├── __init__.py         # Exports all deploy functions
├── core.py             # Core: pyyaml, pre-commit, file copying
├── python.py           # ruff, mypy, bandit, vulture, pip-audit
├── shell.py            # shellcheck, shfmt
├── cpp.py              # clang-format, clang-tidy
├── node.py             # biome
├── rust.py             # cargo-audit
├── go.py               # golangci-lint, govulncheck
└── lua.py              # stylua, luacheck
```

### 2. Package Manager Detection

Modules that need system packages detect the available package manager:

```python
def get_package_manager() -> str | None:
    managers = ["pacman", "apt-get", "dnf", "yum", "apk", "brew"]
    for pm in managers:
        if host.get_fact(Which, command=pm):
            return pm.replace("-get", "")
    return None
```

Priority order: pacman > apt > dnf > yum > apk > brew

### 3. Installation Method Hierarchy

For Python tools:

1. **pipx** (preferred) - PEP 668 compliant, isolated environments
2. **pip --user** (fallback) - When pipx unavailable

For system tools:

1. **System package manager** - Native packages when available
2. **Language toolchain** - go install, cargo install as fallback

### 4. Idempotent Operations

All pyinfra operations are idempotent by design. Running `install.py` twice:

- First run: Installs tools
- Second run: No changes (tools already present)

## Command Line Interface

```bash
# Install core only
python3 install.py

# Install all language tools
python3 install.py --all

# Install specific languages
python3 install.py --python --rust --shell

# Force reinstall
python3 install.py --force --all

# Dry run (show what would happen)
python3 install.py --dry-run --all

# Uninstall
python3 install.py --uninstall
```

## Installation Paths

Unchanged from bash installer:

| Path | Purpose |
|------|---------|
| `~/.ai-guardrails/` | Main installation directory |
| `~/.ai-guardrails/bin/` | CLI scripts |
| `~/.ai-guardrails/lib/` | Hooks, Python modules |
| `~/.ai-guardrails/templates/` | Pre-commit and workflow templates |
| `~/.ai-guardrails/configs/` | Language-specific config files |
| `~/.local/bin/` | Symlinks for CLI commands |

## Quality Standards

### Code Quality

- All ruff checks pass (zero warnings/errors)
- Type hints on all functions
- Google-style docstrings on public functions
- No noqa comments (no skipping lints)
- Line length: 100 characters

### Testing

- 32 unit tests for installer modules
- Mocked pyinfra facts for package manager detection
- CLI argument parsing tests
- All 132 project tests pass

### Linting

Uses the project's pedantic ruff configuration with additional ignores for CLI-specific patterns:

- `T201` - print statements (expected in CLI)
- `PLR0912/PLR0915/C901` - complexity (acceptable for CLI main())

## Migration Status

Migration from bash to Python installer is **complete**. The legacy `install.sh`
and `lib/installers/*.sh` files have been removed. `install.py` is the only installer.

## Future Enhancements

Potential improvements enabled by pyinfra architecture:

1. **Progress reporting** - pyinfra's operation callbacks
2. **Parallel installation** - Multiple tools at once
3. **Remote installation** - SSH deployment to multiple machines
4. **Custom tool lists** - YAML/JSON configuration
5. **Plugin architecture** - User-defined installers
