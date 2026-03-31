# Plan: Init Pipeline Improvements (SPEC-010 through SPEC-013)

## Overview

4 independent features improving the `ai-guardrails init` pipeline.
All touch different files — full parallel execution.

## Phases

| # | Spec | Name | Files | Difficulty |
|---|------|------|-------|------------|
| 1 | SPEC-012 | hook-binary-resolution | claude-settings.ts + tests | S |
| 2 | SPEC-010 | fresh-repo-guard | lefthook.ts + tests | S |
| 3 | SPEC-011 | ci-direct-tools | setup-ci.ts, github-actions.ts, init/types.ts + tests | M |
| 4 | SPEC-013 | version-pinning | config/schema.ts, utils/version.ts (new), init/modules/version-pin.ts (new), commands/status.ts, cli.ts + tests | M |

## Dependency Graph

```
Phase 1 ──┐
Phase 2 ──┤── all independent, run in parallel
Phase 3 ──┤
Phase 4 ──┘
```

## Branch Architecture

```
main
└── feat/spec-010-013-init-improvements
    ├── feat/spec-010-013-init-improvements/01-hook-binary-resolution
    ├── feat/spec-010-013-init-improvements/02-fresh-repo-guard
    ├── feat/spec-010-013-init-improvements/03-ci-direct-tools
    └── feat/spec-010-013-init-improvements/04-version-pinning
```
