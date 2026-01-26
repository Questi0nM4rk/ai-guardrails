#!/bin/bash
# ============================================
# Shell Tools Installer
# Installs: shellcheck, shfmt
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

echo -e "${GREEN}Installing Shell tools...${NC}"

PM=$(detect_package_manager)

case "$PM" in
pacman)
	echo "  Using pacman..."
	sudo pacman -S --needed --noconfirm shellcheck shfmt >/dev/null 2>&1 || {
		echo -e "${YELLOW}    Warning: Failed to install shellcheck and shfmt${NC}"
		echo "    Try: sudo pacman -S shellcheck shfmt"
	}
	;;
apt)
	echo "  Using apt..."
	sudo apt-get install -y shellcheck >/dev/null 2>&1 || {
		echo -e "${YELLOW}    Warning: Failed to install shellcheck${NC}"
	}
	# shfmt not in apt by default, install via go
	if command -v go &>/dev/null; then
		echo "    Installing shfmt via go..."
		if go install mvdan.cc/sh/v3/cmd/shfmt@latest 2>/dev/null; then
			# Add Go bin to PATH for verification
			GOBIN_DIR="${GOBIN:-$HOME/go/bin}"
			if [[ ":$PATH:" != *":$GOBIN_DIR:"* ]]; then
				export PATH="$GOBIN_DIR:$PATH"
				echo -e "${YELLOW}    Note: Add to PATH for permanent access: $GOBIN_DIR${NC}"
			fi
		else
			echo -e "${YELLOW}    Warning: Failed to install shfmt via go${NC}"
		fi
	else
		echo -e "${YELLOW}    Warning: shfmt requires Go to install${NC}"
		echo "    Try: go install mvdan.cc/sh/v3/cmd/shfmt@latest"
	fi
	;;
dnf | yum)
	echo "  Using $PM..."
	sudo "$PM" install -y ShellCheck >/dev/null 2>&1 || {
		echo -e "${YELLOW}    Warning: Failed to install ShellCheck${NC}"
		echo "    Try: sudo $PM install ShellCheck"
	}
	# shfmt via go on RHEL/Fedora
	if command -v go &>/dev/null; then
		echo "    Installing shfmt via go..."
		if go install mvdan.cc/sh/v3/cmd/shfmt@latest 2>/dev/null; then
			GOBIN_DIR="${GOBIN:-$HOME/go/bin}"
			if [[ ":$PATH:" != *":$GOBIN_DIR:"* ]]; then
				export PATH="$GOBIN_DIR:$PATH"
				echo -e "${YELLOW}    Note: Add to PATH for permanent access: $GOBIN_DIR${NC}"
			fi
		else
			echo -e "${YELLOW}    Warning: Failed to install shfmt via go${NC}"
		fi
	else
		echo -e "${YELLOW}    Warning: shfmt requires Go to install${NC}"
		echo "    Try: go install mvdan.cc/sh/v3/cmd/shfmt@latest"
	fi
	;;
apk)
	echo "  Using apk..."
	sudo apk add --no-cache shellcheck shfmt >/dev/null 2>&1 || {
		echo -e "${YELLOW}    Warning: Failed to install shellcheck and shfmt${NC}"
		echo "    Try: sudo apk add shellcheck shfmt"
	}
	;;
brew)
	echo "  Using brew..."
	brew install shellcheck shfmt >/dev/null 2>&1 || {
		echo -e "${YELLOW}    Warning: Failed to install shellcheck and shfmt${NC}"
		echo "    Try: brew install shellcheck shfmt"
	}
	;;
none)
	echo -e "${YELLOW}  No package manager detected${NC}"
	echo "  Install manually:"
	echo "    • shellcheck: https://github.com/koalaman/shellcheck"
	echo "    • shfmt: go install mvdan.cc/sh/v3/cmd/shfmt@latest"
	exit 1
	;;
esac

# Verify installation
FAILED=false
if command -v shellcheck &>/dev/null; then
	echo -e "  ${GREEN}✓${NC} shellcheck"
else
	echo -e "  ${RED}✗${NC} shellcheck not found"
	FAILED=true
fi

if command -v shfmt &>/dev/null; then
	echo -e "  ${GREEN}✓${NC} shfmt"
else
	echo -e "  ${RED}✗${NC} shfmt not found"
	FAILED=true
fi

if [[ "$FAILED" == true ]]; then
	exit 1
fi

echo -e "${GREEN}Shell tools installation complete!${NC}"
