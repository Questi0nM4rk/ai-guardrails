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

## Shell (Bash)

- `set -euo pipefail` at script start
- Quote all variables: `"$var"` not `$var`
- Use `[[` not `[` for conditionals (Bash scripts only)
- For `/bin/sh` scripts, use POSIX-compatible `[` instead
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

## Review Focus

- Security: No hardcoded secrets, no command injection, proper input validation
- Type safety: No `Any`, no unvalidated casts, strict generics
- Error handling: Specific exception types, proper cleanup, no silent failures
- Performance: No N+1 patterns, minimize subprocess calls, cache expensive operations
