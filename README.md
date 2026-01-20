# AI Guardrails

Reusable AI workflow utilities for any project. Extract PR review tasks,
set up git hooks, and configure AI guardrails for Claude Code.

## Features

- **PR Task Extraction**: Parse CodeRabbit review comments into actionable JSON
- **Git Hooks**: Pre-commit, pre-push, and auto-format hooks for AI development
- **Claude Code Guardrails**: Strict settings to prevent dangerous operations
- **Multi-language Support**: Templates for .NET, Rust, Lua, C++, Python, Node.js

## Installation

```bash
# Clone the repo
git clone https://github.com/Questi0nM4rk/ai-guardrails.git
cd ai-guardrails

# Install globally
./install.sh

# Or install gh-pr-review extension (for PR task extraction)
gh extension install agynio/gh-pr-review
```

## Quick Start

### 1. Initialize a Project

```bash
cd /path/to/your/project

# Set up CLAUDE.md and Claude Code settings
ai-guardrails-init

# Set up git hooks and pre-commit
ai-hooks-init --pre-commit
```

### 2. Extract PR Review Tasks

```bash
# Fetch PR reviews and extract tasks
gh pr-review review view --repo owner/repo --pr 123 --unresolved \
  | ai-review-tasks --pretty

# Filter by severity
ai-review-tasks --severity major reviews.json
```

## Commands

### ai-guardrails-init

Set up AI guardrails for Claude Code in your project.

```bash
ai-guardrails-init                # Auto-detect project type
ai-guardrails-init --type rust    # Specify project type
ai-guardrails-init --force        # Overwrite existing CLAUDE.md
```

Creates:

- `CLAUDE.md` - Project-specific guidance for Claude Code
- `~/.claude/settings.json` - Guardrails (permissions, hooks)
- `.ai-guardrails/` - Local context directory

### ai-hooks-init

Initialize git hooks for AI-driven development.

```bash
ai-hooks-init              # Install to project
ai-hooks-init --global     # Install globally
ai-hooks-init --pre-commit # Also install pre-commit config
```

Hooks installed:

- `dangerous-command-check.sh` - Blocks dangerous bash commands
- `pre-commit.sh` - Runs tests before commits
- `pre-push.sh` - Full test suite + security scan before push
- `auto-format.sh` - Auto-formats files after edits

### ai-review-tasks

Extract actionable tasks from CodeRabbit PR reviews.

```bash
# From stdin
gh pr-review review view --pr 1 | ai-review-tasks

# From file
ai-review-tasks reviews.json

# Pretty print
ai-review-tasks --pretty reviews.json

# Filter by severity (critical, major, minor, suggestion)
ai-review-tasks --severity major reviews.json
```

Output format:

```json
{
  "tasks": [
    {
      "id": "task-001",
      "type": "inline",
      "file": "src/main.rs",
      "line": 42,
      "message": "Fix memory leak in buffer handling",
      "severity": "major",
      "analysis": "The buffer is allocated but never freed...",
      "suggested_fix": "- let buf = alloc();\n+ defer!(free(buf));"
    }
  ],
  "summary": {
    "total": 15,
    "inline": 12,
    "outside_diff": 2,
    "nitpick": 1,
    "by_severity": {
      "critical": 0,
      "major": 5,
      "minor": 8,
      "suggestion": 2
    }
  }
}
```

## Templates

### CLAUDE.md Templates

Language-specific templates in `templates/`:

- `CLAUDE.md.dotnet` - .NET / C# projects
- `CLAUDE.md.rust` - Rust / Cargo projects
- `CLAUDE.md.lua` - Lua projects
- `CLAUDE.md.cpp` - C/C++ / CMake projects

### Pre-commit Config

`templates/pre-commit-config.yaml` includes:

- **Security**: gitleaks, detect-private-key
- **Python**: ruff, bandit
- **TypeScript**: biome, tsc
- **C#/.NET**: dotnet format, dotnet build
- **Shell**: shellcheck, shfmt
- **Markdown**: markdownlint

### Claude Code Settings

`templates/settings.json.strict` configures:

- Blocked operations (rm -rf /, sudo, secrets access)
- Pre-tool hooks for dangerous command detection
- Post-tool hooks for auto-formatting

## Directory Structure

```text
ai-guardrails/
├── bin/
│   ├── ai-review-tasks        # PR task extraction CLI
│   ├── ai-hooks-init          # Git hooks setup
│   └── ai-guardrails-init     # Project setup
├── lib/
│   ├── hooks/                 # Hook scripts
│   │   ├── dangerous-command-check.sh
│   │   ├── pre-commit.sh
│   │   ├── pre-push.sh
│   │   └── auto-format.sh
│   └── python/
│       └── coderabbit_parser.py  # CodeRabbit comment parser
├── templates/
│   ├── pre-commit-config.yaml    # Multi-language pre-commit
│   ├── settings.json.strict      # Claude Code guardrails
│   └── CLAUDE.md.*               # Language templates
├── install.sh
└── README.md
```

## Requirements

- Python 3.10+
- [GitHub CLI (gh)](https://cli.github.com/)
- [gh-pr-review extension](https://github.com/agynio/gh-pr-review)

Optional:

- [pre-commit](https://pre-commit.com/) - For running pre-commit hooks

## License

MIT
