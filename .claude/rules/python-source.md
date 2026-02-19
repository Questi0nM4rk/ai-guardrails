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

## Infrastructure Boundaries

- subprocess calls go through `CommandRunner` — never `subprocess.run` directly
- File I/O goes through injected abstractions in step functions
- Console output goes through `Console` — never raw `print()`

## Type Safety

- `dict[str, Any]` is banned across module boundaries — use dataclasses or TypedDict
- All public functions have type annotations
- `argparse.Namespace` stays at CLI boundary — business logic receives dataclasses

## Module Size

- Max 200 lines per module — split into submodules if larger
- One concern per module — if you need "and" to describe it, split it
