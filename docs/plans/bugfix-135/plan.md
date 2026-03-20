# Bugfix Plan: Issue #135 — Dynamic biome schema version

## Problem

`biome.jsonc` hardcodes `$schema: "https://biomejs.dev/schemas/2.4.6/schema.json"`.
When the user has a newer biome (e.g., 2.4.8), every `biome check` emits a schema
mismatch warning. Users can't edit the file without triggering tamper detection.

## Solution

Detect installed biome version at pipeline level, pass to generator via
`config.values`, generate matching schema URL. Drop `$schema` entirely if
version can't be detected (biome works fine without it).

## Files

- `src/generators/biome.ts` — read version from config.values, dynamic schema URL
- `src/pipelines/install.ts` — detect biome version, store on config
- `src/runners/biome.ts` — add `detectBiomeVersion()` (follows golangci-lint pattern at line 69-96)

## Implementation

### 1. src/runners/biome.ts — add version detection

Follow the golangci-lint pattern (cached promise, parse version output):

- `detectBiomeVersion(commandRunner, projectDir)` — runs `biome --version`, parses semver
- `getBiomeVersion(commandRunner, projectDir)` — cached wrapper
- `resetBiomeVersionCache()` — for test isolation
- Uses `resolveToolPath("biome", projectDir)` (already used in biomeRunner)
- Uses `commandRunner.run()` (no shell, safe from injection)

### 2. src/pipelines/install.ts — detect and pass version

Inside the existing `hasTypeScript` block (line 37-52), after noConsole detection:
- Call `getBiomeVersion(commandRunner, projectDir)`
- Build final config with `biome_version` in `config.values`
- `config.values` has `[key: string]: unknown` passthrough, so this is type-safe

### 3. src/generators/biome.ts — use dynamic schema

- Read `config.values.biome_version` with type narrowing (`typeof === "string"`)
- If present: `$schema: https://biomejs.dev/schemas/${version}/schema.json`
- If absent: omit `$schema` field entirely (biome works without it)

## Tests

- Update biome generator snapshot (schema may be absent)
- Add test: generator with `biome_version: "2.4.8"` in values produces matching schema URL
- Add test: generator without biome_version omits $schema field
- Add test: `getBiomeVersion` parses "Version: 2.4.8" correctly
- Add test: `getBiomeVersion` returns undefined on failure

## Acceptance

- `init --force` with biome 2.4.8 installed produces biome.jsonc with matching schema
- `biome check` produces no schema mismatch warning
- If biome not installed, $schema omitted (no warning, no error)
