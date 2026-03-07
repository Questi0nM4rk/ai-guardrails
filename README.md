# AI Guardrails

The guardrails AI agents can't remove.

---

## The Problem

AI coding agents are the main contributors in modern codebases. They write
most of the code, run most of the commits, touch most of the files.
And they cheat.

They add `# noqa` to silence lint errors. They weaken ruff configs to make
their code pass. They `git push --force` over your branch protection. They
delete test files that fail. They `rm -rf` things they shouldn't touch.
They do all of this because **markdown rules are suggestions, not enforcement**.

`CLAUDE.md` says "don't add suppression comments." The agent adds one anyway.
Nothing stops it. Nothing even notices.

Your five-team startup just shipped an AI-first product. Three agents are
committing around the clock. Who is auditing what they do? Who enforces the
rules across every repo, every team, consistently, without drift?

## The Solution

ai-guardrails answers a question no other tool asks:

> **Is the AI agent trying to weaken its own rules?**

trunk.io asks "are there lint errors?" eslint asks "does the code pass?"
pre-commit asks "did the hooks run?" None of them ask whether the agent is
actively undermining the system that checks it.

We do. Three rings of defense, each catching what the last one missed:

| Ring | When | What it catches |
|------|------|-----------------|
| **Agent hooks** | Real-time, in-process | Dangerous commands, config edits — before they execute |
| **Commit hooks** | Pre-commit | Suppression comments, tampered configs, lint violations |
| **CI gate** | Pull request | Config freshness, hold-the-line diff, agent-strict enforcement |

An agent can bypass one ring. It cannot bypass all three simultaneously.

---

## Philosophy

**1. Everything is an error or it's ignored.**
No warnings. No "acknowledged." If a rule exists, it blocks. If it doesn't
matter, delete the rule entirely. Gray areas are where agents hide.

**2. Structural enforcement beats documentation.**
A `TreatWarningsAsErrors` flag does more than paragraphs of instructions.
`ruff.toml` is enforcement. `CLAUDE.md` is a suggestion.

**3. Config tamper protection.**
Generated configs are owned by the tool. Every config has a SHA-256 hash
header. Edit it outside ai-guardrails and it's flagged as tampered. The agent
cannot weaken its own rules.

**4. Audit trail is the control.**
Every exception has a reason. Every reason has an owner. Every owner is on
record. No silent suppressions anywhere in the stack.

**5. Domain rules cascade, project rules stay bounded.**
Org-level policies lock down what matters most. Teams customize within their
budget. Projects customize within the team's budget. No project can opt out
of domain-level rules. No agent can expand its own permissions.

**6. Agents propose. Humans approve.**
An agent can write `ai-guardrails-allow(ruff/E501, reason="...")` in code.
It cannot approve the exception. A human commits the registry entry.
The exception expires on a date. When it does, CI fails until renewed or fixed.

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

# Check for new lint issues (hold-the-line)
ai-guardrails check
```

---

## Governance Model

Rules cascade top-down. Each level can lock rules so levels below cannot override them.

```
Organization (org.toml)          ← domain rules — locked, non-negotiable
        |
        v inherits + locks
Team (.guardrails-team.toml)     ← team rules — per directory or repo
        |
        v inherits + locks
Project (.guardrails-exceptions.toml)  ← project rules — within budget
        |
        v registers into
Exception Store (.guardrails/exceptions/)  ← queryable, one record per exception
        ^
        | inline suppressions register here too
  # ai-guardrails-allow(rule, reason, expires, ticket)
```

### Domain Level (`~/.guardrails/org.toml` or distributed via your internal package)

```toml
[profile]
default = "standard"
allowed = ["strict", "standard"]    # teams cannot go below standard

[locked_rules]
# These CANNOT be overridden at team or project level
"gitleaks"        = { reason = "secrets scanning is non-negotiable" }
"ruff/S603"       = { reason = "no subprocess in production code" }
"semgrep/auth"    = { reason = "auth checks always enforced" }
```

### Team Level (`.guardrails-team.toml`)

```toml
[team]
name = "backend"
owners = ["alice", "bob"]
profile = "strict"
exception_budget = 10              # max 10 active project-level exceptions
owns = ["src/api/", "src/models/"]

[locked_rules]
"ruff/ARG002" = { reason = "Protocol pattern required in all services" }

[overrideable_rules]
"ruff/E501"   = { allow_project_override = true }
```

### Project Level (`.guardrails-exceptions.toml`)

```toml
schema_version = 1

[profile]
inherit = "team"    # or "org", or explicit name

[[file_exceptions]]
glob = "src/cli.py"
tool = "ruff"
rules = ["PLR0913"]
reason = "CLI commands legitimately accept many flags"
expires = 2026-09-01
approved_by = "alice"
ticket = "PROJ-42"
```

### Inline (in code, agent-proposable, human-approved)

```python
# The old way — silent, untracked, blocks at commit:
x = some_long_url  # noqa: E501

# The new way — registered, queryable, expires:
x = some_long_url  # ai-guardrails-allow(ruff/E501, reason="URL cannot be wrapped", expires=2026-09-01)
```

The hook validates reason is non-empty and expiry is in the future, then
registers the exception in the store. The agent can write the comment;
only a human can approve it by committing the corresponding registry entry.

---

## Profile System

Profiles compose the enforcement posture for a team or project.

| Profile | Suppressions | Expiry required | Ticket required | Agent commits | Exception budget |
|---------|-------------|-----------------|-----------------|---------------|-----------------|
| `strict` | Block all | Yes | Yes | Require review | 0 — no exceptions |
| `standard` | Block noqa, allow `ai-guardrails-allow` | Yes | No | Standard rules | 20 per project |
| `minimal` | Warn only | No | No | Standard rules | Unlimited |

Custom profiles are TOML files in your org's internal package:

```toml
# profiles/fintech-strict.toml
[inherits]
from = "strict"

[overrides]
exception_budget = 0
require_ticket = true
require_dual_approval = true   # two owners must approve any exception
```

---

## Exception Protocol

No exception is silent. Every exception is tracked, owned, and expirable.

```bash
# Propose a project-level exception (agent or human)
ai-guardrails allow ruff/E501 \
  --glob "src/generated/*.py" \
  --reason "Generated protobuf output, cannot reformat" \
  --expires 2026-09-01 \
  --ticket PROJ-99

# Query the exception store
ai-guardrails query                          # all active exceptions
ai-guardrails query --rule ruff/E501         # all E501 exceptions
ai-guardrails query --expired                # expired — need cleanup or renewal
ai-guardrails query --team backend           # backend team exceptions
ai-guardrails query --approved-by nobody     # proposed but not yet approved
ai-guardrails query --scope domain           # across all repos (requires API)

# Generate refreshed configs from current registry state
ai-guardrails generate

# CI: fail if any exception is expired or configs are tampered
ai-guardrails generate --check
```

---

## Team Features

```bash
# Team overview
ai-guardrails team list
# backend   8/10 exceptions used  owners: alice, bob   profile: strict
# frontend  3/20 exceptions used  owners: carol        profile: standard

# Team status
ai-guardrails team status --team backend
# 8/10 exception budget used
# 2 exceptions expire in < 30 days — renew or fix
# 1 exception proposed, awaiting approval

# Approve a proposed exception (must be a team owner)
ai-guardrails approve <exception-id>

# Team activity report
ai-guardrails report --team backend --days 30
# Commits:            142 total  (89 AI-authored, 53 human)
# Hook bypasses attempted: 7    (all blocked)
# New exceptions proposed: 3    (2 approved, 1 pending)
# Expired exceptions:      1    (fixed in commit a1b2c3d)
# Config tampering:        0
```

---

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

### Multi-Agent Rules Files

One source of truth. All agent instruction files generated from it:

```bash
ai-guardrails generate
# Writes:
#   AGENTS.md                         ← canonical, all agents read this
#   CLAUDE.md                         ← Claude Code specific additions
#   .cursorrules                      ← Cursor
#   .windsurfrules                    ← Windsurf
#   .github/copilot-instructions.md  ← GitHub Copilot
# All hash-protected. Edit one, regenerate all.
```

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

The `ai-guardrails-allow` syntax is the only permitted path. It requires a
reason, an expiry date, and registers in the queryable store.

### Hold-the-Line (`ai-guardrails check`)

Like trunk.io's algorithm, adapted for AI-native workflows — with a baseline
system for gradual adoption in legacy codebases.

```bash
# Snapshot all current issues so they're ignored going forward
ai-guardrails baseline create

# Only report NEW issues introduced since the baseline
ai-guardrails check

# See everything including legacy (for visibility)
ai-guardrails check --all

# Bring a specific rule back into full enforcement, with a deadline to fix legacy
ai-guardrails baseline promote --rule ruff/E501 --deadline 2026-09-01

# Targeted: full scan for one rule only
ai-guardrails check --rule ruff/E501

# Zero tolerance — baseline ignored (AI-authored commits use this automatically)
ai-guardrails check --strict

# SARIF output for GitHub code scanning
ai-guardrails check --format sarif > results.sarif
```

**Three baseline states per rule:**

| State | What it means | CI behaviour |
|-------|--------------|-------------|
| `legacy` | Existed at snapshot time | Ignored in `check` |
| `burn-down` | Committed to fix by deadline | Fail if count rises or deadline passes |
| `promoted` | Fully re-enforced | Any instance fails CI |

```bash
ai-guardrails baseline status
# ruff/E501      legacy     142 issues  (no deadline)
# ruff/PLR0913   burn-down   23 issues  deadline: 2026-09-01  -3/month  ON TRACK
# ruff/S101      promoted     0 issues  fully enforced since 2026-04-01
```

If the commit author is Claude, Copilot, Cursor, or another known agent,
`--strict` activates automatically. No new issues. No baseline exemptions.
Human commits get standard hold-the-line treatment.

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

### Coming (v2 — AI-team governance)

- [ ] **Governance hierarchy** — org → team → project rule cascade with locking
- [ ] **Locked rules** — domain-level rules no project can override
- [ ] **Configuration profiles** — `strict / standard / minimal`, composable, inheritable
- [ ] **Multi-agent rules files** — generate `.cursorrules`, `.windsurfrules`, `copilot-instructions.md` from one source
- [ ] **Agent attribution** — detect AI-authored commits, auto-apply `--strict`
- [ ] **Hold-the-line** — only report new issues vs upstream merge-base
- [ ] **GitHub Action** — `uses: Questi0nM4rk/ai-guardrails-action@v1`
- [ ] **SARIF output** — native GitHub PR annotations, no bot required
- [ ] **`ai-guardrails-allow` syntax** — inline suppression with reason + expiry, registered in store
- [ ] **Queryable exception store** — `ai-guardrails query --expired`, `--team`, `--rule`
- [ ] **Team features** — ownership, exception budgets, approval workflow
- [ ] **`ai-guardrails report`** — agent behavior analytics per team
- [ ] **`init --upgrade`** — migrate existing projects to latest configs

### Later (v3+)

- [ ] **Plugin marketplace** — `uv tool install ai-guardrails-kotlin`
- [ ] **VS Code extension** — inline warnings, config freshness indicator
- [ ] **Self-hosted API** — `query --scope domain` across all repos
- [ ] **Compliance export** — SOC 2 / ISO 27001 audit trail export

---

## How It Compares

| Feature | trunk.io | CodeRabbit | pre-commit | **ai-guardrails** |
|---------|----------|------------|------------|-------------------|
| Config tamper protection | No | No | No | **Yes** |
| Suppression detection | No | No | No | **Yes** |
| AI agent containment | No | No | No | **Yes** |
| Defense in depth (3 rings) | No | No | No | **Yes** |
| Governance hierarchy (org/team/project) | No | No | No | **v2** |
| Locked domain rules | No | No | No | **v2** |
| Queryable exception store | No | No | No | **v2** |
| Team budgets + approvals | No | No | No | **v2** |
| Hold-the-line | Yes | No | No | **v2** |
| Agent attribution + auto-strict | No | No | No | **v2** |
| One-line CI | Yes | No | Yes | **v2** |
| SARIF output | Yes | No | No | **v2** |
| Expiry-aware suppressions | No | No | No | **v2** |
| Multi-agent rules files | No | No | No | **v2** |
| AI behavior analytics | No | No | No | **v2** |

We steal proven UX from trunk.io and convert it for AI-native workflows.
We're not competing on linter breadth — we're competing on
**making AI agents un-cheatable at org scale**.

---

## Commands

```bash
# Setup
ai-guardrails install                              # global: Claude Code hooks, PATH
ai-guardrails install --upgrade                    # re-run after updating
ai-guardrails init                                 # per-project: detect, generate, hook
ai-guardrails init --profile strict                # explicit profile
ai-guardrails init --force                         # overwrite existing configs
ai-guardrails init --upgrade                       # refresh configs, preserve exceptions

# Generate & Check
ai-guardrails generate                             # regenerate from registry
ai-guardrails generate --check                     # CI: exit 1 if stale or expired exceptions
ai-guardrails generate --check --format sarif      # SARIF for GitHub code scanning

# Check (hold-the-line)
ai-guardrails check                                # new issues only vs upstream
ai-guardrails check --strict                       # zero tolerance
ai-guardrails check --format sarif > results.sarif # for CI upload

# Status
ai-guardrails status                               # project health dashboard

# Exceptions
ai-guardrails allow ruff/E501 --reason "..." --expires 2026-09-01
ai-guardrails approve <exception-id>               # team owner only
ai-guardrails query                                # all active exceptions
ai-guardrails query --expired                      # need cleanup
ai-guardrails query --team backend
ai-guardrails query --rule ruff/E501

# Teams
ai-guardrails team list
ai-guardrails team status --team backend

# Reports
ai-guardrails report --days 30                     # project: agent activity
ai-guardrails report --team backend --days 30      # team: agent activity
```

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [lefthook](https://github.com/evilmartians/lefthook) (installed during `init`)
- [gh](https://cli.github.com/) (optional, for branch protection setup)

## License

MIT
