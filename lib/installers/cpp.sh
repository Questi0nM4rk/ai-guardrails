#!/bin/bash
# ============================================
# C/C++ Tools Installer
# Installs: clang-format, clang-tidy
# ============================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Source package manager detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/installers/detect_pm.sh
source "$SCRIPT_DIR/detect_pm.sh"

echo -e "${GREEN}Installing C/C++ tools...${NC}"

PM=$(detect_package_manager)

case "$PM" in
  pacman)
    echo "  Using pacman..."
    sudo pacman -S --needed --noconfirm clang >/dev/null 2>&1 || {
      echo -e "${YELLOW}    Warning: Failed to install clang (clang-format, clang-tidy)${NC}"
      echo "    Try: sudo pacman -S clang"
    }
    ;;
  apt)
    echo "  Using apt..."
    sudo apt-get install -y clang-format clang-tidy >/dev/null 2>&1 || {
      echo -e "${YELLOW}    Warning: Failed to install clang-format and clang-tidy${NC}"
      echo "    Try: sudo apt-get install clang-format clang-tidy"
    }
    ;;
  dnf | yum)
    echo "  Using $PM..."
    sudo "$PM" install -y clang clang-tools-extra >/dev/null 2>&1 || {
      echo -e "${YELLOW}    Warning: Failed to install clang and clang-tools-extra${NC}"
      echo "    Try: sudo $PM install clang clang-tools-extra"
    }
    ;;
  apk)
    echo "  Using apk..."
    sudo apk add --no-cache clang clang-extra-tools >/dev/null 2>&1 || {
      echo -e "${YELLOW}    Warning: Failed to install clang tools${NC}"
      echo "    Try: sudo apk add clang clang-extra-tools"
    }
    ;;
  brew)
    echo "  Using brew..."
    brew install clang-format >/dev/null 2>&1 || {
      echo -e "${YELLOW}    Warning: Failed to install clang-format${NC}"
    }
    # Install llvm for clang-tidy
    brew install llvm >/dev/null 2>&1 || {
      echo -e "${YELLOW}    Warning: Failed to install llvm (provides clang-tidy)${NC}"
    }
    # Add llvm to PATH for current script
    LLVM_BIN="$(brew --prefix llvm 2>/dev/null)/bin"
    if [[ -d "$LLVM_BIN" ]]; then
      export PATH="$LLVM_BIN:$PATH"
      echo -e "${YELLOW}    Note: Add to PATH for permanent access: $LLVM_BIN${NC}"
    fi
    ;;
  none)
    echo -e "${YELLOW}  No package manager detected${NC}"
    echo "  Install manually:"
    echo "    • clang-format"
    echo "    • clang-tidy"
    exit 1
    ;;
esac

# Verify installation
FAILED=false
if command -v clang-format &>/dev/null; then
  echo -e "  ${GREEN}✓${NC} clang-format"
else
  echo -e "  ${RED}✗${NC} clang-format not found"
  FAILED=true
fi

if command -v clang-tidy &>/dev/null; then
  echo -e "  ${GREEN}✓${NC} clang-tidy"
else
  echo -e "  ${RED}✗${NC} clang-tidy not found"
  FAILED=true
fi

if [[ "$FAILED" == true ]]; then
  exit 1
fi

echo -e "${GREEN}C/C++ tools installation complete!${NC}"
