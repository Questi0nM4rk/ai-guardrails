# Git Workflow Rules

## Pushing

- NEVER push without asking the human first
- Complete ALL changes locally before pushing (all files, tests passing, lint clean)
- Batch related changes into logical commits — push all at once

## Review Bots

| Bot | Focus | Trigger |
|-----|-------|---------|
| PR-Agent | Semantic code review, inline suggestions | **Auto** on PR open; manual `/review`, `/improve` |
| CodeRabbit | Static analysis, security, language conventions | **Manual only** (`@coderabbitai review`) |
| Claude | Code quality, architecture, modern patterns | **Manual** (`@claude` in PR comment) |

- Address ALL review feedback before pushing again — fix every comment, push once
- Trigger CodeRabbit last as final gate before merge

## Review Thread Resolution Protocol

Every review comment must be categorized and resolved properly:

| Category | Action | Comment Format |
|----------|--------|----------------|
| Actionable | Fix the code | `Fixed in <commit-hash>` |
| False positive | Explain why it's wrong | `False positive: <reason>` |
| Won't fix | Justify the decision | `Won't fix: <reason>` |
| Nitpick/style | Fix it anyway | `Fixed in <commit-hash>` |

**Never:**

- Resolve with just "Acknowledged" or "Noted"
- Batch-resolve without reading each comment
- Dismiss actionable feedback as "out of scope"

The `ai-guardrails comments --resolve` command enforces this: messages
must start with a valid category prefix (`Fixed in`, `False positive:`,
or `Won't fix:`). Messages without a proper category are rejected.

## Commits

- Conventional commit messages: `feat:`, `fix:`, `refactor:`, `chore:`, `test:`, `docs:`
- Don't create fix-on-fix commits — squash locally before pushing
- Max 3-4 related fixes per PR

## Branch Cleanup

- Delete branches after PR merge (both local and remote)
- When using worktrees, clean up worktree AND branch together: `git worktree remove <path> && git branch -d <name>`
- Run `git fetch --prune` periodically to remove stale remote-tracking refs
