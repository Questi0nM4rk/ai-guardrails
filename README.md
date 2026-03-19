# AI Guardrails

The guardrails AI agents can't remove.

---

## The Problem

AI coding agents are the main contributors in modern codebases. They write
most of the code, run most of the commits, touch most of the files.
And they cheat.

They add `# noqa` to silence lint errors. They weaken configs to make their
code pass. They `git push --force` over your branch protection. They `rm -rf`
things they shouldn't touch. They do all of this because **markdown rules are
suggestions, not enforcement**.

`CLAUDE.md` says "don't add suppression comments." The agent adds one anyway.
Nothing stops it. Nothing even notices.

## The Solution

ai-guardrails answers a question no other tool asks:

> **Is the AI agent trying to weaken its own rules?**

Three rings of defense, each catching what the last one missed:

| Ring | When | What it catches |
|------|------|-----------------|
| **Agent hooks** | Real-time, in-process | Dangerous commands, config edits — before they execute |
| **Commit hooks** | Pre-commit | Suppression comments, tampered configs, lint violations |
| **CI gate** | Pull request | Config freshness, hold-the-line diff, agent-strict enforcement |

An agent can bypass one ring. It cannot bypass all three simultaneously.

---

## Quick Start

```bash
# Initialize any project
bunx ai-guardrails init

# Check for new lint issues (hold-the-line)
bunx ai-guardrails check
```

That's it. `init` detects your languages, generates linter configs, installs
commit hooks, and wires PreToolUse hooks into Claude Code.

---

## Features

### 9 Language Plugins, 12 Linter Runners

Auto-detects what's in your repo and configures the right tools:

| Language | Linters / Formatters |
|----------|---------------------|
| TypeScript / JavaScript | biome (ALL rules) |
| Python | ruff (ALL 800+ rules), pyright |
| Rust | clippy, rustfmt |
| Go | golangci-lint |
| Shell | shellcheck, shfmt |
| C / C++ | clang-tidy, clang-format |
| Lua | selene, stylua |
| .NET / C# | dotnet-format, roslyn analyzers |

### Hold-the-Line Baseline

Gradual adoption in any codebase — without fixing everything upfront:

```bash
# Snapshot current issues — they're ignored going forward
bunx ai-guardrails snapshot

# Only new issues introduced since the snapshot fail CI
bunx ai-guardrails check

# Zero tolerance — baseline ignored
bunx ai-guardrails check --strict
```

### Config Tamper Protection

Every generated config carries a SHA-256 hash header. Edit it outside
ai-guardrails and it's flagged as tampered. The agent cannot weaken its own rules.

### Suppression Comment Detection

Blocked across all languages at commit time:

| Language | Blocked patterns |
|----------|-----------------|
| Python | `# noqa`, `# type: ignore`, `# pragma: no cover` |
| TypeScript/JS | `// @ts-ignore`, `eslint-disable` |
| Rust | `#[allow(...)]` |
| Go | `//nolint` |
| C# | `#pragma warning disable`, `[SuppressMessage]` |
| Shell | `# shellcheck disable` |
| Lua | `--luacheck: ignore` |
| C/C++ | `// NOLINT`, `#pragma diagnostic ignored` |

### PreToolUse Hook System

Intercepts Claude Code tool calls in real time:

| Hook | What it blocks |
|------|---------------|
| `dangerous-cmd` | `rm -rf`, `git push --force`, destructive ops |
| `protect-configs` | Writes to ai-guardrails-managed config files |
| `protect-reads` | Reads of sensitive files (keys, secrets) |
| `suppress-comments` | Adding suppression comments via Edit/Write |

---

## CLI Commands

```bash
bunx ai-guardrails init              # detect languages, generate configs, install hooks
bunx ai-guardrails check             # run all linters, hold-the-line vs baseline
bunx ai-guardrails check --strict    # zero tolerance (no baseline exemptions)
bunx ai-guardrails snapshot          # create/update baseline
bunx ai-guardrails status            # project health dashboard
bunx ai-guardrails generate          # regenerate managed configs
bunx ai-guardrails report            # lint summary report
bunx ai-guardrails hook <type>       # invoke a hook manually (dangerous-cmd, protect-configs, …)
bunx ai-guardrails completion        # shell completion (bash/zsh/fish)
```

---

## Configuration

Config lives in `.ai-guardrails/config.toml`:

```toml
[profile]
name = "standard"   # strict | standard | minimal

[languages]
enabled = ["typescript", "python", "rust"]

[ignore]
paths = ["dist/", "node_modules/", "*.generated.ts"]
```

### Profiles

| Profile | Suppressions | Exception budget |
|---------|-------------|-----------------|
| `strict` | Block all | 0 — no exceptions |
| `standard` | Block `noqa`-style, allow documented exceptions | 20 per project |
| `minimal` | Warn only | Unlimited |

---

## Philosophy

**1. Everything is an error or it's ignored.**
No warnings. No "acknowledged." If a rule exists, it blocks. Gray areas are where agents hide.

**2. Structural enforcement beats documentation.**
A config with `TreatWarningsAsErrors` does more than paragraphs of instructions.

**3. Config tamper protection.**
Generated configs are owned by the tool. The agent cannot weaken its own rules.

**4. Agents propose. Humans approve.**
An agent can write a suppression comment with a reason and expiry. A human commits the
approval. The exception expires on a date.

---

## Development

```bash
bun install
bun test                 # 896 tests across 51 files
bun run build            # compile → dist/ai-guardrails
bun run lint             # biome check src/ tests/
bun run typecheck        # tsc --noEmit
```

Runtime: Bun >= 1.2.0. No Node.

---

## License

MIT
