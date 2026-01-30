#!/bin/bash
# ============================================
# Integration test for install.py
# ============================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "Testing install.py..."
echo

# Test 1: Help output contains expected flags
echo -n "Test 1: Help output... "
if python3 install.py --help 2>&1 | grep -q -- "--python"; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  exit 1
fi

# Test 2: Invalid flag is rejected
echo -n "Test 2: Invalid flag rejection... "
if ! python3 install.py --invalid-flag &>/dev/null 2>&1; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  exit 1
fi

# Test 3: Python installer modules exist
echo -n "Test 3: Installer modules exist... "
if [[ -f lib/installers/python.py ]] \
  && [[ -f lib/installers/node.py ]] \
  && [[ -f lib/installers/shell.py ]] \
  && [[ -f lib/installers/rust.py ]] \
  && [[ -f lib/installers/go.py ]] \
  && [[ -f lib/installers/cpp.py ]] \
  && [[ -f lib/installers/lua.py ]] \
  && [[ -f lib/installers/_utils.py ]]; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  exit 1
fi

# Test 4: Core module exists and has expected functions
echo -n "Test 4: Core module has expected functions... "
if grep -q "def install_core" lib/installers/core.py \
  && grep -q "def create_directories" lib/installers/core.py; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  exit 1
fi

# Test 5: Python installer uses pipx/pip hierarchy
echo -n "Test 5: Python installer pip hierarchy... "
if grep -q "pipx" lib/installers/python.py \
  && grep -q "pip" lib/installers/python.py; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  exit 1
fi

# Test 6: Package manager detection utility exists
echo -n "Test 6: Package manager detection... "
if grep -q "def get_package_manager" lib/installers/_utils.py; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  exit 1
fi

echo
echo -e "${GREEN}All tests passed!${NC}"
