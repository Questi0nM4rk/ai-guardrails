# E2E Fixtures — Phase Overview

## Dependency Graph

```
Phase 1 (fixtures)  ──┐
                      ├──→ Phase 3 (steps + features) ──→ Phase 4 (binary validation)
Phase 2 (merge)     ──┘
```

Phases 1 and 2 are independent — run in parallel.
Phase 3 depends on both. Phase 4 depends on 3.

## Phases

| # | Name | Description | Depends on |
|---|------|-------------|------------|
| 1 | fixture-files | Static fixture projects for all 8 languages (bare + preconfigured) | none |
| 2 | config-merge | Deep merge strategy for init when existing configs found | none |
| 3 | steps-and-features | BDD step definitions + .feature files using feats | 1, 2 |
| 4 | binary-validation | Build binary, run full E2E, fix what breaks | 3 |
