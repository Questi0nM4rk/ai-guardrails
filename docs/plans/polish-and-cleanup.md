# Plan: Complete Polish, Cleanup & Hardening

## Context

The `feat/python-rewrite` PR converted all bash hook logic and CLI scripts into a
proper `guardrails` Python package. This plan covers everything needed to make the
project production-quality after that rewrite merges.

## 1. Delete Dead Bash Scripts

The following scripts are fully superseded by the Python package and the unified
`ai-guardrails` CLI. They should be deleted:

| File | Replaced By |
|------|-------------|
| `bin/ai-guardrails-init` (639 lines) | `guardrails.init` via `ai-guardrails init` |
| `bin/ai-guardrails-generate` | `guardrails.generate` via `ai-guardrails generate` |
| `bin/ai-review-tasks` | `guardrails.coderabbit` via `ai-guardrails review` |
| `bin/ai-hooks-init` | Evaluate if still needed or fold into `ai-guardrails init` |

Update `lib/installers/core.py` BIN_SCRIPTS to remove deleted entries.

## 2. Rename Test Files

| Old Name | New Name |
|----------|----------|
| `tests/test_assemble_precommit.py` | `tests/test_assemble.py` |
| `tests/test_coderabbit_parser.py` | `tests/test_coderabbit.py` |

Update docstrings inside to match.

## 3. Add Tests for Hook Modules

Zero test coverage on the 5 new hook modules:

- `tests/test_hook_suppress_comments.py`
- `tests/test_hook_config_ignore.py`
- `tests/test_hook_protect_configs.py`
- `tests/test_hook_dangerous_cmd.py`
- `tests/test_hook_format_stage.py`

Each hook module has a `main()` that reads git state and exits with a code.
Test with mocked `subprocess.run` and temp git repos.

## 4. Add Tests for `init.py`

`guardrails/init.py` has ~400 lines with zero test coverage. Key functions
to test:

- `run_init()` — end-to-end with a temp project dir
- `_detect_python_deps()` — pip vs uv detection
- `_resolve_languages()` — language auto-detection
- `_copy_config()` — file copy with force/skip logic
- `_scaffold_registry()` — creates `.guardrails-exceptions.toml`
- `_setup_precommit()` — pre-commit config assembly

## 5. Add Tests for `cli.py`

Test CLI arg parsing and dispatch for all three subcommands.

## 6. Type Checking (pyright)

Add pyright to the dev workflow:

```toml
[tool.pyright]
include = ["lib/python/guardrails"]
pythonVersion = "3.10"
typeCheckingMode = "standard"
```

Fix any type errors.

## 7. ~~Remove `pre-commit.sh` and `pre-push.sh`~~ (DONE)

`pre-commit.sh` and `pre-push.sh` were rewritten in the `feat/python-rewrite`
PR. `pre-commit.sh` now delegates to the `pre-commit` framework (exits 1 if
not installed). `pre-push.sh` runs semgrep and pre-commit full-suite checks,
only printing success when at least one tool ran.

## 8. Clean Up `conftest.py`

- Update comment from "importing coderabbit_parser" to "importing guardrails"
- The `sys.path` insert for `lib/python` is still correct (needed for
  `from guardrails.X import` to resolve)

## 9. Clean Up `pyproject.toml`

- Remove any remaining dead per-file-ignores for old file paths
- Audit all ruff ignore rules — remove any that are no longer triggered

## 10. Update CI Workflow

`.github/workflows/test.yml` references old module paths. Update all
`python3 lib/python/assemble_precommit.py` calls to use
`python3 -m guardrails.assemble`.

## 11. Documentation

- Update `CLAUDE.md` references to old module names
- Update any README sections about usage/installation
- Update `docs/plans/bin-scripts-conversion.md` status

## 12. Compact the Codebase

- Remove any unused imports across the package
- Remove dead code paths (functions never called)
- Consolidate duplicate logic
- Ensure consistent error handling patterns (all hooks use same exit codes)

## 13. Coverage Target

Aim for 85%+ coverage on the `guardrails` package. Current coverage is
high on generators/registry/assemble/coderabbit but zero on hooks/init/cli.

## Execution Order

1. Delete dead bash scripts (quick win, reduces confusion)
2. Rename test files
3. Add hook + init + cli tests (biggest effort)
4. pyright type checking
5. CI workflow updates
6. Documentation pass
7. Final coverage audit
