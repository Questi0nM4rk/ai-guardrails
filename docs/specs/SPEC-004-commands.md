# SPEC-004: CLI Commands

## Status: Draft

---

## Entry Point

```
ai-guardrails <command> [options]
```

Built as a single Bun-compiled binary. Each command maps to a pipeline.
All commands support `--project-dir <path>` to override the working directory.
All commands validate the target directory is a git repo before running.

---

## `install`

```
ai-guardrails install [--upgrade]
```

**Purpose:** One-time machine setup. Run once after installing the binary.

**What it does:**
1. Scaffolds `~/.ai-guardrails/config.toml` with default profile (skip if exists, overwrite if `--upgrade`)
2. Merges Claude Code PreToolUse hooks into `~/.claude/settings.json`:
   - `ai-guardrails hook dangerous-cmd`
   - `ai-guardrails hook protect-configs`
3. Prints confirmation of what was created/updated

**Idempotent:** Re-running without `--upgrade` is safe — skips existing files,
merges hooks without duplicating.

---

## `init`

```
ai-guardrails init [--profile <profile>] [--force] [--upgrade]
                   [--no-hooks] [--no-ci] [--no-agent-rules]
                   [--dry-run] [--interactive]
```

**Purpose:** Per-project setup. Run once per repo.

**Pipeline steps:**
1. `detect-languages` — find which languages are present
2. `load-config` — load + merge machine + existing project config (if any)
3. `scaffold-config` — write `.ai-guardrails/config.toml` with detected languages pre-populated
4. `generate-configs` — write all managed config files (ruff.toml, biome.json, etc.)
5. `generate-agent-rules` — write AGENTS.md, .cursorrules, .windsurfrules, copilot-instructions.md
6. `setup-agent-instructions` — append guardrails section to CLAUDE.md
7. `setup-ci` — write `.github/workflows/guardrails-check.yml`
8. `setup-hooks` — run `lefthook install`

**Flags:**
- `--profile` — override profile for this project (`strict` | `standard` | `minimal`)
- `--force` — overwrite existing managed files (except `.ai-guardrails/config.toml`)
- `--upgrade` — refresh all generated files, preserve `.ai-guardrails/config.toml`
- `--no-hooks` — skip lefthook install
- `--no-ci` — skip CI workflow generation
- `--no-agent-rules` — skip AGENTS.md and IDE rule files
- `--dry-run` — print what would happen, write nothing
- `--interactive` — Y/N prompt for each optional step (default: auto-detect TTY)

**Guard:** If `.ai-guardrails/config.toml` exists and `--force`/`--upgrade` not set,
abort with a clear message explaining the flags.

---

## `generate`

```
ai-guardrails generate [--check] [--dry-run]
```

**Purpose:** Regenerate all managed config files from `.ai-guardrails/config.toml`.

**Pipeline steps:**
1. `detect-languages`
2. `load-config`
3. `generate-configs` — (re)write ruff.toml, mypy.ini, biome.json, etc. with hash headers
4. `generate-agent-rules` — (re)write AGENTS.md and IDE files

**`--check` mode (CI use):**
- Does NOT write any files
- Verifies each managed file exists and its hash header matches current generation
- Exits 1 if any file is stale, missing, or tampered
- Used in CI: `ai-guardrails generate --check`

**`--dry-run`:** Print what would be written without writing.

---

## `snapshot`

```
ai-guardrails snapshot [--baseline <path>] [--dry-run]
```

**Purpose:** Capture current lint state as a baseline for hold-the-line enforcement.

**What it does:**
1. Detects languages, loads config
2. Runs all active runners across the project
3. Applies config-level ignores (but NOT baseline suppression — captures everything)
4. Writes `.ai-guardrails/baseline.json` with fingerprints of all current issues

**After snapshotting:** `ai-guardrails check` will only flag issues whose
fingerprint is NOT in the baseline — new issues only.

**`--baseline <path>`:** Custom output path (default: `.ai-guardrails/baseline.json`)

**`--dry-run`:** Print issue count without writing baseline.

---

## `check`

```
ai-guardrails check [--baseline <path>] [--format text|sarif] [--strict]
```

**Purpose:** Hold-the-line enforcement. Fails if new issues found since baseline.

**Pipeline steps:**
1. `detect-languages`
2. `load-config`
3. `check-step`:
   a. Load baseline (empty baseline = no suppression, all issues are new)
   b. Run all active runners concurrently per language (`Promise.all`)
   c. Apply config-level ignores (`ResolvedConfig.isAllowed`)
   d. Apply inline allow comments (second pass over source lines)
   e. Filter: issues in baseline = suppressed, issues not in baseline = new
   f. Write audit record to `.ai-guardrails/audit.jsonl`
   g. Return error if any new issues

**Exit codes:**
- `0` — no new issues
- `1` — new issues found

**`--format sarif`:** Emit SARIF 2.1.0 JSON to stdout for GitHub Code Scanning
upload. Text output still goes to stderr.

**`--strict`:** Ignore the baseline entirely — all issues are new. Intended for
AI-authored commits (agent cannot claim baseline exemption).

**`--baseline <path>`:** Custom baseline path.

**Inline allow comment flow:**
```
For each issue at (file, line):
  1. Read that source line
  2. Parse ai-guardrails-allow comments
  3. If rule is in a valid allow (with reason): suppress, count +1
  4. If rule is in a bare allow (no reason): replace with AI001 issue
  5. Otherwise: include in results
```

**Audit record written per run:**
```jsonl
{"timestamp":"2026-03-08T12:00:00Z","command":"check","new_issues":0,"suppressed_baseline":12,"suppressed_allow":3,"status":"ok"}
```

---

## `status`

```
ai-guardrails status
```

**Purpose:** Project health dashboard. Informational only — never exits 1.

**Output format:**
```
Languages:    python, shell
Profile:      standard

Configs:
  ruff.toml                 fresh
  mypy.ini                  fresh
  .editorconfig             STALE — run: ai-guardrails generate
  lefthook.yml              fresh
  AGENTS.md                 fresh

Hooks:        lefthook 1.8.2 installed
Baseline:     captured 2026-03-07  (142 suppressed issues)
Last check:   2026-03-08 09:14  — ok (0 new issues)
```

**What it checks:**
- Active language plugins (from detection)
- Each managed config: call `generator.verify()` → fresh/stale
- Hooks: `lefthook version` → installed/not installed
- Baseline: exists + date + suppressed count
- Last audit record from `.ai-guardrails/audit.jsonl`

---

## `report`

```
ai-guardrails report [--last <n>]
```

**Purpose:** Show recent check run history from `.ai-guardrails/audit.jsonl`.

**Default:** Last 10 runs.

**Output:**
```
Recent check history:
  2026-03-08 09:14  ok       0 new,  12 baseline,  3 allowed
  2026-03-07 22:01  error    2 new,  10 baseline,  1 allowed
  2026-03-07 18:33  ok       0 new,  10 baseline,  1 allowed
```

---

## `hook` (internal subcommand)

```
ai-guardrails hook <hook-name> [args...]
```

**Purpose:** Dispatcher for hook implementations. Invoked by lefthook and
Claude Code — not intended for direct user use.

**Subcommands:**

| Hook | Trigger | What |
|------|---------|------|
| `dangerous-cmd` | Claude Code PreToolUse | Block rm -rf, force-push, checkout -- |
| `protect-configs` | Claude Code PreToolUse | Block edits to managed config files |
| `suppress-comments` | lefthook pre-commit | Detect noqa/ts-ignore/eslint-disable |
| `format-stage` | lefthook pre-commit | Run formatters + re-stage |

**Exit codes for hook subcommands:**
- `0` — allow / pass
- `1` — block / fail (with message to stderr)

---

## Global Flags

All commands accept:

```
--project-dir <path>   Override working directory (default: cwd)
--quiet                Suppress info/success output (errors still print)
--no-color             Disable ANSI color output
```

---

## Shell Completion

```
ai-guardrails completion bash   # → bash completion script
ai-guardrails completion zsh    # → zsh completion script
ai-guardrails completion fish   # → fish completion script
```

Generated via Commander.js built-in completion support.
