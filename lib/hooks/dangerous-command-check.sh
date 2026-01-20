#!/bin/bash
# ============================================
# Dangerous Command Check Hook
# Blocks or warns on dangerous bash commands
# Exit 0 = allow, Exit 2 = block with message
# ============================================

COMMAND="$1"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Block patterns (exit 2 to block)
# shellcheck disable=SC2221,SC2222  # Intentional pattern overlap for defense in depth
case "$COMMAND" in
  *'rm -rf ~'* | *'rm -rf $HOME'* | *'rm -rf /home'*)
    echo -e "${RED}BLOCKED:${NC} Refusing to delete home directory"
    exit 2
    ;;
  *'rm -rf /'*)
    echo -e "${RED}BLOCKED:${NC} Refusing to delete root filesystem"
    exit 2
    ;;
  *'> /dev/sda'* | *'dd if='*'of=/dev/'*)
    echo -e "${RED}BLOCKED:${NC} Refusing to write directly to block device"
    exit 2
    ;;
  *'mkfs.'*'/dev/'*)
    echo -e "${RED}BLOCKED:${NC} Refusing to format disk"
    exit 2
    ;;
  *':(){:|:&};:'* | *'fork bomb'*)
    echo -e "${RED}BLOCKED:${NC} Fork bomb detected"
    exit 2
    ;;
esac

# Warning patterns (allow but warn)
case "$COMMAND" in
  *'rm -rf'*)
    echo -e "${YELLOW}WARNING:${NC} Recursive force delete - verify target"
    ;;
  *'chmod -R 777'*)
    echo -e "${YELLOW}WARNING:${NC} Insecure permissions"
    ;;
  *'curl'*'| bash'* | *'wget'*'| bash'*)
    echo -e "${YELLOW}WARNING:${NC} Piping to bash - verify source"
    ;;
  *'--force'* | *'-f'*)
    # Only warn on destructive force flags
    case "$COMMAND" in
      *'git push'* | *'git reset'* | *'docker rm'*)
        echo -e "${YELLOW}WARNING:${NC} Force flag on destructive operation"
        ;;
    esac
    ;;
esac

# Allow command
exit 0
