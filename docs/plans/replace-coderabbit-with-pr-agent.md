# Plan: Replace CodeRabbit with PR-Agent (Self-Hosted)

## Status: READY

## Motivation

CodeRabbit's free/OSS tier has hard limits:

- 3 reviews/hour rate limit
- Auto-review disabled to conserve quota
- No self-hosting — dependent on CodeRabbit's SaaS infrastructure
- Feature gating behind paid Pro tier

**PR-Agent** (by Qodo, formerly CodiumAI) is AGPL-3.0 licensed, fully self-hostable,
and has no rate limits when self-hosted. The open-source version includes:

- Inline committable code suggestions (via `commitable_code_suggestions = true`)
- Auto-approval (`enable_auto_approval = true`)
- Multi-model support (OpenAI, Claude, DeepSeek, Ollama, **OpenRouter**)
- GitHub Action, Docker, webhook, and CLI deployment modes

**Key finding**: Inline comments and auto-approval are NOT gated behind Pro in the
open-source code. They're controlled by config flags that default to `false`.

## Decisions (Resolved)

### 1. LLM Model: MiniMax M2.5 via OpenRouter

**Primary**: `openrouter/minimax/minimax-m2.5`
**Fallback**: `openrouter/moonshotai/kimi-k2.5`

| Model | SWE-bench | Input $/1M | Output $/1M | $/PR review | $/month (400 calls) |
|-------|-----------|------------|-------------|-------------|---------------------|
| MiniMax M2.5 | **80.2%** | $0.30 | $1.10 | $0.004 | **$1.50** |
| Kimi K2.5 | 76.8% | $0.23 | $3.00 | $0.005 | $2.10 |
| Claude Haiku 4.5 | 73.3% | $1.00 | $5.00 | $0.014 | $5.60 |
| Claude Sonnet 4.6 | ~80%+ | $3.00 | $15.00 | $0.042 | $16.80 |

**Why MiniMax M2.5**:

- 80.2% SWE-bench Verified — within 0.6 points of Claude Opus 4.6 (80.8%)
- $1.50/month at 50 PRs/week (200 PRs/month, 2 calls each)
- Explicitly trained on GitHub Issues, PRs, and test cases across 10+ languages
- Released Feb 12, 2026 — most recent frontier model
- Cheapest output tokens ($1.10/M) among frontier-class models

**Why Kimi K2.5 as fallback**:

- 76.8% SWE-bench, 85.0% LiveCodeBench v6 (leads all models)
- Strong multi-file reasoning and agentic tool-use
- Different provider = availability hedge

**Cost estimate**: ~8K input + ~1.2K output tokens per `/review` call on a 500-line diff.
At 50 PRs/week running `/review` + `/improve` = **$1.50/month**.

### 2. Auto-Review: On PR Open Only, Not Every Push

Auto-review triggers on `opened`, `reopened`, `ready_for_review` — not on every push.

Rationale: Even at $0.004/review, auto-reviewing every push on WIP PRs generates
noise. Review on open, then manual `/review` and `/improve` via PR comments for
subsequent iterations.

### 3. Bot Identity: GitHub Action (`github-actions[bot]`)

Use GitHub Action deployment. Simpler than a custom GitHub App.

For the `comments` subcommand, use **content-based detection**: PR-Agent comments
contain distinctive markers (tool name in comment body). Add a secondary filter
that checks comment body for PR-Agent signatures when bot is `github-actions`.

### 4. Inline Comments: All Inline (`commitable_code_suggestions = true`)

Every suggestion posted as an inline diff comment with GitHub's native
```` ```suggestion ```` syntax. One-click "Apply suggestion" for each.

No hybrid mode — the whole point of replacing CodeRabbit is getting real inline
comments, not summary tables.

### 5. API Key: OpenRouter Key as GitHub Secret

Consumer repos add `OPENROUTER_KEY` as a repository or org-level secret.
Documented as a required manual step in the template's comments and README.

---

## Scope

Replace CodeRabbit with PR-Agent across:

1. ai-guardrails' own config (`.coderabbit.yaml` → `.pr_agent.toml`)
2. The template distributed to consumer projects (`templates/.coderabbit.yaml`)
3. The init system that installs review bot configs
4. The `comments` subcommand that interacts with review bot threads
5. The `status` subcommand that checks for review bot configs
6. CI workflows referencing CodeRabbit
7. Documentation (CLAUDE.md, README.md, templates, specs)

---

## Research: PR-Agent Architecture

### Config Format

PR-Agent uses TOML (`.pr_agent.toml` in repo root). Key sections:

```toml
[config]
model = "openrouter/minimax/minimax-m2.5"
model_turbo = "openrouter/minimax/minimax-m2.5"
fallback_models = ["openrouter/moonshotai/kimi-k2.5"]

[pr_reviewer]
extra_instructions = ""
enable_auto_approval = true
auto_approve_for_no_suggestions = true
auto_approve_for_low_review_effort = 3

[pr_code_suggestions]
commitable_code_suggestions = true

[pr_description]
publish_labels = true
enable_semantic_files_types = true

[github_action_config]
pr_commands = [
    "/describe",
    "/review",
    "/improve --pr_code_suggestions.commitable_code_suggestions=true",
]
```

### OpenRouter Integration

PR-Agent supports OpenRouter natively via `openrouter/` prefix:

```toml
# .pr_agent.toml
[config]
model = "openrouter/minimax/minimax-m2.5"

# API key goes in GitHub secrets, passed via env var in the workflow
```

### Deployment: GitHub Action

```yaml
name: PR-Agent
on:
  pull_request:
    types: [opened, reopened, ready_for_review]
  issue_comment:

jobs:
  pr-agent:
    if: ${{ github.event.sender.type != 'Bot' }}
    runs-on: ubuntu-latest
    permissions:
      issues: write
      pull-requests: write
      contents: read
    steps:
      - uses: qodo-ai/pr-agent@main
        env:
          OPENAI_KEY: ${{ secrets.OPENROUTER_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Note: PR-Agent uses `OPENAI_KEY` env var for OpenRouter too — the OpenRouter API
is OpenAI-compatible, so the same env var works. The model string prefix
`openrouter/` tells PR-Agent to route to OpenRouter's endpoint.

### Bot Identity on GitHub

PR-Agent posts as `github-actions[bot]` when run as a GitHub Action. This affects
the `comments` subcommand's bot filtering — handled via content-based detection
(see Phase 3).

### Key Difference from CodeRabbit

PR-Agent is **LLM-only** — it doesn't run static analysis tools (ruff, shellcheck,
semgrep, etc.). Those are already handled by our pre-commit hooks and CI. This is
actually cleaner: PR-Agent focuses on semantic code review while pre-commit
handles mechanical linting.

---

## Phase 1: Template & Config Replacement

**Branch**: `feat/replace-coderabbit`

### 1.1 Create PR-Agent config template

Create `templates/.pr_agent.toml`:

```toml
# PR-Agent Configuration (Qodo Merge OSS)
# https://qodo-merge-docs.qodo.ai/usage-guide/configuration_options/
#
# SETUP REQUIRED:
#   1. Add OPENROUTER_KEY to your GitHub repo/org secrets
#   2. The pr-agent.yml workflow will use this config automatically
#
# Manual commands (comment on PR):
#   /review       — Re-run code review
#   /improve      — Re-run code suggestions
#   /describe     — Re-generate PR description
#   /ask "question" — Ask about the PR

[config]
model = "openrouter/minimax/minimax-m2.5"
model_turbo = "openrouter/minimax/minimax-m2.5"
fallback_models = ["openrouter/moonshotai/kimi-k2.5"]

[pr_reviewer]
# Review instructions — ported from CodeRabbit path_instructions
extra_instructions = """
Focus areas:
- Static analysis: flag issues caught by linters (ruff, shellcheck, biome)
- Security: secrets, injection, unsafe operations
- Language conventions: enforce per-language best practices
- Flag code that bypasses pre-commit hooks or suppresses linting

Python:
- Enforce type hints on all function signatures
- Check for proper exception handling (no bare except)
- Verify docstrings on public functions/classes
- Enforce modern Python: f-strings, pathlib, walrus operator

TypeScript:
- Ensure strict TypeScript (no any, no type assertions without reason)
- Enforce modern TS: satisfies over as, optional chaining, nullish coalescing

Shell:
- Verify scripts use set -euo pipefail
- Check for proper quoting of variables

Tests:
- Focus on test coverage and edge cases
- Verify meaningful assertions
- Check for test isolation
"""

# Auto-approval: approve when no actionable suggestions found
enable_auto_approval = true
auto_approve_for_no_suggestions = true
auto_approve_for_low_review_effort = 3

[pr_code_suggestions]
# Post suggestions as inline diff comments with "Apply suggestion" button
commitable_code_suggestions = true

[pr_description]
publish_labels = true
enable_semantic_files_types = true

[github_action_config]
# Auto-trigger on PR open
pr_commands = [
    "/describe",
    "/review",
    "/improve --pr_code_suggestions.commitable_code_suggestions=true",
]
```

### 1.2 Create PR-Agent workflow template

Create `templates/workflows/pr-agent.yml`:

```yaml
name: PR-Agent
on:
  pull_request:
    types: [opened, reopened, ready_for_review]
  issue_comment:

jobs:
  pr-agent:
    # Skip bot-triggered events to prevent loops
    if: ${{ github.event.sender.type != 'Bot' }}
    runs-on: ubuntu-latest
    permissions:
      issues: write
      pull-requests: write
      contents: read
    steps:
      - uses: qodo-ai/pr-agent@main
        env:
          # OpenRouter API key (OpenAI-compatible endpoint)
          OPENAI_KEY: ${{ secrets.OPENROUTER_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 1.3 Remove CodeRabbit template

- Delete `templates/.coderabbit.yaml`
- Keep `.coderabbit.yaml` in repo root until migration is verified (remove in Phase 4)

---

## Phase 2: Init System Changes

### 2.1 Rename init parameter

In `lib/python/guardrails/init.py`:

- Rename `install_coderabbit` → `install_pr_agent` in:
  - `run_init()` parameter and docstring (line 687)
  - `_dry_run_report()` parameter (line 609)
  - `_github_integrations` list (line 784)
  - `_integration_names` list (line 657)
- Rename `_install_coderabbit()` → `_install_pr_agent()` (line 510)
- Update function body: copy `.pr_agent.toml` instead of `.coderabbit.yaml`
- Add: also copy `pr-agent.yml` to `.github/workflows/` inside `_install_pr_agent()`
- Update print messages: "Setting up PR-Agent..." instead of "Setting up CodeRabbit..."
- Update tip: "Customize extra_instructions in .pr_agent.toml" instead of path_instructions

In `lib/python/guardrails/cli.py`:

- Rename `--coderabbit` / `--no-coderabbit` → `--pr-agent` / `--no-pr-agent` (line 38-39)
- Update `_resolve_flag(args, "coderabbit")` → `_resolve_flag(args, "pr_agent")` (line 140)

### 2.2 Update status check

In `lib/python/guardrails/status.py` (line 44-48):

```python
# Before:
_BOT_CONFIGS = [
    (".coderabbit.yaml", "CodeRabbit"),
    (".deepsource.toml", "DeepSource"),
    (".gemini/config.yaml", "Gemini"),
]

# After:
_BOT_CONFIGS = [
    (".pr_agent.toml", "PR-Agent"),
    (".deepsource.toml", "DeepSource"),
    (".gemini/config.yaml", "Gemini"),
]
```

### 2.3 Update dry-run report

In `_dry_run_report()` (line 657):

```python
# Before:
(install_coderabbit, "CodeRabbit config (.coderabbit.yaml)"),

# After:
(install_pr_agent, "PR-Agent config (.pr_agent.toml)"),
```

---

## Phase 3: Comments Subcommand

### 3.1 Update bot aliases

In `lib/python/guardrails/comments.py` (line 43-48):

```python
# Before:
BOT_ALIASES: dict[str, str] = {
    "coderabbit": "coderabbitai",
    "deepsource": "deepsource-io",
    "gemini": "gemini-code-assist",
    "claude": "claude",
}

# After:
BOT_ALIASES: dict[str, str] = {
    "pr-agent": "github-actions",
    "deepsource": "deepsource-io",
    "gemini": "gemini-code-assist",
    "claude": "claude",
}
```

### 3.2 Content-based PR-Agent detection

Since `github-actions[bot]` is shared by many GitHub Actions, add a secondary
filter in `parse_thread()` that detects PR-Agent-authored comments by checking
for distinctive markers in the comment body (e.g., "**PR-Agent**", "/review",
the Qodo branding text).

```python
# PR-Agent markers found in comment bodies
_PR_AGENT_MARKERS = ("pr-agent", "qodo", "/review", "/improve")

def _detect_pr_agent(body: str) -> bool:
    """Check if a comment body was generated by PR-Agent."""
    lower = body.lower()
    return any(marker in lower for marker in _PR_AGENT_MARKERS)
```

In `parse_thread()`, when `author == "github-actions"` and body matches PR-Agent
markers, override bot name to `"pr-agent"`.

### 3.3 Backward compatibility

Keep `"coderabbit": "coderabbitai"` in `BOT_ALIASES` during transition so that
`ai-guardrails comments --bot coderabbit` still works on repos that haven't
migrated yet. Remove in a future version.

Updated aliases:

```python
BOT_ALIASES: dict[str, str] = {
    "pr-agent": "github-actions",
    "coderabbit": "coderabbitai",  # deprecated, remove after migration
    "deepsource": "deepsource-io",
    "gemini": "gemini-code-assist",
    "claude": "claude",
}
```

### 3.4 Thread identification

PR-Agent's inline comments are standard GitHub review comments — the existing
GraphQL query already handles them. No query changes needed.

---

## Phase 4: Documentation & Cleanup

### 4.1 Update CLAUDE.md

- Replace all CodeRabbit references with PR-Agent
- Remove rate limit warnings (no longer applicable)
- Update "Supported bots" list: PR-Agent, Claude, Gemini, DeepSource
- Update review workflow:

  ```text
  1. Push changes, let CI run
  2. PR-Agent auto-reviews on PR open
  3. For re-review: comment /review on the PR
  4. For new suggestions: comment /improve on the PR
  ```

- Remove the "trigger CodeRabbit last" workflow step

### 4.2 Update README.md

- Update review bot integration section
- Add PR-Agent setup instructions (OPENROUTER_KEY secret)

### 4.3 Update Gemini styleguide

In `templates/.gemini/styleguide.md` and `.gemini/styleguide.md`:

- Replace "CodeRabbit" with "PR-Agent" in specialization references
- Update "Do NOT flag" section: "PR-Agent handles these" instead of "CodeRabbit handles these"

### 4.4 Update CI workflows

In `.github/workflows/claude-code-review.yml` and `templates/workflows/claude-review.yml`:

- Replace CodeRabbit references in comments with PR-Agent
- Update the "other bots handle" comment header

### 4.5 Update specs and plan docs

- `docs/specs/project_specs.xml` — update CodeRabbit parser references
- `docs/specs/review-checklist.md` — update bot list
- `docs/REVIEW_BOT_FALSE_POSITIVES.md` — update CodeRabbit section
- `docs/plans/bin-scripts-conversion.md` — update references
- `templates/CLAUDE.md.guardrails` — update bot list

### 4.6 Remove old configs

- Delete `.coderabbit.yaml` from repo root
- Delete `templates/.coderabbit.yaml`

### 4.7 Update tests

In `tests/test_status.py`:

- Change `.coderabbit.yaml` → `.pr_agent.toml` in all fixtures (lines 139, 147, 244)
- Update expected bot name: `"CodeRabbit"` → `"PR-Agent"`

In `tests/test_comments.py`:

- Add PR-Agent bot alias tests
- Add content-based detection tests (`_detect_pr_agent()`)
- Keep backward-compat tests for `"coderabbit"` alias
- Update default fixture bot from `"coderabbitai"` to `"github-actions"` where appropriate

In `tests/test_comments_cli.py`:

- Update fixture data: author `"coderabbitai[bot]"` → `"github-actions[bot]"` for new tests
- Keep some fixtures with `"coderabbitai[bot]"` for backward-compat testing

---

## Phase 5: Verify & Deploy

### 5.1 Self-test

- Run `ai-guardrails init --force` in a test repo
- Verify `.pr_agent.toml` is created (not `.coderabbit.yaml`)
- Verify `.github/workflows/pr-agent.yml` is created
- Verify `ai-guardrails status` shows PR-Agent as configured
- Run full test suite: `uv run pytest tests/ -v`

### 5.2 PR-Agent live test

- Add `OPENROUTER_KEY` secret to ai-guardrails repo
- Create `.pr_agent.toml` in ai-guardrails repo root (from template)
- Create `.github/workflows/pr-agent.yml` (from template)
- Open a test PR and verify:
  - PR-Agent posts inline suggestions on diff lines
  - Auto-generates PR description with labels
  - Responds to `/review` and `/improve` commands in comments
  - Approves PR when no issues found
  - Uses MiniMax M2.5 (check response latency and quality)

### 5.3 Consumer repo test

- Run `ai-guardrails init --force` in codeagent repo
- Verify PR-Agent config is distributed correctly
- Add `OPENROUTER_KEY` secret to codeagent repo
- Create a test PR and verify review behavior

### 5.4 Decommission CodeRabbit

- Uninstall the CodeRabbit GitHub App from the organization/repos
- Remove any CodeRabbit-related branch protection rules
- Verify no workflows reference CodeRabbit

---

## Cost Summary

| Metric | Value |
|--------|-------|
| Volume | 50 PRs/week (200/month) |
| Calls per PR | 2 (`/review` + `/improve`) |
| Total calls/month | 400 |
| Tokens per call | ~8K input + ~1.2K output |
| Model | MiniMax M2.5 via OpenRouter |
| Cost per call | ~$0.004 |
| **Monthly cost** | **~$1.50** |
| Fallback model | Kimi K2.5 (~$0.005/call) |
| CodeRabbit equivalent | Free tier (3/hr limit) or $15/seat/month |

---

## Files Changed (Complete List)

### New Files

- `templates/.pr_agent.toml` — PR-Agent config template
- `templates/workflows/pr-agent.yml` — GitHub Action workflow template

### Modified Files

- `lib/python/guardrails/init.py` — rename coderabbit → pr_agent, update installer
- `lib/python/guardrails/cli.py` — rename `--coderabbit` → `--pr-agent` CLI flags
- `lib/python/guardrails/comments.py` — update BOT_ALIASES, add content-based detection
- `lib/python/guardrails/status.py` — update _BOT_CONFIGS
- `CLAUDE.md` — replace CodeRabbit docs with PR-Agent
- `README.md` — update review bot section
- `templates/.gemini/styleguide.md` — update references
- `templates/workflows/claude-review.yml` — remove CodeRabbit refs
- `templates/CLAUDE.md.guardrails` — update bot list
- `.github/workflows/claude-code-review.yml` — remove CodeRabbit refs
- `.gemini/styleguide.md` — update references (repo root copy)
- `docs/specs/project_specs.xml` — update parser references
- `docs/specs/review-checklist.md` — update bot list
- `docs/REVIEW_BOT_FALSE_POSITIVES.md` — update CodeRabbit section
- `docs/plans/bin-scripts-conversion.md` — update references
- `tests/test_status.py` — update config file checks
- `tests/test_comments.py` — add PR-Agent alias/detection tests
- `tests/test_comments_cli.py` — update fixture data

### Deleted Files

- `.coderabbit.yaml` (repo root)
- `templates/.coderabbit.yaml`

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| PR-Agent inline comments drop for lines outside diff | Low | Built-in fallback/verification logic |
| `github-actions[bot]` identity conflicts | Medium | Content-based PR-Agent marker detection |
| AGPL-3.0 license | Low | Using, not modifying/serving — no copyleft trigger |
| MiniMax M2.5 quality regression | Low | Kimi K2.5 fallback; model string is a one-line config change |
| OpenRouter downtime | Low | Fallback model on different provider possible |
| PR-Agent structured output failures | Low | MiniMax M2.5 is frontier-class (80.2% SWE-bench) |
| Consumer repos missing OPENROUTER_KEY | Low | Clear setup docs in template comments + README |
