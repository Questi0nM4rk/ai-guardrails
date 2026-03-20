# Bugfix Plan: Issues #123, #124, #125, #126, #127

## Context

Five bugs from real-world dogfooding. They compound — #124 causes false language
detection which makes #123 worse. #125/#126 mean CI skips linters. #127 generates
noisy false positives for CLI projects.

## Bug Summary

| Issue | Problem | Impact |
|-------|---------|--------|
| #123 | Generators run unconditionally | ruff.toml in TS-only projects |
| #124 | Detection scans node_modules/.venv/vendor | False Python/Shell detection |
| #125/#126 | CI workflow missing bun install | Linters skip in CI |
| #127 | noConsole: "error" wrong for CLI projects | 22 false positives |

## Phases (4 parallel code fixes + 1 sequential test phase)

### Phase 1: CI workflow fix (#125, #126)

**Files:** `src/steps/setup-ci.ts`

Add conditional `bun install --frozen-lockfile` with hashFiles guard:

```yaml
- name: Install dependencies
  run: bun install --frozen-lockfile
  if: hashFiles('bun.lock', 'bun.lockb', 'package.json') != ''
```

**Acceptance:** Workflow contains bun install, hashFiles condition, correct ordering.

### Phase 2: Language-gate generators (#123)

**Files:**

- `src/generators/types.ts` — add `readonly languages?: readonly string[]`
- `src/generators/ruff.ts` — add `languages: ["python"]`
- `src/generators/biome.ts` — add `languages: ["typescript"]`
- `src/steps/generate-configs.ts` — filter by active language IDs

**Logic:**

```typescript
const activeIds = new Set(languages.map(l => l.id));
const applicable = ALL_GENERATORS.filter(g =>
  g.languages === undefined || g.languages.some(id => activeIds.has(id))
);
```

**Acceptance:**

- Python-only: ruff.toml YES, biome.jsonc NO
- TypeScript-only: biome.jsonc YES, ruff.toml NO
- Rust/Go/Shell/C++/Lua/dotnet-only: neither ruff nor biome
- Polyglot Python+TS: both
- Universal-only: neither, but editorconfig/codespell/lefthook/etc YES

### Phase 3: Exclude dirs from detection (#124)

**Files:**

- `src/infra/file-manager.ts` — add `ignorePaths?: readonly string[]` to glob()
- `src/languages/types.ts` — add `ignorePaths?: readonly string[]` to DetectOptions
- `src/languages/registry.ts` — pass ignorePaths through to detect()
- `src/steps/detect-languages.ts` — pass config.ignorePaths + DEFAULT_IGNORE
- `src/languages/python.ts` — pass ignorePaths to glob
- `src/languages/typescript.ts` — pass ignorePaths to glob
- `src/languages/shell.ts` — pass ignorePaths to glob
- `src/languages/cpp.ts` — pass ignorePaths to glob
- `src/languages/lua.ts` — pass ignorePaths to glob
- `src/languages/dotnet.ts` — pass ignorePaths to glob
- `tests/fakes/fake-file-manager.ts` — update glob signature

**DEFAULT_IGNORE** (hardcoded, always applied):

```typescript
export const DEFAULT_IGNORE: readonly string[] = [
  "node_modules/**", ".venv/**", "venv/**", "vendor/**",
  "dist/**", "build/**", "target/**", ".git/**", "__pycache__/**",
];
```

Merged with user's `config.ignorePaths` before passing to detect.

Marker files (pyproject.toml, package.json, Cargo.toml, go.mod, CMakeLists.txt,
*.csproj) check via `fileManager.exists()` — NOT glob. So they always trigger
regardless of ignore paths. Only the fallback glob scan (`**/*.py` etc.) respects
ignore paths.

**Acceptance:**

- node_modules/pkg/helper.py does NOT trigger Python
- .venv/lib/python3.11/... does NOT trigger Python
- vendor/github.com/... does NOT trigger Go
- dist/bundle.js does NOT trigger TypeScript
- pyproject.toml at root ALWAYS triggers Python (marker file)
- src/app.py still triggers Python (not in ignored dir)

### Phase 4: Context-aware noConsole (#127)

**Files:**

- `src/config/schema.ts` — add `noConsoleLevel: "off" | "warn" | "error"` to ResolvedConfig
- `src/steps/detect-languages.ts` — detect project type from package.json
- `src/generators/biome.ts` — use config.noConsoleLevel instead of hardcoded "error"

**Detection logic:**

```typescript
function detectNoConsoleLevel(packageJson: unknown): "off" | "warn" | "error" {
  if (!isPlainObject(packageJson)) return "warn";

  // Browser frameworks → error (console is debugging)
  const allDeps = { ...packageJson.dependencies, ...packageJson.devDependencies };
  const BROWSER_FRAMEWORKS = ["react", "vue", "svelte", "@angular/core",
    "next", "nuxt", "solid-js", "preact", "qwik"];
  if (BROWSER_FRAMEWORKS.some(f => f in allDeps)) return "error";

  // CLI tools → off (console is the output mechanism)
  if ("bin" in packageJson) return "off";

  // Default: warn (could be server, library, or unknown)
  return "warn";
}
```

Browser wins over CLI (if both bin and react, error).

**Acceptance:**

- package.json with `"bin"` → noConsole "off" in biome.jsonc
- package.json with react → noConsole "error"
- package.json with bin + react → noConsole "error" (browser wins)
- package.json with express → noConsole "warn"
- No package.json → noConsole "warn"

### Phase 5: Exhaustive test scenarios (depends on 1-4)

**6 new feature files, ~95 scenarios total:**

#### A. generator-language-filtering.feature (~30 scenarios)

Tests every single-language project skips wrong generators:

- Python-only: ruff YES, biome NO
- TypeScript-only: biome YES, ruff NO
- Rust-only: neither
- Go-only: neither
- Shell-only: neither
- C++-only: neither
- Lua-only: neither
- dotnet-only: neither
- Universal-only: neither ruff nor biome, but editorconfig/codespell YES
- Python+TypeScript: both
- Python+Rust: ruff YES, biome NO
- TypeScript+Go: biome YES, ruff NO
- Rust+Go: neither

Plus universal configs always present (Scenario Outline across all languages).
Plus exact file counts per language combo.
Plus generator.languages field type assertions (ruff has ["python"], biome has
["typescript"], all others undefined).

#### B. language-detection-ignore.feature (~30 scenarios)

Tests every ignored directory for every language:

- node_modules: .py, .ts, .js, .lua, .sh files → NOT detected
- .venv/venv: .py → NOT detected
- vendor: .go, .py → NOT detected
- dist/build: .js, .cpp, .c → NOT detected
- target: .rs → NOT detected

Plus marker file override tests (pyproject.toml, package.json, Cargo.toml,
go.mod, CMakeLists.txt, .csproj always detect regardless of ignore).

Plus legitimate files outside ignored dirs still detect.
Plus multiple ignored dirs at once.
Plus DEFAULT_IGNORE list content assertions.
Plus custom ignore_paths from config merged with DEFAULT_IGNORE.

#### C. ci-workflow.feature (~15 scenarios)

Tests CI workflow content and structure:

- Contains actions/checkout@v4, setup-bun, bun install, hashFiles, bunx check
- Correct step ordering (checkout → setup-bun → install → check)
- hashFiles checks both bun.lock and bun.lockb
- Install step has if condition
- Valid YAML structure
- Job name is "check", runs on ubuntu-latest
- Triggers on push and pull_request
- File written to correct path

#### D. no-console-detection.feature (~20 scenarios)

Tests every project type combination:

- bin field (string and object forms) → off
- Each browser framework (react, vue, svelte, angular, next, nuxt, solid-js, preact) → error
- Framework in devDependencies → error
- bin + react (browser wins) → error
- Express/fastify (no bin, no browser) → warn
- Minimal package.json → warn
- No package.json → warn
- Integration: biome generator output contains correct noConsole level

#### E. bug-fixes.feature (E2E binary, ~15 scenarios)

End-to-end with compiled binary against fixtures:

- Init on each single-language fixture: correct configs present/absent
- Init on monorepo: both language configs present
- Universal configs always present (Scenario Outline)
- CI workflow contains bun install
- Init then check succeeds
- TypeScript fixture with node_modules .py file → ruff.toml absent

#### F. regression-prevention.feature (~10 scenarios)

Explicit regression tests for each bug:

- #123: generateConfigsStep with wrong language → file NOT written
- #124: detection with .py only in node_modules → only universal
- #125: CI_WORKFLOW contains bun install
- #127: biome generator with CLI config → no "error" for noConsole
- Cross-bug: ignore_paths propagates to detection + generation + check

### New step definition files

1. `tests/steps/generator-filtering.steps.ts` — generateConfigsStep with
   mock language plugins, assert files written/not written
2. `tests/steps/ci-workflow.steps.ts` — CI template content assertions,
   YAML validity, step ordering
3. `tests/steps/no-console.steps.ts` — project type detection from
   package.json, noConsole level assertions

### Existing step files to extend

1. `tests/steps/language.steps.ts` — add "should NOT be detected",
   "detected with default ignore paths", DEFAULT_IGNORE assertions
2. `tests/e2e/steps/init.steps.ts` — add "{string} should not exist"
3. `tests/e2e/steps/project.steps.ts` — fixture with seeded node_modules

### New E2E fixtures needed

- TypeScript fixture variant with `node_modules/pkg/helper.py` (for #124 E2E)

## Verification

Per phase:

1. `bun test` — all pass
2. `bun run typecheck` — clean
3. `bun run lint` — clean
4. `bun run build && ./dist/ai-guardrails check` — self-dogfood passes

Final:

5. Manual: `mkdir /tmp/ts-only && echo '{}' > /tmp/ts-only/package.json && ./dist/ai-guardrails init --project-dir /tmp/ts-only && ls /tmp/ts-only/ruff.toml` → should not exist
6. Manual: CLI project with bin field → noConsole "off" in biome.jsonc
7. Close issues #123, #124, #125, #126, #127 with fix commit references

## Notes

- #126 is duplicate of #125 — close #125 as duplicate, implement #126's hashFiles suggestion
- #127 is lower priority but easy to include since we're modifying biome generator for #123
- Browser wins over CLI when both present (conservative default)
- DEFAULT_IGNORE is hardcoded, not configurable — it's a sensible baseline that users
  can't misconfigure. Custom ignores come from config.ignorePaths on top.
