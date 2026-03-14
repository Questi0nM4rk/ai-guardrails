# Phase 3 — Rule Declarations

## Deliverables

Create `src/check/rules/commands.ts` and `src/check/rules/paths.ts`.
Create `src/check/ruleset.ts`.

This phase moves all policy out of hooks and into declarative rule arrays.

## `src/check/rules/commands.ts`

```typescript
import { callRule, pipeRule, recurseRule } from "@/check/builder-cmd";
import type { CommandRule } from "@/check/types";

const PIPE_SHELLS = ["bash", "sh", "dash", "zsh", "ksh", "csh", "tcsh", "fish"] as const;
const CURL_WGET = ["curl", "wget"] as const;

export const COMMAND_RULES: CommandRule[] = [
  // Recurse into inline scripts first
  recurseRule(),

  // Pipe-based remote code execution
  pipeRule([...CURL_WGET], [...PIPE_SHELLS], "curl/wget piped into a shell (remote code execution)"),

  // rm -rf
  callRule("rm", {
    flags: ["-r", "-f"],
    reason: "rm with -r and -f flags",
  }),
  callRule("rm", {
    flags: ["--recursive", "--force"],
    reason: "rm with --recursive and --force flags",
  }),

  // git push --force (but not --force-with-lease)
  callRule("git", {
    flags: ["--force"],
    noFlags: ["--force-with-lease"],
    reason: "git push --force",
  }),
  callRule("git", {
    flags: ["-f"],
    reason: "git push -f",
  }),

  // git reset --hard
  callRule("git", {
    flags: ["--hard"],
    reason: "git reset --hard",
  }),

  // git checkout/restore -- (discard changes)
  callRule("git", {
    hasDdash: true,
    reason: "git checkout/restore -- (discard working tree changes)",
  }),

  // git clean --force
  callRule("git", {
    flags: ["-f"],
    reason: "git clean -f",
  }),
  callRule("git", {
    flags: ["--force"],
    reason: "git clean --force",
  }),

  // git commit --no-verify
  callRule("git", {
    flags: ["--no-verify"],
    reason: "git commit --no-verify (bypasses hooks)",
  }),
  callRule("git", {
    flags: ["-n"],
    reason: "git commit -n (bypasses hooks)",
  }),

  // git branch -D (force delete)
  callRule("git", {
    flags: ["-D"],
    reason: "git branch -D (force delete)",
  }),

  // chmod -R 777
  callRule("chmod", {
    flags: ["-R"],
    reason: "chmod -R 777 (world-writable recursive)",
  }),
];

/**
 * Claude settings permissions.deny glob patterns — second line of defence.
 * These block at Claude tool-use layer before the hook even runs.
 */
export const DANGEROUS_DENY_GLOBS: string[] = [
  "Bash(git push --force)",
  "Bash(git push --force *)",
  "Bash(git push -f *)",
  "Bash(git reset --hard*)",
  "Bash(git checkout -- *)",
  "Bash(git restore -- *)",
  "Bash(git clean -f*)",
  "Bash(git clean --force*)",
  "Bash(git commit --no-verify*)",
  "Bash(git commit -n *)",
  "Bash(git branch -D *)",
  "Bash(rm -rf *)",
  "Bash(rm -fr *)",
  "Bash(sudo rm -rf*)",
  "Bash(sudo rm -fr*)",
  "Bash(chmod -R 777*)",
  "Bash(curl * | bash)",
  "Bash(curl * | sh)",
  "Bash(curl * | zsh)",
  "Bash(curl * | dash)",
  "Bash(curl * | ksh)",
  "Bash(wget * | bash)",
  "Bash(wget * | sh)",
  "Bash(wget * | zsh)",
  "Bash(wget * | dash)",
  "Bash(wget * | ksh)",
  "Bash(eval $(*))",
  "Bash(python -c*import os*system*)",
];
```

### Note on CallRule specificity

The `callRule` for `git` matches any `git` invocation with the given flags — the subcommand
check (`sub === "push"` etc.) is done inside `engine.ts` by checking `args[0]`. The builder
does not need a `sub` field because `git` flags are subcommand-scoped by the git CLI itself:
`--force` is only valid for `push`, `--hard` only for `reset`, etc. If a false positive
emerges, add a `sub` field to `CallRule` in a future phase.

## `src/check/rules/paths.ts`

```typescript
import { protectRead, protectWrite } from "@/check/builder-path";
import type { PathRule } from "@/check/types";

export const DEFAULT_MANAGED_FILES: string[] = [
  ".env",
  ".env.local",
  ".env.production",
  ".env.staging",
  ".env.development",
  "biome.jsonc",
  ".gitignore",
  ".eslintrc",
  ".eslintrc.js",
  ".eslintrc.json",
  ".prettier*",
  "tsconfig.json",
  "tsconfig.*.json",
  "package.json",
  "Cargo.toml",
  "pyproject.toml",
  "lefthook.yml",
  ".claude/settings.json",
  ".claude/settings.local.json",
];

export const DEFAULT_PATH_RULES: PathRule[] = [
  // Secrets
  protectWrite(/\.(env|env\.\w+)$/, "Writing to .env file (contains secrets)"),
  protectRead(/\.(env|env\.\w+)$/, "Reading .env file (contains secrets)"),

  // SSH / GPG
  protectRead(/\/\.ssh\//, "Reading SSH directory"),
  protectRead(/\/\.gnupg\//, "Reading GPG directory"),

  // Config files managed by this tool
  protectWrite(/biome\.jsonc?$/, "Writing to biome config (managed by ai-guardrails)"),
  protectWrite(/\.claude\/settings(\.local)?\.json$/, "Writing to Claude settings"),

  // CI
  protectWrite(/\.(github|gitlab)\/(workflows|ci)\//, "Writing to CI pipeline config"),

  // Package manifests
  protectWrite(/package\.json$/, "Writing to package.json"),
  protectWrite(/Cargo\.toml$/, "Writing to Cargo.toml"),
  protectWrite(/pyproject\.toml$/, "Writing to pyproject.toml"),
];
```

## `src/check/ruleset.ts`

```typescript
import type { HooksConfig, RuleSet } from "@/check/types";
import { COMMAND_RULES } from "@/check/rules/commands";
import { DEFAULT_PATH_RULES } from "@/check/rules/paths";
import { protectRead, protectWrite } from "@/check/builder-path";

export function buildRuleSet(config: HooksConfig): RuleSet {
  const extraPathRules = [
    ...(config.managedFiles ?? []).map((f) =>
      protectWrite(new RegExp(escapeRegExp(f) + "$"), `Writing to managed file: ${f}`)
    ),
    ...(config.managedPaths ?? []).map((p) =>
      protectWrite(new RegExp(escapeRegExp(p)), `Writing to managed path: ${p}`)
    ),
    ...(config.protectedReadPaths ?? []).map((p) =>
      protectRead(new RegExp(escapeRegExp(p)), `Reading protected path: ${p}`)
    ),
  ];

  return {
    commandRules: COMMAND_RULES,
    pathRules: [...DEFAULT_PATH_RULES, ...extraPathRules],
  };
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export async function loadHookConfig(): Promise<HooksConfig> {
  // Load from ai-guardrails config file (hooks section), return {} if not present
  // Actual implementation depends on config loader — placeholder for Phase 4
  return {};
}
```

## Tests

`tests/check/rules.test.ts`:

- `COMMAND_RULES` contains at least one `RecurseRule`
- `COMMAND_RULES` contains `CallRule` for `rm` with flags `["-r", "-f"]`
- `DEFAULT_PATH_RULES` has rule matching `.env` for `write`
- `DEFAULT_PATH_RULES` has rule matching `.ssh/` for `read`
- `buildRuleSet({})` returns default rules
- `buildRuleSet({ managedFiles: ["custom.lock"] })` adds protectWrite for `custom.lock`

## Acceptance Criteria

- [ ] `bun run typecheck` passes
- [ ] Rules tests pass
- [ ] `DANGEROUS_DENY_GLOBS` matches existing export in old `dangerous-patterns.ts` (for generator compatibility)
- [ ] No duplicate rule logic between `commands.ts` and `engine.ts`
