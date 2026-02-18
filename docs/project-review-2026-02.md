# ai-guardrails: Comprehensive Project Review

**Date:** 2026-02-17
**Version:** 0.2.0
**Stats:** 509 tests, 91% coverage, ~12K lines Python

---

## Architecture Summary

ai-guardrails is a code quality enforcement system that:

1. Installs base + language-specific linter configs and pre-commit hooks
   into consumer projects
2. Provides a TOML-based exception registry as single source of truth
   for suppressions
3. Generates tool configs from that registry
4. Installs Claude Code PreToolUse hooks that intercept dangerous
   commands and unauthorized config edits

```text
ai-guardrails/
├── bin/                    # Shell entry-point shims
├── configs/                # Base config templates (8 files)
├── docs/                   # Plans, specs, review notes
├── ideas/                  # Design sketches (not implemented)
├── lib/
│   ├── hooks/              # 8 shell shims (thin wrappers to Python)
│   ├── installers/         # 9 pyinfra deploy modules
│   └── python/guardrails/  # Core Python package (~3,500 lines)
├── templates/              # Files deployed to consumer projects
│   ├── pre-commit/         # 9 YAML fragments (base + 8 languages)
│   └── workflows/          # 2 GitHub Actions templates
├── tests/                  # 22 test modules, 509 tests (~6K lines)
├── install.py              # pyinfra-based machine installer
└── pyproject.toml
```

---

## What's Working Well

- **Clean module boundaries** — Every hook is a thin shell shim
  delegating to Python. Easy to test, no bash logic to unit-test.
- **`constants.py` as single source of truth** — Suppression patterns,
  file lists, dangerous command rules, ANSI codes all centralized.
- **Atomic config generation** — tempdir + `shutil.move` prevents
  partial writes.
- **Hash-based re-staging** in `format_stage.py` — Only re-stages
  files actually changed by formatters.
- **Well-typed `ExceptionRegistry`** — Proper dataclasses, validation,
  clear separation of concerns.
- **`expires` field** in registry entries — Genuinely useful, fully
  implemented time-limited exceptions.
- **Meta-tests enforce consistency** — `test_coverage_enforcement.py`
  checks CI/CLAUDE.md/pyproject.toml agree on 85%;
  `test_template_sync.py` checks prompt parity.
- **Unique features no competitor has:**
  1. AI-bypass prevention (dangerous-command-check,
     protect-generated-configs)
  2. Exception registry with expiry dates
  3. PR review bot integration (`ai-guardrails comments`)
  4. Suppression detection across 8 languages

---

## High Priority Issues

### 1. No PyPI Package

`pyproject.toml` has correct hatchling config but has never been
published. No release workflow in `.github/workflows/`. Version is
`0.2.0` with no changelog. The enterprise assessment identifies this
as P0.

### 2. No Version Pinning for Consumers

When a consumer project runs `ai-guardrails init --force`, it gets
whatever version is installed on the developer's machine. No mechanism
to pin `requires >= 0.2.0`. If dev A has 0.1 and dev B has 0.2, they
get silent behavior drift. The `.ai-guardrails/` directory is
gitignored by design, so each dev gets their own copy.

### 3. `init.py` Excluded from Coverage

Largest file (837 lines), most complex, explicitly in the coverage
`omit` list. The 91% figure is misleading — actual `init.py` coverage
is likely below 50%. Integration tests exist (9 tests in
`test_init_integration.py`) but only cover happy paths.

Missing test coverage:

- Error case: `find_configs_dir()` raises `FileNotFoundError`
- `--all` type: all language configs copied
- Auto-detection: no `--type` argument, multiple languages
- `_configure_pip_audit` with `uv` mode
- `_add_to_gitignore` when `.gitignore` doesn't end with newline
- `_install_pretooluse_hook` when `settings.json` already has the hook
- `_install_pretooluse_hook` when `settings.json` has corrupt JSON

### 4. Template Version Drift

Project uses `pre-commit-hooks v6.0.0` but `base.yaml` ships
`v5.0.0`. Consumers who install via `ai-guardrails init` get older
versions. No automation to keep template versions in sync.

---

## Medium Priority Issues

### Language Support Gaps

- **Go**: Template exists but uses deprecated `--enable-all`
  (golangci-lint v1.57+). No `.golangci.yml` config file — flags
  passed on CLI which is fragile.
- **C/C++**: `.clang-tidy` enables `*` but no dedicated security
  scanner (cppcheck, FlawFinder, semgrep `p/c`).
- **C#/.NET**: Good rule coverage (200+) but no CVE scanning
  (`dotnet list package --vulnerable` missing).
- **Shell**: No `.shellcheckrc` config file deployed.

### format-and-stage Incomplete

Handles `.py`, `.sh`, `.bash`, `.md`, `.ts`, `.tsx`, `.js`, `.jsx`,
`.json`, `.toml` but NOT:

- `.rs` (rustfmt)
- `.cs` (dotnet format)
- `.lua` (stylua)
- `.go` (gofmt)
- `.cpp`/`.c`/`.h` (clang-format)

Inconsistent with "auto-fix everything" philosophy.

### format-and-stage TOML Stash Bug (Still Active)

When TOML files are staged and untracked files exist, `taplo format`
reformats TOML, then stash pop conflicts. Workaround: gitignore
untracked files before committing. Root cause is pre-commit's stash
mechanism, not format-and-stage itself.

### `semgrep --config auto` Non-Reproducible

Rules change between runs. Passing CI today may fail tomorrow on
same code. For "black/white only" philosophy, pinning to `p/default`
or `p/owasp-top-ten` would be more consistent.

### `_paths.py` at 54% Coverage

Global install fallback paths (`~/.ai-guardrails/`) entirely
untested. If path resolution fallback breaks, tests won't catch it.

### `init.py` String-Replace Hack

Post-hoc `content.replace("entry: lib/hooks/...",
"entry: .ai-guardrails/hooks/...")` is fragile. Should generate
correct paths during assembly.

### Hardcoded `pip-audit v2.10.0`

`_configure_pip_audit` pins version in a string block. Will silently
go stale.

### Pyright Generation Not Checkable

`--check` mode skips pyright because it's in-place edit of
`pyproject.toml`. `validate-generated-configs.sh` won't catch stale
pyright config.

---

## Low Priority / Nice-to-Have

### Missing Languages

- **Java/Kotlin**: No config, template, or installer. Checkstyle,
  SpotBugs, PMD, ktlint, detekt all absent.
- **Swift**: Not mentioned anywhere.
- **YAML as first-class**: `yamllint` via CodeRabbit but no yamllint
  config deployed.

### Missing CLI Commands

- `ai-guardrails doctor` — Active checks (run hooks, verify tool
  versions, test configs parse) vs passive `status`
- `ai-guardrails upgrade` — Update hook revisions in
  `.pre-commit-config.yaml`
- `ai-guardrails lint` — Run all checks without staged files
- `ai-guardrails audit` — Security/CVE hooks only
- `ai-guardrails exceptions list/expire` — Inspect and manage
  registry

### Missing `init` Flags

- `--verify` — Run `ai-guardrails status` after init to confirm
- `--update` — Smarter than `--force`, update without overwriting

### `generate --diff` Mode

`--check` reports stale but not which lines differ.

### Distribution

- No Docker image for containerized CI
- No SBOM generation (CycloneDX/SPDX)
- No `CONTRIBUTING.md`

### Security Gaps (Minor)

- Rust: No SAST beyond cargo-audit. No `cargo-geiger` for unsafe
  census.
- `.secrets.baseline` has no audit trail (no reason/expiry for
  suppressed false positives)

### Dead Files

- `.test/` directory: ~626 lines of scratch/exploratory files
- `configs/.ruff_cache/`: Accidentally committed cache directory
- `templates/pre-commit-config.yaml` (top-level): Duplicate, assembly
  uses `templates/pre-commit/*.yaml`
- `templates/settings.json.strict`: Not referenced by any init code

---

## Code Smells

### 1. `status.py` review bots check returns `warn` not `skip`

When no bots are configured, non-GitHub projects always show
"degraded." No way to indicate bots are intentionally absent.

### 2. `biome.py` `$generated` JSON sentinel key

Pollutes config schema since JSON has no comments. The `$generated`
key appears as a real key in the output.

### 3. `suppress_comments.py` silent cap

Shows max 10 violations per pattern but doesn't tell user there may
be more.

### 4. Tilde in PreToolUse hook paths

`_install_pretooluse_hook` writes `~/.ai-guardrails/hooks/...` as
raw string. Works in shells but breaks if invoked without tilde
expansion. `str(Path.home())` would be safer.

### 5. ANSI colors duplicated

`install.py` defines RED/GREEN/YELLOW/BLUE/NC locally (can't import
from package due to import ordering), same as `constants.py`.

### 6. Path resolution inconsistency

`_paths.py` prefers local repo over global install, but
`assemble.py:find_installation_paths()` checks global first.
Maintenance risk.

### 7. Project doesn't dogfood all its hooks

`detect-suppression-comments`, `detect-config-ignore-edits`,
`validate-generated-configs` are in `base.yaml` template but absent
from project's own `.pre-commit-config.yaml`.

### 8. `comments.py` truncates body previews twice

Once in `format_json()` (120 chars) and already via
`_clean_body()` when parsing. Inefficient for large thread lists.

### 9. `status` missing planned features

`--verbose` flag and dependency availability check were designed in
`ideas/plan-status-command.md` but not implemented.

---

## Recommended Priority Order

1. Publish to PyPI + release workflow
2. Add `init.py` to coverage measurement
3. Fix template version drift (CI check or sync script)
4. Add missing formatters to format-and-stage
5. Replace Go `--enable-all` with `.golangci.yml`
6. Add C# CVE scanning
7. Dogfood all hooks in project's own `.pre-commit-config.yaml`
8. Clean up dead files (`.test/`, `.ruff_cache`, stale templates)
