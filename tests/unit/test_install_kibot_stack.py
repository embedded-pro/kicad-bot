"""Unit tests for the KiBot-stack install script wired into ``action.yml``.

These guard the fix for the wxPython source-build failure (``Failed to build
wxPython``): the stack must install a *prebuilt* wxPython wheel -- binary-only,
from the official extras index -- *before* installing kibot, so pip never falls
back to compiling wxPython from source on a CI runner.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "install-kibot-stack.sh"
ACTION = ROOT / "action.yml"


@pytest.fixture
def script_text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_script_exists_and_is_bash(script_text: str) -> None:
    assert SCRIPT.is_file()
    assert script_text.startswith("#!") and "bash" in script_text.splitlines()[0]


def test_installs_prebuilt_wxpython_binary_only(script_text: str) -> None:
    # Restrict pip to binary wheels so it can never silently build from source...
    assert "--only-binary wxPython" in script_text
    # ...and point it at the official prebuilt-wheel extras index.
    assert "extras.wxpython.org" in script_text
    assert "--find-links" in script_text


def test_never_builds_wxpython_from_source(script_text: str) -> None:
    assert "--no-binary" not in script_text


def test_wxpython_installed_before_kibot(script_text: str) -> None:
    wx = script_text.index("pip install --only-binary wxPython")
    kibot = script_text.index("pip install kibot")
    assert 0 <= wx < kibot


def test_action_delegates_to_script() -> None:
    action = ACTION.read_text(encoding="utf-8")
    # The action calls the script instead of the old inline source-build install.
    assert "scripts/install-kibot-stack.sh" in action
    assert "pip install kibot kicost kidiff" not in action
