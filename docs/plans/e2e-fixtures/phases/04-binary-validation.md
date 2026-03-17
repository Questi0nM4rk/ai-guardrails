# Phase 4: Binary Validation

## Task

Build the binary, run the full E2E suite, fix any issues discovered.

## Dependencies

- Phase 3 (steps and features exist)

## Steps

1. `bun run build` — compile binary
2. `bun test tests/e2e/` — run E2E suite against compiled binary
3. Fix any failures:
   - Runner output parsing issues
   - Config generation edge cases
   - Init flow bugs on fresh projects
   - Fingerprint instability (if exposed)
4. Re-run until all scenarios pass for installed tools

## Acceptance criteria

- `bun run build` succeeds
- `bun test tests/e2e/` passes for all installed tools
- No regressions in existing 589 unit tests
- `bun test && bun run typecheck && bun run lint` all clean
