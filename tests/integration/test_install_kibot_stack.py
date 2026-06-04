"""Integration test: run the real install script with stubbed system tools.

We execute ``scripts/install-kibot-stack.sh`` for real, but with fake
``sudo``/``apt-get``/``add-apt-repository``/``pip`` executables on ``PATH`` that
just record their arguments. This exercises the actual script end to end --
without network access or root -- and proves that it installs a prebuilt
wxPython wheel (binary-only) *before* kibot, so the original "Failed to build
wxPython" failure can never recur.

The test only needs ``bash`` and so runs in the integration job regardless of
whether KiCad is installed.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "install-kibot-stack.sh"

# Each stub logs "<name> <args...>" to $KICAD_BOT_CALLS and exits 0.
_STUB = '#!/usr/bin/env bash\necho "$(basename "$0") $*" >> "$KICAD_BOT_CALLS"\nexit 0\n'


def _make_stub(bindir: Path, name: str) -> None:
    path = bindir / name
    path.write_text(_STUB, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def run_script(tmp_path: Path):
    if shutil.which("bash") is None:
        pytest.skip("bash not available; skipping install-script integration test")

    bindir = tmp_path / "bin"
    bindir.mkdir()
    for tool in ("sudo", "apt-get", "add-apt-repository", "pip"):
        _make_stub(bindir, tool)

    calls = tmp_path / "calls.log"
    env = dict(os.environ)
    env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"
    env["KICAD_BOT_CALLS"] = str(calls)

    def _run(*args: str) -> list[str]:
        proc = subprocess.run(
            ["bash", str(SCRIPT), *args],
            env=env,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        return calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []

    return _run


def test_script_runs_clean(run_script) -> None:
    # The script completes successfully with the stubbed toolchain.
    assert run_script("9")


def test_wxpython_wheel_installed_before_kibot(run_script) -> None:
    lines = run_script("9")
    pip_calls = [line for line in lines if line.startswith("pip ")]

    # wxPython is installed as a prebuilt binary wheel from the extras index...
    wx_index = "https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-"
    assert any("--only-binary" in line and wx_index in line and "wxPython" in line for line in pip_calls)

    # ...strictly before kibot, so kibot's wxPython dependency is already met.
    wx_idx = next(i for i, line in enumerate(pip_calls) if "wxPython" in line)
    kibot_idx = next(i for i, line in enumerate(pip_calls) if "kibot" in line)
    assert wx_idx < kibot_idx

    # wxPython is never forced to build from source.
    assert all("--no-binary" not in line for line in pip_calls)


def test_passes_kicad_version_to_ppa(run_script) -> None:
    lines = run_script("8")
    assert any("add-apt-repository" in line and "kicad-8.0-releases" in line for line in lines)
