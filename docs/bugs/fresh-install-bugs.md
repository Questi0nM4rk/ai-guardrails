# Fresh Install Bug Reports

Bugs discovered during a fresh `ai-guardrails init` on a real project
(`guardrails-review` repo, 2026-02-26).

## Prerequisites

ai-guardrails assumes these tools are installed on the system. If missing,
specific hooks will fail silently or with confusing errors.

| Tool | Required by | Install |
|------|-------------|---------|
| `pre-commit` | Hook framework | `pip install pre-commit` / `uv tool install pre-commit` |
| `detect-secrets` | Secret scanning + baseline | `pip install detect-secrets` / `uv tool install detect-secrets` |
| `gitleaks` | Secret scanning | `brew install gitleaks` / [releases](https://github.com/gitleaks/gitleaks/releases) |
| `ruff` | Python lint + format | `pip install ruff` / `uv tool install ruff` |
| `biome` | JS/TS lint + format | `npm i -g @biomejs/biome` |
| `codespell` | Typo checking | `pip install codespell` / `uv tool install codespell` |
| `semgrep` | SAST scanning | `pip install semgrep` / `brew install semgrep` |

**TODO:** `ai-guardrails init` should check for required tools and warn
about missing ones before generating configs that depend on them.

---

## BUG-001: pip-audit YAML block nests inside previous hooks list

**Severity:** HIGH -- breaks pre-commit entirely (YAML parse error)
**Status:** Fixed
**Found in:** `lib/python/guardrails/init.py` lines 257-264
**Repro:** Run `ai-guardrails init` on any Python project with `uv.lock`

### BUG-001 Symptom

Generated `.pre-commit-config.yaml` has the pip-audit `- repo:` block
indented at 2 spaces, which makes it a child of the previous `hooks:`
list instead of a top-level `repos` entry:

```yaml
  - id: name-tests-test
    name: python - test files named test_*
    args:
    - --pytest-test-first

  # pip-audit - CVE scanning for Python dependencies
  - repo: https://github.com/pypa/pip-audit   # <-- BUG: 2-space indent
    rev: v2.10.0
    hooks:
      - id: pip-audit
```

Should be:

```yaml
  - id: name-tests-test
    name: python - test files named test_*
    args:
    - --pytest-test-first

# pip-audit - CVE scanning for Python dependencies
- repo: https://github.com/pypa/pip-audit   # <-- correct: 0-space indent
  rev: v2.10.0
  hooks:
  - id: pip-audit
```

### BUG-001 Root Cause

`_configure_pip_audit()` uses an f-string with 2-space indentation for
the entire block. The function appends raw text to the YAML file, so the
indentation in the f-string becomes the indentation in the output:

```python
# init.py:257-264
block = f"""
  # pip-audit - CVE scanning for Python dependencies
  - repo: https://github.com/pypa/pip-audit
    rev: {_PIP_AUDIT_REV}
    hooks:
      - id: pip-audit
        name: "python - pip-audit CVE scan"
        args: ["--strict", "--progress-spinner", "off", "-r", "requirements-audit.txt"]"""
```

The `- repo:` should be at column 0, not column 2. The `hooks:` items
should use 2-space indent (matching the rest of the generated YAML), not
6-space.

### BUG-001 Fix

Change the f-string indentation to match the top-level `repos` structure
used by the rest of the generated `.pre-commit-config.yaml`:

```python
block = f"""
# pip-audit - CVE scanning for Python dependencies
- repo: https://github.com/pypa/pip-audit
  rev: {_PIP_AUDIT_REV}
  hooks:
  - id: pip-audit
    name: "python - pip-audit CVE scan"
    args: ["--strict", "--progress-spinner", "off", "-r", "requirements-audit.txt"]"""
```

Both the `uv` and `pip` mode blocks (lines 257-264 and 269-276) have
the same indentation bug.

### BUG-001 Impact

- Every Python project with uv.lock gets a broken `.pre-commit-config.yaml`
- `pre-commit run --all-files` fails with YAML parse error
- Blocks initial commit on any freshly initialized repo

**Fixed:** Yes -- `init.py` f-string indentation corrected + regression test added.

---

## BUG-002: Shell shims resolve wrong PYTHONPATH (missing `lib/` segment)

**Severity:** HIGH -- all local hooks fail with `ModuleNotFoundError`
**Status:** Fixed
**Found in:** `lib/hooks/*.sh` (all 6 shim scripts)
**Repro:** Run `ai-guardrails init` then `pre-commit run --all-files`

### BUG-002 Symptom

Every local hook fails immediately:

```text
format and stage.........................................................Failed
- hook id: format-and-stage
- exit code: 1

/usr/bin/python3: Error while finding module specification for
'guardrails.hooks.format_stage' (ModuleNotFoundError: No module named 'guardrails')
```

### BUG-002 Root Cause

`init.py:196` copies the Python runtime to:

```text
.ai-guardrails/lib/python/guardrails/
```

But all 6 shell shims resolve PYTHONPATH as:

```bash
LIB_PYTHON="$SCRIPT_DIR/../python"
# SCRIPT_DIR = .ai-guardrails/hooks/
# Resolves to: .ai-guardrails/python  <-- WRONG, missing lib/
```

Should be:

```bash
LIB_PYTHON="$SCRIPT_DIR/../lib/python"
# Resolves to: .ai-guardrails/lib/python  <-- CORRECT
```

### BUG-002 Affected Files

All shims in `lib/hooks/`:

- `format-and-stage.sh:5`
- `detect-suppression-comments.sh:5`
- `validate-generated-configs.sh:5`
- `protect-generated-configs.sh:6`
- `detect-config-ignore-edits.sh:5`
- `dangerous-command-check.sh:5`

### BUG-002 Fix

Change `$SCRIPT_DIR/../python` to `$SCRIPT_DIR/../lib/python` in all 6
shim scripts. Also update the fallback path on line 6 from
`$HOME/.ai-guardrails/lib/python` (already correct for global install)
to match.

### BUG-002 Impact

- Every `pre-commit run` fails on the first hook (`format-and-stage`)
- With `fail_fast: true`, no other hooks even get a chance to run
- Blocks all commits on freshly initialized repos

**Fixed:** Yes -- all 6 shims updated to `$SCRIPT_DIR/../lib/python`.

---

## BUG-003: detect-secrets fails -- `.secrets.baseline` not created during init

**Severity:** HIGH -- `fail_fast: true` blocks all subsequent hooks
**Status:** Fixed
**Found in:** `lib/python/guardrails/assemble.py` (template) + `init.py` (missing step)
**Repro:** Run `ai-guardrails init` then `pre-commit run --all-files`

### BUG-003 Symptom

```text
security - detect-secrets enhanced.......................................Failed
- hook id: detect-secrets
- exit code: 2

detect-secrets-hook: error: argument --baseline: Invalid path: .secrets.baseline
```

### BUG-003 Root Cause

The pre-commit template (`templates/pre-commit/base.yaml:43`) configures
detect-secrets with `--baseline .secrets.baseline`, but `init` never creates
this file. detect-secrets requires the baseline file to exist.

### BUG-003 Fix

Run `detect-secrets scan > .secrets.baseline` during `_setup_precommit()`
after generating the pre-commit config. Fall back gracefully if
`detect-secrets` is not installed (warn, don't fail).

### BUG-003 Prerequisites

Requires `detect-secrets` to be installed on the system (see Prerequisites
table above).

### BUG-003 Impact

- detect-secrets hook fails on every file
- With `fail_fast: true`, blocks gitleaks, semgrep, and all subsequent hooks
- Every freshly initialized repo hits this

**Fixed:** Yes -- `init.py` now runs `detect-secrets scan` during setup.

---

## BUG-004: validate-generated-configs uses byte comparison, fails on formatted files

**Severity:** MEDIUM -- blocks commits when registry is staged
**Status:** Fixed
**Found in:** `lib/python/guardrails/generate.py:84`

### BUG-004 Root Cause

`_check_freshness()` uses `filecmp.cmp()` (byte-exact). Formatters like
taplo and biome normalize output (inline single-element arrays, change
indent style). Generated output != formatted output even when semantically
identical.

### BUG-004 Fix

Replaced with `_semantically_equal()`: parse TOML via `tomllib`, JSON via
`json`, compare parsed dicts. Falls back to byte comparison for unknown
formats.

**Fixed:** Yes -- `generate.py` updated + tests adjusted.

---

## BUG-005: Generator produces biome.json for Python-only projects

**Severity:** HIGH -- creates broken hook chain for non-JS projects
**Status:** Fixed
**Found in:** `lib/python/guardrails/generate.py` + `generators/biome.py`

### BUG-005 Root Cause

`_generate_to_dir()` always generates ALL config files (ruff.toml,
biome.json, .markdownlint.jsonc, .codespellrc) regardless of which
languages the project uses. A Python-only project gets biome.json, then
the biome pre-commit hook tries to lint non-existent JS/TS files.

Additionally, the biome generator targets biome v1 schema (`1.9.4`) but
biome v2 (`2.x`) is the current stable release. The format-and-stage hook
runs biome which auto-migrates the config to v2 schema, making the
freshness check fail in an infinite cycle.

### BUG-005 Fix

`_generate_to_dir()` now accepts a `languages` parameter. Language-specific
generators (ruff.toml, biome.json) are gated by language detection via
`languages.yaml`. Language-agnostic generators (markdownlint, codespell,
allowlist) always run. `run_generate_configs()` and `_check_freshness()`
auto-detect project languages using `assemble.detect_languages()`.

Remaining: biome v2 schema update (separate issue).

**Fixed:** Yes -- `generate.py` updated with language filtering + regression tests.

---

## BUG-006: Language detection false positive -- `node` detected without JS/TS

**Severity:** MEDIUM -- causes BUG-005 to trigger on Python-only repos
**Status:** Mitigated (BUG-005 fix makes this tolerable)
**Found in:** `lib/python/guardrails/assemble.py` (detect_languages)

### BUG-006 Root Cause

The guardrails-review repo has no `package.json`, no `tsconfig.json`, no
`.js/.ts/.tsx/.jsx` files, yet language detection reports `node`. Likely
detecting something outside the expected file patterns. Needs investigation.

### BUG-006 Mitigation

With the BUG-005 fix, even if `node` is falsely detected, config generation
is now filtered by detected languages. If the project has no JS/TS files
detected via `languages.yaml` patterns, biome.json is not generated.
However, false detection could still cause unnecessary pre-commit hooks.

### BUG-006 Fix Needed

Debug `detect_languages()` on the guardrails-review repo to find what
triggers `node` detection. May need to add exclusion directories
(node_modules, .ai-guardrails) to the glob-based detection in
`assemble.py`.

---
