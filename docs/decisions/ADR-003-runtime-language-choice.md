# ADR-003: Runtime & language — TypeScript compiled to Bun single binaries

**Status:** accepted · **Date:** 2026-05-12 · **Supersedes:** the Python/cyclopts direction in the deleted `docs/features/SPEC-v1.md`

## Context

ai-guardrails runs on every commit (lefthook), on every agent tool call (PreToolUse/PostToolUse), and in CI.
The single most load-bearing operation is reading a base config, merging reasoned exceptions, and writing the result.
Distribution to developer machines is the #1 UX risk: the tool is worthless if it does not install in one command.

An earlier evaluation (recorded in the now-deleted SPEC-v1.md and in [ADR-002](./ADR-002-greenfield-architecture.md) §3)
weighed Python, Go, Rust, and TypeScript, and recommended *staying in Python* with `uv tool install`. That recommendation was reversed.
This ADR records the decision that actually shipped so the SPEC-* series can assume TypeScript/Bun as a given without re-litigating it.

## Decision

**Author in TypeScript; ship as Bun-compiled single binaries.** Three binaries from one source tree
(`ai-guardrails`, `ai-guardrails-hk`, `ai-guardrails-hk-cc-tools`). Modules are TypeScript classes against a typed
`Module` interface, `bun build --compile`d at install/update time. No Python in any shipping path; bash only as bootstrap glue.

## Rejected alternatives

- **Python / cyclopts (the SPEC-v1 direction).** Best config round-trip libraries, but distribution is the dealbreaker:
  requires a Python runtime + venv manager on every target, and the hook layer needed bash→Python shims
  (fragile `PYTHONPATH`, two files per hook). The strong round-trip argument (`tomlkit`/`ruamel.yaml`) lost relevance
  once the engine settled on emitting whole generated configs with hash headers rather than comment-preserving in-place edits.
- **Go / cobra.** Single static binary solves distribution, fast startup, easy contributors — but config TOML/YAML round-trip editing is materially weaker, and choosing Go forfeits sharing the typed `Module` contract and parsers with the rest of the `@questi0nm4rk/*` TypeScript stack.
- **Rust.** Best startup and a native TOML story, but contributor friction and slower iteration outweigh the performance win for a config-manipulation tool that is not on a keystroke hot path.

## Durable lessons that drove the reversal (carried from production)

- **Distribution is the product's first impression.** "Install a runtime, then a package manager, then fix PATH" loses users on step one. A single self-contained binary is the bar.
- **No shell shims that delegate to a runtime.** One executable per surface, invoked directly by lefthook / the agent harness. Shims were a recurring source of path-resolution bugs.
- **Startup time is a non-issue for this tool, but the runtime dependency is the real cost.** The decision is driven by zero-runtime distribution, not by milliseconds.
- **Stay in one language across the stack** so the `Module` interface, result unions, and rdjson/SARIF parsers are shared rather than reimplemented per binary.

The product-architecture lessons that predate this decision (review-bot discipline, git-workflow pitfalls, the DONTs catalogue) remain in [ADR-002](./ADR-002-greenfield-architecture.md). Forward-looking architecture and feature scope live in [docs/specs/SPEC-INDEX.md](../specs/SPEC-INDEX.md).
