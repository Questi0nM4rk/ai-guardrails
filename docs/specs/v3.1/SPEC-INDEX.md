# AI Guardrails v3.1 Spec Suite Index

## Status: Draft
## Last Updated: 2026-03-20

All specs follow the spec-driven development format: Problem → Solution → Philosophy (with WHYs) → Constraints → Domain Sections → Testing Strategy → Evolution → Cross-References.

## Specs

| Number | Domain | Status | Description |
|--------|--------|--------|-------------|
| SPEC-000 | Overview | Draft | Constitution — project purpose, philosophy, technology stack, scope |
| SPEC-001 | Architecture | Draft | Module structure, core interfaces, DI pattern, design patterns |
| SPEC-002 | Config System | Draft | Schema hierarchy, merge rules, Zod validation, profiles |
| SPEC-003 | Linter System | Draft | LinterRunner interface, 12 runners, language plugins, detection |
| SPEC-004 | CLI Commands | Draft | 8 commands, flags, exit codes, output formats |
| SPEC-005 | Hook System | Draft | PreToolUse hooks, check engine, shell AST, rule groups, flag aliases |
| SPEC-006 | Config Generators | Draft | 8 generators, hash headers, language gates, merge strategy |
| SPEC-007 | Baseline System | Draft | Fingerprinting, hold-the-line, snapshot/check contract |
| SPEC-008 | Interactive Init | Draft | InitModule interface, wizard, 13 modules, dependency graph |
| SPEC-009 | Release & Distribution | Draft | Cross-platform builds, install script, versioning |

## Notes

- Old specs (pre-v3.1) in `docs/specs/` root are superseded by this suite
- SPEC-000 is the constitution — all other specs reference it
- Each spec covers exactly one domain (Iron Law 4)
