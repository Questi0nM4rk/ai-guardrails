# AI Agent Rules

This file is managed by [ai-guardrails](https://github.com/Questi0nM4rk/ai-guardrails).
Do not edit manually — changes will be overwritten on the next `ai-guardrails generate`.

## Code Quality

- All suppression comments (`# noqa`, `# type: ignore`, `# pylint: disable`, etc.) are
  tracked. Do not add them without a documented reason in `.guardrails-exceptions.toml`.
- Every exception must be proposed with a reason and approved by a human reviewer.
- Run `ai-guardrails generate --check` after any change to detect config drift.

## Security

- Never add hard-coded secrets, credentials, API keys, or tokens to any file.
- All subprocess invocations must go through the project's approved command abstraction.
- Do not disable security linters (`bandit`, `semgrep`) for entire files.

## Commit Standards

- Follow conventional commit format: `feat:`, `fix:`, `refactor:`, `chore:`, `test:`, `docs:`
- Do not commit directly to `main` or `master`.
- Run pre-commit hooks before committing (`lefthook install` if not already set up).
- Batch related fixes into one commit — avoid fix-on-fix micro-commits.

## Exception Protocol

- To suppress a lint finding, add an entry to `.guardrails-exceptions.toml`, not inline.
- Every exception entry requires: `rule`, `glob`, `reason`, `proposed_by`, `expires`.
- Exceptions with `approved_by = null` are pending — they must not be merged to main.
