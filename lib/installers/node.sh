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
if npm install -g @biomejs/biome 2>/dev/null; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  echo -e "${YELLOW}    Warning: Failed to install biome${NC}"
  echo "    Try: npm install -g @biomejs/biome"
fi

echo -e "${GREEN}Node.js tools installation complete!${NC}"
