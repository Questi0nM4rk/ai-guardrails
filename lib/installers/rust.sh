#!/bin/bash
# ============================================
# Rust Tools Installer
# Installs: cargo-audit
# ============================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Installing Rust tools...${NC}"

# Check for cargo
if ! command -v cargo &>/dev/null; then
  echo -e "${RED}Error: cargo not found${NC}"
  echo "Install Rust first"
  echo "  https://rustup.rs/"
  exit 1
fi

# Install cargo-audit
echo -n "  Installing cargo-audit... "
if cargo install --quiet cargo-audit 2>/dev/null; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  echo -e "${YELLOW}    Warning: Failed to install cargo-audit${NC}"
  echo "    Try: cargo install cargo-audit"
fi

echo -e "${GREEN}Rust tools installation complete!${NC}"
