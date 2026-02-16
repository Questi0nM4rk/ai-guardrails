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

## Gemini

No systematic false positives identified. Gemini findings have been accurate.
