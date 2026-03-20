# Bugfix Plan: Issue #134 — Stale config cleanup on --force

## Problem

When a language is no longer detected (e.g., after #124 fixed false Python detection),
`init --force` stops generating that language's config but doesn't remove the old file.
`ruff.toml` sits in a TypeScript-only project confusing users.

## Solution

After generating applicable configs, check inactive generators' config files. If the
file exists AND has our `ai-guardrails:sha256=` hash header (proving we created it),
delete it. Only trigger on `--force` (strategy "replace") to avoid surprising users.

## Files

- `src/infra/file-manager.ts` — add `delete(path: string): Promise<void>` to interface + RealFileManager
- `tests/fakes/fake-file-manager.ts` — add `delete()` to FakeFileManager
- `src/steps/generate-configs.ts` — add stale cleanup after writing applicable configs
- `src/generators/registry.ts` — already has `ALL_GENERATORS` and `applicableGenerators()`

## Implementation

### 1. FileManager.delete

Interface addition:
```typescript
delete(path: string): Promise<void>;
```

RealFileManager: `await fs.unlink(path)`
FakeFileManager: `this.files.delete(path); this.deleted.push(path);`

### 2. generate-configs.ts — stale cleanup

After the existing write loop (line 75), before building the result message:

```typescript
const removed: string[] = [];
if (strategy === "replace") {
  const inactive = ALL_GENERATORS.filter(
    (g) => g.languages !== undefined && !g.languages.some((id) => activeIds.has(id))
  );
  for (const g of inactive) {
    const dest = join(projectDir, g.configFile);
    if (await fileManager.exists(dest)) {
      const content = await fileManager.readText(dest);
      const firstLine = content.split("\n")[0] ?? "";
      if (firstLine.includes("ai-guardrails:sha256=")) {
        await fileManager.delete(dest);
        removed.push(g.configFile);
      }
    }
  }
}
```

Add removed count to the result message.

Import `ALL_GENERATORS` alongside `applicableGenerators` from registry.

### 3. Hash header detection

The hash header is always on line 1:
- TOML/Python: `# ai-guardrails:sha256=<hash>`
- JSONC: `// ai-guardrails:sha256=<hash>`
- Markdown: `<!-- ai-guardrails:sha256=<hash> -->`

Checking `firstLine.includes("ai-guardrails:sha256=")` covers all formats.
User-created files without the header are never touched.

## Tests

- Add test: generateConfigsStep with strategy "replace", python-only project → ruff.toml written, biome.jsonc NOT written
- Add test: same setup but seed a biome.jsonc WITH hash header → it gets deleted
- Add test: seed a biome.jsonc WITHOUT hash header (user-created) → it survives
- Add test: strategy "merge" with stale config → NOT deleted (only --force cleans up)
- FakeFileManager.deleted array tracks deletions for assertions

## Acceptance

- `init --force` on TS-only project after upgrading from version with false Python detection → ruff.toml removed
- User-created config files without hash header are never deleted
- Normal `init` (no --force) never deletes anything
