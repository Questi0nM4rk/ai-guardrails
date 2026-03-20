#!/bin/sh
# shellcheck shell=sh
set -eu

# Usage: curl -fsSL https://raw.githubusercontent.com/Questi0nM4rk/ai-guardrails/main/scripts/install.sh | sh
#
# Environment variables:
#   AI_GUARDRAILS_INSTALL_DIR  — installation directory (default: ~/.local/bin)

REPO="Questi0nM4rk/ai-guardrails"
INSTALL_DIR="${AI_GUARDRAILS_INSTALL_DIR:-$HOME/.local/bin}"

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$OS" in
  linux)  PLATFORM="linux" ;;
  darwin) PLATFORM="darwin" ;;
  *)
    printf 'Error: unsupported OS: %s\n' "$OS" >&2
    exit 1
    ;;
esac

case "$ARCH" in
  x86_64|amd64)   ARCH="x64" ;;
  aarch64|arm64)  ARCH="arm64" ;;
  *)
    printf 'Error: unsupported architecture: %s\n' "$ARCH" >&2
    exit 1
    ;;
esac

BINARY="ai-guardrails-${PLATFORM}-${ARCH}"

# ---------------------------------------------------------------------------
# Resolve latest release tag
# ---------------------------------------------------------------------------

TAG=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" \
  | grep '"tag_name"' \
  | sed 's/.*: "//;s/".*//')

if [ -z "$TAG" ]; then
  printf 'Error: could not determine latest release\n' >&2
  exit 1
fi

printf 'Installing ai-guardrails %s (%s/%s)...\n' "$TAG" "$PLATFORM" "$ARCH"

# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${TAG}"
TMP_BINARY="/tmp/${BINARY}"
TMP_CHECKSUMS="/tmp/checksums.sha256"

# Cleanup helper — called on success and failure
cleanup() {
  rm -f "$TMP_BINARY" "$TMP_CHECKSUMS"
}
trap cleanup EXIT

curl -fsSL "${DOWNLOAD_URL}/${BINARY}"          -o "$TMP_BINARY"
curl -fsSL "${DOWNLOAD_URL}/checksums.sha256"   -o "$TMP_CHECKSUMS"

# ---------------------------------------------------------------------------
# SHA-256 verification
# ---------------------------------------------------------------------------

EXPECTED=$(grep "${BINARY}" "$TMP_CHECKSUMS" | awk '{print $1}')

if [ -z "$EXPECTED" ]; then
  printf 'Error: %s not found in checksums file\n' "$BINARY" >&2
  exit 1
fi

# sha256sum on Linux; shasum -a 256 on macOS
if command -v sha256sum > /dev/null 2>&1; then
  ACTUAL=$(sha256sum "$TMP_BINARY" | awk '{print $1}')
else
  ACTUAL=$(shasum -a 256 "$TMP_BINARY" | awk '{print $1}')
fi

if [ "$EXPECTED" != "$ACTUAL" ]; then
  printf 'Error: checksum mismatch!\n' >&2
  printf '  Expected: %s\n' "$EXPECTED" >&2
  printf '  Got:      %s\n' "$ACTUAL" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

mkdir -p "$INSTALL_DIR"

# Move binary out of /tmp before the EXIT trap removes it
cp "$TMP_BINARY" "${INSTALL_DIR}/ai-guardrails"
chmod +x "${INSTALL_DIR}/ai-guardrails"

printf 'Installed ai-guardrails to %s/ai-guardrails\n' "$INSTALL_DIR"
printf '\n'

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
