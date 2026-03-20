# Phase 1: Stale config cleanup on --force

## Task
Add `delete()` to FileManager interface. In generateConfigsStep, when strategy is "replace" (--force), find inactive generators whose config files exist with our hash header and delete them.

## Files
- `src/infra/file-manager.ts` — add `delete(path: string): Promise<void>` to interface + RealFileManager (`fs.unlink`)
- `tests/fakes/fake-file-manager.ts` — add `delete()` to FakeFileManager (remove from map, track in `deleted` array)
- `src/steps/generate-configs.ts` — after writing applicable configs, cleanup stale ones when strategy is "replace"
- Import `ALL_GENERATORS` from registry alongside `applicableGenerators`

## Cleanup Logic
```
inactive = ALL_GENERATORS where languages is set AND none match activeIds
for each inactive generator:
  if configFile exists AND first line contains "ai-guardrails:sha256=" → delete it
```

Only when strategy === "replace". Never on "merge" or "skip".

## Acceptance Criteria
- strategy "replace" + python-only: ruff.toml written, stale biome.jsonc with hash header deleted
- strategy "replace" + stale biome.jsonc WITHOUT hash header: NOT deleted (user file)
- strategy "merge" with stale config: NOT deleted
- FakeFileManager.deleted tracks deletions
- All existing tests pass
- typecheck + lint clean
