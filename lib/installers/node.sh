#!/bin/bash
# ============================================
# Node.js Tools Installer
# Installs: biome
# ============================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_FAILED=false

echo -e "${GREEN}Installing Node.js tools...${NC}"

# Check for npm
if ! command -v npm &>/dev/null; then
  echo -e "${RED}Error: npm not found${NC}"
  echo "Install Node.js and npm first"
  echo "  https://nodejs.org/"
  exit 1
fi

# Install biome globally
echo -n "  Installing @biomejs/biome... "
if NPM_ERR=$(npm install -g @biomejs/biome 2>&1); then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  if echo "$NPM_ERR" | grep -qE "EACCES|EPERM"; then
    echo -e "${YELLOW}    Permission denied. Try: npm config set prefix ~/.npm-global${NC}"
  else
    echo -e "${YELLOW}    Warning: Failed to install biome${NC}"
  fi
  echo "    Try: npm install -g @biomejs/biome"
  INSTALL_FAILED=true
fi

if [[ "$INSTALL_FAILED" == true ]]; then
  echo -e "${YELLOW}Node.js tools installation completed with errors${NC}"
  exit 1
fi

echo -e "${GREEN}Node.js tools installation complete!${NC}"
