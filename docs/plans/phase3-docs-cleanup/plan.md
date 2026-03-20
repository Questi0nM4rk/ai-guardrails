# Phase 3: Stale Docs Cleanup

## Context

Several docs reference Python-era bugs that are fixed. README doesn't reflect the
TS rewrite. Two stale issues need closing.

## Scope

### 3.1 Mark bug docs as RESOLVED
- `docs/bugs/hook-bypass-regex-limitations.md` — all 3 issues fixed by AST engine
- `docs/bugs/fresh-install-bugs.md` — all 6 bugs eliminated by TS rewrite

### 3.2 Update README
- Reflect TS binary, current CLI commands, hook system
- Separate shipped (v3) from planned features
- Add quick start, installation, usage examples

### 3.3 Close stale issues
- #41: Publish to PyPI — obsolete (TS rewrite)
- #45: Review items, close what's done

## Single phase — all docs work, no code changes
