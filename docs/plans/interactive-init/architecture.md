# Interactive Init — Modular Architecture

## Design Principle

Every init action is an **InitModule** — a self-contained unit that knows:
- What it does
- What it needs (dependencies)
- How to detect if it's applicable
- How to prompt the user
- How to execute

Modules compose like language plugins. Adding a new init feature = adding a file.

## Module Interface

```typescript
// src/init/types.ts

interface InitModule {
  /** Stable identifier: "ruff-config", "lefthook", "ci-github", etc. */
  readonly id: string;

  /** Human-readable name shown in prompts */
  readonly name: string;

  /** One-line description shown in prompts */
  readonly description: string;

  /** Category for grouping in the wizard */
  readonly category: InitCategory;

  /** Default state: on or off */
  readonly defaultEnabled: boolean;

  /** CLI flag that disables this module (e.g., "--no-hooks") */
  readonly disableFlag?: string;

  /** Other module IDs that must run before this one */
  readonly dependsOn?: readonly string[];

  /** Check if this module is applicable to the project */
  detect(ctx: InitContext): Promise<boolean>;

  /** Execute the module's action */
  execute(ctx: InitContext): Promise<InitModuleResult>;
}

type InitCategory =
  | "language-config"    // ruff.toml, biome.jsonc
  | "universal-config"   // .editorconfig, .markdownlint.jsonc, .codespellrc
  | "hooks"              // lefthook, claude-settings
  | "agent"              // agent-rules, tool-specific symlinks
  | "ci"                 // GitHub Actions, GitLab CI
  | "baseline"           // initial snapshot
  | "config";            // profile, tuning, ignore rules

interface InitModuleResult {
  status: "ok" | "skipped" | "error";
  message: string;
  filesCreated?: string[];
  filesModified?: string[];
}

interface InitContext {
  projectDir: string;
  fileManager: FileManager;
  commandRunner: CommandRunner;
  console: Console;
  config: ResolvedConfig;
  languages: LanguagePlugin[];
  selections: Map<string, boolean>;  // module ID → enabled
  isTTY: boolean;
  createReadline: () => ReadlineInterface;
}
```

## Module Registry

```typescript
// src/init/registry.ts

import type { InitModule } from "@/init/types";

// Language configs
import { ruffConfigModule } from "@/init/modules/ruff-config";
import { biomeConfigModule } from "@/init/modules/biome-config";

// Universal configs
import { editorconfigModule } from "@/init/modules/editorconfig";
import { markdownlintModule } from "@/init/modules/markdownlint";
import { codespellModule } from "@/init/modules/codespell";

// Hooks
import { lefthookModule } from "@/init/modules/lefthook";
import { claudeSettingsModule } from "@/init/modules/claude-settings";

// Agent
import { agentRulesModule } from "@/init/modules/agent-rules";

// CI
import { githubActionsModule } from "@/init/modules/github-actions";

// Baseline
import { baselineModule } from "@/init/modules/baseline";

export const ALL_INIT_MODULES: readonly InitModule[] = [
  // Language configs (detected)
  ruffConfigModule,
  biomeConfigModule,

  // Universal configs (always applicable)
  editorconfigModule,
  markdownlintModule,
  codespellModule,

  // Hooks
  lefthookModule,
  claudeSettingsModule,

  // Agent rules
  agentRulesModule,

  // CI
  githubActionsModule,

  // Baseline
  baselineModule,
];
```

## Module File Layout

```
src/init/
  types.ts                    # InitModule, InitContext, InitCategory
  registry.ts                 # ALL_INIT_MODULES
  wizard.ts                   # Interactive prompt flow
  runner.ts                   # Execute selected modules in dependency order
  modules/
    ruff-config.ts            # Python → ruff.toml
    biome-config.ts           # TypeScript → biome.jsonc
    editorconfig.ts           # Universal → .editorconfig
    markdownlint.ts           # Universal → .markdownlint.jsonc
    codespell.ts              # Universal → .codespellrc
    lefthook.ts               # Hooks → lefthook.yml + lefthook install
    claude-settings.ts        # Hooks → .claude/settings.json
    agent-rules.ts            # Agent → .ai-guardrails/agent-rules/
    github-actions.ts         # CI → .github/workflows/ai-guardrails.yml
    baseline.ts               # Baseline → .ai-guardrails/baseline.json
```

## Example Module

```typescript
// src/init/modules/ruff-config.ts

import type { InitModule } from "@/init/types";
import { ruffGenerator } from "@/generators/ruff";

export const ruffConfigModule: InitModule = {
  id: "ruff-config",
  name: "Ruff Config",
  description: "Generate ruff.toml for Python linting and formatting",
  category: "language-config",
  defaultEnabled: true,
  disableFlag: "--no-ruff",

  async detect(ctx) {
    return ctx.languages.some((l) => l.id === "python");
  },

  async execute(ctx) {
    const content = ruffGenerator.generate(ctx.config);
    const dest = `${ctx.projectDir}/${ruffGenerator.configFile}`;
    await ctx.fileManager.writeText(dest, content);
    return {
      status: "ok",
      message: `Generated ${ruffGenerator.configFile}`,
      filesCreated: [ruffGenerator.configFile],
    };
  },
};
```

## Wizard Flow

```typescript
// src/init/wizard.ts

async function runWizard(ctx: InitContext): Promise<Map<string, boolean>> {
  const selections = new Map<string, boolean>();

  // Group modules by category
  const groups = groupByCategory(ALL_INIT_MODULES);

  // For each category, show applicable modules and prompt
  for (const [category, modules] of groups) {
    const applicable = await filterApplicable(modules, ctx);
    if (applicable.length === 0) continue;

    ctx.console.info(`\n── ${categoryLabel(category)} ──`);

    for (const mod of applicable) {
      const enabled = await askYesNo(
        ctx.createReadline(),
        `${mod.name} — ${mod.description}`,
        mod.defaultEnabled
      );
      selections.set(mod.id, enabled);
    }
  }

  return selections;
}
```

## Runner (Dependency-Aware Execution)

```typescript
// src/init/runner.ts

async function executeModules(
  modules: readonly InitModule[],
  selections: Map<string, boolean>,
  ctx: InitContext
): Promise<InitModuleResult[]> {
  // Topological sort by dependsOn
  const sorted = topologicalSort(modules, selections);
  const results: InitModuleResult[] = [];

  for (const mod of sorted) {
    if (selections.get(mod.id) !== true) continue;

    ctx.console.step(`${mod.name}...`);
    const result = await mod.execute(ctx);

    if (result.status === "ok") {
      ctx.console.success(result.message);
    } else if (result.status === "error") {
      ctx.console.error(result.message);
    }

    results.push(result);
  }

  return results;
}
```

## How It Replaces the Current Pipeline

### Current flow (monolithic)
```
init.ts → detect → prompt profile → prompt ignore → write config
        → install.ts → detect → load config → generate ALL configs
                     → validate → setup hooks → setup CI → agent rules
```

### New flow (modular)
```
init.ts → detect languages
        → detect applicable modules
        → if TTY: run wizard (per-module y/n)
        → if --yes: all defaults
        → write config.toml (always)
        → execute selected modules in dependency order
```

### Migration path (no breaking changes)

1. Keep existing generators in `src/generators/` — modules call them
2. Keep existing steps in `src/steps/` — modules call them
3. New `src/init/` directory wraps existing functionality
4. `--yes` flag produces identical output to current behavior
5. Old `--no-hooks`, `--no-ci`, `--no-agent-rules` map to module selections

## Adding a New Feature

To add a new init feature (e.g., "Prettier config"):

1. Create `src/init/modules/prettier.ts`:
   ```typescript
   export const prettierModule: InitModule = {
     id: "prettier",
     name: "Prettier",
     description: "Generate .prettierrc for code formatting",
     category: "language-config",
     defaultEnabled: true,
     async detect(ctx) { return ctx.languages.some(l => l.id === "typescript"); },
     async execute(ctx) { /* write .prettierrc */ },
   };
   ```

2. Register in `src/init/registry.ts`:
   ```typescript
   import { prettierModule } from "@/init/modules/prettier";
   // Add to ALL_INIT_MODULES
   ```

3. Done. The wizard automatically shows it, the runner automatically executes it.

## Category Display Order

```
1. language-config  → "Language Configs"      (detected per-project)
2. universal-config → "Universal Configs"     (always applicable)
3. hooks            → "Hooks"                 (pre-commit + AI agent)
4. agent            → "AI Agent Rules"        (tool-specific)
5. ci               → "CI Pipeline"           (GitHub Actions, etc.)
6. baseline         → "Baseline"              (initial snapshot)
7. config           → "Config Tuning"         (line length, indent, ignores)
```

## Future Modules (just add a file)

- `gitlab-ci.ts` — GitLab CI pipeline
- `bitbucket-pipelines.ts` — Bitbucket Pipelines
- `prettier.ts` — Prettier config (if we add it)
- `tsconfig.ts` — TypeScript strictness profiles
- `branch-protection.ts` — GitHub branch protection setup
- `husky.ts` — Alternative to lefthook
- `docker.ts` — Dockerfile lint config
- `terraform.ts` — tflint config
