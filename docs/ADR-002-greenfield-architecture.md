# ADR-002: AI Guardrails — Greenfield Architecture & Development Guide

> **Status: SUPERSEDED by [SPEC-v1.md](features/SPEC-v1.md) for all forward-looking decisions.**
>
> This ADR remains the authoritative source for **DONTs / lessons learned** (section 2)
> and **competitive landscape analysis** (section 7). All other sections (language choice,
> project structure, feature inventory, testing strategy) are superseded by SPEC-v1.md.
>
> Key decisions that changed since this ADR was written:
>
> | Topic | ADR-002 | SPEC-v1.md (authoritative) |
> |-------|---------|---------------------------|
> | CLI framework | click | **cyclopts** (dataclass-native, less boilerplate) |
> | Hook runner | pre-commit | **lefthook** (single binary, direct tool calls) |
> | Approach | Refactor current code | **Fresh start** in `src/ai_guardrails/` |
> | GitHub API client | 4th core component | **Separate product** (guardrails-review) |
> | Go greenfield | Presented as alternative | **Rejected** — Python confirmed |

**If we were starting over, what would we do differently?** This document captures every lesson learned, anti-pattern discovered, architectural decision, and feature roadmap for ai-guardrails — a CLI tool that enforces pedantic code quality on AI-maintained repositories. This is not a web service. It is developer tooling: a CLI, a config generator, a hook orchestrator, and a policy engine. The architecture must reflect that.

---

## Table of Contents

1. [What this project actually is](#1-what-this-project-actually-is)
2. [DONTs — Lessons from production](#2-donts--lessons-from-production)
3. [Language & framework evaluation](#3-language--framework-evaluation)
4. [Recommended architecture](#4-recommended-architecture)
5. [Project structure](#5-project-structure)
6. [Distribution & packaging](#6-distribution--packaging)
7. [Competitive landscape](#7-competitive-landscape)
8. [Complete feature inventory](#8-complete-feature-inventory)
9. [Testing strategy](#9-testing-strategy)
10. [Agent instructions template](#10-agent-instructions-template)

---

## 1. What this project actually is

ai-guardrails is **developer tooling**, not a service. Specifically, it is four things:

| Component | What it does | Analogous to |
|-----------|-------------|--------------|
| **Config generator** | Merges base templates + exception registry into tool configs | Yeoman, cookiecutter |
| **Hook orchestrator** | Installs and manages pre-commit hooks + Claude Code hooks | pre-commit, lefthook, husky |
| **Policy engine** | Enforces code quality rules via exception registry with audit trail | OPA, trunk.io |
| **GitHub API client** | Manages PR review threads across multiple bots | gh CLI extensions |

This distinction matters because:

- It has **zero runtime** — it runs at commit time, CI time, or on-demand
- It must start **instantly** (< 100ms) because it runs on every commit
- It ships **to developer machines**, not to servers — distribution is the #1 UX problem
- It manipulates **config files** (TOML, YAML, JSON) as its primary operation
- It wraps **other tools** (ruff, biome, gitleaks, etc.) rather than reimplementing them

---

## 2. DONTs — Lessons from production

### 2.1 Review Bot DONTs

**DON'T run multiple review bots simultaneously.**
We ran 4 bots (CodeRabbit, Claude, Gemini, DeepSource) on a small codebase. In one week: 56 CodeRabbit reviews, 95 Claude reviews, 19 DeepSource, 9 Gemini. The overlap was massive — Claude and DeepSource flagged the same things ruff catches locally. Gemini just wrote summaries. One bot that finds real bugs beats four that echo each other.

> Rule: One review bot max. Strong local pre-commit hooks replace the rest.

**DON'T enable auto-review on every push.**
Claude auto-reviewed every push. Each fix triggered 5 new "minor" threads. Those threads required resolution before merge. PR #37 accumulated 42 Claude reviews. The review→fix→push→review loop never converges.

> Rule: Auto-review on PR open only, never on push. Manual re-review when ready.

**DON'T batch-resolve with "Acknowledged".**
We batch-resolved review threads with "Acknowledged" to unblock merges. This defeats the entire point. We had to go back and fix 4 items we'd dismissed. Three valid resolutions only: `Fixed in <commit>`, `False positive: <reason>`, `Won't fix: <reason>`. Enforce this in tooling, not just docs.

**DON'T let `dismiss_stale_reviews: true` coexist with `strict: true`.**
Updating the branch dismisses the approval. So: get approved → rebase → approval dismissed → need new review → new review finds new things → fix → push → dismissed again. Infinite loop.

> Rule: Either disable `dismiss_stale_reviews` or don't use `strict: true`. Pick one.

### 2.2 Git Workflow DONTs

**DON'T squash-merge when you stack PRs.**
When you squash-merge PR #1, PR #2 (branched from #1) carries all of #1's pre-squash commits. Rebasing onto main causes conflicts because the squash commit is a different hash. You need `git rebase --onto origin/main <last-ancestor> <branch>` to transplant only the unique commits.

> Rule: If you stack PRs, know the `--onto` rebase pattern before you start. Or don't stack.

**DON'T create issues when asked for PRs.**
Twice we were asked to create PRs and created GitHub issues instead. Listen to exact words. "Create a PR" means a pull request with code, not an issue with a description.

**DON'T bundle more than 3-4 related fixes per PR.**
A bundled "medium/low/code-smell" PR started at 6 items. Review bots found more. Each fix triggered new comments. The PR went through 4 rounds and grew to 13 files. Smaller PRs = faster merges.

### 2.3 Codebase DONTs (from current ai-guardrails analysis)

**DON'T use module-level `Path.home()` constants.**
`_GLOBAL_INSTALL = Path.home() / ".ai-guardrails"` (`_paths.py:11`) is evaluated at import time. `patch.object(Path, "home", return_value=tmp)` after import does nothing. You must patch the constant directly: `patch("guardrails._paths._GLOBAL_INSTALL", tmp_dir)`.

> Rule: If you define module-level paths, document how to mock them. Or defer evaluation with a function.

**DON'T put 800 lines and 15 concerns in one file.**
`init.py` (807 lines) handles: project detection, Python dep detection, GitHub detection, config copying, pre-commit setup, hook installation, Claude Code hooks, registry scaffolding, config generation, CI workflows, CodeRabbit setup, PR-Agent setup, agent instructions, dry-run reporting, and main orchestration. It has 40+ private helper functions with no grouping.

> Rule: One module = one concern. Max 200 lines per module. Group related functions into classes.

**DON'T mix test classes and standalone functions in the same codebase.**
The test suite has 106 class-based tests and 95 function-based tests scattered across 21 files, with no documented convention for when to use which. DeepSource flagged every method that doesn't use `self` (PTC-W0049). Converting classes to functions was busywork across every PR.

> Rule: Use standalone test functions from the start. No classes unless you need shared fixtures/state. Decide on day one.

**DON'T use `except Exception: pass` for non-critical failures.**
`status.py:324` silently swallows all exceptions during language detection with `except Exception: pass`. `generate.py:162` catches all exceptions including `KeyboardInterrupt`. The user never knows why something failed.

> Rule: Catch specific exceptions. Log failures at `warning` level. Never bare `except Exception: pass`.

**DON'T scatter subprocess calls without abstraction.**
Subprocess calls appear in `comments.py`, `format_stage.py`, `config_ignore.py`, `init.py` — each with slightly different error handling, timeout behavior, and output capture. Testing requires mocking `subprocess.run` at 15+ call sites.

> Rule: Create a `CommandRunner` class. One place for timeouts, error handling, logging. Mock one thing in tests.

**DON'T use `print()` for CLI output and `logging` for debugging in the same module.**
`init.py` uses `print()` with ANSI colors for user output. Other modules use `logging.getLogger()`. Some use `print(file=sys.stderr)` for errors. Three output mechanisms with no consistency.

> Rule: Use `logging` everywhere. Configure a handler that renders ANSI colors for TTY, plain text for CI. One output mechanism.

**DON'T pass `dict[str, Any]` across module boundaries.**
`assemble.py:46` accepts `registry: dict[str, Any]`. `comments.py` uses plain dicts for parsed threads. All type information is lost at module boundaries. IDEs can't autocomplete, type checkers can't validate.

> Rule: Define dataclasses or TypedDicts for all structured data. `dict[str, Any]` is only acceptable inside a single function scope for JSON parsing.

**DON'T use raw `argparse.Namespace` in business logic.**
CLI handlers receive `argparse.Namespace` and do ad-hoc normalization (`args.project_type or ("all" if args.all else "")`, `_resolve_flag(args, "ci")`). Business logic can receive invalid states.

> Rule: Parse `Namespace` into a validated dataclass at the CLI boundary. Business logic never sees argparse.

**DON'T duplicate language-to-config mappings.**
`_LANG_CONFIGS` is defined in both `init.py:34` and `status.py:34` — two identical dictionaries. When a language is added, both must be updated. They will drift.

> Rule: Single source of truth. Define once, import everywhere. Or better: derive from `languages.yaml`.

**DON'T hardcode tool versions in Python source.**
`_PIP_AUDIT_REV = "v2.10.0"` is buried in `init.py:29`. Pre-commit hook versions are embedded in YAML templates. When versions drift, the only test that catches it (`test_precommit_hook_revisions_match_templates`) was added retroactively after months of silent drift.

> Rule: All pinned versions in one file (`versions.toml`). CI test validates against upstream. Add this test on day one.

**DON'T exclude your largest file from test coverage.**
`pyproject.toml:49` excludes `init.py` (807 lines — the largest file!) from coverage. The excuse is "it does subprocess calls and file I/O." That's exactly what needs testing.

> Rule: Never exclude files from coverage. If it's hard to test, that's an architecture problem. Fix the architecture.

**DON'T have shell shims that delegate to Python.**
Every hook is a bash script that sets `PYTHONPATH` and calls `python3 -m guardrails.hooks.X`. This creates two files per hook, requires bash on the system, and makes the Python module path resolution fragile.

> Rule: Use Python entry points or `console_scripts` in pyproject.toml. One file, no shim.

### 2.4 Scope & Process DONTs

**DON'T let "improvements" grow a PR.**
Review bots finding "one more thing" on each push turns a 6-item fix into a 13-file PR across 4 review rounds.

> Rule: Address the original scope only. New findings → new issue → new PR.

**DON'T treat template sync as an afterthought.**
The project's `.pre-commit-config.yaml` had `pre-commit-hooks v6.0.0` while the template shipped `v5.0.0`. 8 drifted repos across 4 template files. Silent for months.

> Rule: `test_template_versions_match_project()` is a day-one test.

---

## 3. Language & framework evaluation

### 3.1 Requirements for this project type

| Requirement | Weight | Notes |
|-------------|--------|-------|
| Fast CLI startup | HIGH | Runs on every commit via hooks |
| Config file manipulation (TOML, YAML, JSON) | HIGH | Core operation |
| Cross-platform distribution | HIGH | macOS, Linux, Windows dev machines |
| Low install friction | HIGH | `one-command install` or bust |
| GitHub API integration | MEDIUM | GraphQL + REST for comments |
| Subprocess orchestration | MEDIUM | Wrapping ruff, biome, gitleaks |
| Contributor accessibility | MEDIUM | Open source, community PRs |
| Ecosystem / library availability | MEDIUM | Pre-commit, git, etc. |

### 3.2 Language comparison

#### Python (current)

| Aspect | Assessment |
|--------|-----------|
| **Startup time** | 100-300ms (bad for hooks) |
| **TOML/YAML/JSON** | Excellent: tomllib, tomli-w, tomlkit, PyYAML, json stdlib |
| **Distribution** | Painful: requires Python runtime, pip/pipx/uv, virtualenvs |
| **Install friction** | Medium: `pipx install ai-guardrails` or `uv tool install ai-guardrails` |
| **GitHub API** | Good: subprocess to `gh` CLI, or PyGithub/httpx |
| **Subprocess** | Excellent: subprocess stdlib |
| **Contributors** | Excellent: most developers know Python |
| **CLI frameworks** | click, typer (excellent), argparse (adequate) |

**Verdict:** Good language for the logic, terrible for distribution. Current choice.

#### TypeScript/Node

| Aspect | Assessment |
|--------|-----------|
| **Startup time** | 200-500ms (worse than Python with Node.js) |
| **TOML/YAML/JSON** | JSON native; TOML via `@iarna/toml`; YAML via `js-yaml` |
| **Distribution** | Good: `npm install -g`, npx for one-shot |
| **Install friction** | Low: `npx ai-guardrails init` (no install needed) |
| **GitHub API** | Excellent: Octokit, fetch native |
| **Subprocess** | Adequate: child_process, execa |
| **Contributors** | Excellent: largest developer pool |
| **CLI frameworks** | oclif (best-in-class), commander, yargs |

**Verdict:** Best distribution story. `npx` is zero-install. But TOML manipulation is weaker, and Node.js startup is slow for hooks.

#### Rust

| Aspect | Assessment |
|--------|-----------|
| **Startup time** | < 5ms (best possible) |
| **TOML/YAML/JSON** | Excellent: toml (native!), serde_yaml, serde_json |
| **Distribution** | Excellent: single static binary, no runtime |
| **Install friction** | Low: `cargo install`, `brew install`, or download binary |
| **GitHub API** | Adequate: octocrab, reqwest |
| **Subprocess** | Excellent: std::process::Command |
| **Contributors** | Limited: smaller pool, steeper learning curve |
| **CLI frameworks** | clap (excellent), cargo-dist for releases |

**Verdict:** Best startup time and distribution. TOML is native. But contributor pool is small and development speed is slower. Tools in this space (ruff, biome) chose Rust for good reason.

#### Go

| Aspect | Assessment |
|--------|-----------|
| **Startup time** | < 10ms (excellent) |
| **TOML/YAML/JSON** | Good: BurntSushi/toml, go-yaml, encoding/json |
| **Distribution** | Excellent: single static binary via `go build` |
| **Install friction** | Low: `go install`, `brew install`, or download binary |
| **GitHub API** | Excellent: google/go-github |
| **Subprocess** | Excellent: os/exec |
| **Contributors** | Good: large pool, easy to learn |
| **CLI frameworks** | cobra (industry standard), goreleaser for releases |

**Verdict:** Best balance of speed, distribution, and contributor accessibility. Cobra + goreleaser is proven. Config manipulation is adequate but less ergonomic than Python/Rust.

### 3.3 Config file round-trip editing — the decisive factor

ai-guardrails' core operation is reading a base config, merging exceptions, and writing the result while preserving comments and formatting. This is the single most important technical capability.

| Language | TOML round-trip | YAML round-trip | Quality |
|----------|----------------|-----------------|---------|
| **Python** | `tomlkit` (preserves comments, formatting, ordering) | `ruamel.yaml` (preserves comments, formatting) | Excellent — best in any language |
| **Rust** | `toml_edit` (preserves comments, more complex API) | No good round-trip library | Good TOML, poor YAML |
| **Go** | `pelletier/go-toml` v2 (partial preservation) | `gopkg.in/yaml.v3` (no preservation) | Mediocre |
| **TypeScript** | `@iarna/toml` (basic) | `js-yaml` (no preservation) | Poor |

Python's `tomlkit` + `ruamel.yaml` are **materially better** than anything in Rust or Go. This is the strongest technical argument for staying in Python.

### 3.4 Startup time — does it actually matter?

This tool runs in two contexts:

1. **Pre-commit hooks** — where `pre-commit` framework already adds 1-3 seconds of overhead. Python's 100-150ms is noise.
2. **One-shot CLI invocations** (`init`, `generate`, `status`) — where users explicitly run a command. 150ms is imperceptible.

This is NOT a tool that runs on every keystroke (like ruff or biome). Startup time is a non-issue. The case for Rust/Go would be strong if this were a linter. It is not — it's a linter *configuration manager*.

### 3.5 Recommendation

**Primary: Python with `uv tool install` distribution** (pragmatic path)

The current Python codebase works. The problems are architectural, not linguistic. A rewrite would lose 400+ tests, 12,300 lines of battle-tested test code, and months of edge-case handling. Instead:

- Fix distribution with `uv tool install ai-guardrails` (single command, manages virtualenv)
- Migrate from argparse to **click** (reduces boilerplate ~30%, better `--flag`/`--no-flag` handling, `CliRunner` for testing, shell completion generation)
- Embed templates/configs inside the Python package (eliminate `~/.ai-guardrails/` path resolution hell)
- Fix the architecture per this document

**If starting truly greenfield: Go with Cobra**

- Single binary solves the distribution problem permanently
- `goreleaser` handles cross-platform builds + homebrew taps + GitHub releases
- Fast startup for hooks
- cobra CLI framework is proven at scale (kubectl, gh, docker CLI)
- Go is easy enough for community contributors
- **Caveat:** Go's TOML/YAML round-trip editing is significantly worse than Python's. Config generation code will be more verbose and lossy.

**Do NOT choose Rust** unless the team has Rust expertise. The contributor friction outweighs the performance benefit for a config-manipulation tool. `toml_edit` is good but the YAML story is poor.

**Do NOT choose TypeScript** despite the npm distribution advantage. Node.js startup time (200-500ms) is worse than Python for a tool that runs on every commit. The TOML ecosystem is weaker. `npx ai-guardrails init` is appealing but not worth the tradeoffs.

---

## 4. Recommended architecture

### 4.1 Architecture pattern: Pipeline + Plugin

This is not a service, so no MVC/CQRS/VSA. The right pattern for CLI tools is **Pipeline + Plugin**:

```
CLI Parser → Command Factory → Pipeline → [Plugin, Plugin, ...] → Output
```

Each subcommand is a pipeline of steps. Each step is a plugin that can be:

- Skipped (dry-run mode)
- Replaced (testing)
- Extended (new languages, new hooks)

### 4.2 Core abstractions

```
┌─────────────────────────────────────────────────┐
│                    CLI Layer                      │
│  Parses args → validated Command dataclass       │
│  Dispatches to appropriate pipeline              │
└─────────────┬───────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────┐
│                Pipeline Layer                     │
│  InitPipeline, GeneratePipeline, etc.            │
│  Orchestrates steps in order                     │
│  Handles dry-run, logging, error aggregation     │
└─────────────┬───────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────┐
│                Step Layer (Plugins)               │
│  DetectLanguages, CopyConfigs, SetupPreCommit,   │
│  InstallHooks, ScaffoldRegistry, SetupCI, ...    │
│  Each step: validate() → execute() → report()   │
└─────────────┬───────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────┐
│              Infrastructure Layer                 │
│  FileManager    - all filesystem operations      │
│  CommandRunner  - all subprocess calls           │
│  GitHubClient   - all GitHub API calls           │
│  ConfigLoader   - TOML/YAML/JSON parsing         │
│  Console        - all user-facing output         │
└─────────────────────────────────────────────────┘
```

### 4.3 Key design principles

1. **Dependency injection everywhere.** No module-level `Path.home()`. No direct `subprocess.run()`. Everything through interfaces injected at construction.

2. **Command objects at CLI boundary.** `argparse.Namespace` → `InitCommand(dataclass)` → pipeline. Business logic never imports argparse.

3. **FileManager abstraction.** Every file read/write/copy goes through `FileManager`. Dry-run mode returns "would copy X to Y" without touching disk. Tests inject an in-memory `FileManager`.

4. **CommandRunner abstraction.** Every subprocess call goes through `CommandRunner`. Tests inject a fake that returns predetermined `CompletedProcess` results. Timeouts, retries, logging all in one place.

5. **Console abstraction.** All user-facing output goes through `Console`. Auto-detects TTY for ANSI colors. Structured output for JSON mode. Tests capture output cleanly.

6. **Registry as single source of truth.** `languages.yaml` is the only place that defines language → config mappings, detection rules, template paths. Everything else derives from it. No duplicate `_LANG_CONFIGS` dicts.

### 4.4 Each pipeline step is a class

```python
@dataclass
class StepResult:
    status: Literal["ok", "skip", "warn", "error"]
    message: str

class PipelineStep(Protocol):
    def validate(self, ctx: PipelineContext) -> list[str]:
        """Return validation errors (empty = valid)."""
        ...

    def execute(self, ctx: PipelineContext) -> StepResult:
        """Run the step. May modify ctx."""
        ...
```

Benefits:

- Each step is independently testable
- Steps can be reordered, skipped, or replaced
- Dry-run calls `validate()` only
- Error aggregation happens at pipeline level
- New features = new step class, not editing a 800-line function

---

## 5. Project structure

### 5.1 For Python (refactoring current codebase)

```
ai-guardrails/
├── src/
│   └── ai_guardrails/              # PEP 621 src layout
│       ├── __init__.py              # Version only
│       ├── __main__.py              # python -m ai_guardrails
│       ├── cli.py                   # argparse → Command dataclasses → dispatch
│       │
│       ├── commands/                # Validated command dataclasses
│       │   ├── __init__.py
│       │   ├── init_cmd.py          # InitCommand dataclass
│       │   ├── generate_cmd.py      # GenerateCommand dataclass
│       │   ├── comments_cmd.py      # CommentsCommand dataclass
│       │   └── status_cmd.py        # StatusCommand dataclass
│       │
│       ├── pipelines/               # Pipeline orchestrators
│       │   ├── __init__.py
│       │   ├── init_pipeline.py     # InitPipeline (calls steps in order)
│       │   ├── generate_pipeline.py
│       │   ├── comments_pipeline.py
│       │   └── status_pipeline.py
│       │
│       ├── steps/                   # Individual pipeline steps
│       │   ├── __init__.py
│       │   ├── detect_languages.py
│       │   ├── copy_configs.py
│       │   ├── setup_precommit.py
│       │   ├── install_hooks.py
│       │   ├── scaffold_registry.py
│       │   ├── generate_configs.py
│       │   ├── setup_ci.py
│       │   ├── setup_review_bots.py
│       │   └── setup_agent_instructions.py
│       │
│       ├── generators/              # Config file generators
│       │   ├── __init__.py
│       │   ├── ruff.py
│       │   ├── biome.py
│       │   ├── markdownlint.py
│       │   ├── codespell.py
│       │   ├── pyright.py
│       │   └── allowlist.py
│       │
│       ├── hooks/                   # Pre-commit hook implementations
│       │   ├── __init__.py
│       │   ├── format_stage.py
│       │   ├── suppress_comments.py
│       │   ├── protect_configs.py
│       │   ├── config_ignore.py
│       │   └── dangerous_cmd.py
│       │
│       ├── github/                  # GitHub API layer
│       │   ├── __init__.py
│       │   ├── client.py            # GraphQL + REST via gh CLI
│       │   ├── threads.py           # Thread parsing, filtering
│       │   └── types.py             # ReviewThread, BotInfo dataclasses
│       │
│       ├── infra/                   # Infrastructure abstractions
│       │   ├── __init__.py
│       │   ├── file_manager.py      # All filesystem operations
│       │   ├── command_runner.py    # All subprocess calls
│       │   ├── config_loader.py     # TOML/YAML/JSON loading + validation
│       │   └── console.py           # User-facing output (colors, JSON)
│       │
│       ├── models/                  # Domain models
│       │   ├── __init__.py
│       │   ├── registry.py          # ExceptionRegistry, FileException, etc.
│       │   ├── language.py          # LanguageConfig, DetectionRules
│       │   └── project.py           # ProjectInfo (detected languages, paths)
│       │
│       └── constants.py             # Suppression patterns, dangerous commands
│
├── configs/                         # Base config templates (shipped with package)
│   ├── languages.yaml               # Single source of truth for languages
│   ├── versions.toml                # All pinned tool versions
│   ├── ruff.toml
│   ├── biome.json
│   ├── rustfmt.toml
│   ├── stylua.toml
│   ├── .clang-format
│   └── .editorconfig
│
├── templates/                       # Templates for generated files
│   ├── pre-commit/
│   │   ├── base.yaml
│   │   ├── python.yaml
│   │   └── ...
│   ├── workflows/
│   │   ├── check.yml
│   │   └── pr-agent.yml
│   ├── .coderabbit.yaml
│   ├── .pr_agent.toml
│   ├── guardrails-exceptions.toml
│   └── CLAUDE.md.guardrails
│
├── tests/
│   ├── conftest.py                  # Shared fixtures: fake FileManager, fake CommandRunner
│   ├── test_cli.py                  # CLI parsing → Command dataclass
│   ├── steps/
│   │   ├── test_detect_languages.py
│   │   ├── test_copy_configs.py
│   │   └── ...
│   ├── generators/
│   │   ├── test_ruff.py
│   │   └── ...
│   ├── hooks/
│   │   ├── test_format_stage.py
│   │   └── ...
│   ├── github/
│   │   ├── test_threads.py
│   │   └── ...
│   └── infra/
│       ├── test_file_manager.py
│       └── test_command_runner.py
│
├── pyproject.toml
├── CLAUDE.md
└── README.md
```

### 5.2 For Go (greenfield)

```
ai-guardrails/
├── cmd/
│   └── ai-guardrails/
│       └── main.go                  # Cobra root command
│
├── internal/
│   ├── commands/                    # Subcommand definitions
│   │   ├── init.go
│   │   ├── generate.go
│   │   ├── comments.go
│   │   └── status.go
│   │
│   ├── pipeline/                    # Pipeline orchestration
│   │   ├── pipeline.go              # Step interface, runner
│   │   └── context.go               # Shared pipeline context
│   │
│   ├── steps/                       # Pipeline step implementations
│   │   ├── detect.go
│   │   ├── configs.go
│   │   ├── precommit.go
│   │   ├── hooks.go
│   │   └── ...
│   │
│   ├── generators/                  # Config generators
│   │   ├── ruff.go
│   │   ├── biome.go
│   │   └── ...
│   │
│   ├── github/                      # GitHub API
│   │   ├── client.go
│   │   └── threads.go
│   │
│   ├── infra/                       # Infrastructure
│   │   ├── fs.go                    # FileManager interface
│   │   ├── runner.go                # CommandRunner interface
│   │   └── console.go               # Output formatting
│   │
│   └── models/                      # Domain types
│       ├── registry.go
│       ├── language.go
│       └── project.go
│
├── configs/                         # Embedded via go:embed
│   └── ...
│
├── templates/                       # Embedded via go:embed
│   └── ...
│
├── go.mod
├── go.sum
├── .goreleaser.yml                  # Cross-platform binary builds
├── CLAUDE.md
└── README.md
```

Key Go advantages:

- `go:embed` bundles configs/templates into the binary — no `find_configs_dir()` hell
- `goreleaser` produces binaries for all platforms + homebrew tap in CI
- Single binary = no `_GLOBAL_INSTALL` path resolution, no PYTHONPATH shims

---

## 6. Distribution & packaging

### 6.1 Current state (Python — problematic)

```bash
# User must have Python 3.11+, then:
python3 install.py              # pyinfra-based, installs to ~/.ai-guardrails
# OR
pip install ai-guardrails       # Requires pip, pollutes global packages
# OR
pipx install ai-guardrails      # Better, but requires pipx
```

Problems:

- 3 install methods, none are great
- `install.py` uses pyinfra (heavyweight dependency for installation)
- Shell shims bridge bash→Python (fragile PYTHONPATH)
- No single binary option

### 6.2 Recommended (Python — improved)

```bash
# Primary: uv (Astral's tool installer, fast, handles venvs)
uv tool install ai-guardrails

# Fallback: pipx
pipx install ai-guardrails

# CI: pip (in ephemeral environments)
pip install ai-guardrails
```

Changes needed:

- Drop `install.py` and pyinfra dependency entirely
- Use `[project.scripts]` entry points (already partially done)
- Hook scripts become Python entry points, not bash shims
- Package configs/templates as package data via `[tool.hatch.build]`

### 6.3 Recommended (Go — greenfield)

```bash
# Primary: homebrew
brew install ai-guardrails

# Direct binary download
curl -sSfL https://raw.githubusercontent.com/.../install.sh | sh

# Go users
go install github.com/user/ai-guardrails@latest

# CI
# Just download the binary — no runtime needed
```

Distribution via goreleaser:

- Builds for linux/amd64, linux/arm64, darwin/amd64, darwin/arm64, windows/amd64
- Publishes to GitHub Releases
- Generates homebrew formula automatically
- Creates checksums + SBOM

---

## 7. Competitive landscape

### 7.1 Tools that overlap

| Tool | What it does | Where ai-guardrails differs |
|------|-------------|---------------------------|
| **trunk.io** | Hermetic linter orchestration, hold-the-line mode | Commercial (free tier). Manages tool installation. ai-guardrails is opinionated policy, trunk is flexible orchestration |
| **MegaLinter** | 50+ linters in Docker, CI-focused | Docker-heavy, not local-first. Runs all linters, doesn't enforce policy |
| **super-linter** | GitHub Action for running linters in CI | CI-only, not local. No exception registry |
| **pre-commit** | Git hook framework | We build ON pre-commit. It's infrastructure, we're policy |
| **lefthook** | Fast git hooks in Go | Hook runner only. No config generation, no policy |
| **husky + lint-staged** | JS-ecosystem git hooks | JS-only. No multi-language. No policy |
| **reviewdog** | CI linter result reporter | Reporting only. No enforcement, no hooks |

### 7.2 Detailed competitive positioning

**trunk.io** is the closest competitor. Key differences:

- Trunk manages tool installation hermetically (downloads ruff, eslint, etc. into `.trunk/tools/`). ai-guardrails assumes tools are pre-installed.
- Trunk's "hold-the-line" mode only lints changed lines. ai-guardrails enforces on all code.
- Trunk has no concept of an exception registry. You suppress inline or in tool configs.
- Trunk is closed-source with a free tier. ai-guardrails is MIT.
- Trunk stores config in `.trunk/trunk.yaml`. ai-guardrails generates native tool configs (ruff.toml, biome.json).

**MegaLinter** runs 50+ linters in Docker with parallel execution. It's CI-focused — no local development story, no pre-commit integration, no config generation. Good for "run everything once in CI" but not for "enforce standards on every commit."

**lefthook** (Go, single binary) is the best git hooks runner. Fast, parallel, YAML config. But it only runs hooks — no config generation, no exception management, no review bot integration. ai-guardrails could potentially use lefthook instead of pre-commit as its hooks backend.

**reviewdog** (Go) pipes linter output to PR review comments. Integrates any linter with GitHub checks. But it's reporting-only — no local enforcement, no config management. Could complement ai-guardrails rather than compete.

### 7.3 What none of them do

No existing tool provides all of:

1. **Opinionated max-strictness configs** (all rules on by default)
2. **Auditable exception registry** (every deviation has a reason + expiration)
3. **Config tamper protection** (AI agents can't weaken their own rules)
4. **Multi-bot review management** (unified thread triage across CodeRabbit, Claude, PR-Agent)
5. **AI agent hook integration** (Claude Code PreToolUse hooks, dangerous command detection)

This is the moat. trunk.io is the closest competitor, but it's flexible where we're opinionated, commercial where we're open source, and has no concept of an auditable exception registry.

---

## 8. Complete feature inventory

### 8.1 Existing features (v0.2.0)

| # | Feature | Status |
|---|---------|--------|
| 1 | One-command project init with language auto-detection | Done |
| 2 | Maximally strict configs for 8 languages | Done |
| 3 | Auditable exception registry (.guardrails-exceptions.toml) | Done |
| 4 | Auto-fix + hard-block pre-commit pipeline | Done |
| 5 | Suppression comment detection and rejection | Done |
| 6 | Config protection hooks (Claude Code PreToolUse) | Done |
| 7 | Dangerous command detection hook | Done |
| 8 | Security scanning (gitleaks, semgrep, bandit, CVE audits) | Done |
| 9 | Unified PR review bot management (comments CLI) | Done |
| 10 | CI workflow generation | Done |
| 11 | CodeRabbit + PR-Agent config generation | Done |
| 12 | Project health dashboard (status command) | Done |
| 13 | Config generation from exception registry (generate command) | Done |
| 14 | Dry-run mode for all operations | Done |
| 15 | Template version sync testing | Done |

### 8.2 Near-term features (v0.3–0.5)

| # | Feature | Description | Priority |
|---|---------|-------------|----------|
| 16 | **Multi-repo orchestration** | Run init/status across N repos. Org-wide compliance report. "Which repos have stale configs?" | HIGH |
| 17 | **Exception review workflow** | When someone adds an exception, auto-create a PR or require approval. Track exception count over time. | HIGH |
| 18 | **`ai-guardrails upgrade`** | Detect config drift from latest ai-guardrails version. Offer to upgrade in-place. Versioned config generations. | HIGH |
| 19 | **Metrics dashboard** | Track violations over time: exception count, expiring soon, most-violated rules. Per-repo and per-team. | MEDIUM |
| 20 | **GitLab / Bitbucket support** | CI workflows for GitLab CI and Bitbucket Pipelines. Extend comments CLI to non-GitHub. | MEDIUM |
| 21 | **Validate resolve messages** | Enforce `Fixed in <commit>` / `False positive: <reason>` / `Won't fix: <reason>` when resolving threads. Reject "Acknowledged". | HIGH |
| 22 | **Single-binary distribution** | PyInstaller/Nuitka build for Python, or goreleaser for Go. Homebrew formula. | HIGH |
| 23 | **`ai-guardrails check`** | Unified lint orchestrator: runs all configured linters, reports unified results. The gap that trunk.io fills. One command to run ruff + biome + pyright + gitleaks and report pass/fail. | HIGH |

### 8.3 Medium-term features (v0.6–1.0)

| # | Feature | Description | Priority |
|---|---------|-------------|----------|
| 24 | **AI Agent Scorecard** | Grade each agent's output quality: "Claude introduced 3 suppressions this week, Copilot had 12 type errors caught." Data-driven agent selection. | MEDIUM |
| 25 | **Custom rule authoring** | Project-specific rules beyond linters: "no direct DB calls from controllers", "no new deps without review", naming conventions. Declarative TOML format. | MEDIUM |
| 26 | **Policy-as-Code engine** | Express policies like "all public APIs must have integration tests" or "no new dependencies without security review" as rules. | MEDIUM |
| 27 | **IDE integration** | VS Code / JetBrains extensions: inline violations, exception context, "add to registry" quick-fixes. | LOW |
| 28 | **Guardrails-native reviewer** | Review bot that understands the exception registry. "This PR disables rule X but doesn't add a registry entry." Auto-comment on PRs. | MEDIUM |
| 29 | **Language/framework packs** | Community-contributed config packs: "Django strict", "Next.js production", "Embedded C safety-critical". Opinionated starting points. | LOW |

### 8.4 Long-term / platform features (v2.0+)

| # | Feature | Description |
|---|---------|-------------|
| 30 | **Guardrails-as-a-Service** | SaaS dashboard: connect GitHub org, see every repo's compliance, push config updates centrally, approval workflows. |
| 31 | **AI Agent Sandbox** | Before an agent's changes hit your branch, run through guardrails sandbox. Score the output. Reject below threshold. |
| 32 | **Compliance mapping** | Map rules to SOC 2, ISO 27001, OWASP. "Your codebase is 94% compliant with OWASP Top 10." Auto-generate audit artifacts. |
| 33 | **Org policy inheritance** | Org-level policies cascade to all repos. Team-level overrides. Central governance with local flexibility. |
| 34 | **Stacked PR awareness** | Detect stacked branches. Warn about squash-merge conflicts. Auto-suggest `--onto` rebase commands. |

---

## 9. Testing strategy

### 9.1 Conventions (decided on day one)

- **Standalone functions only.** No test classes unless shared fixtures require it. If a test method doesn't use `self`, it should be a function.
- **One test file per module.** `src/steps/detect_languages.py` → `tests/steps/test_detect_languages.py`
- **Fixtures in conftest.py.** Shared fixtures (fake FileManager, fake CommandRunner, tmp project dirs) live in `tests/conftest.py`.
- **No mocking of internal functions.** Mock at the infrastructure boundary (FileManager, CommandRunner, GitHubClient). Never mock `_private_helpers`.
- **No coverage exclusions.** Every line of source code is covered or has a documented reason in a skip marker.

### 9.2 Test pyramid

```
                    ┌─────────┐
                    │  E2E    │  3-5 tests: full init → pre-commit run → check
                    ├─────────┤
                  ┌─┤  Integ  ├─┐  20-30 tests: pipeline with real filesystem
                  │ ├─────────┤ │
              ┌───┤ │  Unit   │ ├───┐  200+ tests: steps, generators, parsers
              │   │ └─────────┘ │   │
              └───┴─────────────┴───┘
```

### 9.3 Infrastructure fakes (not mocks)

```python
# conftest.py

class FakeFileManager:
    """In-memory filesystem for testing."""
    def __init__(self):
        self.files: dict[Path, str] = {}
        self.copied: list[tuple[Path, Path]] = []

    def write_text(self, path: Path, content: str) -> None:
        self.files[path] = content

    def copy(self, src: Path, dst: Path) -> None:
        self.copied.append((src, dst))
        if src in self.files:
            self.files[dst] = self.files[src]

    def exists(self, path: Path) -> bool:
        return path in self.files

    def read_text(self, path: Path) -> str:
        return self.files[path]


class FakeCommandRunner:
    """Predetermined subprocess results for testing."""
    def __init__(self):
        self.responses: dict[str, subprocess.CompletedProcess] = {}
        self.calls: list[list[str]] = []

    def run(self, args: list[str], **kwargs) -> subprocess.CompletedProcess:
        self.calls.append(args)
        key = " ".join(args)
        for pattern, response in self.responses.items():
            if pattern in key:
                return response
        return subprocess.CompletedProcess(args, 0, "", "")
```

Benefits:

- No `@patch` decorators
- Tests are readable (setup fake → call function → assert)
- Refactoring internal function names doesn't break tests
- Fakes can assert on call order, args, etc.

---

## 10. Agent instructions template

### CLAUDE.md for ai-guardrails development

```markdown
# ai-guardrails Development

## Build & test

- `uv run pytest tests/ -v` — run all tests
- `uv run pytest tests/steps/test_detect_languages.py -v` — run single file
- `uv run ruff check src/` — lint
- `uv run ruff format --check src/` — format check
- `uv run pyright` — type check

## Architecture

Pipeline + Plugin pattern. See docs/ADR-002-greenfield-architecture.md.

Each subcommand (init, generate, comments, status) is a pipeline of steps.
Steps are independent classes with validate() and execute() methods.
Infrastructure (filesystem, subprocess, output) is injected, never imported directly.

## DONTs (hard rules)

- NEVER use `except Exception: pass` — catch specific exceptions
- NEVER call subprocess.run directly — use CommandRunner
- NEVER read/write files directly — use FileManager
- NEVER use print() for output — use Console
- NEVER use dict[str, Any] across module boundaries — use dataclasses/TypedDict
- NEVER duplicate constants — derive from languages.yaml or versions.toml
- NEVER exclude files from test coverage
- NEVER use test classes without shared state — standalone functions only

## Adding a new language

1. Add detection rules to configs/languages.yaml
2. Add base config to configs/
3. Add pre-commit template to templates/pre-commit/
4. Add generator to src/ai_guardrails/generators/ (if language has exception support)
5. Add suppression patterns to constants.py
6. Add formatter entry to hooks/format_stage.py
7. Tests: detection, config generation, hook formatting

## Adding a new pipeline step

1. Create src/ai_guardrails/steps/my_step.py implementing PipelineStep protocol
2. Add to appropriate pipeline in pipelines/
3. Test with FakeFileManager and FakeCommandRunner in tests/steps/
```

---

## Conclusion

The current ai-guardrails codebase delivers real value — 400+ tests, 8 languages, working pre-commit integration, and a unique exception registry concept that no competitor offers. The problems are architectural: a monolithic init module, scattered infrastructure calls, inconsistent patterns, and painful distribution.

The three highest-impact changes for a greenfield or major refactor:

1. **Pipeline + Plugin architecture** — Split the 800-line `init.py` into independent, testable steps. Each step gets dependency-injected infrastructure. This is the single biggest quality improvement.

2. **Infrastructure abstractions** — `FileManager`, `CommandRunner`, `Console`. Mock at the boundary, not at 15 internal call sites. This halves the test maintenance burden.

3. **Single-binary distribution** — Whether via Go rewrite, PyInstaller, or Nuitka, the "install Python 3.11, then pip install, then fix PATH" story loses users on step one. `brew install ai-guardrails` or `curl | sh` is the target.

The exception registry with audit trail and expiration dates is the moat. No competitor has it. Everything else is execution detail.

---

## Sources & References

- [Trunk.io Code Quality Docs](https://docs.trunk.io/code-quality/linters)
- [MegaLinter vs Super-Linter](https://megalinter.io/v8/mega-linter-vs-super-linter/)
- [Lefthook — Fast git hooks manager](https://github.com/evilmartians/lefthook)
- [reviewdog — Linter output to PR comments](https://github.com/reviewdog/reviewdog)
- [Ruff Contributing / Internals](https://docs.astral.sh/ruff/contributing/)
- [Biome 2025 Roadmap](https://biomejs.dev/blog/roadmap-2025/)
- [Rust CLI Packaging Guide](https://rust-cli.github.io/book/tutorial/packaging.html)
- [GoReleaser Rust Support](https://goreleaser.com/customization/builds/rust/)
- [Typer Alternatives Comparison](https://typer.tiangolo.com/alternatives/)
- [Cross-Compiling Rust CLI Crates Statically](https://blog.pkgforge.dev/cross-compiling-10000-rust-cli-crates-statically)
