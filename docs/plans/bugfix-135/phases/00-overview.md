# Bugfix #135 — Phases Overview

Single phase (small fix, no parallelism needed).

## Phase 1: biome-schema-version
- Detect installed biome version, generate matching $schema URL
- Files: src/runners/biome.ts, src/generators/biome.ts, src/pipelines/install.ts
- Depends on: nothing
