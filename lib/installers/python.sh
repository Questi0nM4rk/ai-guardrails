#!/bin/bash
# ============================================
# Python Tools Installer
# Installs: ruff, mypy, bandit, vulture, pip-audit
# ============================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Installing Python tools...${NC}"

# Tools to install
TOOLS=(
  "ruff"
  "mypy"
  "bandit"
  "vulture"
  "pip-audit"
)

# Determine installation method
if command -v pipx &>/dev/null; then
  # Use pipx (recommended for PEP 668 compliance)
  echo "  Using pipx..."
  for tool in "${TOOLS[@]}"; do
    echo -n "    Installing $tool... "
    if pipx install "$tool" &>/dev/null || pipx upgrade "$tool" &>/dev/null 2>&1; then
      echo -e "${GREEN}✓${NC}"
    else
      echo -e "${RED}✗${NC}"
      echo -e "${YELLOW}      Warning: Failed to install $tool${NC}"
    fi
  done
elif command -v pip3 &>/dev/null; then
  # Try pip3 --user (may fail on PEP 668 systems)
  echo "  Using pip3..."
  for tool in "${TOOLS[@]}"; do
    echo -n "    Installing $tool... "
    if pip3 install --user --quiet "$tool" 2>/dev/null; then
      echo -e "${GREEN}✓${NC}"
    elif pip3 install --user --break-system-packages --quiet "$tool" 2>/dev/null; then
      echo -e "${GREEN}✓${NC} (--break-system-packages)"
    else
      echo -e "${RED}✗${NC}"
      echo -e "${YELLOW}      Warning: Failed to install $tool${NC}"
    fi
  done
else
  echo -e "${RED}Error: Neither pipx nor pip3 found${NC}"
  echo "Install pipx (recommended) or pip3:"
  echo "  • Arch: sudo pacman -S python-pipx"
  echo "  • Debian/Ubuntu: sudo apt install pipx"
  echo "  • macOS: brew install pipx"
  exit 1
fi

echo -e "${GREEN}Python tools installation complete!${NC}"
