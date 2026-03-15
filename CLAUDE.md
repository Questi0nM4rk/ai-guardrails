# AI Guardrails v3 — TypeScript Rewrite

## Build & Test

```bash
bun install
bun test                    # run all tests
bun test --watch            # watch mode
bun run lint                # biome check src/ tests/
bun run typecheck           # tsc --noEmit
bun run build               # compile single binary → dist/ai-guardrails
```

## Architecture

Pipeline + Plugin with DI. Full spec: `docs/specs/` — read before implementing anything.

| Spec | Content |
|------|---------|
| SPEC-000 | Overview, MVP scope, tech stack |
| SPEC-001 | Architecture, interfaces, module structure |
| SPEC-002 | Config system (machine → project → inline) |
| SPEC-003 | Linter system, all runners, language plugins |
| SPEC-004 | CLI commands, flags, exit codes |
| SPEC-005 | Hooks (Claude Code PreToolUse + lefthook) |
| SPEC-006 | Battle-tested defaults |
| SPEC-007 | Implementation guide, phases, testing conventions |
| SPEC-008 | Per-language tool reference |

## Branch Strategy

- `main` — default branch; all PRs target `main`
- Each feature maps to one or more spec sections

## Module Layout (`src/`)

```
src/
  cli.ts                    # Entry point — Commander wiring
  commands/                 # One file per CLI command
  runners/                  # One file per linter (LinterRunner interface)
  languages/                # Language plugins (compose runners)
  generators/               # Config file generators
  config/                   # Zod schemas, loader, defaults
  models/                   # Pure domain types (LintIssue, BaselineEntry…)
  pipelines/                # Pipeline orchestrators
  steps/                    # Reusable pipeline steps
  hooks/                    # Hook implementations (dangerous-cmd, protect-configs…)
  writers/                  # Output serializers (SARIF, text)
  infra/                    # FileManager, CommandRunner, Console (injected, never direct)
  utils/                    # Pure functions — hash, fingerprint, glob
  templates/                # Static data files (ruff.toml defaults, CI YAML…)
```

## Key Constraints

- Bun >= 1.2.0 runtime
- `strict: true`, `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess` — no exceptions
- No `any` — use `unknown` + Zod at boundaries
- No `!` non-null assertions — handle `undefined` explicitly
- No barrel files (`index.ts`) — explicit named imports
- No inheritance — `implements` only, composition over inheritance
- No `new Service()` in domain code — DI via PipelineContext
- Fakes not mocks — `FakeFileManager`, `FakeCommandRunner`, `FakeConsole`

## NON-NEGOTIABLE: NO HACKS, NO WORKAROUNDS

**I WILL NOT ACCEPT ANY HACK, ANY WORKAROUND, OR ANY IMPROPER WAY OF WORKING WITH THIS CODEBASE.**

If there is a correct, proper way to implement something and you do it any other way — without
first asking and explaining why — that is a failure. This means:

- No regex where AST parsing exists
- No string matching where typed data exists
- No monkeypatching where proper interfaces exist
- No "TODO: fix later" shortcuts shipped as real code
- No duplicating logic that should be shared
- No bypassing type safety with casts, `as`, or `any`

If the proper solution is more complex or out of scope, **stop and ask**. Do not silently take
the easier wrong path. The cost of asking is zero. The cost of wrong architecture compounds.

## DONTs

- NEVER push directly to `main` — open a PR
- NEVER use `any` — `unknown` + Zod at boundaries
- NEVER non-null assert (`!`) — handle undefined explicitly
- NEVER import infra directly in domain code — inject via context
- NEVER use `--reporter=json` for biome — use `--reporter=rdjson`
- NEVER use mypy — use pyright (`mypy --output json` is explicitly unstable)
- NEVER use luacheck as primary — use selene (has JSON output, luacheck does not)
- NEVER `extends` (except Error subclasses) — composition only

## AI Guardrails - Code Standards

This project uses [ai-guardrails](https://github.com/Questi0nM4rk/ai-guardrails) for pedantic code enforcement.
Pre-commit hooks auto-fix formatting, then run security scans, linting, and type checks.
cc-review auto-reviews every PR on open. Interactive via `@cc-review` comments.

### Review Bot (cc-review)

cc-review auto-reviews on PR open. It posts REQUEST_CHANGES with inline comments
for bugs, security issues, and logic errors. Supports 4 modes: standard, strict,
bug-hunt, simplify (via labels or workflow_dispatch). Interactive via `@cc-review`.

**Fix every review comment that is not a false positive. Even nitpicks. Even style.**

- Fix ALL findings locally, then push once. One push per review round.
- Ask the human before pushing. Explain what changed.

**Do not:**

- **Never dismiss a review comment because it's "just a nitpick."**
  Nitpicks are how code quality compounds. A style fix takes 30 seconds. Ignoring
  it means the next reviewer wastes time on the same thing. Fix it and move on.

- **Never resolve a thread without fixing it or explaining why it's a false positive.**
  Resolving a thread means "this is handled." If it's not handled, it's lying to the
  reviewer. If you disagree with a finding, reply with a reason — don't silently resolve.

- **Never batch-resolve threads you haven't read.**
  Each thread exists because a reviewer flagged something. Read it, decide if it's real
  or false positive, then act. `--resolve-all` is for documented false positives you've
  already triaged (e.g. a bot that always flags pytest `self`), not for blindly closing.

- **Never push after each individual fix.**
  Every push triggers all bots. Fixing 5 comments in 5 pushes creates 5 full review
  cycles of noise. Fix everything locally, push once.

- **Never skip a false positive without documenting it.**
  If a bot repeatedly flags something that's wrong, that's useful information for tuning
  the bot's config. Log it so it can be fixed upstream. Resolve with a reference to
  where it's documented.

### Pre-commit Workflow

```
biome --write → re-stage → typecheck → gitleaks → codespell → markdownlint → commit
```
