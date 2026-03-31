# SPEC-013: Version Pinning and Drift Detection

## Status: Draft
## Version: 1.0
## Last Updated: 2026-03-31
## Depends on: SPEC-002 (Config System), SPEC-004 (Commands), SPEC-009 (Interactive Init)

---

## Problem

When multiple developers work on the same project, each has their own version of
`ai-guardrails` installed. There is no mechanism to declare "this project requires
ai-guardrails >= X.Y.Z." Developer A on v3.0 and Developer B on v3.1 get different
linting behavior, different hook versions, and different generated configs — silently.

The `.ai-guardrails/` directory is gitignored by design (local config), so there's no
coordination between machines. CI may run yet another version. The result is
hard-to-debug inconsistencies where "it passes on my machine" is caused by version drift,
not code differences.

## Solution

Store the minimum required ai-guardrails version in the project's `config.toml` (tracked
in git). The `status` command reads this field and warns when the installed version is
older than the pinned version.

Chose `config.toml` over a standalone `.ai-guardrails-version` file because:
- Config already exists and is tracked — no new file to manage
- The version is a project-level concern alongside profile, ignores, and hooks config
- TOML parsing is already implemented via Zod schemas
- Fewer files in the project root

---

## Affected Components

| Component | File/Path | Change Type |
|-----------|-----------|-------------|
| Config schema | `src/config/schema.ts` | modify |
| Config loader | `src/config/loader.ts` | modify |
| Version utilities | `src/utils/version.ts` | new |
| Version pin init module | `src/init/modules/version-pin.ts` | new |
| Init registry | `src/init/registry.ts` | modify |
| Status command | `src/commands/status.ts` | modify |
| CLI flags | `src/cli.ts` | modify |
| Version util tests | `tests/utils/version.test.ts` | new |
| Version pin module tests | `tests/init/modules/version-pin.test.ts` | new |
| Status command tests | `tests/commands/status.test.ts` | modify |

---

## Acceptance Criteria

1. When `ai-guardrails init` runs, it writes `min_version = "X.Y.Z"` (the currently
   installed version) into `config.toml`.
2. When `ai-guardrails status` runs and the installed version is older than
   `min_version`, it prints a warning: "Version mismatch: project requires >=X.Y.Z,
   installed A.B.C".
3. When `ai-guardrails status` runs and the installed version meets or exceeds
   `min_version`, it prints: "Version: A.B.C (pinned: >=X.Y.Z)".
4. When `config.toml` has no `min_version` field, `status` prints:
   "Version: A.B.C (not pinned — run init to pin)".
5. When `--min-version <version>` is passed to `init`, that version is written instead
   of the installed version.
6. The `min_version` field validates as a semver string (X.Y.Z format).

---

## Config Schema Change

Add `min_version` to `ProjectConfigSchema` in `src/config/schema.ts`:

```typescript
const ProjectConfigSchema = z.object({
  profile: z.enum(["strict", "standard", "minimal"]).optional(),
  min_version: z.string().regex(/^\d+\.\d+\.\d+$/).optional(),
  config: ConfigValuesSchema.default({}),
  ignore: z.array(IgnoreEntrySchema).default([]),
  allow: z.array(AllowEntrySchema).default([]),
  hooks: HooksConfigSchema.optional(),
  ignore_paths: z.array(z.string()).default([]),
});
```

In `config.toml`:

```toml
profile = "standard"
min_version = "3.1.0"

[config]
indent_width = 2
```

---

## Version Utilities

New file `src/utils/version.ts`:

```typescript
/**
 * Compare two semver strings. Returns true if a < b.
 * Only handles X.Y.Z — no pre-release or build metadata.
 */
/**
 * Only handles strict X.Y.Z — no pre-release, no build metadata, no calver.
 * The Zod regex /^\d+\.\d+\.\d+$/ on config.toml enforces this at parse time.
 * Missing parts default to 0 via ?? 0, so "3.1" (if it somehow passes validation)
 * is treated as "3.1.0".
 *
 * We roll our own instead of importing `semver` npm package because:
 * - The comparison is 6 lines, not worth a dependency
 * - We explicitly reject pre-release (semver package would parse it)
 * - The Zod schema is the primary validator — this is just a comparator
 */
export function semverLt(a: string, b: string): boolean {
  const pa = a.split(".").map(Number);
  const pb = b.split(".").map(Number);
  for (let i = 0; i < 3; i++) {
    if ((pa[i] ?? 0) < (pb[i] ?? 0)) return true;
    if ((pa[i] ?? 0) > (pb[i] ?? 0)) return false;
  }
  return false;
}

/**
 * Get the installed ai-guardrails version from package.json.
 * Bun embeds this at compile time.
 */
export function getVersion(): string {
  // imported at module level from package.json
}
```

---

## Init Module

New `versionPinModule` in `src/init/modules/version-pin.ts`:

- **id**: `"version-pin"`
- **category**: `"profile"` (runs in the profile/config phase)
- **dependsOn**: `["profile-selection"]`
- **detect**: always returns `true`
- **execute**: reads the `--min-version` flag from context or falls back to
  `getVersion()`, writes the value into config.toml's `min_version` field

The module does NOT write config.toml directly — it sets `min_version` on the
`InitContext.configValues` so the config-tuning module handles the actual write.
This follows the existing pattern where modules contribute values and one module
writes the file.

### Idempotency rule: never downgrade the pin

When `init --force` is re-run, the module reads the existing `min_version` from
config.toml. If the existing pin is higher than the installed version, the module
preserves the existing pin and prints a warning:

```
Version pin preserved: project requires >=3.2.0 but installed 3.1.0.
Use --min-version to override.
```

Only `--min-version <version>` explicitly overrides the pin. This prevents
accidental downgrades when a developer on an older version re-runs init.

### SPEC-009 integration note

SPEC-009 §Module Registry does not list `version-pin` — it must be updated to
include this module after this spec is implemented. The module registers in
`src/init/registry.ts` with `dependsOn: ["profile-selection"]` and
`category: "profile"`.

---

## Status Command Integration

`src/commands/status.ts` — after loading project config:

```
const minVersion = resolvedConfig.values.min_version;  // from config.toml
const installed = getVersion();

if (minVersion && semverLt(installed, minVersion)) {
  console.warn(`Version mismatch: project requires >=${minVersion}, installed ${installed}`);
}
```

The warning is informational — `status` does not exit non-zero for version mismatch.
Teams wanting CI enforcement can add `ai-guardrails status --strict` in a future spec.

---

## Edge Cases

| Scenario | Expected Behavior | Priority |
|----------|-------------------|----------|
| No `min_version` in config.toml | `status` prints "(not pinned)" — no warning | high |
| Installed == pinned | Normal output, no warning | high |
| Installed > pinned | Normal output, no warning (newer is fine) | high |
| Installed < pinned | Warning printed to stderr | high |
| `--min-version 99.0.0` passed to init | Writes `99.0.0` even if installed is lower | medium |
| `init --force` with older version than pin | Preserves existing pin, prints warning | high |
| `init --force` with newer version than pin | Updates pin to installed version | high |
| Malformed `min_version` in config.toml | Zod validation error on config load | medium |
| Pre-release versions (e.g., `3.1.0-beta.1`) | Not supported — regex rejects, use X.Y.Z only | low |

---

## Cross-References

- SPEC-002 §ProjectConfig — defines the config.toml schema.
  **Note:** SPEC-002 must be updated to include `min_version` in `ProjectConfigSchema`
  after this spec is implemented.
- SPEC-004 §status — defines the status command
- SPEC-009 §Module Registry — where versionPinModule will be registered.
  **Note:** SPEC-009 must be updated to include `version-pin` in the module list
  after this spec is implemented.
- GitHub: #42 (feature request, labeled priority: high)
