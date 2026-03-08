# SPEC-003: Linter System

## Status: Draft

---

## Overview

Every linter is a `LinterRunner`. Every language is a `LanguagePlugin` that
composes runners. The `check` pipeline asks each active plugin for its runners,
runs them, and gets back normalized `LintIssue[]`. No linter-specific code
lives outside its runner file.

---

## LintIssue — normalized domain type

```typescript
// models/lint-issue.ts

export interface LintIssue {
  readonly rule: string;       // "E501", "no-unused-vars", "S1481"
  readonly linter: string;     // "ruff", "mypy", "biome"
  readonly file: string;       // absolute path
  readonly line: number;       // 1-indexed
  readonly col: number;        // 1-indexed
  readonly message: string;
  readonly severity: "error" | "warning";
  readonly fingerprint: string; // content-stable SHA-256
}

/** Compute a fingerprint that survives file moves and minor reformats */
export function computeFingerprint(opts: {
  rule: string;
  file: string;
  lineContent: string;      // content of the flagged line
  contextBefore: string[];  // up to 2 lines before
  contextAfter: string[];   // up to 2 lines after
}): string { ... }
```

---

## Language → Runner mapping

| Language | Runners (standard profile) | Detection |
|----------|---------|-----------|
| Python | ruff + **pyright** (not mypy — see SPEC-008) | `pyproject.toml` OR `*.py` files |
| TypeScript/JS | biome + tsc | `package.json` OR `*.ts`/`*.js` files |
| Shell | shellcheck + shfmt | `*.sh`, `*.bash`, `*.zsh` files |
| Rust | clippy | `Cargo.toml` |
| Go | go-vet, staticcheck | `go.mod` |
| C/C++ | clang-tidy | `CMakeLists.txt` OR `*.cpp`/`*.c` |
| .NET | dotnet-build | `*.csproj` OR `*.sln` |
| Lua | luacheck | `*.lua` files |
| Universal | codespell, markdownlint | Always active |

---

## Runner Specifications

## Critical output format notes

Several tools produce **NDJSON** (newline-delimited JSON — one object per line, NOT a JSON array).
Parse these differently:

```typescript
// JSON array: JSON.parse(stdout)               ← ruff, bandit, shellcheck, selene, biome rdjson
// NDJSON:     stdout.split("\n").filter(Boolean).map(line => JSON.parse(line))
//                                               ← clippy, staticcheck, govulncheck
// Text/regex: per-tool regex on stdout/stderr   ← clang-tidy, dotnet build, tsc, codespell
// Exit code:  result.exitCode !== 0             ← rustfmt, shfmt, clang-format, stylua
```

**pyright vs mypy:** Use pyright. `mypy --output json` is explicitly unstable (open issues
\#10816, \#13874 upstream). pyright's `--outputjson` is stable and single-document.

**biome reporter:** Use `--reporter=rdjson` not `--reporter=json`. The json reporter is
marked experimental and may change in patch releases. rdjson (Review Dog JSON) is stable.

**golangci-lint flag change (v1.64+):** `--out-format=json` was renamed to
`--output.json.path=stdout`. Version-detect before choosing the flag.

**govulncheck exit code:** Always 0 when using `-json` regardless of findings. Must parse stream.

**clang-tidy:** No native JSON output. Parse text from stderr with regex, or use the
`clang-tidy-sarif` wrapper (separate binary) to get SARIF output.

**dotnet format exit code:** Exits **2** (not 1) on formatting violations.

---

### `ruff` (Python linting + formatting)

```typescript
export const ruffRunner: LinterRunner = {
  id: "ruff",
  name: "Ruff",
  configFile: "ruff.toml",

  async isAvailable(runner) {
    const r = await runner.run(["ruff", "--version"]);
    return r.exitCode === 0;
  },

  async run({ projectDir, config, commandRunner }) {
    const result = await commandRunner.run(
      ["ruff", "check", "--output-format=json", projectDir],
      { cwd: projectDir }
    );
    return parseRuffOutput(result.stdout, config);
  },

  generateConfig(config) {
    return renderRuffToml(config); // template + config values merged
  },
};

// Output shape from `ruff check --output-format=json`:
// [{ "code": "E501", "filename": "...", "location": { "row": 1, "column": 1 }, "message": "..." }]
function parseRuffOutput(stdout: string, config: ResolvedConfig): LintIssue[] { ... }
```

### `pyright` (Python type checking — preferred over mypy)

```typescript
export const pyrightRunner: LinterRunner = {
  id: "pyright",
  name: "Pyright",
  configFile: "pyrightconfig.json",

  async run({ projectDir, commandRunner }) {
    const result = await commandRunner.run(
      ["pyright", "--outputjson", projectDir],
      { cwd: projectDir }
    );
    return parsePyrightOutput(result.stdout);
  },

  generateConfig(config) {
    return renderPyrightConfig(config);
  },
};

// pyright --outputjson: single stable JSON document
// { "generalDiagnostics": [{ "file": "...", "range": { "start": { "line": 9 } },
//   "severity": "error", "message": "...", "rule": "reportMissingTypeArgument" }],
//   "summary": { "errorCount": 1 } }
//
// WHY NOT mypy: `mypy --output json` is explicitly unstable (upstream issues #10816, #13874).
// Format changes between minor versions. pyright --outputjson is stable and single-document.
```

### `shellcheck` (Shell linting)

```typescript
export const shellcheckRunner: LinterRunner = {
  id: "shellcheck",
  name: "ShellCheck",
  configFile: null,  // no managed config file

  async run({ projectDir, commandRunner, fileManager }) {
    const files = await fileManager.glob("**/*.{sh,bash,zsh}", projectDir);
    if (files.length === 0) return [];
    const result = await commandRunner.run(
      ["shellcheck", "--format=json1", ...files],
      { cwd: projectDir }
    );
    return parseShellcheckOutput(result.stdout);
  },

  generateConfig: () => null,
};

// shellcheck --format=json1:
// {"comments": [{"file": "...", "line": 1, "column": 1, "level": "error", "code": 2034, "message": "..."}]}
```

### `clippy` (Rust linting)

```typescript
export const clippyRunner: LinterRunner = {
  id: "clippy",
  name: "Clippy",
  configFile: null,  // clippy config is in Cargo.toml [workspace.metadata.clippy]

  async run({ projectDir, commandRunner }) {
    const result = await commandRunner.run(
      ["cargo", "clippy", "--message-format=json", "--", "-D", "warnings"],
      { cwd: projectDir }
    );
    return parseClippyOutput(result.stdout);
  },

  generateConfig: () => null,
};

// cargo clippy --message-format=json: one JSON object per line
// { "reason": "compiler-message", "message": { "code": { "code": "clippy::..." }, "spans": [...] } }
```

### `biome` (TypeScript/JS linting + formatting)

```typescript
export const biomeRunner: LinterRunner = {
  id: "biome",
  name: "Biome",
  configFile: "biome.json",

  async run({ projectDir, commandRunner }) {
    // Use rdjson (Review Dog JSON) — more stable than --reporter=json which is experimental
    const result = await commandRunner.run(
      ["biome", "ci", "--reporter=rdjson", projectDir],
      { cwd: projectDir }
    );
    return parseBiomeRdjsonOutput(result.stdout);
  },

  generateConfig(config) {
    return renderBiomeJson(config);
  },
};

// rdjson shape:
// { "diagnostics": [{ "location": { "path": { "text": "src/foo.ts" },
//   "range": { "start": { "line": 10, "column": 5 } } },
//   "severity": "ERROR", "code": { "value": "lint/correctness/noUnusedVariables" },
//   "message": "..." }] }
```

### `golangci-lint` (Go — meta-linter wrapping go vet + staticcheck + 50+ more)

```typescript
export const golangciLintRunner: LinterRunner = {
  id: "golangci-lint",
  name: "golangci-lint",
  configFile: ".golangci.yml",

  async run({ projectDir, commandRunner }) {
    // CRITICAL: flag changed in v1.64. Detect version first.
    const versionResult = await commandRunner.run(["golangci-lint", "--version"], { cwd: projectDir });
    const version = parseGolangciVersion(versionResult.stdout); // e.g. "1.64.1"
    const jsonFlag = isGte(version, "1.64.0")
      ? "--output.json.path=stdout"
      : "--out-format=json";

    const result = await commandRunner.run(
      ["golangci-lint", "run", jsonFlag, "./..."],
      { cwd: projectDir }
    );
    return parseGolangciOutput(result.stdout);
  },

  generateConfig(config) {
    return renderGolangciYml(config);
  },
};

// WHY golangci-lint over separate go vet + staticcheck:
// golangci-lint wraps both, plus 50+ more linters, in a single configurable run.
// Used by Kubernetes, Prometheus, Terraform. De facto Go CI standard.
```

### `clang-tidy` (C/C++)

```typescript
export const clangTidyRunner: LinterRunner = {
  id: "clang-tidy",
  name: "clang-tidy",
  configFile: ".clang-tidy",

  async run({ projectDir, commandRunner, fileManager }) {
    const files = await fileManager.glob("**/*.{cpp,c,cxx,cc}", projectDir);
    if (files.length === 0) return [];
    // Run with --export-fixes to get JSON output
    const result = await commandRunner.run(
      ["clang-tidy", "--quiet", ...files],
      { cwd: projectDir }
    );
    return parseClangTidyOutput(result.stderr); // clang-tidy writes to stderr
  },

  generateConfig(config) {
    return renderClangTidy(config);
  },
};
```

### `selene` (Lua — preferred over luacheck)

```typescript
export const seleneRunner: LinterRunner = {
  id: "selene",
  name: "selene",
  configFile: "selene.toml",

  async run({ projectDir, commandRunner }) {
    // Json2 is the newer, preferred format
    const result = await commandRunner.run(
      ["selene", "--display-style=Json2", projectDir],
      { cwd: projectDir }
    );
    return parseSeleneOutput(result.stdout);
  },

  generateConfig(config) {
    return renderSeleneToml(config);
  },
};

// WHY selene over luacheck:
// selene has JSON output (Json2). luacheck has NO JSON output.
// selene handles Luau syntax; actively maintained. luacheck dev has slowed.
//
// Json2 shape:
// [{ "filename": "src/foo.lua", "primary_label": "unused variable `x`",
//    "code": "unused_variable", "severity": "Warning",
//    "start_line": 10, "start_column": 5 }]
```

### `codespell` (Universal spell checking)

```typescript
export const codespellRunner: LinterRunner = {
  id: "codespell",
  name: "codespell",
  configFile: ".codespellrc",

  async run({ projectDir, commandRunner }) {
    const result = await commandRunner.run(
      ["codespell", "--quiet-level=2"],
      { cwd: projectDir }
    );
    return parseCodespellOutput(result.stdout);
  },

  generateConfig(config) {
    return renderCodespellrc(config);
  },
};
```

### `markdownlint` (Universal markdown)

```typescript
export const markdownlintRunner: LinterRunner = {
  id: "markdownlint",
  name: "markdownlint",
  configFile: ".markdownlint.jsonc",

  async run({ projectDir, commandRunner }) {
    const result = await commandRunner.run(
      ["markdownlint-cli2", "**/*.md", "--config", ".markdownlint.jsonc"],
      { cwd: projectDir }
    );
    return parseMarkdownlintOutput(result.stdout);
  },

  generateConfig(config) {
    return renderMarkdownlintJsonc(config);
  },
};
```

---

## Language Plugin Registry (`languages/registry.ts`)

```typescript
/** All built-in language plugins, in detection priority order */
const ALL_PLUGINS: readonly LanguagePlugin[] = [
  pythonPlugin,
  typescriptPlugin,
  rustPlugin,
  goPlugin,
  shellPlugin,
  cppPlugin,
  dotnetPlugin,
  luaPlugin,
  universalPlugin,   // always last — always active
];

/**
 * Detect which languages are present in the project.
 * Returns active plugins in priority order.
 * Universal plugin is always included.
 */
export async function detectLanguages(
  projectDir: string,
  fileManager: FileManager,
): Promise<LanguagePlugin[]> {
  const results = await Promise.all(
    ALL_PLUGINS.map(async (plugin) => ({
      plugin,
      active: await plugin.detect({ projectDir, fileManager }),
    }))
  );
  return results.filter((r) => r.active).map((r) => r.plugin);
}
```

---

## Applying Config to Linter Output

After a runner returns `LintIssue[]`, the check pipeline filters based on
`ResolvedConfig`:

```typescript
function filterIssues(
  issues: LintIssue[],
  config: ResolvedConfig,
): LintIssue[] {
  return issues.filter(
    (issue) => !config.isAllowed(issue.rule, issue.file)
  );
}
```

Inline allow comments are applied as a second pass:

```typescript
function applyInlineAllows(
  issues: LintIssue[],
  sourceLines: Map<string, string[]>, // file → lines
): { kept: LintIssue[]; suppressedCount: number; ai001Issues: LintIssue[] } {
  ...
}
```

---

## Adding a New Linter (future)

1. Create `runners/<linter>.ts` implementing `LinterRunner`
2. Add fixture output sample to `tests/fixtures/<linter>-output.*`
3. Write unit test covering output parsing
4. Import and add to the relevant language plugin in `languages/<lang>.ts`
5. Add generator to `generators/<linter>.ts` if it needs a managed config

No changes to CLI, pipelines, or steps required. Fully pluggable.

---

## dotnet-build note

.NET Roslyn analyzers run at build time, not as a standalone linter. The
`dotnet-build` runner invokes `dotnet build --no-restore` and parses the
MSBuild JSON log. This means `dotnet restore` must have run first — the step
validates this and skips gracefully if dependencies aren't restored.
