"""Pytest configuration shared by the unit and integration suites.

CI installs the package with ``pip install -e``, but adding ``src`` to the path
also lets the suite run from a bare checkout without an install step.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

FIXTURES = Path(__file__).resolve().parent / "fixtures"
EXAMPLES = ROOT / "examples"


@pytest.fixture
def fixtures_dir() -> Path:
    """Directory holding the checked-in JSON report fixtures."""
    return FIXTURES


@pytest.fixture
def examples_dir() -> Path:
    """Directory holding the runnable example KiCad projects."""
    return EXAMPLES


@pytest.fixture(scope="session")
def kicad_cli() -> str:
    """Path to a real ``kicad-cli``, or skip the test when none is installed.

    Integration tests that drive the actual KiCad engine depend on this; they
    are skipped automatically on machines (or CI jobs) without KiCad so the
    unit suite stays hermetic.
    """
    import os

    name = os.environ.get("KICAD_CLI", "kicad-cli")
    resolved = shutil.which(name)
    if resolved is None:
        pytest.skip(f"{name} not found on PATH; skipping kicad-cli integration test")
    return resolved
