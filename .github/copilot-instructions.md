# AI Agent Rules

## Core Principles

- Never push directly to main — always open a PR
- Never commit secrets, credentials, or .env files
- Run tests before committing: all tests must pass
- Fix ALL review findings including nitpicks
- Never batch-resolve review threads without reading each one

## Git Workflow

- Conventional commit messages: feat:, fix:, refactor:, chore:, test:, docs:
- Create feature branches: git checkout -b feat/<name>
- Keep commits focused — one logical change per commit

## Code Quality

- No any — use unknown + type narrowing at boundaries
- No non-null assertions (!) — handle undefined explicitly
- No commented-out code — delete it or open an issue
- No TODO without an issue reference

## Security

- Never log secrets, tokens, or passwords
- Never eval() user input
- Never trust user-provided paths without sanitization

## GitHub Copilot Specific

- This project uses strict linting — suggestions must pass lint and typecheck
- Follow conventional commit format for all commit messages
- Check existing patterns in the codebase before suggesting new abstractions
