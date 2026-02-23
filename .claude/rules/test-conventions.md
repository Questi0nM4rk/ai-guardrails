---
globs: tests/**/*.py
---

# Test Conventions

## Structure

- Prefer standalone test functions for new tests
- Test classes are acceptable for grouping related tests (existing pattern)
- One test file per source module: `lib/.../foo.py` -> `tests/test_foo.py`
- Fixtures live in `tests/conftest.py`

## Mocking

- Mock at infrastructure boundaries (subprocess, filesystem, network)
- Never mock private helper functions — test through public API
- Use `unittest.mock.patch` and `MagicMock` for subprocess/IO boundaries
- `tmp_path` for filesystem tests — never write to real paths

## Coverage

- No `# pragma: no cover` without documented justification
- No file exclusions in pyproject.toml coverage config
- Target 85%+ coverage on all modules

## Naming

- `test_{function_name}_{scenario}_{expected}` pattern
- Example: `test_detect_languages_python_project_returns_python`
