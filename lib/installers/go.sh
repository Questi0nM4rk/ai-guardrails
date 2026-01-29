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

INSTALL_FAILED=false

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
  INSTALL_FAILED=true
fi

# Install govulncheck
echo -n "  Installing govulncheck... "
if go install golang.org/x/vuln/cmd/govulncheck@latest 2>/dev/null; then
  echo -e "${GREEN}✓${NC}"
else
  echo -e "${RED}✗${NC}"
  echo -e "${YELLOW}    Warning: Failed to install govulncheck${NC}"
  INSTALL_FAILED=true
fi

# Note about PATH
GOBIN="${GOBIN:-${GOPATH:-$HOME/go}/bin}"
if [[ ":$PATH:" != *":$GOBIN:"* ]]; then
  echo -e "${YELLOW}  Note: Add to PATH for tool access: $GOBIN${NC}"
fi

if [[ "$INSTALL_FAILED" == true ]]; then
  echo -e "${YELLOW}Go tools installation completed with errors${NC}"
  exit 1
fi

echo -e "${GREEN}Go tools installation complete!${NC}"
