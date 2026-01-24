"""Pytest configuration for ai-guardrails tests.

Adds lib/python to sys.path for imports.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add lib/python to path for importing coderabbit_parser
lib_path = Path(__file__).parent.parent / "lib" / "python"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))
