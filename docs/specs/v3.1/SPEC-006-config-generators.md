# SPEC-006: Config Generators

## Status: Draft
## Version: 3.1
## Last Updated: 2026-03-20

---

## Problem

Linter configs drift. A developer adds `"ignorePattern": ".*"` to their
`.eslintrc` to silence a noisy rule, and six months later every file matches
the pattern. An AI agent weakens `ruff.toml` to pass a check that should have
failed. Neither change is caught until the linter produces misleading results.

Manually auditing linter configs is tedious and error-prone. The configs are
scattered, formatted differently (TOML, JSONC, YAML, INI), and nobody remembers
what the intentional settings were.

The generator system also needs to be language-aware. A Python-only project
should not receive a `biome.jsonc` — generating dead configs creates confusion
and false validation failures.

---

## Solution

Eight generators, each responsible for one config file. Generators are pure
functions: `generate(config: ResolvedConfig): string`. They know nothing about
the filesystem — they produce a string and return it.

Every generated file receives a **hash header**: a SHA-256 digest of the file
body, embedded as a comment in the first line. The hash lets `validateConfigsStep`
detect tampering (hash present but invalid) vs user-owned files (no hash header).

Language gates (`languages?: readonly string[]`) prevent generators from running
when the relevant languages are not detected. The `applicableGenerators()`
function in `registry.ts` filters the full generator list to those matching
the active language set.

Config merge strategy (`merge | replace | skip`) lets users preserve their own
settings while absorbing guardrails additions. The merge strategy performs a
structured deep merge (existing data wins on key collision) for JSON/JSONC/TOML
files. Non-mergeable formats (`lefthook.yml`, `.editorconfig`, `.codespellrc`)
always replace.

---

## Philosophy

1. **Generators are pure functions.**
   WHY: Pure functions are testable in isolation, composable, and produce
   deterministic output. A generator that touches the filesystem cannot be
   unit tested without a fake filesystem.

2. **Hash headers make ownership explicit.**
   WHY: Without ownership markers, there is no way to distinguish a
   user-edited file from a generated one. The hash encodes "this file was
   last written by ai-guardrails and has not been touched since."

3. **Tamper detection is separate from staleness detection.**
   WHY: A merged file has a valid hash (re-hashed after merge) but would fail
   a staleness check against the raw generator output (because user settings
   were overlaid). Conflating the two would cause false staleness failures.
   The system detects tampering (hash present, invalid) but defers staleness
   detection to a future phase requiring provenance tracking.

4. **Stale config cleanup is opt-in via `replace` strategy.**
   WHY: Auto-deleting configs when a language is removed would surprise users
   who have other tools reading the same file. Explicit `replace` strategy
   signals the user's intent to let ai-guardrails own the config fully.

5. **Dynamic detection runs outside the pure generator.**
   WHY: Detecting biome version or noConsole level requires filesystem access.
   Polluting the generator with I/O would make it impure. The detection runs
   in the install pipeline and the result is injected into `ResolvedConfig.values`
   before generators are called.

6. **lefthook is a special-case generator.**
   WHY: `lefthook.yml` content depends on active language plugins, not just
   `ResolvedConfig`. The standard `generate(config)` signature cannot express
   this dependency. `generateLefthookConfig(config, languages)` is the correct
   call site. The `lefthookGenerator.generate()` method throws — it must never
   be called directly.

---

## Constraints

### Hard Constraints

- `ConfigGenerator.generate()` must be a pure function — no filesystem access
- Hash headers must be computed over the body content only (not including the
  header line itself)
- The `lefthookGenerator.generate()` method must throw to prevent accidental
  direct invocation
- Stale cleanup only removes files whose first line starts with a known hash
  prefix — never user-owned files
- Language gate filtering uses `g.languages.some(id => activeIds.has(id))`
  (any match, not all)

### Soft Constraints

- Generators should use `withHashHeader` / `withJsoncHashHeader` / `withMarkdownHashHeader`
  from `src/utils/hash.ts` — not compute hashes manually
- Merged files for JSONC extensions use `withJsoncHashHeader` after serialization
- Merged files for TOML extensions use `withHashHeader` after serialization
- Merged plain JSON files (`.json`) receive no hash header after merge (JSON
  has no comment syntax)

### Assumptions

| Assumption | If Wrong | Action |
|------------|----------|--------|
| biome v2 uses `files.includes` with negated globs for exclusions | biome changes exclusion syntax | Update `renderBiomeJson` filesSection |
| ruff `target-version = "py311"` is appropriate default | Python 3.10 support required | Add `target_version` to `ResolvedConfig.values`, make configurable |
| `.codespellrc` INI format is stable | codespell switches config format | Update codespell generator |
| lefthook `stage_fixed: true` replaces lint-staged behavior | lefthook changes API | Update lefthook generator and test fixtures |
| `noConsole` level detection from `package.json` is sufficient | Monorepo or non-standard layout | Add explicit `noConsole` config field |

---

## 1. Generators

Eight generators are registered in `ALL_GENERATORS` (order determines generation sequence):

| ID | Config File | Language Gate | Hash Format | Special Logic |
|----|-------------|---------------|-------------|---------------|
| `ruff` | `ruff.toml` | `python` | `# ai-guardrails:sha256=` | Uses `line_length`, `indent_width` from config values |
| `biome` | `biome.jsonc` | `typescript` | `// ai-guardrails:sha256=` | Dynamic `biome_version`, `noConsoleLevel`, negated glob exclusions |
| `editorconfig` | `.editorconfig` | none (always) | `# ai-guardrails:sha256=` | Static content |
| `markdownlint` | `.markdownlint.jsonc` | none (always) | `// ai-guardrails:sha256=` | Static content |
| `codespell` | `.codespellrc` | none (always) | `# ai-guardrails:sha256=` | Static content |
| `lefthook` | `lefthook.yml` | none (always) | `# ai-guardrails:sha256=` | Requires `generateLefthookConfig(config, languages)` — `generate()` throws |
| `claude-settings` | `.claude/settings.json` | none (always) | none (strict JSON, no comments) | Emits deny globs from `ALL_RULE_GROUPS`, three PreToolUse hook entries |
| `agent-rules` | `.ai-guardrails/agent-rules/base.md` | none (always) | `<!-- ai-guardrails:sha256= -->` | Base rules only; tool-specific additions handled separately |

### ruff (python-only)

Output file: `ruff.toml`. Language gate: `python`.

Generated content uses `config.values.line_length` (default 88) and
`config.values.indent_width` (default 4). All rules are selected (`select = ["ALL"]`),
with a curated `ignore` list excluding formatter conflicts, ANN (redundant with
pyright), docstring rules (opt-in), development markers, and high-false-positive rules.

Per-file ignores: `tests/**/*.py` ignores `ARG001`, `ARG002`, `PLR2004`.
`**/__init__.py` ignores `F401`.

### biome (typescript-only)

Output file: `biome.jsonc`. Language gate: `typescript`.

Dynamic behavior:
- `$schema` URL: included only when `config.values.biome_version` is a string.
  Set by `getBiomeVersion(commandRunner, projectDir)` during install pipeline.
- `files.includes`: negated glob exclusions (`["**", "!<path>", ...]`) from
  `config.ignorePaths`. Section omitted when `config.ignorePaths` is empty.
- `noConsole` level: `config.noConsoleLevel` — detected from `package.json` by
  `detectNoConsoleLevel()`. Values: `"off"` (CLI tools), `"warn"` (default),
  `"error"` (browser frameworks).
- `useBiomeIgnoreFolder` is explicitly set to `"off"` (prevents biome from
  silently skipping generated-code directories).

### editorconfig (always)

Output file: `.editorconfig`. No language gate.

Applies `indent_size = 4` for all files, overridden to `indent_size = 2` for
`*.{ts,js,tsx,jsx,json,yaml,yml,toml,md}`. Makefiles use tab indentation.
Go files use tab indentation. Static — ignores `ResolvedConfig`.

### markdownlint (always)

Output file: `.markdownlint.jsonc`. No language gate.

`MD013` line length set to 120, with `tables: false` and `code_blocks: false`
(long lines in tables/code blocks are acceptable). Several rules disabled for
compatibility with common documentation patterns. Static — ignores `ResolvedConfig`.

### codespell (always)

Output file: `.codespellrc`. No language gate.

Skips: `.git`, `*.lock`, `*.baseline`, `node_modules`, `.venv`, `venv`, `dist`,
`build`, `*/tests/fixtures/*`. `quiet-level = 2` suppresses binary file warnings.
Static — ignores `ResolvedConfig`.

### lefthook (always, special)

Output file: `lefthook.yml`. No language gate.

`lefthookGenerator.generate()` throws unconditionally. Callers must use
`generateLefthookConfig(config, activePlugins)` which receives the active
language plugin list and builds a language-aware pre-commit config.

Language-conditional hooks:
- `ruff-fix` (Python): `ruff check --fix {staged_files} && git add {staged_files}`
- `biome-fix` (TypeScript): `biome check --write {staged_files} && git add {staged_files}`

Language-independent hooks (always included):
- `gitleaks`: `gitleaks protect --staged --no-banner`
- `codespell`: spelling check on source files
- `markdownlint`: `markdownlint-cli2`
- `check-suppress-comments`: `ai-guardrails hook suppress-comments {staged_files}`
- `no-commits-to-main`: shell script guarding against direct main commits
- `commit-msg` hook: conventional commits regex validation

`ignorePaths` from config are converted from glob to Go regex via `globToRegex()`
and applied as `exclude:` fields on applicable hooks.

### claude-settings (always)

Output file: `.claude/settings.json`. No language gate. No hash header (strict
JSON has no comment syntax — tamper detection uses content comparison instead).

Emits:
1. `permissions.deny`: all `denyGlobs` collected from `ALL_RULE_GROUPS` via
   `collectDenyGlobs()`. Always emits ALL groups regardless of `disabled_groups`
   config — deny globs are a static safety net independent of hook-level config.
2. `hooks.PreToolUse`: three entries:
   - `Bash` → `dangerous-cmd`
   - `Edit|Write|NotebookEdit` → `protect-configs`
   - `Read` → `protect-reads`

Each hook command is prefixed with the guard:
```
[ ! -f ./dist/ai-guardrails ] && exit 0; ./dist/ai-guardrails hook <name>
```

### agent-rules (always)

Output file: `.ai-guardrails/agent-rules/base.md`. No language gate.
Hash format: `<!-- ai-guardrails:sha256= -->` (Markdown HTML comment).

Contains `BASE_RULES` only: five sections (Core Principles, Git Workflow, Code
Quality, Security). Tool-specific additions (Claude, Cursor, Windsurf, Copilot,
Cline, Aider) are built by `buildAgentRules(tool)` and written to separate
symlink targets by `setupAgentInstructionsStep`. The generator only writes the
base file.

---

## 2. Hash Header System

Three hash header formats, one per comment syntax:

| Prefix | Suffix | Used By | Function |
|--------|--------|---------|----------|
| `# ai-guardrails:sha256=` | none | `.editorconfig`, `ruff.toml`, `.codespellrc`, `lefthook.yml` | `withHashHeader()` |
| `// ai-guardrails:sha256=` | none | `biome.jsonc`, `.markdownlint.jsonc` | `withJsoncHashHeader()` |
| `<!-- ai-guardrails:sha256= ` | ` -->` | `.ai-guardrails/agent-rules/base.md` | `withMarkdownHashHeader()` |

The hash is computed over the body text only — the string passed to
`withHashHeader(content)` is hashed, then `${header}\n${content}` is returned.
The header line itself is never included in the hash input.

Validation in `validateConfigsStep`:
1. Extract first line (up to first `\n`).
2. Test against `HASH_HEADER_PATTERN` regex (covers all three formats).
3. Extract stored hash from capture group 1 (line-style) or group 2 (HTML comment).
4. Compute `computeHash(content_after_first_newline)`.
5. If stored hash does not match computed hash: report `tampered: <file>`.
6. If no hash header present: file is user-owned, skip tamper check.

IMPORTANT: `.claude/settings.json` has no hash header (JSON has no comment
syntax). Its tamper detection uses regeneration comparison — generate fresh
content and compare byte-for-byte.

---

## 3. Language Gates

The `languages?: readonly string[]` field on `ConfigGenerator` specifies which
language IDs must be detected for the generator to run.

```typescript
export interface ConfigGenerator {
  readonly id: string;
  readonly configFile: string;
  readonly languages?: readonly string[];
  generate(config: ResolvedConfig): string;
}
```

`applicableGenerators(activeLanguageIds: ReadonlySet<string>)` filters:
- Generators with `languages === undefined` always run
- Generators with a `languages` array run if `languages.some(id => activeIds.has(id))`

Language IDs used in gates:
- `"python"` — activates `ruff`
- `"typescript"` — activates `biome`
- All others (Go, Rust, Lua, C/C++, C#, shell) have no dedicated generator yet

The `activeLanguageIds` set is built from `detectLanguagesStep()` output:
```typescript
const activeLanguageIds = new Set(languages.map((l) => l.id));
```

In `validateConfigsStep`, if `activeLanguageIds` is provided, only applicable
generators are validated. Without it, all generators are validated (used by
`generate --check` which validates regardless of current language detection).

---

## 4. Config Merge Strategy

Three strategies available via `--config-strategy` flag:

| Strategy | Behavior on Existing File | Behavior on New File |
|----------|--------------------------|---------------------|
| `merge` (default) | Deep merge: existing wins on collision | Write generated content |
| `replace` | Overwrite with generated content | Write generated content |
| `skip` | Leave file untouched | Write generated content |

### Merge Implementation

`applyStrategy()` in `src/utils/config-merge.ts`:

1. If file does not exist: return generated content (strategy irrelevant).
2. If strategy is `skip`: return `null` (caller skips the write).
3. If strategy is `replace`: return generated content.
4. If strategy is `merge`:
   - Check if file extension is in `MERGEABLE_EXTENSIONS` (`.json`, `.jsonc`, `.toml`).
   - Non-mergeable formats (YAML, INI, Markdown): return generated content (replace behavior).
   - Parse existing content and generated content into `Record<string, unknown>`.
   - If either parse fails: throw `Error` with a message directing the user to
     `--config-strategy=replace`.
   - `deepMerge(generatedData, existingData)`: existing data wins on key collision.
   - Serialize the merged result with `serializeForMerge()`.
   - Apply hash header appropriate to file extension: JSONC → `withJsoncHashHeader`,
     TOML → `withHashHeader`, JSON → no header.

### Stale Config Cleanup

When strategy is `replace`, inactive generators whose config files still exist
and have a hash header are deleted:

```typescript
const inactive = ALL_GENERATORS.filter(
  (g) => g.languages !== undefined && !g.languages.some((id) => activeIds.has(id))
);
```

Only language-gated generators (those with `languages !== undefined`) are
candidates for cleanup — language-agnostic generators (editorconfig, lefthook,
etc.) are never removed. Only files whose first line starts with a known hash
prefix are deleted — user-owned files are never touched.

---

## 5. Dynamic Detection

Two values are detected at install/generate time and injected into
`ResolvedConfig` before generators run:

### biome Version Detection

`getBiomeVersion(commandRunner, projectDir)` runs biome to extract its version
string. The version is stored in `config.values.biome_version`. The biome
generator uses this to emit a versioned `$schema` URL.

Called only when TypeScript is an active language (biome is TypeScript-only).
Resolved by checking `projectDir/node_modules/.bin/biome` first, then global.

### noConsole Level Detection

`detectNoConsoleLevel(packageJson: unknown)` in `src/utils/detect-project-type.ts`
reads the parsed `package.json` and returns one of three levels:

| Condition | Level | Rationale |
|-----------|-------|-----------|
| Browser framework in dependencies | `"error"` | `console.log` is debugging noise in browser apps |
| `bin` field present (and no browser framework) | `"off"` | `console.log` is the output mechanism for CLI tools |
| Everything else | `"warn"` | Default for server, library, or unknown project type |

Browser frameworks detected: `react`, `vue`, `svelte`, `@angular/core`, `next`,
`nuxt`, `solid-js`, `preact`, `qwik`.

Browser detection takes precedence over CLI detection — a project with both
a `bin` field and a React dependency is treated as a browser app.

Called only when TypeScript is active and `package.json` exists. Falls back to
`config.noConsoleLevel` (from `ResolvedConfig`) if file is absent or not parseable.

---

## Testing Strategy

- Each generator is unit tested by calling `generate(config)` with known `ResolvedConfig`
  values and asserting the output string
- Snapshot tests capture generator output: `expect(output).toMatchSnapshot()`.
  Snapshot changes require explicit `bun test --update-snapshots` and review.
- `withHashHeader`, `withJsoncHashHeader`, `withMarkdownHashHeader` are unit tested
  for correct prefix format and hash inclusion
- `computeHash` is tested for determinism (same input → same output)
- `applyStrategy` is tested for each combination of (strategy × file exists/absent ×
  mergeable/non-mergeable extension)
- `detectNoConsoleLevel` is tested with: no package.json, browser framework dep,
  bin field, browser+bin, plain library
- `applicableGenerators` is tested with: empty set, python-only, typescript-only, both
- `generateConfigsStep` is tested with `FakeFileManager` for written/skipped/removed
  outcome classification
- `validateConfigsStep` is tested for: valid hash, tampered hash, missing file, no header
- `lefthookGenerator.generate()` is tested to throw
- Coverage target: 85%+ on all generators/, steps/generate-configs.ts,
  steps/validate-configs.ts, utils/hash.ts, utils/config-merge.ts

---

## Evolution

| Stable While | Revisit If | Impact |
|-------------|------------|--------|
| Eight generators are the full set | Adding new language support | registry.ts, ALL_GENERATORS, this spec |
| `# ai-guardrails:sha256=` hash prefix | Changing tamper detection mechanism | hash.ts, validate-configs.ts, HASH_HEADER_PATTERN |
| Stale cleanup checks first-line hash prefix | Adding a non-hash-header generator | generate-configs.ts stale cleanup logic |
| `merge/replace/skip` are the three strategies | Adding `interactive` merge strategy | config/schema.ts ConfigStrategySchema, applyStrategy |
| biome v2 negated glob syntax for exclusions | biome v3 changes config format | biome.ts renderBiomeJson |
| lefthook `generate()` throws | Refactoring to pass languages through config | lefthook.ts, generate-configs.ts special case |
| Provenance tracking is deferred | Implementing staleness detection | validate-configs.ts, generate-configs.ts |

---

## Cross-References

- SPEC-000: Overview — tamper protection philosophy, whitelist model
- SPEC-001: Architecture — `ConfigGenerator` interface, `PipelineContext`, infra injection
- SPEC-002: Config System — `ResolvedConfig`, `ConfigStrategy`, `noConsoleLevel`
- SPEC-003: Linter System — language plugin IDs used in language gates
- SPEC-004: CLI Commands — `generate`, `init`, `install` commands that invoke generators
- SPEC-005: Hook System — `claudeSettingsGenerator` emits deny globs from rule groups
