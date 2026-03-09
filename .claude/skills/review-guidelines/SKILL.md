---
description: "Code review guidelines, language-specific patterns, and quality standards for the cc-review bot. Covers C#/.NET, TypeScript, and Python review patterns with severity classification."
globs: "**/*"
alwaysApply: true
---

# Review Guidelines

## Read When

| File | Read When |
|------|-----------|
| `references/csharp-patterns.md` | PR contains `.cs`, `.csproj`, `.sln` files |
| `references/typescript-patterns.md` | PR contains `.ts`, `.tsx`, `.js`, `.jsx` files |
| `references/python-patterns.md` | PR contains `.py` files |

Load only the references matching the PR's languages. Do not load all three.

## Review Iron Laws

1. **Single review block** — ONE `gh api` call with all comments in the `comments` array
2. **Every finding needs a failure scenario** — "When X happens, Y breaks because..."
3. **Verify before reporting** — Read surrounding code, check if issue is handled elsewhere
4. **No false positives from config** — Check `.cc-review.yaml` `known_patterns` and project memory
5. **In-diff comments only** — If a finding can't map to a diff line, put it in the review body
6. **No severity labels in strict mode** — Every finding is a required change

## Review Classification (Standard Mode)

| Action | When |
|--------|------|
| Request changes | Bugs, security vulnerabilities, data loss, breaking changes, AI slop |
| Approve + comment | Performance in hot paths, missing validation on external input |
| Approve silently | No issues found, or only style/preference differences |

## What to Ignore (All Modes)

- Formatting, whitespace, naming style
- Missing comments or docs
- "I would have done it differently" opinions
- Test coverage (unless tests are actively broken)
- Patterns listed as known false positives

## DON'Ts

- Do NOT dump every pattern from references — only flag patterns you actually see in the diff
- Do NOT use generic descriptions ("this could be improved") — be specific
- Do NOT report the same issue on multiple lines — pick the most representative line
- Do NOT pad reviews with praise ("great PR overall") — get to the point
