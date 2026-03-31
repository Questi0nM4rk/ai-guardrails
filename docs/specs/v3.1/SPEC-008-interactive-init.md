# SPEC-008: Interactive Init

## Status: Draft — NOT YET IMPLEMENTED
## Version: 3.2
## Last Updated: 2026-03-31
## Depends on: SPEC-000 (Overview), SPEC-001 (Architecture), SPEC-002 (Config), SPEC-004 (CLI Commands), SPEC-006 (Config Generators)

> **This spec describes a planned feature. No code in `src/init/` exists yet.**
> The current `src/pipelines/init.ts` is the monolithic implementation this
> spec replaces. See the Migration Path section for backward-compat guarantees.

---

## Problem

`ai-guardrails init` is monolithic. It runs everything or nothing. The only
customization available today is profile selection and ignore rules. Users
cannot selectively configure which generators run, which universal configs
are installed, or skip components they don't need.

Specifically:

- A TypeScript-only project does not want `ruff.toml` generated (Python config)
- A project already using Prettier does not want `.editorconfig` overwriting its settings
- A team not using Claude Code does not want `.claude/settings.json` created
- A project using GitLab CI, not GitHub Actions, gets a GitHub workflow it will never use
- There is no way to capture an initial baseline as part of init
- No branch protection rules are created on GitHub — PRs can be merged without CI passing
- No code review bot (CodeRabbit / CC-Reviewer) is configured — AI reviews are opt-in by hand
- No on-save linting — feedback only arrives at commit time, not during editing
- Missing tools are reported but never installed — requires manual follow-up

Adding a new init feature today means modifying `init.ts` or `install.ts`
directly — monolithic files that are hard to test in isolation. Feature flags
accumulate as boolean guards inside a single execution path.

---

## Solution

Replace the monolithic init/install pipeline with a modular system where every
action is an **InitModule**. Each module is self-contained: it declares its
category, whether it's applicable to the project, its default state, and how
to execute. The interactive wizard iterates over applicable modules grouped
by category and prompts for each one. Non-interactive mode (`--yes`) accepts
all defaults without prompting.

The module system is additive. Adding a new init feature means adding one file
in `src/init/modules/` and one line in the registry. No other files change.

---

## Philosophy

1. **One concern per module.** Each `InitModule` does exactly one thing. It
   generates one config file, installs one hook system, or sets up one CI provider.
   WHY: Monolithic functions fail partially and leave the project in an undefined
   state. A module-per-concern makes partial failure recoverable — the failed
   module is reported, others succeed.

2. **Detect before prompt.** Modules that are not applicable to the project are
   never shown in the wizard. The wizard does not ask about Python configs in a
   TypeScript project.
   WHY: Irrelevant prompts erode trust in the wizard. If users see options they
   don't understand, they will skip the wizard entirely and use `--yes`. The
   wizard should only surface decisions that matter for this project.

3. **Defaults that are always right.** Every module has `defaultEnabled: true`
   or `false`. The defaults are chosen so that `--yes` (accept all defaults)
   produces a sensible, complete setup for any project type.
   WHY: Most users will hit Enter for most prompts. Defaults represent the
   "recommended by the tool" choice. Defaults that require manual correction
   are UX failures.

4. **Topology enforced, not documented.** Module dependencies are declared in
   `dependsOn` and enforced by topological sort in the runner. A module cannot
   execute before its dependencies.
   WHY: If dependency order is only documented, it will be violated by future
   modules. The runner enforces the order structurally — declaring a dependency
   is sufficient, no human needs to remember the execution order.

5. **`--yes` means full setup, always.** `--yes` runs all applicable modules —
   original 13 and v3.2 additions. If a module is not applicable (editor not
   detected, GitHub not authenticated), it is skipped automatically.
   WHY: A `--yes` flag that does less than what the wizard offers is a trap.
   Users who run `--yes` in CI or automation expect the complete recommended
   setup, not a frozen subset from a previous version.

6. **Under 30 seconds, end to end.** The interactive wizard — from launch to
   "Done!" — must complete within 30 seconds of user input on a standard laptop
   with a warm network. Each module runs only what it needs; the baseline
   module is the only step that touches the network (prerequisite installs).
   Non-interactive mode (`--yes`) must complete in under 10 seconds.
   WHY: A setup wizard that takes minutes gets abandoned halfway through. Speed
   is a UX requirement, not a nice-to-have.

7. **Per-file conflict detection before overwrite.** Before any module writes a
   file, it checks whether that file already exists. If it does, the module
   prompts once per file: `"biome.jsonc exists. Merge? [Y/n]"`. The default
   (`Y`) merges the guardrails config into the existing file without losing
   user customization. The user can also choose `n` (skip this file) or is
   offered `r` (replace entirely) only if `--force` is active.
   WHY: Silently overwriting user config is the fastest way to lose trust.
   Per-file prompts give users control over each generated file individually,
   without requiring them to know the `--config-strategy` flag in advance.

8. **Existing generators and steps are not replaced.** Modules wrap them. The
   `src/generators/` and `src/steps/` directories are stable. Only the
   orchestration layer changes.
   WHY: Generators are well-tested, battle-tested, and snapshot-tested. Rewriting
   them to fit a new architecture is unnecessary risk. The module interface is
   an orchestration boundary, not a reimplementation boundary.

9. **Network-requiring modules are optional and last.** Modules that call GitHub
   API or install packages are in categories `github` and `tools`, appear after
   all local config modules, and default to `true` only when the required
   credentials/context are detected (e.g., `GH_TOKEN` present, `gh` CLI authenticated).
   WHY: Init should succeed offline for the local config path. Network failures
   in optional modules should not abort the entire wizard.

10. **On-save feedback is editor-agnostic.** The on-save module generates
    config files consumed by editors (`.vscode/settings.json`, `.helix/languages.toml`)
    but does not mandate an editor. Each editor config is its own sub-section,
    prompted separately.
    WHY: Mandating VS Code in a tool used across neovim/Helix/Zed/VS Code teams
    causes immediate rejection. Generate what's applicable, skip the rest.

---

## Constraints

### Hard Constraints

- No new `src/init/` code exists until implementation starts — this spec is design only
- Each `--no-X` flag disables exactly one module
- Modules may not import from other modules (only from generators and steps)
- Module `id` values are stable after shipping — they are CLI-facing identifiers
- `dependsOn` references must be resolvable in `ALL_INIT_MODULES` at startup
- The runner uses topological sort — circular `dependsOn` chains are a startup error
- Total interactive wizard time must not exceed 30 seconds (excluding user think time)
- Non-interactive (`--yes`) must complete in under 10 seconds
- Every module that writes a file must check for existence and prompt before overwrite
  (format: `"<filename> exists. Merge? [Y/n]"`, default Y = merge)
- GitHub modules must gracefully degrade if `gh` CLI is not authenticated
- On-save modules must not install editor extensions — only generate config files

### Soft Constraints

- Prefer readline-based prompts over third-party prompt libraries
- Module `execute()` returns `InitModuleResult`, never throws
- Wizard groups modules by category in the display order defined in this spec
- Each module file stays under 200 lines
- Conflict resolution prompt uses three options: Merge (Y), Skip (n), Replace (r, only with --force)
- New modules added in v3.2 have `defaultEnabled: true` when applicable (detect() returns true)
  and `defaultEnabled: false` only when the module is explicitly opt-in by nature (e.g., `nvim-on-save`)

### Assumptions

| Assumption | If Wrong | Action |
|------------|----------|--------|
| Node readline is sufficient for wizard prompts | Windows terminal incompatibility | Evaluate `enquirer` or `@inquirer/prompts` as readline wrapper |
| 20 modules covers all init scenarios for v3.2 | New init feature does not fit any module | Add a new module file and category if needed, update this spec |
| Topological sort is sufficient for dependency management | Circular dependencies introduced by future module | Detect cycle at startup, fail with clear error listing the cycle |
| `--yes` flag is the right backward-compat path | Some CI pipelines use flags incompatible with `--yes` | Audit all known usages, add alias if needed |
| Generators stay stable during implementation | Generator signature changes | Update module wrappers, not the generators themselves |
| `gh` CLI is the GitHub API surface | Team uses GitLab/Bitbucket | GitHub modules detect `origin` remote URL; skip if not github.com |
| On-save config files are per-editor | Editor stores config elsewhere | Module detects editor markers before writing |

---

## 1. InitModule Interface

```typescript
// src/init/types.ts

interface InitModule {
  /** Stable identifier used for selections and CLI flags. Never change after shipping. */
  readonly id: string;

  /** Human-readable name shown in wizard prompts */
  readonly name: string;

  /** One-line description shown in prompts */
  readonly description: string;

  /** Category for grouping in the wizard */
  readonly category: InitCategory;

  /** Default state when user hits Enter (or --yes) */
  readonly defaultEnabled: boolean;

  /** CLI flag that disables this module (e.g., "--no-hooks") */
  readonly disableFlag?: string;

  /** Other module IDs that must execute before this one */
  readonly dependsOn?: readonly string[];

  /** Check if this module is applicable to the project */
  detect(ctx: InitContext): Promise<boolean>;

  /** Execute the module's action */
  execute(ctx: InitContext): Promise<InitModuleResult>;
}

type InitCategory =
  | "profile"           // profile selection, config tuning
  | "language-config"   // ruff.toml, biome.jsonc
  | "universal-config"  // .editorconfig, .markdownlint.jsonc, .codespellrc
  | "hooks"             // lefthook, claude-settings
  | "agent"             // agent-rules, tool-specific symlinks
  | "ci"                // GitHub Actions, CI workflows
  | "github"            // branch protection, reviewer bots, PR settings
  | "editor"            // on-save linting, LSP config, editor integration
  | "tools"             // per-tool installation prompts
  | "baseline";         // initial snapshot

interface InitModuleResult {
  status: "ok" | "skipped" | "error";
  message: string;
  filesCreated?: readonly string[];
  filesModified?: readonly string[];
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
  flags: Record<string, unknown>;
  /** GitHub repo info, populated by detect() of github modules. Null if not github.com. */
  github?: { owner: string; repo: string; authenticated: boolean };
}
```

---

## 2. Module Registry

All modules are registered in a flat array. Order within the array determines
display order within a category.

```typescript
// src/init/registry.ts

export const ALL_INIT_MODULES: readonly InitModule[] = [
  // Original 13 modules (v3.1)
  profileSelectionModule,    // profile
  configTuningModule,        // profile
  ruffConfigModule,          // language-config
  biomeConfigModule,         // language-config
  editorconfigModule,        // universal-config
  markdownlintConfigModule,  // universal-config
  codespellConfigModule,     // universal-config
  lefthookModule,            // hooks
  claudeSettingsModule,      // hooks
  agentRulesModule,          // agent
  githubActionsModule,       // ci
  toolInstallModule,         // tools
  baselineModule,            // baseline

  // New modules (v3.2)
  githubBranchProtectionModule,  // github
  githubCcReviewerModule,        // github
  githubPrTemplateModule,        // github
  vscodeOnSaveModule,            // editor
  helixOnSaveModule,             // editor
  nvimOnSaveModule,              // editor
  zedOnSaveModule,               // editor
];
```

---

## 3. Module Specifications

### Original 13 Modules (v3.1 — unchanged)

| Module ID | Category | detect() | defaultEnabled | disableFlag | dependsOn |
|-----------|----------|----------|----------------|-------------|-----------|
| `profile-selection` | `profile` | always true | true | — | none |
| `config-tuning` | `profile` | always true | true | — | `profile-selection` |
| `ruff-config` | `language-config` | Python detected | true | `--no-ruff` | `config-tuning` |
| `biome-config` | `language-config` | TypeScript detected | true | `--no-biome` | `config-tuning` |
| `editorconfig` | `universal-config` | always true | true | `--no-editorconfig` | `config-tuning` |
| `markdownlint-config` | `universal-config` | always true | true | `--no-markdownlint` | `config-tuning` |
| `codespell-config` | `universal-config` | always true | true | `--no-codespell` | `config-tuning` |
| `lefthook` | `hooks` | always true | true | `--no-hooks` | `config-tuning` |
| `claude-settings` | `hooks` | always true | true | `--no-agent-hooks` | `config-tuning` |
| `agent-rules` | `agent` | any AI tool detected | true | `--no-agent-rules` | none |
| `github-actions` | `ci` | `.git` exists | true | `--no-ci` | none |
| `tool-install` | `tools` | any runner missing | true | — | `profile-selection` |
| `baseline` | `baseline` | always true | true | `--no-baseline` | all config + `tool-install` |

---

### New Module: `github-branch-protection`

| Field | Value |
|-------|-------|
| id | `github-branch-protection` |
| category | `github` |
| detect | `.git/` exists AND `gh auth status` succeeds AND remote is `github.com` |
| defaultEnabled | true |
| disableFlag | `--no-branch-protection` |
| dependsOn | `github-actions` |

**Problem it solves:** Without branch protection, the `no-commits-to-main` lefthook
is the only guard — and it only fires locally. A developer on a different machine,
or using `git push` with a GUI client, can still push directly to `main` and merge
without CI passing.

**Prompts:**
- Y/N: Set up branch protection on `main`? Shows what will be configured.
- Y/N: Require PRs before merging? [Y/n]
- Y/N: Require CI status checks to pass? [Y/n] (only if `github-actions` was enabled)
- Y/N: Require at least 1 approving review? [Y/n]
- Y/N: Dismiss stale reviews on new push? [Y/n]
- Y/N: Prevent force pushes? [Y/n]

**Execute:**

Step 1 — collect required status check names by parsing all workflow files under
`.github/workflows/`. For each file, extract every `jobs.<id>.name` value (the
human-readable job name used by GitHub status checks). If no `name:` is set,
fall back to the job key. This produces the exact strings GitHub registers as
status checks (e.g. `"Test & Coverage"`, `"Lint & Static Analysis"`, `"check"`).

Step 2 — apply protection:
```
gh api repos/{owner}/{repo}/branches/main/protection \
  --method PUT \
  --field required_status_checks[strict]=true \
  --field required_status_checks[contexts][]=<job-name-1> \
  --field required_status_checks[contexts][]=<job-name-2> \
  --field enforce_admins=false \
  --field required_pull_request_reviews[required_approving_review_count]=1 \
  --field required_pull_request_reviews[dismiss_stale_reviews]=true \
  --field restrictions=null \
  --field allow_force_pushes=false \
  --field allow_deletions=false \
  --field required_conversation_resolution=true
```

`required_conversation_resolution=true` ensures all PR review comments must be
resolved before merge — matching the ai-guardrails repo's own protection config.

**Error handling:**
- If `gh` is not authenticated: prints hint `gh auth login`, marks module as skipped (not error)
- If repo is private and no billing: prints note about free-tier branch protection limits
- If `main` branch does not exist yet: skips with message "branch protection will be applied on first push to main"

**Files created/modified:** None (GitHub API only, no local files)

---

### New Module: `github-cc-reviewer`

| Field | Value |
|-------|-------|
| id | `github-cc-reviewer` |
| category | `github` |
| detect | `.git/` exists AND `gh auth status` succeeds AND remote is `github.com` |
| defaultEnabled | true |
| disableFlag | `--no-reviewer` |
| dependsOn | `github-branch-protection` |

**Problem it solves:** Without an automated code reviewer, PRs get merged without
any review of logic, style, or security issues. CodeRabbit (the "CC reviewer"
or `coderabbit[bot]`) provides free AI-powered PR reviews. Without this module,
setup requires navigating `coderabbit.ai`, creating an account, and manually
adding the bot — friction that causes most users to skip it.

**What is CC-Reviewer:**
CodeRabbit is a GitHub App that comments on PRs with a line-by-line review summary,
issues, and suggestions. It is free for open source repositories. The bot is
enabled by either: (a) installing the GitHub App from the marketplace, or
(b) adding a `.coderabbit.yaml` config file to the repo (triggers auto-installation
on first PR).

**Prompts:**
- Y/N: Add CodeRabbit AI reviewer to PRs? Shows what it does. [Y/n]
- Choice: Review profile [auto/chill/assertive] (default: auto)
- Y/N: Block PR merge until CodeRabbit review passes? [y/N] (default: false, requires Pro plan)

**Execute (path A — YAML config only, no GitHub App install required):**
- Writes `.coderabbit.yaml` to project root:

```yaml
# ai-guardrails managed — CodeRabbit AI reviewer config
language: "en-US"
tone_instructions: ""
early_access: false
enable_free_tier: true
reviews:
  profile: "auto"           # auto | chill | assertive
  request_changes_workflow: false
  high_level_summary: true
  poem: false
  review_status: true
  collapse_walkthrough: false
  auto_review:
    enabled: true
    drafts: false
    base_branches: ["main"]
chat:
  auto_reply: true
```

**Files created:** `.coderabbit.yaml`

**Notes:**
- `.coderabbit.yaml` presence triggers CodeRabbit auto-install on first PR open (no manual GitHub App install needed for public repos)
- The `block_merge` option (if selected Y) adds `coderabbit` to required status checks in branch protection — requires `github-branch-protection` module to have run first

---

### New Module: `github-pr-template`

| Field | Value |
|-------|-------|
| id | `github-pr-template` |
| category | `github` |
| detect | `.git/` exists AND remote is `github.com` |
| defaultEnabled | true |
| disableFlag | `--no-pr-template` |
| dependsOn | none |

**Problem it solves:** Without a PR template, developers open PRs with empty
descriptions. CodeRabbit and other review bots perform better when context is
provided. A standard template enforces: summary, test plan, and checklist.

**Prompts:**
- Y/N: Add PR description template? [Y/n]

**Execute:**
- Creates `.github/pull_request_template.md`:

```markdown
## Summary

<!-- 1-3 bullet points describing what changed and why -->

## Test plan

<!-- Checklist of steps to verify the change works -->
- [ ]

## Notes

<!-- Anything reviewers should know: breaking changes, migration steps, known issues -->
```

**Files created:** `.github/pull_request_template.md`

---

### New Module: `vscode-on-save`

| Field | Value |
|-------|-------|
| id | `vscode-on-save` |
| category | `editor` |
| detect | `.vscode/` directory exists OR `code` CLI is in PATH |
| defaultEnabled | true |
| disableFlag | `--no-vscode` |
| dependsOn | `biome-config`, `ruff-config` |

**Problem it solves:** Without on-save config, developers only see lint errors
at commit time (pre-commit hook) or when running `ai-guardrails check` manually.
Errors discovered 10 minutes after writing code are harder to fix than errors
caught in real time. VS Code's `editor.formatOnSave` + `editor.codeActionsOnSave`
enables immediate feedback on every file save.

**Prompts:**
- Y/N: Configure VS Code to lint and format on save? [Y/n]

**Execute:**
- Creates or merges `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.biome": "explicit",
    "source.organizeImports.biome": "explicit"
  },
  "[typescript]": { "editor.defaultFormatter": "biomejs.biome" },
  "[javascript]": { "editor.defaultFormatter": "biomejs.biome" },
  "[json]": { "editor.defaultFormatter": "biomejs.biome" },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true
  },
  "python.linting.enabled": true,
  "ruff.enable": true,
  "ruff.fixAll": true,
  "ruff.organizeImports": true
}
```

Only includes language sections for detected languages (no Python section in a
TypeScript-only project).

- Creates `.vscode/extensions.json` recommending relevant extensions:

```json
{
  "recommendations": [
    "biomejs.biome",
    "charliermarsh.ruff"
  ]
}
```

Only adds extensions for detected languages.

**Files created/modified:** `.vscode/settings.json`, `.vscode/extensions.json`

**Merge strategy:** Deep merge — does not overwrite existing keys, only adds
missing ones. User's formatter preferences are preserved.

---

### New Module: `helix-on-save`

| Field | Value |
|-------|-------|
| id | `helix-on-save` |
| category | `editor` |
| detect | `~/.config/helix/` exists OR `hx` CLI is in PATH |
| defaultEnabled | true |
| disableFlag | `--no-helix` |
| dependsOn | `biome-config`, `ruff-config` |

**Problem it solves:** Helix has first-class LSP support but requires per-language
server configuration in the project's `.helix/languages.toml`. Without this file,
Helix uses system defaults which may not match the project's biome/ruff config paths.

**Prompts:**
- Y/N: Configure Helix LSP for on-save linting? [Y/n]

**Execute:**
- Creates `.helix/languages.toml` with LSP configuration for detected languages:

```toml
# TypeScript/JavaScript via biome
[[language]]
name = "typescript"
formatter = { command = "biome", args = ["format", "--write", "--stdin-file-path", "file.ts"] }
auto-format = true

[[language]]
name = "javascript"
formatter = { command = "biome", args = ["format", "--write", "--stdin-file-path", "file.js"] }
auto-format = true

# Python via ruff
[[language]]
name = "python"
formatter = { command = "ruff", args = ["format", "-"] }
auto-format = true
language-servers = ["pylsp"]
```

**Files created:** `.helix/languages.toml`

---

### New Module: `nvim-on-save`

| Field | Value |
|-------|-------|
| id | `nvim-on-save` |
| category | `editor` |
| detect | `~/.config/nvim/` exists OR `nvim` CLI is in PATH |
| defaultEnabled | false |
| disableFlag | `--no-nvim` |
| dependsOn | `biome-config`, `ruff-config` |

**Note:** `defaultEnabled: false` because nvim configs are highly personal and
opinionated. Users who want this will opt in explicitly.

**Prompts:**
- Y/N: Generate nvim null-ls / conform.nvim config snippet for on-save linting? [y/N]

**Execute:**
- Creates `.nvim/conform.lua` (a project-local config snippet, not a global nvim config):

```lua
-- ai-guardrails: project on-save config for conform.nvim
-- Add to your init.lua: require("conform").setup(require(".nvim.conform"))
return {
  formatters_by_ft = {
    typescript = { "biome" },
    javascript = { "biome" },
    python = { "ruff_format" },
  },
  format_on_save = {
    timeout_ms = 500,
    lsp_fallback = true,
  },
}
```

Prints install hint: `# Requires conform.nvim: https://github.com/stevearc/conform.nvim`

**Files created:** `.nvim/conform.lua`

---

### New Module: `zed-on-save`

| Field | Value |
|-------|-------|
| id | `zed-on-save` |
| category | `editor` |
| detect | `~/.config/zed/` exists OR `zed` CLI is in PATH |
| defaultEnabled | true |
| disableFlag | `--no-zed` |
| dependsOn | `biome-config`, `ruff-config` |

**Prompts:**
- Y/N: Configure Zed to format on save? [Y/n]

**Execute:**
- Creates or merges `.zed/settings.json`:

```json
{
  "format_on_save": "on",
  "formatter": "language_server",
  "languages": {
    "TypeScript": { "formatter": { "external": { "command": "biome", "arguments": ["format", "--write", "--stdin-file-path", "{buffer_path}"] } } },
    "JavaScript": { "formatter": { "external": { "command": "biome", "arguments": ["format", "--write", "--stdin-file-path", "{buffer_path}"] } } },
    "Python": { "formatter": { "external": { "command": "ruff", "arguments": ["format", "-"] } } }
  }
}
```

**Files created/modified:** `.zed/settings.json`

---

## 4. Full Module Table (v3.2 — 20 modules)

| Module ID | Category | detect() | defaultEnabled | disableFlag | dependsOn |
|-----------|----------|----------|----------------|-------------|-----------|
| `profile-selection` | `profile` | always | true | — | — |
| `config-tuning` | `profile` | always | true | — | `profile-selection` |
| `ruff-config` | `language-config` | Python | true | `--no-ruff` | `config-tuning` |
| `biome-config` | `language-config` | TypeScript | true | `--no-biome` | `config-tuning` |
| `editorconfig` | `universal-config` | always | true | `--no-editorconfig` | `config-tuning` |
| `markdownlint-config` | `universal-config` | always | true | `--no-markdownlint` | `config-tuning` |
| `codespell-config` | `universal-config` | always | true | `--no-codespell` | `config-tuning` |
| `lefthook` | `hooks` | always | true | `--no-hooks` | `config-tuning` |
| `claude-settings` | `hooks` | always | true | `--no-agent-hooks` | `config-tuning` |
| `agent-rules` | `agent` | AI tool detected | true | `--no-agent-rules` | — |
| `github-actions` | `ci` | `.git` exists | true | `--no-ci` | — |
| `github-branch-protection` | `github` | git + gh auth + github.com | true | `--no-branch-protection` | `github-actions` |
| `github-cc-reviewer` | `github` | git + gh auth + github.com | true | `--no-reviewer` | `github-branch-protection` |
| `github-pr-template` | `github` | git + github.com | true | `--no-pr-template` | — |
| `vscode-on-save` | `editor` | `.vscode/` or `code` in PATH | true | `--no-vscode` | `biome-config`, `ruff-config` |
| `helix-on-save` | `editor` | `~/.config/helix/` or `hx` in PATH | true | `--no-helix` | `biome-config`, `ruff-config` |
| `nvim-on-save` | `editor` | `~/.config/nvim/` or `nvim` in PATH | false | `--no-nvim` | `biome-config`, `ruff-config` |
| `zed-on-save` | `editor` | `~/.config/zed/` or `zed` in PATH | true | `--no-zed` | `biome-config`, `ruff-config` |
| `tool-install` | `tools` | any runner missing | true | — | `profile-selection` |
| `baseline` | `baseline` | always | true | `--no-baseline` | all config + `tool-install` |

---

## 5. Wizard Flow (v3.2)

```
AI Guardrails Setup
═══════════════════

Detected: TypeScript
Tools: Claude Code
Editor: VS Code
Git remote: github.com/Questi0nM4rk/tagen (authenticated)

── Profile & Config ──────────────────────
? Enforcement profile [strict/standard/minimal]: standard
? Line length (60-200): 88
? Indent width [2/4]: 2
? Rules to ignore (comma-separated):
? Paths to exclude (comma-separated):

── Language Configs ──────────────────────
? Generate biome.jsonc (TypeScript)?        [Y/n]

── Universal Configs ─────────────────────
? Generate .editorconfig?                   [Y/n]
? Generate .markdownlint.jsonc?             [Y/n]
? Generate .codespellrc?                    [Y/n]

── Pre-commit & Agent Hooks ──────────────
? Install lefthook pre-commit hooks?        [Y/n]
? Generate .claude/settings.json?           [Y/n]

── Agent Instructions ────────────────────
? Generate agent rule files?                [Y/n]
  (Detected: Claude Code)

── CI Pipeline ───────────────────────────
? Generate GitHub Actions workflow?         [Y/n]

── GitHub Setup ──────────────────────────
? Set up branch protection on main?         [Y/n]
    Will require: PRs, passing CI, 1 review, no force-push
? Add CodeRabbit AI reviewer to PRs?        [Y/n]
    Free for open source — adds .coderabbit.yaml
? Add PR description template?              [Y/n]

── Editor: VS Code ───────────────────────
? Configure VS Code to lint/format on save? [Y/n]
    Writes .vscode/settings.json + extensions.json

── Tool Installation ─────────────────────
(All tools already installed)

── Baseline ──────────────────────────────
? Capture initial baseline snapshot?        [Y/n]

═════════════════════════════════════════

✓ Config: .ai-guardrails/config.toml
✓ biome.jsonc
✓ .editorconfig
✓ lefthook.yml (8 hooks installed)
✓ .claude/settings.json
✓ GitHub: branch protection set on main
✓ GitHub: .coderabbit.yaml added
✓ GitHub: .github/pull_request_template.md added
✓ Editor: .vscode/settings.json, .vscode/extensions.json
✓ Baseline: 0 issues captured

Done! Run `ai-guardrails check` to verify.
```

---

## 6. Dependency Graph (v3.2)

```
profile-selection
    │
config-tuning
    │
    ├── ruff-config ──────────────────────┐
    ├── biome-config ─────────────────────┤
    ├── editorconfig                      │
    ├── markdownlint-config               │ (editor modules depend on
    ├── codespell-config                  │  language config modules)
    ├── lefthook                          │
    └── claude-settings                   │
                                          │
agent-rules    (independent)             │
                                          │
github-actions (independent)             │
    │                                     │
github-branch-protection                 │
    │                                     │
github-cc-reviewer                       │
                                          │
github-pr-template (independent)         │
                                          │
vscode-on-save ←─────────────────────────┤
helix-on-save  ←─────────────────────────┤
nvim-on-save   ←─────────────────────────┤
zed-on-save    ←─────────────────────────┘

tool-install   (depends on: profile-selection)

baseline       (depends on: ALL config + tool-install)
```

---

## 7. Prompt Helpers (src/init/prompt.ts)

```typescript
async function askYesNo(
  rl: ReadlineInterface,
  question: string,
  defaultYes: boolean
): Promise<boolean>

async function askChoice<T extends string>(
  rl: ReadlineInterface,
  question: string,
  choices: readonly T[],
  defaultChoice: T
): Promise<T>

async function askText(
  rl: ReadlineInterface,
  question: string,
  defaultValue: string
): Promise<string>

async function askCommaSeparated(
  rl: ReadlineInterface,
  question: string
): Promise<string[]>

/** Per-file conflict prompt. Returns "merge" | "skip" | "replace".
 *  "replace" is only offered if force === true. */
async function askFileConflict(
  rl: ReadlineInterface,
  filename: string,
  force: boolean
): Promise<"merge" | "skip" | "replace">
```

`askFileConflict` prompts: `"<filename> exists. Merge? [Y/n]"` in standard
mode; `"<filename> exists. [M]erge / [s]kip / [r]eplace:"` when `force` is
true. Default is always merge. Modules call this before calling any generator
`generate()` method when the output file already exists.

---

## 8. CLI Flags

```
ai-guardrails init
  --yes                   Accept all defaults (non-interactive)
  --profile <p>           Preselect profile (strict | standard | minimal)
  --force                 Overwrite existing managed files
  --upgrade               Refresh generated files, preserve config.toml
  --interactive           Force interactive mode even in non-TTY
  --config-strategy <s>   merge | replace | skip (default: merge)

  -- Original module flags --
  --no-hooks              Disable lefthook module
  --no-ci                 Disable github-actions module
  --no-agent-rules        Disable agent-rules module
  --no-agent-hooks        Disable claude-settings module
  --no-baseline           Disable baseline module
  --no-editorconfig       Disable editorconfig module
  --no-markdownlint       Disable markdownlint-config module
  --no-codespell          Disable codespell-config module
  --no-ruff               Disable ruff-config module
  --no-biome              Disable biome-config module

  -- New module flags (v3.2) --
  --no-branch-protection  Disable github-branch-protection module
  --no-reviewer           Disable github-cc-reviewer module
  --no-pr-template        Disable github-pr-template module
  --no-vscode             Disable vscode-on-save module
  --no-helix              Disable helix-on-save module
  --no-nvim               Disable nvim-on-save module
  --no-zed                Disable zed-on-save module
```

Each `--no-X` flag maps to `selections.set(moduleId, false)` before the
wizard runs. The wizard never prompts for a module that has been pre-disabled.

**`--yes` runs all applicable modules.** All modules with `defaultEnabled: true`
run when `--yes` is passed. Modules where `detect()` returns false are skipped
automatically — no GitHub modules run if not authenticated, no editor modules
run if no editor is detected.

---

## 9. Migration Path

The migration preserves backward compatibility at every step.

### What stays

- `src/generators/` — untouched; modules call generators, not replace them
- `src/steps/` — untouched; modules call steps, not replace them
- All existing `--no-X` flags continue to disable their respective modules

### What changes

| File | Change |
|------|--------|
| `src/pipelines/init.ts` | Rewritten to use module system |
| `src/pipelines/install.ts` | Becomes thin wrapper (all modules enabled) |
| `src/cli.ts` | New flags added (see section 8) |
| New: `src/init/types.ts` | `InitModule`, `InitContext`, `InitCategory`, `InitModuleResult` |
| New: `src/init/registry.ts` | `ALL_INIT_MODULES` |
| New: `src/init/wizard.ts` | Interactive prompt loop grouped by category |
| New: `src/init/runner.ts` | Topological sort + module executor |
| New: `src/init/prompt.ts` | `askYesNo`, `askChoice`, `askText`, `askCommaSeparated`, `askFileConflict` |
| New: `src/init/modules/profile-selection.ts` | |
| New: `src/init/modules/config-tuning.ts` | |
| New: `src/init/modules/ruff-config.ts` | |
| New: `src/init/modules/biome-config.ts` | |
| New: `src/init/modules/editorconfig.ts` | |
| New: `src/init/modules/markdownlint-config.ts` | |
| New: `src/init/modules/codespell-config.ts` | |
| New: `src/init/modules/lefthook.ts` | |
| New: `src/init/modules/claude-settings.ts` | |
| New: `src/init/modules/agent-rules.ts` | |
| New: `src/init/modules/github-actions.ts` | |
| New: `src/init/modules/github-branch-protection.ts` | v3.2 |
| New: `src/init/modules/github-cc-reviewer.ts` | v3.2 |
| New: `src/init/modules/github-pr-template.ts` | v3.2 |
| New: `src/init/modules/vscode-on-save.ts` | v3.2 |
| New: `src/init/modules/helix-on-save.ts` | v3.2 |
| New: `src/init/modules/nvim-on-save.ts` | v3.2 |
| New: `src/init/modules/zed-on-save.ts` | v3.2 |
| New: `src/init/modules/tool-install.ts` | |
| New: `src/init/modules/baseline.ts` | |

### Phased Delivery

| Phase | Content | Deliverable |
|-------|---------|-------------|
| 1 | Core framework (types, prompt, runner, empty registry) | Mergeable in isolation, no behavior change |
| 2 | 13 original module files | Each module tested independently |
| 3 | Rewrite `init.ts` pipeline | Full replacement, backward-compat tested |
| 4 | Wizard UI (grouped prompts, summary) | Requires Phase 3 |
| 5 | Tests (unit + integration) | Parallel with Phase 4 |
| 6 | Original CLI flag additions | Parallel with Phase 4 |
| 7 | 7 new v3.2 modules | Requires Phase 3 complete |
| 8 | v3.2 wizard sections + full test suite | Requires Phase 7 |

Phases 1 and 2 can be developed in parallel. Phase 3 requires both to complete.
Phases 7 and 8 are gated on Phase 3 — they must not block the original delivery.

---

## 10. Testing Strategy

| Test file | Coverage |
|-----------|----------|
| `tests/init/prompt.test.ts` | `askYesNo`, `askChoice`, `askText`, `askFileConflict` with `FakeReadline` |
| `tests/init/runner.test.ts` | Topological sort correct order, skip disabled modules, dependency chain |
| `tests/init/wizard.test.ts` | Integration: wizard with pre-programmed answers produces expected selections |
| `tests/init/modules/profile-selection.test.ts` | detect always true, execute writes config.toml |
| `tests/init/modules/ruff-config.test.ts` | detect false for non-Python, execute calls generator |
| `tests/init/modules/baseline.test.ts` | execute runs linters, writes baseline.json |
| `tests/init/modules/github-branch-protection.test.ts` | detect false when no gh auth, execute calls gh API, graceful skip when unauthenticated |
| `tests/init/modules/github-cc-reviewer.test.ts` | execute writes .coderabbit.yaml, detect false for non-github remotes |
| `tests/init/modules/github-pr-template.test.ts` | execute writes pull_request_template.md |
| `tests/init/modules/vscode-on-save.test.ts` | detect false when no .vscode/ and no code CLI, execute merges settings.json |
| `tests/init/modules/helix-on-save.test.ts` | detect false when no helix, execute writes .helix/languages.toml |
| `tests/init/modules/nvim-on-save.test.ts` | defaultEnabled false, detect false when no nvim |
| `tests/init/modules/zed-on-save.test.ts` | detect false when no .config/zed, execute merges .zed/settings.json |
| `tests/init/modules/*.test.ts` | All 20 modules: detect + execute with fakes |
| `tests/pipelines/init.test.ts` | `--yes` runs all 20 applicable modules |

**FakeReadline:** A test double that feeds pre-programmed responses to readline
prompts. Required for wizard integration tests.

**FakeCommandRunner:** Used to stub `gh api` calls in GitHub module tests without
making real network requests.

**FakeFileManager seeding:** Each module test seeds the fake filesystem with
prerequisite state (e.g., Python detected = `requirements.txt` present,
editor detected = `.vscode/` exists).

---

## 11. Evolution

| Stable While | Revisit If | Impact |
|-------------|------------|--------|
| 20-module registry | New init feature needed | Add one module file + registry entry — no other changes |
| Category display order | UX research shows different grouping preferred | Update `wizard.ts` category order, update this spec |
| `dependsOn` string IDs | Module renamed after shipping | Never rename a module ID — add an alias instead |
| readline-based prompts | Windows terminal issues reported | Evaluate `@inquirer/prompts`, update `prompt.ts` only |
| `--yes` runs all applicable modules | Module adds unwanted side effect | Add `--no-X` flag to opt out; never restrict `--yes` |
| GitHub module API calls | GitHub API changes | Pin `gh` CLI version in CI, test against mock API |
| Editor detection paths | New OS/config locations | Extend `detect()` with additional path checks |
| `.coderabbit.yaml` schema | CodeRabbit updates config format | Pin schema version in header comment |

---

## 12. Cross-References

- SPEC-000: Philosophy principles 6 (composition over inheritance), technology stack
- SPEC-001: `PipelineContext`, `StepResult`, `FileManager`, `CommandRunner`, `Console` interfaces
- SPEC-002: `ResolvedConfig`, profiles, `isAllowed()` — consumed by modules via `InitContext.config`
- SPEC-004: Current init flags, exit codes — this spec extends them
- SPEC-006: Config generators called by modules (`ruffGenerator`, `biomeGenerator`, etc.)
- SPEC-007: `snapshotStep` called by the `baseline` module
