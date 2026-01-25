#!/bin/bash
set -euo pipefail
# ============================================
# Package Manager Detection
# ============================================

detect_package_manager() {
  if command -v pacman &>/dev/null; then
    echo "pacman"
  elif command -v apt-get &>/dev/null; then
    echo "apt"
  elif command -v dnf &>/dev/null; then
    echo "dnf"
  elif command -v yum &>/dev/null; then
    echo "yum"
  elif command -v apk &>/dev/null; then
    echo "apk"
  elif command -v brew &>/dev/null; then
    echo "brew"
  else
    echo "none"
  fi
}
