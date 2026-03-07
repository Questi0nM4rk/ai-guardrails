<!-- ai-guardrails:hash:sha256:375ce79ab761e2bb5aef7fd363e80964ad3ff2a99c8a8a50995d9916ec981cbf -->
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

## GitHub Copilot Rules

- These rules supplement the base agent rules above.
- This file is auto-loaded by GitHub Copilot as `.github/copilot-instructions.md`.
- Do not suggest inline suppression comments — use the exception registry instead.
- Prefer explicit type annotations over `Any` in all suggested code.
- When suggesting test code, follow the project's TDD conventions in `CLAUDE.md`.
