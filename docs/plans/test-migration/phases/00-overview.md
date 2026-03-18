# Test Migration — Phase Overview

## Dependency Graph

```
Phase 1 (hook tests)     ──┐
Phase 2 (engine+config)  ──┼──→ Final merge + simplify
Phase 3 (lang+pipeline)  ──┘
```

All 3 phases are independent — run in parallel.

## Phases

| # | Name | Tests | Feature files | Depends on |
|---|------|-------|---------------|------------|
| 1 | hook-tests | ~99 | 6 | none |
| 2 | engine-config-tests | ~161 | 4 | none |
| 3 | lang-pipeline-tests | ~50 | 3 | none |
