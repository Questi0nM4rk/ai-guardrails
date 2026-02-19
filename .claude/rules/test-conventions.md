---
globs: tests/**/*.py
---

# Test Conventions

## Structure

- Standalone test functions only — no test classes unless shared state requires it
- One test file per source module: `lib/.../foo.py` -> `tests/test_foo.py`
- Fixtures live in `tests/conftest.py`

## Mocking

- Mock at infrastructure boundaries (CommandRunner, Console, filesystem)
- Never mock private helper functions — test through public API
- Prefer fakes (FakeCommandRunner, FakeConsole) over `@patch` decorators
- `tmp_path` for filesystem tests — never write to real paths

## Coverage

- No `# pragma: no cover` without documented justification
- No file exclusions in pyproject.toml coverage config
- Target 85%+ coverage on all modules

## Naming

- `test_{function_name}_{scenario}_{expected}` pattern
- Example: `test_detect_languages_python_project_returns_python`
