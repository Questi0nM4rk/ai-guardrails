#!/bin/sh
# shellcheck shell=sh
set -eu

# Usage: curl -fsSL https://raw.githubusercontent.com/Questi0nM4rk/ai-guardrails/main/scripts/install.sh | sh
#
# Environment variables:
#   AI_GUARDRAILS_INSTALL_DIR  — installation directory (default: ~/.local/bin)
#
# Installs three binaries:
#   ai-guardrails              — main CLI
#   ai-guardrails-hk           — shell wrapper (caller-agnostic Bash gating)
#   ai-guardrails-hk-cc-tools  — Claude Code adapter (Edit/Write/Read events)

REPO="Questi0nM4rk/ai-guardrails"
INSTALL_DIR="${AI_GUARDRAILS_INSTALL_DIR:-$HOME/.local/bin}"
BINARIES="ai-guardrails ai-guardrails-hk ai-guardrails-hk-cc-tools"

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$OS" in
linux) PLATFORM="linux" ;;
darwin) PLATFORM="darwin" ;;
*)
    printf 'Error: unsupported OS: %s\n' "$OS" >&2
    exit 1
    ;;
esac

case "$ARCH" in
x86_64 | amd64) ARCH="x64" ;;
aarch64 | arm64) ARCH="arm64" ;;
*)
    printf 'Error: unsupported architecture: %s\n' "$ARCH" >&2
    exit 1
    ;;
esac

# ---------------------------------------------------------------------------
# Resolve latest release tag
# ---------------------------------------------------------------------------

TAG=$(curl -fsSL --max-time 30 "https://api.github.com/repos/${REPO}/releases/latest" |
    grep '"tag_name"' |
    sed 's/.*: "//;s/".*//')

if [ -z "$TAG" ]; then
    printf 'Error: could not determine latest release\n' >&2
    exit 1
fi

case "$TAG" in
v[0-9]*.[0-9]*.[0-9]*) ;;
*)
    printf 'Error: unexpected tag format: %s\n' "$TAG" >&2
    exit 1
    ;;
esac

printf 'Installing ai-guardrails %s (%s/%s)...\n' "$TAG" "$PLATFORM" "$ARCH"

# ---------------------------------------------------------------------------
# Download + verify + install each binary
# ---------------------------------------------------------------------------

DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${TAG}"
TMP_DIR=$(mktemp -d)
TMP_CHECKSUMS="${TMP_DIR}/checksums.sha256"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

curl -fsSL --max-time 60 "${DOWNLOAD_URL}/checksums.sha256" -o "$TMP_CHECKSUMS"

if command -v sha256sum >/dev/null 2>&1; then
    SHA_CMD="sha256sum"
else
    SHA_CMD="shasum -a 256"
fi

mkdir -p "$INSTALL_DIR"

for BIN in $BINARIES; do
    ASSET="${BIN}-${PLATFORM}-${ARCH}"
    TMP_PATH="${TMP_DIR}/${ASSET}"

    printf '  → %s\n' "$BIN"
    curl -fsSL --max-time 300 "${DOWNLOAD_URL}/${ASSET}" -o "$TMP_PATH"

    EXPECTED=$(grep -F " ${ASSET}" "$TMP_CHECKSUMS" | awk '{print $1}')
    if [ -z "$EXPECTED" ]; then
        printf 'Error: %s not found in checksums file\n' "$ASSET" >&2
        exit 1
    fi
    ACTUAL=$($SHA_CMD "$TMP_PATH" | awk '{print $1}')
    if [ "$EXPECTED" != "$ACTUAL" ]; then
        printf 'Error: checksum mismatch for %s!\n' "$ASSET" >&2
        printf '  Expected: %s\n' "$EXPECTED" >&2
        printf '  Got:      %s\n' "$ACTUAL" >&2
        exit 1
    fi

    cp "$TMP_PATH" "${INSTALL_DIR}/${BIN}"
    chmod +x "${INSTALL_DIR}/${BIN}"
done

printf 'Installed 3 binaries to %s\n\n' "$INSTALL_DIR"

# Cleanup legacy artifacts from pre-v4 installs (UX-002).
# v3.x shipped `ai-guardrails-init` as a separate symlinked binary. v4 uses
# the `ai-guardrails init` subcommand instead, so the symlink is dead weight.
LEGACY_INIT="${INSTALL_DIR}/ai-guardrails-init"
if [ -L "$LEGACY_INIT" ] || [ -f "$LEGACY_INIT" ]; then
    rm -f "$LEGACY_INIT"
    printf 'Removed legacy %s\n' "$LEGACY_INIT"
fi


# ---------------------------------------------------------------------------
# PATH hint
# ---------------------------------------------------------------------------

case ":${PATH}:" in
*":${INSTALL_DIR}:"*) ;;
*)
    printf 'Warning: %s is not in your PATH\n' "$INSTALL_DIR" >&2
    printf "Add it: export PATH=\"%s:\$PATH\"\n" "$INSTALL_DIR" >&2
    ;;
esac

printf "Run 'ai-guardrails --version' to verify.\n"
