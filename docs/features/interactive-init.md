# Feature: Interactive init with Y/N prompts

**Priority:** MEDIUM
**Status:** Proposed
**Parent spec:** [SPEC-v1.md](SPEC-v1.md) — `ai-guardrails init` command section
**Related:** ADR-002 section 8.2 "Near-term features" (superseded by SPEC-v1.md)

---

## Summary

The `ai-guardrails init` command currently runs non-interactively, installing all
components unless explicitly disabled via `--no-X` flags. This requires the user to
already know which flags exist and what each component does. An interactive mode would
walk first-time users through each component with Y/N prompts, making the tool
approachable without sacrificing the non-interactive path for CI and power users.

---

## Proposed UX

### Terminal output (interactive, TTY detected)

```
$ ai-guardrails init

  ai-guardrails v0.3.0 — interactive setup
  ─────────────────────────────────────────

  Scanning project...

  Detected languages: Python, TypeScript, Shell
  Configure for these languages? [Y/n] y

  Pre-commit hooks
    Installs format-on-stage, lint, and security hooks via pre-commit.
    Install pre-commit hooks? [Y/n] y

  Security scanning
    Enables gitleaks, detect-secrets, semgrep, and bandit (Python only).
    Enable security scanning? [Y/n] y

  Guardrails Review bot
    AI-powered PR review bot using OpenRouter.
    Install guardrails-review? [Y/n] y
    OpenRouter model [anthropic/claude-sonnet-4]: anthropic/claude-sonnet-4

  CodeRabbit
    Third-party static analysis review bot (requires CodeRabbit account).
    Install CodeRabbit config? [y/N] n

  CI workflow
    Generates a GitHub Actions workflow that runs lint + type-check + tests.
    Generate GitHub Actions CI workflow? [Y/n] y

  Branch protection
    Configures branch protection rules via the GitHub API (requires `gh` CLI).
    Set up branch protection rules? [Y/n] y
    Require status checks to pass? [Y/n] y

  Claude Code hooks
    Installs PreToolUse hooks that prevent Claude Code from weakening configs.
    Install Claude Code agent hooks? [Y/n] y

  Suppression policy
    Blocks suppression comments (noqa, type: ignore, eslint-disable, etc.)
    in pre-commit. Forces exceptions through the registry instead.
    Block suppression comments? [Y/n] y

  ─────────────────────────────────────────
  Applying configuration...

  [ok] Copied configs for: Python, TypeScript, Shell
  [ok] Installed pre-commit hooks (12 hooks)
  [ok] Security scanning enabled
  [ok] Guardrails-review configured (model: anthropic/claude-sonnet-4)
  [skip] CodeRabbit — skipped
  [ok] CI workflow written to .github/workflows/check.yml
  [ok] Branch protection applied (main: require PR + approval + status checks)
  [ok] Claude Code hooks installed (3 hooks)
  [ok] Suppression comment blocking enabled

  Done. Run `ai-guardrails status` to verify.
```

### Terminal output (non-interactive, `--yes` or non-TTY)

```
$ ai-guardrails init --yes
[ok] Detected: Python, TypeScript, Shell
[ok] Copied configs for: Python, TypeScript, Shell
[ok] Installed pre-commit hooks (12 hooks)
...
```

Identical to current behavior. No prompts, all defaults accepted.

---

## Flags

| Flag | Effect |
|------|--------|
| `--yes` / `-y` | Accept all defaults, no prompts (current behavior) |
| `--no-interactive` | Alias for `--yes` |
| `--no-precommit` | Skip pre-commit hooks (existing flag, also skips the prompt) |
| `--no-ci` | Skip CI workflow (existing flag, also skips the prompt) |
| `--no-guardrails-review` | Skip review bot (existing flag, also skips the prompt) |
| `--no-coderabbit` | Skip CodeRabbit (existing flag, also skips the prompt) |

**Rule:** If a `--no-X` flag is passed, the corresponding prompt is never shown.
If a `--X` flag is passed (e.g., `--ci`, `--coderabbit`), the component is enabled
without prompting. Prompts only appear for components not explicitly set by flags.

---

## Prompt defaults

Each prompt has a default that matches the current non-interactive behavior:

| Component | Default | Rationale |
|-----------|---------|-----------|
| Language detection | Y | Core functionality, always on |
| Pre-commit hooks | Y | Primary value proposition |
| Security scanning | Y | Part of the standard hook set |
| Guardrails-review | Y | Default in current init |
| CodeRabbit | **N** | Third-party dependency, opt-in |
| CI workflow | Y | Default in current init when `.github/` exists |
| Branch protection | Y | Good default for new projects |
| Claude Code hooks | Y | Part of standard install |
| Suppression policy | Y | Core guardrails behavior |

Defaults are shown in the prompt brackets: `[Y/n]` means default yes, `[y/N]` means
default no. Pressing Enter with no input accepts the default.

---

## Implementation notes

### No external dependencies

Use `input()` for prompts. No `inquirer`, `questionary`, `rich.prompt`, or other
TUI libraries. The prompts are simple Y/N -- a library would be over-engineering.

### TTY detection

```python
import sys

def is_interactive() -> bool:
    """Return True if stdin is a TTY and --yes was not passed."""
    return sys.stdin.isatty()
```

When `is_interactive()` is False (piped input, CI environment, cron), all defaults
are accepted silently. This is the same as passing `--yes`.

### Prompt helper

```python
def prompt_yn(message: str, *, default: bool = True) -> bool:
    """Prompt user for Y/N input. Return default if non-interactive."""
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        answer = input(f"  {message} {suffix} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default
    if not answer:
        return default
    return answer in ("y", "yes")
```

### Integration with current architecture

The interactive prompts resolve to the same boolean flags that `--no-X` / `--X`
currently produce. The init function's internal logic does not change -- only the
flag resolution at the CLI boundary changes.

```
CLI args (argparse)
    |
    v
Interactive prompts (only for unset flags, only if TTY)
    |
    v
Resolved flags (same shape as today's args)
    |
    v
init() business logic (unchanged)
```

This means:

- No changes to `init.py` business logic
- No changes to the test suite for init behavior
- New tests only for the prompt layer itself
- Compatible with the Pipeline + Plugin refactor (ADR-002 section 4) -- prompts
  would become part of the CLI layer, before pipeline dispatch

### Branch protection (new capability)

The branch protection prompt introduces a new feature not currently in `init`.
Implementation would call `gh api` to set branch protection rules:

```bash
gh api repos/{owner}/{repo}/branches/main/protection \
  --method PUT \
  --field required_pull_request_reviews='{"required_approving_review_count":1}' \
  --field required_status_checks='{"strict":true,"contexts":["check"]}'
```

This requires:

- `gh` CLI installed and authenticated
- Write access to the repository
- The prompt should warn if `gh` is not available:
  `"[warn] gh CLI not found -- skipping branch protection"`

Branch protection could be deferred to a follow-up if it complicates the initial PR.

### Testing

- `prompt_yn()` is a pure function when given `input()` as a dependency -- inject
  a callable for testing
- Test matrix: TTY + no flags, TTY + some flags, TTY + `--yes`, non-TTY
- No subprocess mocking needed for the prompt layer itself
- Branch protection tests mock `gh api` via `CommandRunner`

---

## What this does NOT cover

- **Wizard-style TUI** with arrow keys, checkboxes, or color pickers. This is
  simple `input()` prompts only.
- **Config file for defaults.** No `~/.ai-guardrails/defaults.toml` that
  pre-populates answers. That is a separate feature.
- **`ai-guardrails reconfigure`** to re-run prompts on an existing project.
  Useful but separate scope.
- **Undo/back** during the prompt flow. Prompts are sequential and final.

---

## Effort estimate

- Prompt helper + TTY detection: ~50 lines
- CLI flag merging (prompts fill in unset flags): ~40 lines
- 9 prompt call sites in init flow: ~30 lines
- Tests for prompt layer: ~100 lines
- Branch protection (if included): ~80 lines + tests

Total: ~300 lines of new code, 0 lines of refactored code. Additive change only.
