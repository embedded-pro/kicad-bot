"""Pytest configuration: make the package importable from a source checkout.

CI installs the package with ``pip install -e``, but adding ``src`` to the path
also lets the suite run from a bare checkout without an install step.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

FIXTURES = Path(__file__).resolve().parent / "fixtures"
