# SPEC-002: Config System

## Status: Draft
## Version: 3.1
## Last Updated: 2026-03-20

---

## Problem

A linting tool must work for many projects with different rules, different line
lengths, different permitted suppressions. If all configuration lives in one
place, a single project cannot override global preferences. If each project owns
all configuration, a developer's personal defaults (e.g. preferred profile) have
nowhere to live. If inline config can silently alter global settings, AI agents
can weaken enforcement without visibility.

Configuration also requires validation — an invalid `line_length: "wide"` should
fail loudly at load time, not produce cryptic linter errors at run time.

---

## Solution

Three-tier hierarchical config with Zod validation at load time and a
`ResolvedConfig` view that merges all tiers for domain code.

| Tier | Location | Format | Owner |
|------|----------|--------|-------|
| Machine | `~/.config/ai-guardrails/config.toml` | TOML | Developer |
| Project | `<project>/.ai-guardrails/config.toml` | TOML | Repository |
| Inline | `ai-guardrails-allow: ...` comments | Source | Justified exception |

`loadMachineConfig` and `loadProjectConfig` each return a typed domain object.
`resolveConfig` merges them into a single `ResolvedConfig`. Domain code only
ever sees `ResolvedConfig` — it never reads raw TOML.

---

## Philosophy

1. **Validate at load time, never at use time.** TOML is parsed and Zod-validated
   when the config is loaded. WHY: failures at the boundary surface a clear error
   message ("line_length must be between 60 and 200") before any linter runs.
   Validating late produces confusing errors far from the source.

2. **Machine config sets defaults; project config overrides.** Profile is resolved
   as `project.profile ?? machine.profile`. WHY: a developer's personal preference
   for `strict` applies to all their projects unless a specific project says
   otherwise. This prevents silent drift where new projects inherit nothing.

3. **Ignore rules merge; project never silently drops machine rules.** Machine and
   project ignores are merged and deduplicated by rule. WHY: an agent modifying the
   project config cannot remove a machine-level ignore — it can only add to it.
   Merge-not-replace is the safe default.

4. **Allow entries are project-only.** Path-scoped rule allowances (`glob` +
   `rule`) live only in the project config. WHY: machine-level allows would create
   a hidden global exception mechanism that cannot be audited per-repository.

5. **Missing config file is always valid.** `readTomlSafe` returns `{}` when the
   file does not exist, which Zod parses to all defaults. WHY: forcing every
   project to have a config file creates friction for adoption. Optional config
   with strong defaults lowers the entry cost.

6. **`passthrough()` on `ConfigValuesSchema`.** Known keys are validated strictly;
   unknown keys pass through to `values`. WHY: tool-specific flags can be stored
   in `[config]` without requiring schema updates for each new key.

---

## Constraints

### Hard Constraints

- No inline config merging in domain code — `ResolvedConfig` is always fully resolved before use
- `profile` field: exactly one of `"strict"`, `"standard"`, `"minimal"`
- `line_length` range: 60–200 (inclusive)
- `indent_width`: exactly 2 or 4
- `IgnoreEntry.rule` format: `linter/RULE_CODE` (regex `^[\w-]+\/[\w\-.]+$`)
- `IgnoreEntry.reason`: non-empty string (required, enforced by Zod)
- `AllowEntry.glob`: non-empty string
- Parse errors from malformed TOML propagate to caller — never silently swallowed

### Soft Constraints

- `smol-toml` for TOML parsing (Bun built-in has no `stringify`)
- Project config path fixed at `.ai-guardrails/config.toml` — not configurable
- Machine config path fixed at `~/.config/ai-guardrails/config.toml`

### Assumptions

| Assumption | If Wrong | Action |
|------------|----------|--------|
| TOML is sufficient for config format | Team prefers JSON/YAML | Add loader variants; `resolveConfig` interface remains unchanged |
| Three tiers (machine, project, inline) are sufficient | Organization-level config needed | Add org tier between machine and project; update `resolveConfig` merge order |
| `passthrough()` covers future tool flags | Unknown field with Zod refinement needed | Add explicit field to `ConfigValuesSchema`, bump version |
| `profile` enum covers all enforcement levels | New level needed (e.g. "pedantic") | Extend `Profile` type, add to Zod enum, update profile-to-rule mapping |

---

## Schema Definitions

### `MachineConfigSchema` (`src/config/schema.ts`)

```typescript
const MachineConfigSchema = z.object({
  profile: z.enum(["strict", "standard", "minimal"]).default("standard"),
  ignore: z.array(IgnoreEntrySchema).default([]),
});

export type MachineConfig = z.infer<typeof MachineConfigSchema>;
```

Defaults: `profile = "standard"`, `ignore = []`.

### `ProjectConfigSchema` (`src/config/schema.ts`)

```typescript
const ProjectConfigSchema = z.object({
  profile: z.enum(["strict", "standard", "minimal"]).optional(),
  config: ConfigValuesSchema.default({}),
  ignore: z.array(IgnoreEntrySchema).default([]),
  allow: z.array(AllowEntrySchema).default([]),
  hooks: HooksConfigSchema.optional(),
  ignore_paths: z.array(z.string()).default([]),
});

export type ProjectConfig = z.infer<typeof ProjectConfigSchema>;
```

`profile` is optional — when absent, machine profile applies. `hooks` is
optional — when absent, hook behaviour uses hardcoded defaults.

### Sub-schemas

```typescript
const IgnoreEntrySchema = z.object({
  rule: z.string().regex(/^[\w-]+\/[\w\-.]+$/, "Format: linter/RULE_CODE"),
  reason: z.string().min(1, "Reason is required"),
});

const AllowEntrySchema = z.object({
  rule: z.string().regex(/^[\w-]+\/[\w\-.]+$/),
  glob: z.string().min(1),
  reason: z.string().min(1),
});

const ConfigValuesSchema = z
  .object({
    line_length: z.number().int().min(60).max(200).default(88),
    indent_width: z
      .number()
      .int()
      .refine((v) => v === 2 || v === 4, { message: "indent_width must be 2 or 4" })
      .default(2),
    python_version: z.string().regex(/^\d+\.\d+$/).optional(),
  })
  .passthrough();

const HooksConfigSchema = z.object({
  managed_files: z.array(z.string()).optional(),
  managed_paths: z.array(z.string()).optional(),
  protected_read_paths: z.array(z.string()).optional(),
  disabled_groups: z.array(z.string()).optional(),
});

export type HooksSchemaConfig = z.infer<typeof HooksConfigSchema>;
```

---

## `ResolvedConfig` Interface

```typescript
export interface ResolvedConfig {
  profile: "strict" | "standard" | "minimal";
  ignore: ReadonlyArray<{ rule: string; reason: string }>;
  allow: ReadonlyArray<{ rule: string; glob: string; reason: string }>;
  values: {
    line_length: number;
    indent_width: number;
    python_version?: string;
    [key: string]: unknown;    // passthrough fields from ConfigValuesSchema
  };
  hooks?: HooksSchemaConfig;
  ignoredRules: ReadonlySet<string>;
  ignorePaths: readonly string[];
  noConsoleLevel: NoConsoleLevel;
  isAllowed(rule: string, filePath: string): boolean;
}
```

`ignoredRules` is a `Set` precomputed from the merged ignore list for O(1)
lookup. `isAllowed(rule, filePath)` checks `ignoredRules` first, then applies
`allow` entries using `minimatch` on the file path. `noConsoleLevel` is
derived from `package.json` content — not stored in TOML.

---

## Hierarchy and Merge Rules

`buildResolvedConfig(machine, project)` (`src/config/schema.ts`):

1. **Profile:** `project.profile ?? machine.profile`
2. **Ignore:** machine ignores iterated first, then project ignores. A `Map<rule, reason>` deduplicates — project reason wins if both set the same rule. Final ignore list is `Array.from(map.entries())`.
3. **Allow:** project entries only — machine config has no `allow` field.
4. **Values:** `ConfigValuesSchema.default({})` ensures `line_length` and `indent_width` always have values; `python_version` is spread conditionally (`python_version !== undefined && { python_version }`).
5. **Hooks:** spread from `project.hooks` only if defined (`project.hooks !== undefined && { hooks: project.hooks }`).
6. **ignorePaths:** taken directly from `project.ignore_paths`.
7. **noConsoleLevel:** hardcoded `"warn"` in `buildResolvedConfig`; detection from `package.json` is handled by the calling step.

---

## Profiles

| Profile | Intended Use |
|---------|-------------|
| `strict` | Pedantic enforcement — all rules, no exceptions |
| `standard` | Default — recommended rules, reasonable exceptions allowed |
| `minimal` | Brownfield — only the most critical rules enforced |

Profile is the primary axis of rule selection: it determines which rules are
enabled in every generated linter config. The config system resolves the active
profile via `project.profile ?? machine.profile` and passes it through
`ResolvedConfig.profile` to every generator.

### Profile Rule Filtering

Each generator implements profile-aware rule selection. The mapping is
generator-specific but follows a consistent three-tier contract:

| Profile | Rule Selection |
|---------|----------------|
| `strict` | All rules enabled — every check the tool can perform |
| `standard` | Recommended ruleset — rules enabled by the tool's own defaults, minus known false-positive-prone rules |
| `minimal` | Critical-only — security, correctness, and crash-causing rules; no style |

Generators receive `config.profile` and branch on it:

```typescript
// Example: ruff generator
function selectRules(profile: "strict" | "standard" | "minimal"): string[] {
  if (profile === "strict")   return ALL_RUFF_RULES;
  if (profile === "standard") return STANDARD_RUFF_RULES;
  return MINIMAL_RUFF_RULES;   // "minimal"
}
```

The `ignore` entries in `ResolvedConfig` provide a second filtering layer: they
suppress specific rules regardless of profile. Profile controls breadth; ignore
entries control per-rule exceptions.

### Per-Generator Profile Behavior

| Generator | strict | standard | minimal |
|-----------|--------|----------|---------|
| `ruff` | All rule groups (`E`, `F`, `W`, `C`, `N`, `D`, `S`, `UP`, …) | `E`, `F`, `W`, `I`, `UP`, `S` | `E`, `F`, `S` (errors + security) |
| `biome` | All rules, severity `error` | All recommended, severity `error` | Recommended correctness only, others `off` |
| `pyright` | `strict` mode (`--strict`) | `basic` mode | `off` for non-error diagnostics |
| `golangci-lint` | All linters enabled | Default linters | `errcheck`, `staticcheck` only |
| `selene` | All lints | Default lints | `error`-severity lints only |
| `clang-tidy` | All enabled checks | Core + bugprone | `clang-diagnostic-*` only |
| Universal configs | Unchanged across profiles — universal rules have no tiers |

Generators that do not yet implement profile-branching default to `standard`
behavior for all profiles until updated. This is documented in each generator's
source file.

---

## Config Values

| Key | Type | Default | Constraint |
|-----|------|---------|-----------|
| `line_length` | `number` | `88` | 60–200 inclusive |
| `indent_width` | `number` | `2` | exactly 2 or 4 |
| `python_version` | `string` | (absent) | `^\d+\.\d+$` |

Additional passthrough keys are stored in `values` as `[key: string]: unknown`.
Generators that use passthrough keys must narrow with type guards before use.

---

## Path Constants (`src/models/paths.ts`)

```typescript
export const BASELINE_PATH    = ".ai-guardrails/baseline.json";
export const AUDIT_PATH       = ".ai-guardrails/audit.jsonl";
export const PROJECT_CONFIG_PATH = ".ai-guardrails/config.toml";
```

These constants are shared across all steps that read or write these files.
They are always relative to the project root.

---

## Loader Functions (`src/config/loader.ts`)

```typescript
export async function loadMachineConfig(path: string, fm: FileManager): Promise<MachineConfig>
export async function loadProjectConfig(projectDir: string, fm: FileManager): Promise<ProjectConfig>
export function resolveConfig(machine: MachineConfig, project: ProjectConfig): ResolvedConfig
```

`loadMachineConfig` accepts a `path` argument — the caller supplies the machine
config location (typically `~/.config/ai-guardrails/config.toml`). This allows
test isolation with a fake path.

`loadProjectConfig` always reads from `<projectDir>/.ai-guardrails/config.toml`.
The path is not configurable.

Both loaders call `readTomlSafe`, which returns `{}` on `ENOENT`, causing Zod to
apply all defaults. Parse errors (malformed TOML) propagate up as exceptions.

---

## Testing Strategy

**Framework:** `bun:test`.

**Fakes:** `FakeFileManager` seeded with TOML content strings for
config-loading tests. No real filesystem access in unit tests.

**Coverage targets:**
- `schema.ts`: `buildResolvedConfig` — merge ordering, deduplication, conditional hooks spread
- `loader.ts`: missing file returns defaults, malformed TOML propagates, valid TOML produces correct types
- `isAllowed()`: rule in ignoredRules returns true, glob match returns true, no-match returns false

**Pattern:** `test_<function>_<scenario>_<expected>`.

---

## Evolution

| Stable While | Revisit If | Impact |
|-------------|------------|--------|
| Three-tier config hierarchy | Org-level tier needed | Add org loader, update merge order in `buildResolvedConfig` |
| `ConfigValuesSchema` with passthrough | Strict enumeration of all keys needed | Remove `passthrough()`, enumerate keys explicitly |
| Machine config at fixed path | Per-project machine config override needed | Add `--machine-config` flag, update `PipelineContext` |
| TOML format for both tiers | JSON or YAML format requested | Add format-specific loaders behind common interface |
| `noConsoleLevel` hardcoded `"warn"` | Browser/CLI detection needed per-project | Wire `detectNoConsoleLevel` into `buildResolvedConfig` |

---

## Cross-References

- SPEC-000: Overview — whitelist model philosophy, technology stack (smol-toml, Zod)
- SPEC-001: Architecture — `ResolvedConfig` in `PipelineContext`, Zod-at-boundaries pattern
- SPEC-003: Linter System — `ResolvedConfig` consumed by `RunOptions`, `isAllowed()` usage
- SPEC-006: Config Generators — `ResolvedConfig.values` consumed by generators
