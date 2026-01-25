#!/bin/bash
# ============================================
# Integration test for install.sh
# ============================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Testing install.sh..."
echo

# Test 1: Help output contains new flags
echo -n "Test 1: Help output... "
if ./install.sh --help 2>&1 | grep -q -- "--python"; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  exit 1
fi

# Test 2: Invalid flag is rejected
echo -n "Test 2: Invalid flag rejection... "
if ! ./install.sh --invalid-flag &>/dev/null; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  exit 1
fi

# Test 3: Installer scripts exist
echo -n "Test 3: Installer scripts exist... "
if [[ -f lib/installers/python.sh ]] \
  && [[ -f lib/installers/node.sh ]] \
  && [[ -f lib/installers/shell.sh ]] \
  && [[ -f lib/installers/detect_pm.sh ]]; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  exit 1
fi

# Test 4: Installer scripts are executable
echo -n "Test 4: Scripts are executable... "
if [[ -x lib/installers/python.sh ]] \
  && [[ -x lib/installers/node.sh ]] \
  && [[ -x lib/installers/shell.sh ]]; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  exit 1
fi

# Test 5: Python installer handles PEP 668
echo -n "Test 5: Python installer PEP 668 handling... "
if grep -q "pipx" lib/installers/python.sh \
  && grep -q "break-system-packages" lib/installers/python.sh; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  exit 1
fi

# Test 6: Package manager detection works (smoke test - uses real system)
# This validates detection works on the actual host; for isolated tests see test_install.bats
echo -n "Test 6: Package manager detection... "
if source lib/installers/detect_pm.sh; then
  PM=$(detect_package_manager)
  if [[ "$PM" != "none" ]]; then
    echo -e "${GREEN}✓${NC} ($PM)"
  else
    echo -e "  ${YELLOW}⚠${NC} No package manager detected (PM=none)"
  fi
else
  echo -e "${RED}✗${NC}"
  exit 1
fi

echo
echo -e "${GREEN}All tests passed!${NC}"
