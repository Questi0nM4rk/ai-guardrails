#!/bin/bash
# ============================================
# C/C++ Tools Installer
# Installs: clang-format, clang-tidy
# ============================================

set -euo pipefail

# Colors
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
  brew)
    echo "  Using brew..."
    brew install clang-format >/dev/null 2>&1 || {
      echo -e "${YELLOW}    Warning: Failed to install clang-format${NC}"
      echo "    Try: brew install clang-format"
    }
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
if command -v clang-format &>/dev/null; then
  echo -e "  ${GREEN}✓${NC} clang-format"
fi

if command -v clang-tidy &>/dev/null; then
  echo -e "  ${GREEN}✓${NC} clang-tidy"
fi

echo -e "${GREEN}C/C++ tools installation complete!${NC}"
