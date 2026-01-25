#!/bin/bash
# ============================================
# Lua Tools Installer
# Installs: stylua, luacheck
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

echo -e "${GREEN}Installing Lua tools...${NC}"

PM=$(detect_package_manager)

# Install stylua (prefer cargo, fallback to package managers)
echo -n "  Installing stylua... "
if command -v cargo &>/dev/null; then
  if cargo install --quiet stylua 2>/dev/null; then
    echo -e "${GREEN}✓${NC} (via cargo)"
  else
    echo -e "${RED}✗${NC}"
    echo -e "${YELLOW}    Warning: Failed to install stylua via cargo${NC}"
  fi
elif [[ "$PM" == "pacman" ]]; then
  if sudo pacman -S --needed --noconfirm stylua >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} (via pacman)"
  else
    echo -e "${RED}✗${NC}"
    echo -e "${YELLOW}    Warning: Failed to install stylua via pacman${NC}"
  fi
else
  echo -e "${YELLOW}⚠${NC}"
  echo "    Install manually: cargo install stylua"
fi

# Install luacheck (via package manager or luarocks)
echo -n "  Installing luacheck... "
case "$PM" in
  pacman)
    if sudo pacman -S --needed --noconfirm luacheck >/dev/null 2>&1; then
      echo -e "${GREEN}✓${NC} (via pacman)"
    else
      echo -e "${RED}✗${NC}"
      echo -e "${YELLOW}    Warning: Failed to install luacheck${NC}"
    fi
    ;;
  apt)
    if sudo apt-get install -y luacheck >/dev/null 2>&1; then
      echo -e "${GREEN}✓${NC} (via apt)"
    else
      echo -e "${RED}✗${NC}"
      echo -e "${YELLOW}    Warning: Failed to install luacheck${NC}"
    fi
    ;;
  brew)
    if brew install luacheck >/dev/null 2>&1; then
      echo -e "${GREEN}✓${NC} (via brew)"
    else
      echo -e "${RED}✗${NC}"
      echo -e "${YELLOW}    Warning: Failed to install luacheck${NC}"
    fi
    ;;
  none)
    echo -e "${YELLOW}⚠${NC}"
    echo "    Install manually: luarocks install luacheck"
    ;;
esac

echo -e "${GREEN}Lua tools installation complete!${NC}"
