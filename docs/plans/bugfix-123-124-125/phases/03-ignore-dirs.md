# Phase 3: Exclude Dirs from Detection (#124)

## Files
- `src/languages/types.ts` — add `ignorePaths?: readonly string[]` to DetectOptions
- `src/languages/registry.ts` — pass ignorePaths through to detect()
- `src/steps/detect-languages.ts` — pass config.ignorePaths + DEFAULT_IGNORE
- `src/languages/python.ts` — pass ignorePaths to glob
- `src/languages/typescript.ts` — pass ignorePaths to glob
- `src/languages/shell.ts` — pass ignorePaths to glob
- `src/languages/cpp.ts` — pass ignorePaths to glob
- `src/languages/lua.ts` — pass ignorePaths to glob
- `src/languages/dotnet.ts` — pass ignorePaths to glob
- `tests/fakes/fake-file-manager.ts` — update glob signature if needed

## Task
Language detection currently scans all directories including node_modules, .venv, vendor, etc.
Add DEFAULT_IGNORE paths that are always excluded from glob-based detection:

```typescript
export const DEFAULT_IGNORE: readonly string[] = [
  "node_modules/**", ".venv/**", "venv/**", "vendor/**",
  "dist/**", "build/**", "target/**", ".git/**", "__pycache__/**",
];
```

These are merged with user's `config.ignorePaths` before passing to detect.

**Important:** Marker files (pyproject.toml, package.json, Cargo.toml, go.mod, etc.)
use `fileManager.exists()` — NOT glob. They always trigger regardless of ignore paths.
Only the fallback glob scan (`**/*.py` etc.) respects ignore paths.

## Acceptance Criteria
- node_modules/pkg/helper.py does NOT trigger Python detection
- .venv/lib/python3.11/... does NOT trigger Python
- vendor/github.com/... does NOT trigger Go
- dist/bundle.js does NOT trigger TypeScript
- pyproject.toml at root ALWAYS triggers Python (marker file)
- src/app.py still triggers Python (not in ignored dir)
- All existing tests pass + typecheck + lint clean
