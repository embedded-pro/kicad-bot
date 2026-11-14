"""Unit tests for the KiCad install script wired into ``action.yml``.

These guard the fix for Ubuntu 26.04 runners, where apt installed Ubuntu's
KiCad 9 instead of the requested PPA KiCad 10: the action and the KiBot stack
must both install KiCad through ``scripts/install-kicad.sh``, which pins the PPA
source to the dpkg architecture and checks the installed major version.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "install-kicad.sh"
KIBOT_SCRIPT = ROOT / "scripts" / "install-kibot-stack.sh"
ACTION = ROOT / "action.yml"


@pytest.fixture
def script_text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_script_exists_and_is_bash(script_text: str) -> None:
    assert SCRIPT.is_file()
    assert script_text.startswith("#!") and "bash" in script_text.splitlines()[0]


def test_pins_ppa_source_to_dpkg_architecture(script_text: str) -> None:
    assert "dpkg --print-architecture" in script_text
    assert "Architectures:" in script_text


def test_checks_installed_major_version(script_text: str) -> None:
    assert "kicad-cli version" in script_text
    assert "::error::" in script_text


def test_pin_comes_before_apt_update(script_text: str) -> None:
    assert script_text.index("Architectures:") < script_text.index("apt-get update")


def test_action_installs_kicad_through_script() -> None:
    action = ACTION.read_text(encoding="utf-8")
    assert "scripts/install-kicad.sh" in action
    assert "add-apt-repository" not in action


def test_kibot_stack_installs_kicad_through_script() -> None:
    kibot = KIBOT_SCRIPT.read_text(encoding="utf-8")
    assert "install-kicad.sh" in kibot
    assert "add-apt-repository" not in kibot
