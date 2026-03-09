---
name: review-pr
description: "Review a PR for bugs, security, and logic issues."
argument-hint: "<PR number>"
allowed-tools: "Bash,Read,Glob,Grep,Agent"
---

Review PR #$ARGUMENTS in this repository.

## Step 0: Load Context

```bash
git show claude-reviewer/memory:MEMORY.md 2>/dev/null || echo "No project memory yet — fresh project."
cat .cc-review.yaml 2>/dev/null || echo "No project config — using defaults."
```

Store both the memory and config. Use them throughout the review.

## Step 1: Gather PR

```bash
gh pr view $ARGUMENTS --json title,body,author,baseRefName,headRefName,files
gh pr diff $ARGUMENTS
```

## Step 2: Triage

If the diff is trivial (version bumps, config-only, dependency updates, markdown edits), approve immediately:
```bash
cat > /tmp/review-payload.json <<'EOF'
{"body":"LGTM — trivial change, no review needed.","event":"APPROVE","comments":[]}
EOF
gh api repos/{owner}/{repo}/pulls/$ARGUMENTS/reviews --method POST --input /tmp/review-payload.json
```

## Step 3: Slop Research

If `.cc-review.yaml` has `slop_detection: true` (or is absent — default is true):
Deploy the `slop-researcher` agent with the PR diff and changed file list. Keep its watchlist in context for Step 5.

## Step 4: Understand the Change

Before reviewing line-by-line:
- Read the PR title and description to understand intent
- Identify which areas of the codebase are touched
- Cross-reference with memory for known patterns in these areas
- If the diff is large (>500 lines), use subagents to review different files in parallel

## Step 5: Review the Changes

Apply the review-guidelines skill. Load language-specific references matching the PR's languages.

For each file changed, check for:
- Bugs: null refs, off-by-one, race conditions, incorrect logic
- Security: injection, auth bypass, secrets in code, insecure defaults
- Data loss: missing transactions, incorrect deletes, broken migrations
- Breaking changes: API contract violations, removed public members
- AI slop: patterns flagged by the slop researcher

Apply `.cc-review.yaml` overrides:
- Skip `ignore_paths` files
- Skip `known_patterns` findings
- Apply `instructions` context

## Step 6: Post the Review

Post exactly ONE review using a SINGLE `gh api` call. Build `/tmp/review-payload.json`:

```json
{
  "body": "Review summary",
  "event": "APPROVE or REQUEST_CHANGES",
  "comments": [
    {"path": "src/file.ts", "line": 42, "body": "Issue description and fix."}
  ]
}
```

Submit:
```bash
gh api repos/{owner}/{repo}/pulls/$ARGUMENTS/reviews --method POST --input /tmp/review-payload.json
```

Rules for comments array:
- `line` must exist in the diff (NEW file side)
- `path` must match exactly the diff file path
- Findings outside the diff go in the review `body`

## Step 7: Update Memory

If you learned new patterns, false positives, or conventions — save via memory-save command.

## Rules

- Post ONE review via ONE `gh api` call — never multiple calls
- ALL inline comments inside the `comments` array — never separate
- NEVER use `gh pr review` — always `gh api repos/{owner}/{repo}/pulls/N/reviews`
- Be concise — no filler, no padding
- Trivial diffs → approve immediately
