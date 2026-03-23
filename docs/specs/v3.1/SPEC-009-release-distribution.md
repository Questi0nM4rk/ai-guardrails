# SPEC-009: Release & Distribution

## Status: Accepted
## Version: 3.1
## Last Updated: 2026-03-20
## Depends on: SPEC-000 (Overview), SPEC-004 (CLI Commands)

---

## Problem

`ai-guardrails` must reach developers who do not have Bun installed. The
binary compiles to a self-contained executable — but that executable must
be downloadable without requiring Bun, npm, or any package manager.

The secondary problem is supply-chain integrity. A binary downloaded over
`curl | sh` with no verification is a known attack vector. A compromised
CDN or a typosquatted repository can silently replace binaries.

The tertiary problem is version management. There must be exactly one
canonical version number, read at runtime, matching the Git tag that
triggered the release. No manual synchronization, no possibility of
tag/binary mismatch.

---

## Solution

GitHub Releases as the distribution primitive. Each semver tag push triggers
a CI workflow that:

1. Runs all tests (must pass — no release from a broken build)
2. Compiles four cross-platform binaries using `bun build --compile`
3. Computes SHA-256 checksums for all binaries
4. Creates a GitHub Release with all binaries and the checksum file attached

An install script handles platform detection, tag resolution, binary download,
checksum verification, installation, and PATH hint. It requires only `sh`,
`curl`, and either `sha256sum` (Linux) or `shasum` (macOS) — present by
default on all target platforms.

Version is read directly from `package.json` at compile time by the CLI. The
CLI binary version string matches the `package.json` version, which matches the
Git tag. The flow is: `npm version` → commit + tag → push tags → release.

---

## Philosophy

1. **No Bun required to use the tool.** The install script downloads a
   self-contained binary. Users never need to install Bun, run `npm install`,
   or touch a package manager.
   WHY: The tool is for teams adopting AI guardrails — many of whom will not
   have Bun. A binary distribution removes the runtime prerequisite from the
   critical path of adoption.

2. **Checksum verification is mandatory.** The install script fails hard if
   the SHA-256 checksum does not match. There is no `--skip-verify` flag.
   WHY: A download without verification is not a secure download. The
   checksum file is signed by the same GitHub Release that provides the
   binary — an attacker would need to compromise both.

3. **Tag is the release.** The release workflow triggers only on `v*` tag
   pushes. There is no manual dispatch. There is no "release from branch."
   WHY: Deterministic release triggers prevent accidental releases. Every
   release is traceable to an exact commit via the Git tag.

4. **Tests gate the release.** The workflow runs `bun test` before building.
   A failing test prevents binary compilation. A broken test suite cannot ship.
   WHY: A released binary is a promise. Shipping a broken binary violates trust
   in a way that is difficult to recover from — users who see a broken install
   do not come back.

5. **Version from package.json, not from environment.** `src/cli.ts` reads
   version from `../package.json` at build time via a static import. The binary
   carries the version baked in.
   WHY: Reading version from `GITHUB_REF` or an environment variable would
   require passing state through the build step. A direct import from
   `package.json` is the single source of truth — it cannot drift.

6. **Cross-compilation on a single runner.** All four targets build on
   `ubuntu-latest`. Bun's cross-compilation support means no matrix of
   platform-specific runners is needed.
   WHY: Matrix builds quadruple CI time and cost. Cross-compilation on one
   runner keeps the release workflow fast (under 5 minutes total).

---

## Constraints

### Hard Constraints

- Release triggers only on `v*` tag pushes — no manual dispatch
- `bun test` must pass before any binary is built
- All four targets must build successfully — no partial release
- Checksum file covers all four binaries
- Install script requires only POSIX sh, curl, sha256sum / shasum
- Install script validates tag format (`v[0-9]*.[0-9]*.[0-9]*`) before download
- Version in CLI binary must match the `package.json` version at build time

### Soft Constraints

- Release changelog generated from git log between previous and current tag
- Install directory defaults to `~/.local/bin` (overridable via `AI_GUARDRAILS_INSTALL_DIR`)
- Install script uses `set -eu` for strict error handling
- Temp directory cleaned up on exit (via `trap cleanup EXIT`)

### Assumptions

| Assumption | If Wrong | Action |
|------------|----------|--------|
| Bun supports cross-compilation for all four targets | A target is dropped or broken | Switch that target to a native runner in a matrix job |
| GitHub Releases API remains stable | API changes | Update install script tag resolution; keep binary URLs stable via semver tags |
| `sha256sum` / `shasum` present on all target systems | Alpine or minimal container lacks `sha256sum` | Add `openssl dgst -sha256` as fallback in install script |
| `curl` present on all target systems | Minimal container lacks curl | Document `wget` alternative; provide `wget`-based install script variant |
| Users install to `~/.local/bin` or a PATH directory | Install to arbitrary location not on PATH | PATH hint is already implemented; consider `--path` flag in future |
| GitHub CDN bandwidth and uptime meets SLA | GitHub outage | Mirror to npm registry as fallback distribution channel |

---

## 1. Release Workflow

File: `.github/workflows/release.yml`

Trigger: `push` on tags matching `v*`

```
on:
  push:
    tags: ["v*"]
```

### Steps

| Step | Detail |
|------|--------|
| Checkout | `fetch-depth: 0` — full history needed for changelog generation |
| Setup Bun | `oven-sh/setup-bun@v2`, pinned to `bun-version: "1.3.10"` |
| Install deps | `bun install --frozen-lockfile` |
| Run tests | `bun test` — blocks release on failure |
| Build binaries | 4 targets (see §2) |
| Compute checksums | `sha256sum ai-guardrails-* > checksums.sha256` |
| Generate changelog | `git log --oneline` from previous tag to HEAD |
| Create Release | `gh release create` with binaries + checksum attached |

### Changelog Generation

```sh
PREV_TAG=$(git tag --sort=-version:refname | sed -n '2p')
if [ -z "$PREV_TAG" ]; then
  CHANGES=$(git log --oneline --no-decorate)
else
  CHANGES=$(git log --oneline --no-decorate "${PREV_TAG}..HEAD")
fi
echo "$CHANGES" > /tmp/changelog.md
```

First release (no previous tag): all commits become the changelog. Subsequent
releases: only commits since the previous tag.

### Permissions

```yaml
permissions:
  contents: write  # required to create GitHub Releases
```

---

## 2. Cross-Platform Builds

Build command pattern:

```sh
bun build src/cli.ts \
  --compile \
  --bytecode \
  --production \
  --target=<TARGET> \
  --outfile dist/<BINARY_NAME>
```

### Four Targets

| Binary | Target | Platform |
|--------|--------|----------|
| `ai-guardrails-linux-x64` | `bun-linux-x64` | Linux, x86-64 |
| `ai-guardrails-linux-arm64` | `bun-linux-arm64` | Linux, ARM64 (AWS Graviton, Pi) |
| `ai-guardrails-darwin-x64` | `bun-darwin-x64` | macOS, Intel |
| `ai-guardrails-darwin-arm64` | `bun-darwin-arm64` | macOS, Apple Silicon |

All four targets compile on `ubuntu-latest` via Bun's cross-compilation.
No Windows target currently — Windows support is deferred.

### Flags

- `--compile`: produces a single self-contained executable (no Bun runtime required)
- `--bytecode`: pre-compiles JavaScript to bytecode (faster startup)
- `--production`: strips dev-only paths, minifies

### Local Build (development)

```sh
bun build src/cli.ts --compile --bytecode --production --outfile dist/ai-guardrails
```

Local build produces the native-platform binary only. The `package.json` build
script uses this form.

---

## 3. Install Script

File: `scripts/install.sh`

### Usage

```sh
curl -fsSL https://raw.githubusercontent.com/Questi0nM4rk/ai-guardrails/main/scripts/install.sh | sh
```

Environment variable override:

```sh
AI_GUARDRAILS_INSTALL_DIR=/usr/local/bin \
  curl -fsSL .../install.sh | sh
```

### Platform Detection

```sh
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
```

| `uname -s` | → `PLATFORM` |
|------------|--------------|
| `linux` | `linux` |
| `darwin` | `darwin` |
| anything else | error + exit 1 |

| `uname -m` | → `ARCH` |
|------------|----------|
| `x86_64`, `amd64` | `x64` |
| `aarch64`, `arm64` | `arm64` |
| anything else | error + exit 1 |

Binary name: `ai-guardrails-${PLATFORM}-${ARCH}`

### Tag Resolution

The script resolves the latest release tag from the GitHub Releases API:

```sh
TAG=$(curl -fsSL --max-time 30 \
  "https://api.github.com/repos/${REPO}/releases/latest" | \
  grep '"tag_name"' | \
  sed 's/.*: "//;s/".*//')
```

Tag format is validated before use:

```sh
case "$TAG" in
v[0-9]*.[0-9]*.[0-9]*) ;;
*)
  printf 'Error: unexpected tag format: %s\n' "$TAG" >&2
  exit 1
  ;;
esac
```

### Download

Both the binary and `checksums.sha256` are downloaded to a temp directory:

```sh
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

curl -fsSL --max-time 300 "${DOWNLOAD_URL}/${BINARY}" -o "$TMP_BINARY"
curl -fsSL --max-time 60 "${DOWNLOAD_URL}/checksums.sha256" -o "$TMP_CHECKSUMS"
```

`--max-time 300` (5 minutes) for the binary; `--max-time 60` for the small
checksum file.

### SHA-256 Verification

```sh
EXPECTED=$(grep -F " ${BINARY}" "$TMP_CHECKSUMS" | awk '{print $1}')

if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL=$(sha256sum "$TMP_BINARY" | awk '{print $1}')
else
  ACTUAL=$(shasum -a 256 "$TMP_BINARY" | awk '{print $1}')
fi

if [ "$EXPECTED" != "$ACTUAL" ]; then
  printf 'Error: checksum mismatch!\n' >&2
  exit 1
fi
```

`sha256sum` on Linux; `shasum -a 256` on macOS. Neither requires additional
installation.

### Installation

```sh
mkdir -p "$INSTALL_DIR"
cp "$TMP_BINARY" "${INSTALL_DIR}/ai-guardrails"
chmod +x "${INSTALL_DIR}/ai-guardrails"
```

`cp` is used (not `mv`) to move the binary out of the temp directory before
the EXIT trap fires. The trap removes the temp directory — if `mv` were used,
the binary would be gone.

### PATH Hint

```sh
case ":${PATH}:" in
*":${INSTALL_DIR}:"*) ;;
*)
  printf 'Warning: %s is not in your PATH\n' "$INSTALL_DIR" >&2
  printf "Add it: export PATH=\"%s:\$PATH\"\n" "$INSTALL_DIR" >&2
  ;;
esac
```

Writes to stderr so it does not pollute piped output. Does not modify shell
profiles — that is the user's decision.

---

## 4. Version Management

### Source of Truth

`package.json` is the single source of version truth:

```json
{
  "name": "ai-guardrails",
  "version": "3.0.0"
}
```

### CLI Version Reading

```typescript
// src/cli.ts
import pkg from "../package.json";

const program = new Command()
  .name("ai-guardrails")
  .description("Pedantic code quality enforcement for AI-maintained repositories")
  .version(pkg.version);
```

The `import pkg from "../package.json"` is a static import resolved at build
time by Bun. The binary carries the version string baked in — it does not
read `package.json` at runtime.

### Release Flow

```
1. npm version patch|minor|major
   → updates package.json version
   → commits: "3.0.1"
   → creates git tag: "v3.0.1"

2. git push origin main --tags
   → pushes commit + tag

3. GitHub Actions: push on tags "v*"
   → workflow triggers
   → bun test passes
   → binaries built from the tagged commit
   → version in binary = package.json version = tag
```

`npm version` is used for its atomic behavior: it updates `package.json`,
commits the change, and creates the annotated tag in a single command. This
prevents version/tag mismatch.

### Versioning Policy

Follows semantic versioning (semver):

| Increment | When |
|-----------|------|
| `patch` | Bug fixes, no API/behavior changes |
| `minor` | New features, backward-compatible |
| `major` | Breaking changes to CLI API or config schema |

---

## Testing Strategy

The release workflow itself is not unit-tested — it is verified by execution
on every actual release.

| Test area | How |
|-----------|-----|
| Version reads correctly | `bun run src/cli.ts --version` outputs `package.json` version in CI |
| Binary is self-contained | Workflow runs the built binary without a Bun install step |
| Install script syntax | `shellcheck scripts/install.sh` in CI lint checks |
| Platform detection logic | Manual test on Linux x64, Linux arm64, macOS x64, macOS arm64 on first release |
| Checksum verification | Workflow: compute checksums, then verify them against the downloaded binary |

**Install script shellcheck:** The install script is POSIX sh and must pass
`shellcheck --shell=sh`. The `# shellcheck shell=sh` directive at the top of
the file enforces this.

---

## Evolution

| Stable While | Revisit If | Impact |
|-------------|------------|--------|
| 4-target cross-compilation on ubuntu-latest | Bun drops a target or breaks cross-compilation | Switch to native runners in a matrix build |
| GitHub Releases + npm as distribution channels | GitHub policy or npm registry issues | Add CDN mirror; both channels are independent |
| npm publish ships Linux x64 only | Platform-specific npm packages needed | Use `optionalDependencies` + `cpu`/`os` fields for per-platform packages (v3.2) |
| `npm version` as release trigger | Switching to a different version bumping tool | Update release process docs; workflow trigger stays the same |
| POSIX sh install script | Adding Windows (PowerShell) support | Provide `install.ps1` alongside `install.sh` |
| `sha256sum` / `shasum` as verifiers | Minimal base images lack both | Add `openssl dgst -sha256` as third fallback |
| Single binary per release | Plugin architecture requiring multiple binaries | Restructure release artifacts, update install script |

---

## 5. npm Publish

`ai-guardrails` is published to the npm registry as a convenience distribution
channel. npm publish runs as part of the same release workflow, after all
binaries are built and verified.

### Package Configuration (`package.json`)

```json
{
  "name": "ai-guardrails",
  "version": "3.1.0",
  "bin": {
    "ai-guardrails": "./dist/ai-guardrails"
  },
  "files": [
    "dist/ai-guardrails",
    "scripts/install.sh",
    "README.md"
  ],
  "engines": {
    "node": ">=18"
  }
}
```

`bin` points to the compiled binary. Users who install via npm get the
platform-native binary placed on PATH automatically by npm's `bin` linking.
No Bun or Node runtime is required at execution time — the binary is
self-contained.

### Publish Step (release.yml)

```yaml
- name: Publish to npm
  run: npm publish --access public
  env:
    NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

This step runs after the GitHub Release is created. The `NODE_AUTH_TOKEN`
secret is configured in the repository settings.

**Pre-condition:** `npm publish` runs only if `bun test` passes and all four
binaries build successfully. A failed test or build prevents npm publish.

### Which Binary Is Published

`package.json` `files` includes `dist/ai-guardrails` — the native-platform
binary built during CI. The release workflow builds the Linux x64 binary on
`ubuntu-latest`, which is what npm users on Linux x64 receive. macOS users
who install via npm on macOS will get the macOS binary if CI is extended to
run `npm publish` per-platform (see Evolution).

> **v3.1 scope:** npm publish provides Linux x64 by default (built on
> `ubuntu-latest`). Platform-specific npm packages (using `optionalDependencies`
> and `cpu`/`os` fields) are deferred to v3.2.

### Usage via npm

```sh
# global install
npm install -g ai-guardrails

# project dev dependency
npm install -D ai-guardrails

# npx (no install required)
npx ai-guardrails check
```

### Version Consistency

The npm package version (`package.json` `version` field) is set by `npm version`
before the tag is pushed. The same `package.json` version is read by the CLI
binary at build time and appears in `ai-guardrails --version`. All three
(npm version, binary version, git tag) are guaranteed to match.

---

## Cross-References

- SPEC-000: Technology stack (Bun >= 1.2.0, binary compilation), scope (GitHub Releases + npm publish)
- SPEC-004: `--version` flag behavior, CLI entry point `src/cli.ts`
