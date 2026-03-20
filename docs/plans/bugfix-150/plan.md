# Bugfix #150 — Stale .claude/settings.json with Python hook commands

## Problem

`.claude/settings.json` still has Python-era hook commands (`uv run python -m ...`)
that point to non-existent modules. The TS binary hooks are what should be there.

## Scope

Single file fix. Regenerate `.claude/settings.json` by running `init --force`
or manually updating the hook commands.

## Fix

Run `./dist/ai-guardrails init --force --project-dir .` which will regenerate
the settings file using the claude-settings generator. This produces the correct
TS binary hook commands with the `[ ! -f ./dist/ai-guardrails ] && exit 0` guard.

Alternatively, since this is our own repo and the generator knows the correct
format, just delete `.claude/settings.json` and let init regenerate it.

Note: `.claude/settings.json` is in `.gitignore` on most projects but IS tracked
in this repo (it's part of the dogfood setup). After regeneration, commit the
updated file.

## Acceptance

- `.claude/settings.json` contains `dist/ai-guardrails hook dangerous-cmd`
- No `uv run python` references
- `Read` hook is present (protect-reads)
- Pre-commit hooks pass
