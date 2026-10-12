# Guide

Reference for the commands, configuration, language support and hooks of `ai-guardrails`.
The README has the short version.

## Commands

Run the binary `ai-guardrails`. During development use `bun run src/cli.ts` or `bunx @questi0nm4rk/ai-guardrails`.

```bash
ai-guardrails init              # detect languages, generate configs, install hooks
ai-guardrails check             # run all linters, report only issues new since the baseline
ai-guardrails check --strict    # ignore the baseline, every issue counts
ai-guardrails snapshot          # create or update the baseline
ai-guardrails status            # project health summary
ai-guardrails generate          # regenerate managed configs
ai-guardrails generate --check  # verify managed configs, exit 1 on missing or tampered files (CI)
ai-guardrails report            # recent check run history
ai-guardrails allow             # add an inline allow rule to .ai-guardrails/config.toml
ai-guardrails query             # list files where a rule is allowed
ai-guardrails completion        # shell completion (bash, zsh, fish)
```

There is no `ai-guardrails hook` command. Hooks run as a separate binary, see "Hooks".

## Hooks

`init` writes `.claude/settings.json` with a PreToolUse and a PostToolUse entry.
Both call the binary `ai-guardrails-hk-cc-tools`, which must be on `PATH`.
`scripts/install.sh` installs it next to `ai-guardrails`.
Build it from source with `bun run build:hk-cc`.

The binary reads one Claude Code hook event as JSON on stdin and writes a decision on stdout.
It is built with [hook-kit](https://github.com/Questi0nM4rk/hook-kit) and parses shell commands with [shell-ast](https://github.com/Questi0nM4rk/shell-ast).
Rules are in `src/check/rules/`.

| Rule | Event | What it does |
| --- | --- | --- |
| dangerous commands | PreToolUse, Bash | Escalates `rm -rf`, `git push --force` and similar to the human (`ask`) |
| protect configs | PreToolUse, Edit/Write | Escalates writes to managed config files |
| protect reads | PreToolUse, Read | Escalates reads of sensitive files such as `.env` |
| suppress comments | PostToolUse, Edit/Write | Flags suppression comments added by the edit |

The decision is `ask`, not `deny`. The human sees the reason and answers.
Managed files, managed paths, protected read paths and disabled rule groups are set in `.ai-guardrails/config.toml`.

## Hold-the-line baseline

```bash
ai-guardrails snapshot          # current issues are recorded and ignored from now on
ai-guardrails check             # only issues introduced after the snapshot fail
ai-guardrails check --strict    # baseline ignored
```

## Config tamper detection

Every generated config starts with a header line `ai-guardrails:sha256=<hash>`.
The hash covers the body below the header.
`ai-guardrails generate --check` recomputes it and reports `tampered: <file>` on a mismatch.

What this does not cover:

- `ai-guardrails check` does not run this comparison. Only `generate --check` does.
- The hash is a plain SHA-256 with no key. Anyone who edits the file can recompute it.
- A file with no header is treated as user-owned and is not checked.
- Checked on 2026-10-12: after stripping the header, and after recomputing the hash, `generate --check` no longer lists the edited `biome.jsonc`.

The hash catches accidental edits and agents that do not know about it. It does not stop an agent that does.

## Suppression comments

The commit hook and the PostToolUse rule look for these patterns:

| Language | Patterns |
| --- | --- |
| Python | `# noqa`, `# type: ignore`, `# pragma: no cover` |
| TypeScript, JavaScript | `// @ts-ignore`, `eslint-disable` |
| Rust | `#[allow(...)]` |
| Go | `//nolint` |
| C# | `#pragma warning disable`, `[SuppressMessage]` |
| Shell | `# shellcheck disable` |
| Lua | `--luacheck: ignore` |
| C, C++ | `// NOLINT`, `#pragma diagnostic ignored` |

## Languages and runners

`src/languages/` has eight language plugins plus a universal one.
`src/runners/` has runners for biome, tsc, ruff, pyright, clippy, golangci-lint, shellcheck, shfmt, clang-tidy, selene, dotnet build, codespell and markdownlint.
A runner whose tool is not installed is skipped and the skip is printed.

## Configuration

`.ai-guardrails/config.toml`:

```toml
[profile]
name = "standard"   # strict | standard | minimal

[languages]
enabled = ["typescript", "python", "rust"]

[ignore]
paths = ["dist/", "node_modules/", "*.generated.ts"]
```

| Profile | Suppressions | Exception budget |
| --- | --- | --- |
| `strict` | Block all | 0 |
| `standard` | Block `noqa`-style, allow documented exceptions | 20 per project |
| `minimal` | Warn only | Unlimited |

## Design rules

1. Every rule is an error or it is ignored. There are no warnings.
2. Structure beats documentation. A config that treats warnings as errors does more than a paragraph in `CLAUDE.md`.
3. Generated configs belong to the tool. Edits are flagged, with the limits above.
4. Agents propose, humans approve. An exception carries a reason and an expiry date.
