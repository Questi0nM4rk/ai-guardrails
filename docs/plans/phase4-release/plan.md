# Phase 4: Release Infrastructure

## Scope for overnight session

### 4.1 Version management
- Read version from package.json instead of hardcoding in cli.ts
- Use `npm version patch|minor|major` for bumping (creates git tag automatically)

### 4.2 Release workflow
- GitHub Actions workflow triggered on tag push (v*)
- Builds binary for Linux x64
- Creates GitHub Release with binary as asset
- Uploads SHA-256 checksum file

### 4.5 Changelog generation
- Script or workflow step that generates CHANGELOG.md from conventional commits
- Uses git log between tags

## Phases (2 parallel + 1 sequential)

### Phase A: Version from package.json (small)
- `src/cli.ts:14` — read version from package.json instead of hardcoding "3.0.0"
- Pattern: `import pkg from "../package.json"` or read at runtime
- Files: src/cli.ts

### Phase B: Release workflow (medium)
- `.github/workflows/release.yml` — triggered on tag push v*
- Steps: checkout → setup-bun → install → build → create release → upload binary + checksum
- Files: .github/workflows/release.yml (new)

### Phase C: Changelog script (small, after A+B)
- Simple script that runs `git log --oneline v{prev}..v{current}` grouped by conventional prefix
- Or use a lightweight tool
- Files: scripts/changelog.ts or inline in workflow
