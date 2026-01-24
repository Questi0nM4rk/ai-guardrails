#!/bin/bash
# ============================================
# AI Guardrails Installer
# Installs ai-guardrails globally
#
# Usage:
#   ./install.sh              # Install
#   ./install.sh --uninstall  # Uninstall
# ============================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="$HOME/.ai-guardrails"
BIN_DIR="$HOME/.local/bin"

# Get script directory (source of installation)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<EOF
Usage: ./install.sh [OPTIONS]

Install AI Guardrails globally.

Options:
  --uninstall     Remove AI Guardrails installation
  --force         Force reinstall (overwrite existing)
  -h, --help      Show this help

Installation locations:
  ~/.ai-guardrails/     Main installation directory
  ~/.local/bin/         CLI symlinks (ai-review-tasks, ai-hooks-init, etc.)

Prerequisites:
  - Python 3.10+
  - gh (GitHub CLI) with gh-pr-review extension

EOF
}

UNINSTALL=false
FORCE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --uninstall)
      UNINSTALL=true
      shift
      ;;
    --force)
      FORCE=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      usage
      exit 1
      ;;
  esac
done

# Uninstall
if [[ "$UNINSTALL" == true ]]; then
  echo -e "${BLUE}Uninstalling AI Guardrails...${NC}"

  # Remove symlinks
  for cmd in ai-review-tasks ai-hooks-init ai-guardrails-init; do
    if [[ -L "$BIN_DIR/$cmd" ]]; then
      rm "$BIN_DIR/$cmd"
      echo "  ✓ Removed $BIN_DIR/$cmd"
    fi
  done

  # Remove installation directory
  if [[ -d "$INSTALL_DIR" ]]; then
    rm -rf "$INSTALL_DIR"
    echo "  ✓ Removed $INSTALL_DIR"
  fi

  echo -e "${GREEN}AI Guardrails uninstalled successfully!${NC}"
  exit 0
fi

# Check prerequisites
echo -e "${BLUE}AI Guardrails Installer${NC}"
echo

echo "Checking prerequisites..."

# Check Python
if ! command -v python3 &>/dev/null; then
  echo -e "${RED}Error: Python 3 is required but not installed${NC}"
  exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  ✓ Python $PYTHON_VERSION"

# Check gh CLI
if ! command -v gh &>/dev/null; then
  echo -e "${YELLOW}Warning: GitHub CLI (gh) not installed${NC}"
  echo "  Install: https://cli.github.com/"
else
  echo "  ✓ GitHub CLI (gh)"

  # Check gh-pr-review extension
  if gh extension list 2>/dev/null | grep -q "pr-review"; then
    echo "  ✓ gh-pr-review extension"
  else
    echo -e "${YELLOW}Warning: gh-pr-review extension not installed${NC}"
    echo "  Install: gh extension install agynio/gh-pr-review"
  fi
fi

echo

# Check if already installed
if [[ -d "$INSTALL_DIR" && "$FORCE" == false ]]; then
  echo -e "${YELLOW}AI Guardrails is already installed at $INSTALL_DIR${NC}"
  echo "Use --force to reinstall"
  exit 1
fi

# Create installation directory
echo "Installing to $INSTALL_DIR..."

if [[ "$FORCE" == true && -d "$INSTALL_DIR" ]]; then
  rm -rf "$INSTALL_DIR"
fi

mkdir -p "$INSTALL_DIR"/{bin,lib/hooks,lib/python,templates,configs}
mkdir -p "$BIN_DIR"

# Copy files
echo -e "${GREEN}Copying files...${NC}"

# Copy bin scripts
for script in ai-review-tasks ai-hooks-init ai-guardrails-init; do
  cp "$SCRIPT_DIR/bin/$script" "$INSTALL_DIR/bin/"
  chmod +x "$INSTALL_DIR/bin/$script"
  echo "  ✓ bin/$script"
done

# Copy lib/hooks
for hook in common.sh dangerous-command-check.sh pre-commit.sh pre-push.sh format-and-stage.sh; do
  if [[ -f "$SCRIPT_DIR/lib/hooks/$hook" ]]; then
    cp "$SCRIPT_DIR/lib/hooks/$hook" "$INSTALL_DIR/lib/hooks/"
    chmod +x "$INSTALL_DIR/lib/hooks/$hook"
    echo "  ✓ lib/hooks/$hook"
  fi
done

# Copy lib/python
cp "$SCRIPT_DIR/lib/python/coderabbit_parser.py" "$INSTALL_DIR/lib/python/"
echo "  ✓ lib/python/coderabbit_parser.py"

# Copy templates (files, including dotfiles)
for template in "$SCRIPT_DIR/templates/"* "$SCRIPT_DIR/templates/."*; do
  if [[ -f "$template" ]]; then
    cp "$template" "$INSTALL_DIR/templates/"
    echo "  ✓ templates/$(basename "$template")"
  fi
done

# Copy templates/workflows directory
if [[ -d "$SCRIPT_DIR/templates/workflows" ]]; then
  mkdir -p "$INSTALL_DIR/templates/workflows"
  for workflow in "$SCRIPT_DIR/templates/workflows/"*; do
    if [[ -f "$workflow" ]]; then
      basename=$(basename "$workflow")
      cp "$workflow" "$INSTALL_DIR/templates/workflows/"
      echo "  ✓ templates/workflows/$basename"
    fi
  done
fi

# Copy configs (including dotfiles)
for config in "$SCRIPT_DIR/configs/"* "$SCRIPT_DIR/configs/."*; do
  if [[ -f "$config" ]]; then
    basename=$(basename "$config")
    # Skip . and .. entries
    [[ "$basename" == "." || "$basename" == ".." ]] && continue
    cp "$config" "$INSTALL_DIR/configs/"
    echo "  ✓ configs/$basename"
  fi
done

# Create symlinks in ~/.local/bin
echo -e "${GREEN}Creating symlinks...${NC}"

for cmd in ai-review-tasks ai-hooks-init ai-guardrails-init; do
  ln -sf "$INSTALL_DIR/bin/$cmd" "$BIN_DIR/$cmd"
  echo "  ✓ $BIN_DIR/$cmd -> $INSTALL_DIR/bin/$cmd"
done

# Also create hooks symlinks for direct access
mkdir -p "$INSTALL_DIR/hooks"
for hook in common.sh dangerous-command-check.sh pre-commit.sh pre-push.sh format-and-stage.sh; do
  if [[ -f "$INSTALL_DIR/lib/hooks/$hook" ]]; then
    ln -sf "$INSTALL_DIR/lib/hooks/$hook" "$INSTALL_DIR/hooks/$hook"
  fi
done

echo
echo -e "${GREEN}AI Guardrails installed successfully!${NC}"
echo
echo "Installation summary:"
echo "  • Main directory: $INSTALL_DIR"
echo "  • CLI commands: ai-review-tasks, ai-hooks-init, ai-guardrails-init"
echo "  • Hooks: $INSTALL_DIR/hooks/"
echo
echo "Quick start:"
echo "  1. cd /path/to/your/project"
echo "  2. ai-guardrails-init           # Set up CLAUDE.md and settings"
echo "  3. ai-hooks-init --pre-commit   # Set up git hooks"
echo
echo "Extract PR review tasks:"
echo "  gh pr-review review view --pr 1 | ai-review-tasks --pretty"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo
  echo -e "${YELLOW}Note: Add ~/.local/bin to your PATH:${NC}"
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
