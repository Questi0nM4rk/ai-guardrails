## Claude Code Rules

- Read `CLAUDE.md` at the start of every session before making changes.
- Use the MCP servers and skills defined in `.claude/settings.json`.
- All Bash tool calls are subject to `PreToolUse` hooks — do not bypass them.
- Never use `--no-verify` or `-c commit.gpgsign=false` unless explicitly authorized.
- Never push to remote without explicit user approval in the current session.
- Use `TodoWrite` for multi-step tasks; mark items complete as you go.
- When blocked by a hook, investigate the root cause — do not work around it.
