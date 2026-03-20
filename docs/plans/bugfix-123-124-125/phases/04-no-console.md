# Phase 4: Context-Aware noConsole (#127)

## Files
- `src/config/schema.ts` — add `noConsoleLevel: "off" | "warn" | "error"` to ResolvedConfig
- `src/steps/detect-languages.ts` — detect project type from package.json
- `src/generators/biome.ts` — use config.noConsoleLevel instead of hardcoded "error"

## Task
The biome generator hardcodes `noConsole: "error"`, which produces 22 false positives
for CLI projects where console IS the output mechanism. Detect project type:

```typescript
function detectNoConsoleLevel(packageJson: unknown): "off" | "warn" | "error" {
  if (!isPlainObject(packageJson)) return "warn";
  const allDeps = { ...packageJson.dependencies, ...packageJson.devDependencies };
  const BROWSER_FRAMEWORKS = ["react", "vue", "svelte", "@angular/core",
    "next", "nuxt", "solid-js", "preact", "qwik"];
  if (BROWSER_FRAMEWORKS.some(f => f in allDeps)) return "error";
  if ("bin" in packageJson) return "off";
  return "warn";
}
```

Browser wins over CLI (if both bin and react → error).

## Acceptance Criteria
- package.json with `"bin"` → noConsole "off" in biome.jsonc
- package.json with react → noConsole "error"
- package.json with bin + react → noConsole "error" (browser wins)
- package.json with express → noConsole "warn"
- No package.json → noConsole "warn"
- All existing tests pass + typecheck + lint clean
