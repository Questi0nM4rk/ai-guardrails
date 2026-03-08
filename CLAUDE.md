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

- `ts-rewrite` — integration branch (treat as main for this rewrite)
- Feature PRs target `ts-rewrite`, NOT `main`
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

## DONTs

- NEVER push directly to `ts-rewrite` or `main` — open a PR
- NEVER use `any` — `unknown` + Zod at boundaries
- NEVER non-null assert (`!`) — handle undefined explicitly
- NEVER import infra directly in domain code — inject via context
- NEVER use `--reporter=json` for biome — use `--reporter=rdjson`
- NEVER use mypy — use pyright (`mypy --output json` is explicitly unstable)
- NEVER use luacheck as primary — use selene (has JSON output, luacheck does not)
- NEVER `extends` (except Error subclasses) — composition only

## AI Guardrails - Code Standards

guardrails-review auto-reviews every PR push. Fix every finding. Even nitpicks.

### Tools

```bash
ai-guardrails comments --pr <N>                                    # List unresolved threads
ai-guardrails comments --pr <N> --resolve <THREAD_ID> "Fixed."    # Resolve with reply
guardrails-review context --pr <N>                                 # Structured review state
```

### Review Thread Resolution

| Category | Comment Format |
|----------|---------------|
| Fixed | `Fixed in <commit-hash>` |
| False positive | `False positive: <reason>` |
| Won't fix | `Won't fix: <reason>` |

Fix all locally, push once per review round. Never push without asking.

### Pre-commit Workflow

```
biome --write → re-stage → typecheck → gitleaks → codespell → markdownlint → commit
```
