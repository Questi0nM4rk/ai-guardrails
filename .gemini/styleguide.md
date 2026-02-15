# Project Code Standards

## Python

- **Version**: 3.11+ (use modern syntax: `X | None` not `Optional[X]`)
- **Imports**: `from __future__ import annotations` required in ALL files
- **Type hints**: Required on all function signatures (params + return)
- **Docstrings**: Required on public functions and classes
- **Exceptions**: No bare `except:` — always specify the exception type
- **Linter**: ruff (ALL rule categories enabled)
- **Formatter**: ruff format (88 char line length)
- **Type checker**: pyright in strict mode

## Shell (POSIX)

- `set -euo pipefail` at script start
- Quote all variables: `"$var"` not `$var`
- Use `[` for conditionals (POSIX-compatible)
- Prefer portable POSIX syntax — avoid bashisms (`[[`, `(( ))`, arrays)
- Validate with shellcheck

## Testing

- 85%+ coverage target
- Test files: `test_*.py` or `*_test.py`
- Meaningful assertions (not just "no errors")
- No shared mutable state between tests
- Use fixtures and parametrize for thorough coverage

## Architecture

```text
configs/          # Base config files (ruff.toml, biome.json, etc.)
templates/        # Templates installed by `ai-guardrails init`
lib/hooks/        # Pre-commit hook scripts
lib/python/       # Python package (guardrails)
tests/            # pytest test suite
```

## Review Focus (auto-review on every push)

Your specialization — focus on these and leave other concerns to CodeRabbit/Claude:

- **Bugs**: code that will fail, produce wrong results, or crash
- **Logic errors**: incorrect conditions, off-by-one, missing edge cases
- **Security**: injection, secrets exposure, unsafe operations
- **Performance**: N+1 patterns, unnecessary allocations, missing caching

Do NOT flag: style/formatting, linting issues, minor nitpicks (CodeRabbit handles these).
Do NOT flag: code duplication, clean code, architecture (Claude handles these).
