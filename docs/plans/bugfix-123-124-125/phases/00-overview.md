# Bugfix Phases Overview

## Phase Dependency Graph

```
Phase 1 (CI workflow)     ─┐
Phase 2 (Generator gates) ─┤── all parallel ──→ Phase 5 (Tests)
Phase 3 (Ignore dirs)     ─┤
Phase 4 (noConsole)       ─┘
```

Phases 1-4 are independent. Phase 5 depends on all of 1-4.

## Execution Strategy

- Spawn phases 1-4 in parallel worktrees
- Each creates PR → feat/bugfix-123-127
- After all 4 merge, spawn phase 5
