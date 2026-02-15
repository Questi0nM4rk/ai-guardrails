# PR Review Checklist - Architecture & Specs

All review bots give their best effort — the PR author decides which findings to act on.

## Bot Responsibilities

| Bot | Focus |
|-----|-------|
| CodeRabbit | Static analysis, security scanning, language conventions |
| Claude | Code duplication, clean code, modern patterns, architecture |
| Gemini | Bugs, logic errors, security, performance |
| DeepSource | Anti-patterns, OWASP, code metrics |

## Required PR Structure

Every PR MUST have:

### 1. Intent Section

- [ ] Clear problem statement or feature description
- [ ] Link to issue/spec if applicable
- [ ] Why this change is needed (business justification)

### 2. Scope Section

- [ ] List of affected components/files
- [ ] What is NOT changing (boundaries)
- [ ] Breaking changes clearly marked

### 3. Acceptance Criteria

- [ ] Testable success conditions
- [ ] Edge cases considered
- [ ] Rollback plan for risky changes

### 4. Test Plan

- [ ] How to verify the change works
- [ ] Manual testing steps if applicable
- [ ] Automated test coverage

## Architecture Rules

### Layering (MANDATORY)

```text
API Controllers → Services → Repositories → Database
       ↓              ↓            ↓
   Validation    Business     Data Access
                  Logic
```

- Controllers: HTTP handling, input validation, response formatting
- Services: Business logic, orchestration, no direct DB access
- Repositories: Data access only, no business logic

### Dependency Direction

- Dependencies flow inward (outer layers depend on inner)
- Core business logic has NO external dependencies
- Use interfaces/abstractions at boundaries

### File Organization

```text
src/
├── api/          # HTTP layer
├── services/     # Business logic
├── repos/        # Data access
├── models/       # Domain models
├── utils/        # Shared utilities
└── types/        # Type definitions
```

## Security Checklist

- [ ] No hardcoded secrets (use env vars)
- [ ] Input validation at all entry points
- [ ] AuthZ checks on every mutation
- [ ] Parameterized queries (no string concat SQL)
- [ ] No eval(), exec(), or dynamic code execution
- [ ] Sensitive data not logged

## Documentation Requirements

### When to Update Docs

- New feature → Update README
- API change → Update API docs
- Config change → Update setup guide
- Breaking change → Migration guide required

### Spec Updates

If changing behavior documented in `.claude/specs/`:

- [ ] Spec updated BEFORE code change
- [ ] Spec change reviewed separately or clearly marked

## Fail Conditions

Claude MUST REQUEST CHANGES if:

1. **No acceptance criteria** in PR body
2. **Spec mismatch** - code doesn't match documented behavior
3. **Architecture violation** - wrong layer dependencies
4. **Missing docs** - new feature without documentation
5. **Security gap** - fails security checklist
6. **Scope creep** - changes beyond stated intent
