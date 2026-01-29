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

# Bash 4.0+ required for associative arrays
if ((BASH_VERSINFO[0] < 4)); then
  echo "Error: This script requires Bash 4.0+ (you have ${BASH_VERSION})"
  echo "macOS users: brew install bash"
  exit 1
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="$HOME/.ai-guardrails"
BIN_DIR="$HOME/.local/bin"

# Track installation results (for accurate summary)
declare -A INSTALLED_LANGS=()
declare -A FAILED_LANGS=()

# Helper function to install pyyaml
install_pyyaml() {
  echo -n "  Installing pyyaml... "
  if python3 -c "import yaml" &>/dev/null; then
    echo -e "${YELLOW}already installed${NC}"
    return 0
  fi

  # Try installation methods
  if python3 -m pip install --user --quiet pyyaml 2>/dev/null \
    || python3 -m pip install --user --break-system-packages --quiet pyyaml 2>/dev/null; then
    if python3 -c "import yaml" &>/dev/null; then
      echo -e "${GREEN}✓${NC}"
      return 0
    fi
  fi

  # Verify not already installed by other means
  if python3 -c "import yaml" &>/dev/null; then
    echo -e "${GREEN}✓${NC}"
    return 0
  fi

  echo -e "${RED}✗${NC}"
  echo -e "${RED}Error: Failed to install pyyaml${NC}"
  return 1
}

# Helper function to install pre-commit
install_precommit() {
  local use_pipx=$1
  echo -n "  Installing pre-commit... "

  # Check if already installed
  if [[ "$use_pipx" == true ]]; then
    if pipx list 2>/dev/null | grep -q "package pre-commit" || command -v pre-commit &>/dev/null; then
      echo -e "${YELLOW}already installed${NC}"
      return 0
    fi
  else
    if python3 -c "import pre_commit" &>/dev/null || command -v pre-commit &>/dev/null; then
      echo -e "${YELLOW}already installed${NC}"
      return 0
    fi
  fi

  # Try installation
  if [[ "$use_pipx" == true ]]; then
    if pipx install pre-commit &>/dev/null || pipx upgrade pre-commit &>/dev/null 2>&1; then
      if pipx list 2>/dev/null | grep -q "package pre-commit"; then
        echo -e "${GREEN}✓${NC}"
        return 0
      fi
    fi
    # Fallback check
    if pipx list 2>/dev/null | grep -q "package pre-commit" || command -v pre-commit &>/dev/null; then
      echo -e "${GREEN}✓${NC}"
      return 0
    fi
  else
    if python3 -m pip install --user --quiet pre-commit 2>/dev/null \
      || python3 -m pip install --user --break-system-packages --quiet pre-commit 2>/dev/null; then
      if python3 -c "import pre_commit" &>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        return 0
      fi
    fi
    # Fallback check
    if python3 -c "import pre_commit" &>/dev/null || command -v pre-commit &>/dev/null; then
      echo -e "${GREEN}✓${NC}"
      return 0
    fi
  fi

  echo -e "${RED}✗${NC}"
  echo -e "${RED}Error: Failed to install pre-commit${NC}"
  return 1
}

# Get script directory (source of installation)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<EOF
Usage: ./install.sh [OPTIONS]

Install AI Guardrails globally.

Options:
  --uninstall     Remove AI Guardrails installation
  --force         Force reinstall (overwrite existing)
  --all           Install all language tools
  --python        Install Python tools (ruff, mypy, bandit, vulture, pip-audit)
  --node          Install Node.js tools (biome)
  --rust          Install Rust tools (cargo-audit)
  --go            Install Go tools (golangci-lint, govulncheck)
  --cpp           Install C/C++ tools (clang-format, clang-tidy)
  --lua           Install Lua tools (stylua, luacheck)
  --shell         Install Shell tools (shellcheck, shfmt)
  -h, --help      Show this help

Installation locations:
  ~/.ai-guardrails/     Main installation directory
  ~/.local/bin/         CLI symlinks (ai-review-tasks, ai-hooks-init, etc.)

Prerequisites:
  - Python 3.10+
  - gh (GitHub CLI) with gh-pr-review extension

Notes:
  - pyyaml and pre-commit are always installed (required)
  - Language tools require their respective toolchains (go, cargo, npm, etc.)
  - System package manager (pacman/apt/brew) used where applicable

EOF
}

UNINSTALL=false
FORCE=false
INSTALL_ALL=false
INSTALL_PYTHON=false
INSTALL_NODE=false
INSTALL_RUST=false
INSTALL_GO=false
INSTALL_CPP=false
INSTALL_LUA=false
INSTALL_SHELL=false

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
    --all)
      INSTALL_ALL=true
      shift
      ;;
    --python)
      INSTALL_PYTHON=true
      shift
      ;;
    --node)
      INSTALL_NODE=true
      shift
      ;;
    --rust)
      INSTALL_RUST=true
      shift
      ;;
    --go)
      INSTALL_GO=true
      shift
      ;;
    --cpp)
      INSTALL_CPP=true
      shift
      ;;
    --lua)
      INSTALL_LUA=true
      shift
      ;;
    --shell)
      INSTALL_SHELL=true
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

# Determine if any language tools should be installed
SHOULD_INSTALL_LANGS=false
if [[ "$INSTALL_ALL" == true ]] || [[ "$INSTALL_PYTHON" == true ]] || [[ "$INSTALL_NODE" == true ]] \
  || [[ "$INSTALL_RUST" == true ]] || [[ "$INSTALL_GO" == true ]] || [[ "$INSTALL_CPP" == true ]] \
  || [[ "$INSTALL_LUA" == true ]] || [[ "$INSTALL_SHELL" == true ]]; then
  SHOULD_INSTALL_LANGS=true
fi

# Track installer failures for explicit flags
INSTALL_ERRORS=0

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

# Install critical Python dependencies
echo
echo "Installing critical dependencies..."

# Use helper functions for installation
install_pyyaml || exit 1

if command -v pipx &>/dev/null; then
  install_precommit true || exit 1
else
  install_precommit false || exit 1
fi

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

mkdir -p "$INSTALL_DIR"/{bin,lib/hooks,lib/python,lib/installers,templates/pre-commit,templates/workflows,configs}
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
for pyfile in "$SCRIPT_DIR/lib/python/"*.py; do
  if [[ -f "$pyfile" ]]; then
    cp "$pyfile" "$INSTALL_DIR/lib/python/"
    echo "  ✓ lib/python/$(basename "$pyfile")"
  fi
done

# Copy lib/installers
for installer in "$SCRIPT_DIR/lib/installers/"*.sh; do
  if [[ -f "$installer" ]]; then
    cp "$installer" "$INSTALL_DIR/lib/installers/"
    chmod +x "$INSTALL_DIR/lib/installers/$(basename "$installer")"
    echo "  ✓ lib/installers/$(basename "$installer")"
  fi
done

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

# Copy templates/pre-commit directory (modular templates)
if [[ -d "$SCRIPT_DIR/templates/pre-commit" ]]; then
  mkdir -p "$INSTALL_DIR/templates/pre-commit"
  for template in "$SCRIPT_DIR/templates/pre-commit/"*.yaml; do
    if [[ -f "$template" ]]; then
      basename=$(basename "$template")
      cp "$template" "$INSTALL_DIR/templates/pre-commit/"
      echo "  ✓ templates/pre-commit/$basename"
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

# Install language-specific tools
if [[ "$SHOULD_INSTALL_LANGS" == true ]]; then
  echo
  echo -e "${GREEN}Installing language tools...${NC}"
  echo

  if [[ "$INSTALL_ALL" == true ]] || [[ "$INSTALL_PYTHON" == true ]]; then
    if "$INSTALL_DIR/lib/installers/python.sh"; then
      INSTALLED_LANGS[python]=true
    else
      echo -e "${YELLOW}Warning: Python tools installation had issues${NC}"
      FAILED_LANGS[python]=true
      [[ "$INSTALL_PYTHON" == true || "$INSTALL_ALL" == true ]] && INSTALL_ERRORS=$((INSTALL_ERRORS + 1))
    fi
    echo
  fi

  if [[ "$INSTALL_ALL" == true ]] || [[ "$INSTALL_NODE" == true ]]; then
    if "$INSTALL_DIR/lib/installers/node.sh"; then
      INSTALLED_LANGS[node]=true
    else
      echo -e "${YELLOW}Warning: Node.js tools installation had issues${NC}"
      FAILED_LANGS[node]=true
      [[ "$INSTALL_NODE" == true || "$INSTALL_ALL" == true ]] && INSTALL_ERRORS=$((INSTALL_ERRORS + 1))
    fi
    echo
  fi

  if [[ "$INSTALL_ALL" == true ]] || [[ "$INSTALL_RUST" == true ]]; then
    if "$INSTALL_DIR/lib/installers/rust.sh"; then
      INSTALLED_LANGS[rust]=true
    else
      echo -e "${YELLOW}Warning: Rust tools installation had issues${NC}"
      FAILED_LANGS[rust]=true
      [[ "$INSTALL_RUST" == true || "$INSTALL_ALL" == true ]] && INSTALL_ERRORS=$((INSTALL_ERRORS + 1))
    fi
    echo
  fi

  if [[ "$INSTALL_ALL" == true ]] || [[ "$INSTALL_GO" == true ]]; then
    if "$INSTALL_DIR/lib/installers/go.sh"; then
      INSTALLED_LANGS[go]=true
    else
      echo -e "${YELLOW}Warning: Go tools installation had issues${NC}"
      FAILED_LANGS[go]=true
      [[ "$INSTALL_GO" == true || "$INSTALL_ALL" == true ]] && INSTALL_ERRORS=$((INSTALL_ERRORS + 1))
    fi
    echo
  fi

  if [[ "$INSTALL_ALL" == true ]] || [[ "$INSTALL_CPP" == true ]]; then
    if "$INSTALL_DIR/lib/installers/cpp.sh"; then
      INSTALLED_LANGS[cpp]=true
    else
      echo -e "${YELLOW}Warning: C/C++ tools installation had issues${NC}"
      FAILED_LANGS[cpp]=true
      [[ "$INSTALL_CPP" == true || "$INSTALL_ALL" == true ]] && INSTALL_ERRORS=$((INSTALL_ERRORS + 1))
    fi
    echo
  fi

  if [[ "$INSTALL_ALL" == true ]] || [[ "$INSTALL_LUA" == true ]]; then
    if "$INSTALL_DIR/lib/installers/lua.sh"; then
      INSTALLED_LANGS[lua]=true
    else
      echo -e "${YELLOW}Warning: Lua tools installation had issues${NC}"
      FAILED_LANGS[lua]=true
      [[ "$INSTALL_LUA" == true || "$INSTALL_ALL" == true ]] && INSTALL_ERRORS=$((INSTALL_ERRORS + 1))
    fi
    echo
  fi

  if [[ "$INSTALL_ALL" == true ]] || [[ "$INSTALL_SHELL" == true ]]; then
    if "$INSTALL_DIR/lib/installers/shell.sh"; then
      INSTALLED_LANGS[shell]=true
    else
      echo -e "${YELLOW}Warning: Shell tools installation had issues${NC}"
      FAILED_LANGS[shell]=true
      [[ "$INSTALL_SHELL" == true || "$INSTALL_ALL" == true ]] && INSTALL_ERRORS=$((INSTALL_ERRORS + 1))
    fi
    echo
  fi
fi

# Exit with error if explicit installer flags failed
if [[ $INSTALL_ERRORS -gt 0 ]]; then
  echo -e "${RED}Installation completed with $INSTALL_ERRORS error(s)${NC}"
  exit 1
fi

echo
echo -e "${GREEN}AI Guardrails installed successfully!${NC}"
echo
echo "Installation summary:"
echo "  • Main directory: $INSTALL_DIR"
echo "  • CLI commands: ai-review-tasks, ai-hooks-init, ai-guardrails-init"
echo "  • Hooks: $INSTALL_DIR/hooks/"
echo

if [[ "$SHOULD_INSTALL_LANGS" == true ]]; then
  # Show successfully installed tools
  if [[ ${#INSTALLED_LANGS[@]} -gt 0 ]]; then
    echo "Successfully installed language tools:"
    [[ "${INSTALLED_LANGS[python]:-}" == true ]] && echo "  • Python: ruff, mypy, bandit, vulture, pip-audit"
    [[ "${INSTALLED_LANGS[node]:-}" == true ]] && echo "  • Node.js: biome"
    [[ "${INSTALLED_LANGS[rust]:-}" == true ]] && echo "  • Rust: cargo-audit"
    [[ "${INSTALLED_LANGS[go]:-}" == true ]] && echo "  • Go: golangci-lint, govulncheck"
    [[ "${INSTALLED_LANGS[cpp]:-}" == true ]] && echo "  • C/C++: clang-format, clang-tidy"
    [[ "${INSTALLED_LANGS[lua]:-}" == true ]] && echo "  • Lua: stylua, luacheck"
    [[ "${INSTALLED_LANGS[shell]:-}" == true ]] && echo "  • Shell: shellcheck, shfmt"
    echo
  fi

  # Show failed installations
  if [[ ${#FAILED_LANGS[@]} -gt 0 ]]; then
    echo -e "${YELLOW}Failed to install:${NC}"
    [[ "${FAILED_LANGS[python]:-}" == true ]] && echo "  • Python tools"
    [[ "${FAILED_LANGS[node]:-}" == true ]] && echo "  • Node.js tools"
    [[ "${FAILED_LANGS[rust]:-}" == true ]] && echo "  • Rust tools"
    [[ "${FAILED_LANGS[go]:-}" == true ]] && echo "  • Go tools"
    [[ "${FAILED_LANGS[cpp]:-}" == true ]] && echo "  • C/C++ tools"
    [[ "${FAILED_LANGS[lua]:-}" == true ]] && echo "  • Lua tools"
    [[ "${FAILED_LANGS[shell]:-}" == true ]] && echo "  • Shell tools"
    echo
  fi
fi

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
