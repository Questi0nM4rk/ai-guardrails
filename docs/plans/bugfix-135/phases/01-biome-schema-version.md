# Phase 1: Dynamic biome schema version

## Task
Add biome version detection to runner, pass through install pipeline, use in generator for dynamic $schema URL. Omit $schema entirely if version unknown.

## Files
- `src/runners/biome.ts` — add `getBiomeVersion()`, `resetBiomeVersionCache()` (follow golangci-lint pattern)
- `src/generators/biome.ts` — read `config.values.biome_version`, dynamic schema URL or omit
- `src/pipelines/install.ts` — detect version inside `hasTypeScript` block, set on config.values

## Acceptance Criteria
- Generator with biome_version "2.4.8" in values → schema URL contains "2.4.8"
- Generator without biome_version → no $schema field
- getBiomeVersion parses version output correctly
- getBiomeVersion returns undefined on failure
- All existing tests pass, snapshot updated
- typecheck + lint clean
