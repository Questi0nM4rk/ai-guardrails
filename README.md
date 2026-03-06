# AI Guardrails

The guardrails AI agents can't remove.

---

## The Problem

AI coding agents are the main contributors in modern codebases. They write
most of the code, they run most of the commits, they touch most of the files.
And they cheat.

They add `# noqa` to silence lint errors. They weaken ruff configs to make
their code pass. They `git push --force` over your branch protection. They
delete test files that fail. They `rm -rf` things they shouldn't touch.
They do all of this because **markdown rules are suggestions, not enforcement**.

`CLAUDE.md` says "don't add suppression comments." The agent adds one anyway.
Nothing stops it. Nothing even notices.

## The Solution

ai-guardrails answers a question no other tool asks:

> **Is the AI agent trying to weaken its own rules?**

trunk.io asks "are there lint errors?" eslint asks "does the code pass?"
pre-commit asks "did the hooks run?" None of them ask whether the agent is
actively undermining the system that checks it.

We do. Three layers of defense, each catching what the last one missed:

| Layer | When | What it catches |
|-------|------|-----------------|
| **Claude Code hooks** | Real-time, in-IDE | Dangerous commands, config edits, before they execute |
| **lefthook commit hooks** | Pre-commit | Suppression comments, tampered configs, lint violations |
| **CI checks** | Pull request | Config freshness, full lint + security scan |

An agent can bypass one layer. It cannot bypass all three simultaneously.

## Philosophy

1. **Everything is an error or it's ignored.** No warnings. No "acknowledged."
   If a rule exists, it blocks. If it doesn't matter, delete the rule entirely.
   Gray areas are where agents hide.

2. **Structural enforcement > documentation.** A `TreatWarningsAsErrors` flag
   does more than paragraphs of instructions. `ruff.toml` is enforcement.
   `CLAUDE.md` is a suggestion.

3. **Config tamper protection.** Generated configs are owned by the tool, not
   the developer. Every config has a SHA-256 hash header. Edit it outside
   ai-guardrails and it's flagged as tampered. The agent cannot weaken its
   own rules.

4. **Audit trail is the control.** Every exception has a reason. Every reason
   has an owner. No inline `# noqa` — all exceptions live in
   `.guardrails-exceptions.toml` with mandatory justification.

5. **One setup, every project.** Same rules everywhere. Humans and agents
   navigate between projects without re-learning. `ai-guardrails init`
   and you're done.

---

## Quick Start

```bash
# Install globally (once per machine)
uv tool install ai-guardrails
ai-guardrails install

# Initialize in any project
cd /path/to/your/project
ai-guardrails init

# Check project health
ai-guardrails status
```

## What It Does

### Auto-Detection

Point ai-guardrails at a repo and it figures out what's there:

| Language | Linter/Formatter | Detection |
|----------|-----------------|-----------|
| Python | ruff (ALL 800+ rules) | `pyproject.toml`, `*.py` |
| Shell | shellcheck, shfmt | `*.sh`, `*.bash` |
| Rust | rustfmt, clippy | `Cargo.toml` |
| Go | go vet, staticcheck | `go.mod` |
| Node | biome (ALL rules) | `package.json` |
| C++ | clang-format, clang-tidy | `CMakeLists.txt`, `*.cpp` |
| .NET | roslyn analyzers (ALL) | `*.csproj`, `*.sln` |
| Lua | stylua, luacheck | `*.lua` |

Plus universal configs for every project: `.editorconfig`, `.markdownlint.jsonc`,
`.codespellrc`, `.claude/settings.json`.

### Exception Registry

No inline suppressions. Ever. All exceptions live in one place:

```toml
# .guardrails-exceptions.toml — single source of truth
schema_version = 1

[global.ruff]
"D" = "project uses type hints as documentation"

[[file_exceptions]]
glob = "tests/**/*.py"
tool = "ruff"
rules = ["S101", "ARG001"]
reason = "Test files need asserts and fixtures"
```

Run `ai-guardrails generate` and the registry becomes tool configs. The agent
never touches `ruff.toml` directly — it proposes changes to the registry, and
a human approves.

### Suppression Comment Detection

Blocked across all languages, at commit time:

| Language | Blocked Patterns |
|----------|-----------------|
| Python | `# noqa`, `# type: ignore`, `# pragma: no cover` |
| TypeScript/JS | `// @ts-ignore`, `eslint-disable` |
| C# | `#pragma warning disable`, `[SuppressMessage]` |
| Rust | `#[allow(...)]` |
| Go | `//nolint` |
| Shell | `# shellcheck disable` |
| Lua | `--luacheck: ignore` |
| C/C++ | `// NOLINT`, `#pragma diagnostic ignored` |

Test files are excluded. For everything else: fix the code, or add it to the
exception registry with a reason.

---

## What's Built vs What's Coming

### Built (v1)

- [x] CLI: `install`, `init`, `generate`, `status`
- [x] Auto-detection for 8 languages
- [x] Config generation from exception registry (ruff.toml, lefthook.yml, etc.)
- [x] SHA-256 tamper protection on all generated configs
- [x] Claude Code PreToolUse hooks (dangerous commands, config protection)
- [x] lefthook commit hooks (format, lint, security, suppression detection)
- [x] CI workflow template (GitHub Actions)
- [x] CLAUDE.md + AGENTS.md agent instructions
- [x] `generate --check` for CI freshness validation
- [x] Pipeline + Plugin architecture with DI (extensible)
- [x] 484 tests, ruff clean, fully dogfooded

### Coming (v1.x)

- [ ] **GitHub Action** — one-liner CI: `uses: ai-guardrails/action@v1`
- [ ] **SARIF output** — `generate --check --format sarif` for GitHub code scanning
- [ ] **Hold-the-line** — only report *new* lint issues (diff against upstream)
- [ ] **Agent attribution** — auto-`--strict` mode for AI-authored commits
- [ ] **Unified allow syntax** — `# ai-guardrails-allow(ruff/E501, reason="...", expires=2026-06-01)`
- [ ] **Expiry-aware exceptions** — suppressions that auto-flag when they expire

### Coming (v2)

- [ ] **Configuration profiles** — `init --profile strict|standard|minimal`
- [ ] **`init --upgrade`** — migrate existing projects to latest configs
- [ ] **Agent-agnostic rules** — generate `.cursorrules`, `.windsurfrules`, `copilot-instructions.md`
- [ ] **Multi-agent awareness** — different strictness per agent (Claude vs Copilot vs Cursor)
- [ ] **AI behavior analytics** — track suppression attempts, rule violations over time
- [ ] **Plugin marketplace** — `uv tool install ai-guardrails-kotlin`
- [ ] **VS Code extension** — inline warnings, config freshness indicator

---

## How It Compares

| Feature | trunk.io | eslint | pre-commit | **ai-guardrails** |
|---------|----------|--------|------------|-------------------|
| Config tamper protection | No | No | No | **Yes** |
| Suppression detection | No | No | No | **Yes** |
| AI agent containment | No | No | No | **Yes** |
| Defense in depth (3 layers) | No | No | No | **Yes** |
| Hold-the-line | Yes | No | No | Planned |
| One-line CI | Yes | No | Yes | Planned |
| SARIF output | Yes | Yes | No | Planned |
| Agent attribution | No | No | No | Planned |
| Expiry-aware suppressions | No | No | No | Planned |

We steal proven UX patterns from trunk.io and convert them for AI-native
workflows. We're not competing on linter breadth — we're competing on
**making AI agents un-cheatable**.

---

## Commands

```bash
ai-guardrails install                              # Global setup
ai-guardrails install --upgrade                    # Re-run after updating

ai-guardrails init                                 # Auto-detect + generate everything
ai-guardrails init --force                         # Overwrite existing configs
ai-guardrails init --no-hooks --no-ci              # Skip optional steps
ai-guardrails init --dry-run                       # Preview without writing
ai-guardrails init --project-dir /path/to/project  # Explicit directory

ai-guardrails generate                             # Regenerate from registry
ai-guardrails generate --check                     # CI: exit 1 if stale
ai-guardrails generate --languages python,shell    # Specific languages

ai-guardrails status                               # Project health dashboard
```

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [lefthook](https://github.com/evilmartians/lefthook) (installed during `init`)

## License

MIT
