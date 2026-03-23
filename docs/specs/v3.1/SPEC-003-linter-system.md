# SPEC-003: Linter System

## Status: Draft
## Version: 3.1
## Last Updated: 2026-03-20

---

## Problem

A multi-language codebase needs different linters for each language: Python needs
ruff and pyright, TypeScript needs biome and tsc, Rust needs clippy. Running all
linters on every project regardless of language wastes time and produces false
"tool not found" errors. Running the wrong linter on the wrong files produces
noise.

Each linter produces output in a different format: JSON arrays, NDJSON,
`rdjson`, text with regex-parsable lines. Downstream code should not need to
handle this variety — it should receive a uniform `LintIssue[]`.

Fingerprinting lint issues by line number is fragile: inserting one line above
an issue shifts every subsequent fingerprint, causing all baseline entries below
the insertion point to be treated as new. Fingerprints must be content-stable.

---

## Solution

Three layered subsystems:

1. **Language plugins** — detect whether a language is present and return the
   applicable runners.
2. **Linter runners** — run one tool, parse its output format, and return
   `LintIssue[]` with content-stable fingerprints.
3. **Fingerprinting** — `applyFingerprints` reads source files, extracts a 5-line
   context window (flagged line ± 2), and produces a SHA-256 digest that is
   stable across line number changes.

The pipeline calls `detectLanguages` once, collects the union of all active
runners, runs them in parallel, and merges the results.

---

## Philosophy

1. **One runner per tool.** Each linter is a self-contained module with its own
   parser, `isAvailable`, and `run`. WHY: coupling multiple linters in one file
   makes it impossible to test or replace them independently.

2. **Parse non-zero exits as output.** Many linters exit non-zero when issues are
   found (biome, selene, markdownlint, codespell). Runners parse `stdout`
   regardless of `exitCode`. WHY: treating non-zero as "error" would suppress all
   issues — exactly the opposite of what enforcement requires.

3. **Content-stable fingerprints.** Fingerprints hash `rule + relative-file-path +
   trimmed line content + 2 lines before + 2 lines after`. WHY: position-based
   fingerprints (using only line number) break whenever code is inserted or
   deleted above the flagged line. Content-based fingerprints survive refactoring
   that doesn't touch the flagged line itself.

4. **Relative paths in fingerprints.** `applyFingerprints` converts the absolute
   `LintIssue.file` to a project-relative path before computing the hash. WHY:
   absolute paths embed the developer's filesystem layout, making baselines
   non-portable across machines and CI environments.

5. **Always-on universal plugin.** `universalPlugin.detect()` always returns
   `true`. WHY: codespell and markdownlint apply to any codebase — typos and
   markdown linting are language-agnostic.

6. **Ignore paths applied at detection, not at lint time.** `DEFAULT_IGNORE` and
   project `ignore_paths` are merged and passed to `detect()` as `ignorePaths`.
   WHY: if `node_modules/` contains a `.py` file, the Python plugin would activate
   even though no user code is Python. Detection must respect the same exclusions
   as linting.

7. **Version-adaptive runner flags.** `golangci-lint` changed its JSON output flag
   in v1.64. The runner detects the version once, caches the result, and uses the
   correct flag. WHY: hardcoding either flag breaks for users on the other side of
   the version boundary. Version detection is the correct solution.

---

## Constraints

### Hard Constraints

- All runners must return `LintIssue[]` — no runner-specific types leak to callers
- `LintIssue.file` is always an absolute path
- `FingerprintOpts.file` is always a project-relative path
- `LintIssue.line` and `LintIssue.col` are always 1-indexed
- Runners must not throw — return `[]` on empty or malformed output
- No mypy — use pyright (`mypy --output json` is explicitly unstable)
- No luacheck — use selene (selene has JSON output, luacheck does not)
- Biome reporter: `--reporter=rdjson` — NOT `--reporter=json` (json is experimental)

### Soft Constraints

- `resolveToolPath` checks `projectDir/node_modules/.bin/` before PATH for
  `biome`, `tsc`, `pyright`
- Version caches (`biomeVersionCache`, `cachedVersionFlagPromise`) are
  module-level — reset between tests with exported `reset*()` functions
- Shell file discovery is shared: `shfmt` reuses `findShellFiles` from `shellcheck`

### Assumptions

| Assumption | If Wrong | Action |
|------------|----------|--------|
| Ruff JSON output format stable | Ruff changes format | Update `isRuffItem` guard and `parseRuffOutput` |
| Biome rdjson `range.start` is 1-indexed | Biome changes to 0-indexed | Add `+1` to line/col in `parseBiomeRdjsonOutput` |
| Pyright `--outputjson` is stable | Pyright changes output format | Update `isPyrightOutput`/`isPyrightDiagnostic` guards |
| `golangci-lint` v1.64 version boundary is correct | Boundary shifts | Update `isV164Plus` logic in `detectVersionFlag` |
| clang-tidy emits diagnostics on stderr | Moves to stdout | Update runner to read `result.stdout` |

---

## Runners

All 13 runners, their IDs, config files, detection method, and output format.

> **Profile-based rule filtering:** Each runner's effective rule set is
> determined by `ResolvedConfig.profile` (strict / standard / minimal). Runners
> receive the resolved config via `RunOptions` and apply profile-specific flags
> or config values before invoking the underlying tool. See SPEC-002 §Profile
> Rule Filtering for the per-runner mapping table.

| ID | Name | `configFile` | Output Format | Install Method |
|----|------|-------------|---------------|----------------|
| `ruff` | Ruff | `ruff.toml` | JSON array | `pip install ruff` |
| `pyright` | Pyright | `pyrightconfig.json` | JSON object (`--outputjson`) | `npm install -D pyright` or `pip install pyright` |
| `biome` | Biome | `biome.jsonc` | rdjson (`--reporter=rdjson`) | `npm install -D @biomejs/biome` |
| `tsc` | TypeScript Compiler | `null` | Text lines (`file(line,col): severity TSxxxx: msg`) | `npm install -D typescript` |
| `shellcheck` | ShellCheck | `null` | JSON object (`--format=json1`) | `brew install shellcheck` / `apt` |
| `shfmt` | shfmt | `null` | Text — one filename per line (`-l`) | `brew install shfmt` / `go install` |
| `clippy` | Clippy | `null` | NDJSON (`--message-format=json`) | `rustup component add clippy` |
| `golangci-lint` | golangci-lint | `.golangci.yml` | JSON object (version-adaptive flag) | `brew install golangci-lint` / `go install` |
| `selene` | Selene | `selene.toml` | JSON array (`--display-style=Json2`) | `cargo install selene` / `brew` |
| `clang-tidy` | clang-tidy | `.clang-tidy` | Text lines on stderr | `brew install llvm` / `apt install clang-tidy` |
| `dotnet-build` | dotnet build | `null` | Text lines (`stdout`, MSBuild format) | Install .NET SDK: https://dot.net |
| `codespell` | Codespell | `.codespellrc` | Text lines (`--quiet-level=2`) | `pip install codespell` |
| `markdownlint` | markdownlint | `.markdownlint.jsonc` | Text lines | `npm install -g markdownlint-cli2` |

### Runner-Specific Notes

**ruff:** Rule codes starting with `E` or `F` map to `"error"` severity;
everything else maps to `"warning"`. Filenames from ruff may be relative —
resolved via `resolve(projectDir, item.filename)`.

**pyright:** Uses `resolveToolPath` to check `node_modules/.bin/pyright` first.
0-indexed lines/columns from pyright converted to 1-indexed: `line + 1`,
`character + 1`. `"information"` severity diagnostics are skipped.

**biome:** Uses `resolveToolPath`. Version cached per `projectDir`. ANSI escape
codes stripped before JSON parsing (biome emits ESC codes in TTY-like contexts).
Range is already 1-indexed in rdjson output.

**tsc:** Uses `resolveToolPath`. Runs with `--noEmit --pretty false`. Parses
combined `stdout + stderr`. No config file managed (`configFile: null`).

**shellcheck:** Runs `findShellFiles()` (glob `**/*.{sh,bash,zsh,ksh}`). Returns
`[]` early if no shell files found. Maps `level === "error"` to `"error"`,
everything else to `"warning"`.

**shfmt:** Reuses `findShellFiles()` from shellcheck module. Runs `shfmt -l`
(list files that would change). Each output line is a filename — synthesizes a
`LintIssue` at `line: 1, col: 1` with `rule: "shfmt/format"`.

**clippy:** Parses NDJSON. Filters to `reason === "compiler-message"` entries
with non-null `code`. Uses primary span (where `is_primary === true`). Runs with
`-D warnings` to treat all warnings as errors.

**golangci-lint:** Detects version once, caches. v1.64+ uses
`--output.json.path=stdout`; older uses `--out-format=json`. `Issues` field may
be `null` (no issues) — handled explicitly.

**selene:** Runs against `projectDir` (not individual files). Returns `[]` early
if no `**/*.lua` files found. `severity === "Error"` maps to `"error"`,
everything else to `"warning"`.

**clang-tidy:** Globs `**/*.cpp`, `**/*.c`, `**/*.cxx`, `**/*.cc`, `**/*.h`,
`**/*.hpp` using `Promise.all`. Deduplicates with a `Set`. Skips `note`-level
diagnostics. Reads `result.stderr` (not stdout).

**codespell:** Runs with `--quiet-level=2`. Strips leading `./` from paths.
Column is always `1` (codespell does not emit column info).

**markdownlint:** Passes hardcoded exclusions: `!node_modules/**`, `!dist/**`,
`!.venv/**`, `!venv/**`, `!build/**`. Column is always `1`.

---

## Language Plugins

All 9 plugins, their IDs, detection rules, and runners:

| ID | Name | Detection | Runners |
|----|------|-----------|---------|
| `python` | Python | `pyproject.toml` exists OR `**/*.py` glob | `ruff`, `pyright` |
| `typescript` | TypeScript/JS | `package.json` exists OR `**/*.ts`/`**/*.js` glob | `biome`, `tsc` |
| `rust` | Rust | `Cargo.toml` exists | `clippy` |
| `go` | Go | `go.mod` exists | `golangci-lint` |
| `shell` | Shell | `**/*.{sh,bash,zsh,ksh}` glob | `shellcheck`, `shfmt` |
| `cpp` | C/C++ | `CMakeLists.txt` exists OR `**/*.cpp`/`**/*.c` glob | `clang-tidy` |
| `dotnet` | .NET | `**/*.csproj` OR `**/*.sln` glob | `dotnet-build` |
| `lua` | Lua | `**/*.lua` glob | `selene` |
| `universal` | Universal | always `true` | `codespell`, `markdownlint` |

### Detection Priority Order

Plugins run in this order in `ALL_PLUGINS` (from `registry.ts`):

```
python → typescript → rust → go → shell → cpp → dotnet → lua → universal
```

All plugins run in parallel via `Promise.all`. Universal is always last by
convention but the order does not affect correctness — all are collected and
filtered.

### Marker File vs Glob Detection

| Strategy | Plugins |
|----------|---------|
| Marker file only (exact exists check) | `rust` (`Cargo.toml`), `go` (`go.mod`) |
| Marker file OR glob | `python` (`pyproject.toml` OR `**/*.py`), `typescript` (`package.json` OR `**/*.ts`/`**/*.js`), `cpp` (`CMakeLists.txt` OR `**/*.cpp`/`**/*.c`) |
| Glob only | `shell`, `lua`, `dotnet` |
| Always | `universal` |

Marker file checks use `fileManager.exists()` and short-circuit before glob.
Glob checks use `fileManager.glob()` with `ignorePaths` to exclude
`DEFAULT_IGNORE` and project `ignore_paths`.

### .NET Plugin Note

`dotnetPlugin.runners()` returns `[dotnetBuildRunner]`. The runner invokes
`dotnet build --no-restore` and parses `stdout` for `warning MSBuild-format`
diagnostic lines. Output format:

```
src/MyClass.cs(12,5): warning CS0168: Variable 'e' is declared but never used [MyProject.csproj]
```

Parser regex: `^(.+)\((\d+),(\d+)\): (warning|error) (CS\d+): (.+)$`

| Field | Source |
|-------|--------|
| `file` | Group 1 — resolved to absolute path via `resolve(projectDir, match[1])` |
| `line` | Group 2 |
| `col` | Group 3 |
| `severity` | Group 4 (`warning` → `"warning"`, `error` → `"error"`) |
| `rule` | Group 5 (e.g. `CS0168`) |
| `message` | Group 6 |

`isAvailable()` runs `dotnet --version`; returns false if the command fails.
`configFile` is `null` — the runner uses whatever `.csproj`/`.sln` files exist
in the project. `installHint` is `"Install .NET SDK: https://dot.net"`.

Profile filtering: `strict` reports warnings and errors; `standard` reports
warnings and errors; `minimal` reports errors only (`CS\d{4}` at error severity).
Warning suppression via `#pragma warning disable CSXXXX` is detected by the
suppress-comments hook and rejected.

---

## Detection System

### `detectLanguages` (`src/languages/registry.ts`)

```typescript
export async function detectLanguages(
  projectDir: string,
  fileManager: FileManager,
  ignorePaths?: readonly string[]
): Promise<LanguagePlugin[]>
```

Merges `DEFAULT_IGNORE` with project `ignorePaths`, then calls all plugins in
parallel. Returns only plugins where `detect()` returned `true`.

### `DEFAULT_IGNORE` (`src/languages/constants.ts`)

```typescript
export const DEFAULT_IGNORE: readonly string[] = [
  "node_modules/**",
  ".venv/**",
  "venv/**",
  "vendor/**",
  "dist/**",
  "build/**",
  "target/**",
  ".git/**",
  "__pycache__/**",
];
```

Applied to every glob call during language detection. Combined with project
`ignore_paths` from `ResolvedConfig.ignorePaths`.

---

## Fingerprinting

### Two-Layer Design

**Layer 1: `fingerprintIssue`** (`src/utils/fingerprint.ts`)

Takes an issue and a `sourceLines: string[]` array. Extracts:
- `lineContent = sourceLines[line - 1]` (1-indexed to 0-indexed)
- `contextBefore`: up to 2 lines before (clamped to array start)
- `contextAfter`: up to 2 lines after (clamped to array end)

Calls `computeFingerprint` with these values.

```typescript
export function fingerprintIssue(
  issue: Omit<LintIssue, "fingerprint">,
  sourceLines: string[]
): string
```

`CONTEXT_LINES = 2` is a module constant.

**Layer 2: `computeFingerprint`** (`src/models/lint-issue.ts`)

```typescript
export function computeFingerprint(opts: FingerprintOpts): string {
  const input = [
    rule,
    file,               // project-relative path
    lineContent.trim(),
    ...contextBefore.map((l) => l.trim()),
    ...contextAfter.map((l) => l.trim()),
  ].join("\n");
  return createHash("sha256").update(input).digest("hex");
}
```

All lines are `.trim()`ped before hashing — fingerprints are whitespace-agnostic
for indentation changes.

### `applyFingerprints` (`src/utils/apply-fingerprints.ts`)

```typescript
export async function applyFingerprints(
  raw: Omit<LintIssue, "fingerprint">[],
  projectDir: string,
  fileManager: FileManager
): Promise<LintIssue[]>
```

Workflow:
1. `groupBy(raw, (i) => i.file)` — group by absolute file path
2. `Promise.all(absFiles.map(readFile))` — read all source files in parallel
3. For each issue in each group:
   - `relFile = relative(projectDir, absFile)` — convert to project-relative
   - `fingerprintIssue({ ...issue, file: relFile }, sourceLines)`
4. Returns complete `LintIssue[]` with fingerprints

If a file cannot be read (deleted between lint and fingerprint), `sourceLines`
is `[]`. `fingerprintIssue` handles this gracefully — `lineContent` becomes `""`.

### `groupBy` (`src/utils/collections.ts`)

```typescript
export function groupBy<T>(items: readonly T[], key: (item: T) => string): Map<string, T[]>
```

Used by `applyFingerprints` to batch source file reads — one `readText` call per
unique file, regardless of how many issues that file has.

---

## Testing Strategy

**Framework:** `bun:test`.

**Fixtures:** `tests/fixtures/` — static linter output samples (JSON, NDJSON,
text). One fixture file per linter per scenario (clean, with issues, malformed).

**Fakes:** `FakeFileManager` seeded with source file content for fingerprint
tests. `FakeCommandRunner` with canned responses for `isAvailable` and `run`
tests.

**Test pattern:** `test_<function>_<scenario>_<expected>`, e.g.:
- `test parseRuffOutput returns empty array for empty stdout`
- `test parseRuffOutput skips items without location field`
- `test applyFingerprints groups by file and reads each once`
- `test fingerprintIssue uses trimmed content for whitespace stability`
- `test detectLanguages skips node_modules when detecting python`

**Snapshot tests:** Not used for linter parsers — fixture-based tests are
more readable and don't require snapshot files.

**Coverage:** All 13 parser functions must have tests for:
- Empty output
- Valid output with one issue
- Valid output with multiple issues
- Malformed output (returns `[]`, does not throw)

---

## Evolution

| Stable While | Revisit If | Impact |
|-------------|------------|--------|
| `fingerprintIssue` uses ±2 context lines | False positives increase | Increase `CONTEXT_LINES` constant — all existing baselines invalidated |
| All runners parse output themselves | Shared parsing utilities needed | Extract common JSON/text parsers to `utils/` |
| `dotnet-build` parses MSBuild text format | dotnet emits structured JSON | Update parser to use JSON output, update fixtures |
| `DEFAULT_IGNORE` is the fixed base | User wants to add global ignores | Add machine-config `ignore_paths` field |
| `golangci-lint` v1.64 is the version boundary | golangci-lint changes output format again | Update `detectVersionFlag` logic, update version cache reset |
| `applyFingerprints` reads all source files | Source files too large to read in full | Add line range reading to `FileManager` interface |

---

## Cross-References

- SPEC-000: Overview — 13 runners / 9 plugins scope, whitelist model
- SPEC-001: Architecture — `LinterRunner`, `LanguagePlugin`, `FileManager` interfaces; `applyFingerprints` DI pattern
- SPEC-002: Config System — `ResolvedConfig.ignorePaths` used in `detectLanguages`; `ResolvedConfig.isAllowed` used in run step filtering
- SPEC-007: Baseline System — fingerprint stability requirements for hold-the-line baseline matching
