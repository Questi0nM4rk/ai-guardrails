# Review Bot False Positives

Track false positives from review bots so we can tune their configs.
Each entry documents the bot, the finding, and why it's a false positive.

## DeepSource

### Line too long (88 chars)

- **Finding:** `line too long (92 > 88 characters)` and similar
- **Frequency:** 7 occurrences on PR #33
- **Why false positive:** Our ruff.toml enforces a 100-char line limit. DeepSource
  uses PEP8's default 88-char limit. Ruff is our source of truth for line length.
- **Fix:** Configure DeepSource to use 100-char limit, or exclude line-length checks
  since ruff already handles this.
- **Status:** FIXED in PR #34 — `max_line_length = 100` in `.deepsource.toml`.

### Starting a process with partial executable

- **Finding:** `Starting a process with a partial executable path`
- **Frequency:** 1 occurrence on PR #33 (comments.py `_run_gh`)
- **Why false positive:** The `gh` CLI must be called by name (not full path). This is
  already in our per-file ruff exceptions (S607). DeepSource duplicates the ruff check
  without respecting our exceptions.
- **Fix:** Exclude S607/subprocess-security rules from DeepSource for files that have
  per-file ruff exceptions.

### Cyclomatic complexity

- **Finding:** `run_comments has a cyclomatic complexity of N`
- **Frequency:** 1 occurrence on PR #33
- **Why false positive:** Already in per-file ruff exceptions (PLR0911). The function
  is a CLI dispatch that handles multiple action types — complexity is inherent.
- **Fix:** Align DeepSource complexity thresholds with ruff config, or exclude files
  that have per-file exceptions.
- **Status:** FIXED in PR #34 — `cyclomatic_complexity_threshold = "high"` in `.deepsource.toml`.

### Method doesn't use class instance (self)

- **Finding:** `Method doesn't use the class instance (self)`
- **Frequency:** 5 occurrences on PR #33 (test files)
- **Why false positive:** Standard pytest pattern — test methods are grouped in classes
  for organization, not for instance state. `self` is unused by design.
- **Fix:** Exclude test files from this check, or configure DeepSource to recognize
  pytest class patterns.

### Missing docstrings on test methods

- **Finding:** `Docstring missing for test_*`
- **Frequency:** 5 occurrences on PR #33
- **Why false positive:** Test names are self-documenting per project convention
  (e.g. `test_resolve_all_with_body`). Adding docstrings to every test method adds
  noise without value.
- **Fix:** Exclude test files from docstring requirements in DeepSource config.
- **Status:** FIXED in PR #34 — `skip_doc_coverage` includes `"nonpublic"` in `.deepsource.toml`.

## CodeRabbit

No systematic false positives identified. CodeRabbit findings have been accurate.

## Claude

### Praise/architecture comments not auto-resolved

- **Finding:** Claude posts "Architecture: excellent" comments that require manual
  resolution even though they're positive feedback, not issues.
- **Frequency:** 6 occurrences on PR #33
- **Why friction:** Positive feedback threads still count as "unresolved" and must be
  individually closed.
- **Fix:** Consider configuring Claude to not post positive-only comments, or to
  auto-resolve them.

### "Content duplication with main CLAUDE.md" on template files

- **Finding:** Claude flags the `CLAUDE.md.guardrails` template as duplicating content
  from the repo's own `CLAUDE.md`, complaining about DRY violations.
- **Frequency:** 3 occurrences per push on PR #34 (repeated across 3 review rounds)
- **Why false positive:** The template gets appended to *consumer* project CLAUDE.md
  files via `ai-guardrails init`. Consumer projects don't have the ai-guardrails repo's
  own CLAUDE.md. There is no duplication in practice.
- **Fix:** Claude's review prompt needs context that template files are installed into
  other projects, not used within the same repo.

### "Philosophical inconsistency" between template rules and repo philosophy

- **Finding:** Claude flags the review bot rules ("fix every comment") as conflicting
  with the "hard stops only" philosophy, arguing that review comments are "suggestions"
  not "hard stops."
- **Frequency:** 1 occurrence per push on PR #34 (repeated 3 times)
- **Why false positive:** Review bots ARE the hard stops. They enforce standards
  automatically, and agents must comply with their findings. This is the philosophy
  working as intended, not a contradiction.
- **Fix:** Claude's review prompt needs to understand that review bots are enforcement
  tools, not advisory suggestions.

### "Tool may not apply to consumer projects"

- **Finding:** Claude flags `ai-guardrails comments` tool documentation as potentially
  inapplicable to consumer projects.
- **Frequency:** 1 occurrence per push on PR #34 (repeated 3 times)
- **Why false positive:** If the template is installed, the project has ai-guardrails
  installed. The tool is available by definition.
- **Fix:** Claude needs context that templates are only installed by the `ai-guardrails
  init` command, which also installs the CLI tools.

## Gemini

No systematic false positives identified. Gemini findings have been accurate.

---

## guardrails-review (inline code annotations, PR #95, 2026-03-08)

The inline code annotation comments (as opposed to the fullbody round reviews) on PR #95
were largely false positives. The bot scans the full cumulative diff from `main` to HEAD,
so it re-reviews files from commits that were already addressed in earlier rounds.

### SPEC-001 library table row duplication

- **Finding:** "Lefthook vs node script distinction unclear in library table"
- **Why false positive:** The table had already been split into three separate rows
  (`Pre-commit hooks`, `Claude Code hooks runtime`, `Hook target projects`) in an earlier
  round before the bot ran. The bot was reviewing an older commit's diff hunk.

### CLAUDE.md build description

- **Finding:** "Binary requires Bun runtime — document it"
- **Why false positive:** The build command uses `bun build --compile`, which embeds the
  Bun runtime into a standalone binary. The binary does NOT require Bun on target machines.
  The bot confused `--compile` (standalone) with a plain `bun run` invocation.

### SPEC-003 `isAvailable` parameter name

- **Finding:** "`isAvailable(runner)` should be `isAvailable(commandRunner)` for consistency"
- **Why false positive:** The parameter was already named `commandRunner` in the actual
  implementation. The bot was reviewing a spec example from an older commit.

### `ruff.toml` missing `exclude` array

- **Finding:** "`exclude = [\"tests/fixtures\"]` was removed, restore it"
- **Why false positive:** The `exclude` array was already present in `ruff.toml` at the
  time the bot ran. The bot was diffing against a state that predated the current file.

### `tests/runners/clippy.test.ts` missing `clippyRunner.run` test

- **Finding:** "Add a test for `clippyRunner.run`"
- **Why false positive:** The test already existed at `describe("clippyRunner.run")` in
  the same file. The bot reviewed a diff hunk that showed an older file state.

### Pattern

All five false positives share the same root cause: the bot performs a cumulative diff
from `main` to HEAD and posts inline comments anchored to diff hunks, some of which
represent intermediate states that were already fixed. The fullbody round review comments
(written separately) were accurate and addressed real issues.
