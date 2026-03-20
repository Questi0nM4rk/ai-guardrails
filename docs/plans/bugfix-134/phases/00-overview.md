# Bugfix #134 — Phases Overview

Single phase (medium fix, self-contained).

## Phase 1: stale-config-cleanup
- Add FileManager.delete, clean up stale configs on --force
- Files: src/infra/file-manager.ts, tests/fakes/fake-file-manager.ts, src/steps/generate-configs.ts
- Depends on: nothing
