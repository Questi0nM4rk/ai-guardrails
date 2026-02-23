---
globs: lib/python/**/*.py
---

# Python Source Conventions

## Imports

- `from __future__ import annotations` — first line after module docstring, every file
- Modern type syntax: `X | None` not `Optional[X]`, `list[str]` not `List[str]`

## Error Handling

- Catch specific exceptions only — never `except Exception: pass`
- No bare `except:` — always name the exception type
- Log failures at warning level before re-raising or returning error

## subprocess

- Current pattern: direct `subprocess.run` with explicit error handling
- Planned: `CommandRunner` abstraction (see ADR-002) — new code should
  minimize new `subprocess.run` call sites to ease future migration

## Output

- Current pattern: `print()` with ANSI color helpers (`_print_ok`, etc.)
- Planned: `Console` abstraction (see ADR-002)

## Type Safety

- `dict[str, Any]` is banned across module boundaries — use dataclasses or TypedDict
- All public functions have type annotations
- `argparse.Namespace` stays at CLI boundary — business logic receives dataclasses

## Module Size

- Max 200 lines per module — split into submodules if larger
- One concern per module — if you need "and" to describe it, split it
