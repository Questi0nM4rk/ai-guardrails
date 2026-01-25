#!/bin/bash
# ============================================
# Go Tools Installer
# Installs: golangci-lint, govulncheck
# ============================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Installing Go tools...${NC}"

# Check for go
if ! command -v go &>/dev/null; then
  echo -e "${RED}Error: go not found${NC}"
  echo "Install Go first"
  echo "  https://go.dev/doc/install"
  exit 1
fi

# Install golangci-lint
echo -n "  Installing golangci-lint... "
if go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest 2>/dev/null; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  echo -e "${YELLOW}    Warning: Failed to install golangci-lint${NC}"
fi

# Install govulncheck
echo -n "  Installing govulncheck... "
if go install golang.org/x/vuln/cmd/govulncheck@latest 2>/dev/null; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  echo -e "${YELLOW}    Warning: Failed to install govulncheck${NC}"
fi

echo -e "${GREEN}Go tools installation complete!${NC}"
