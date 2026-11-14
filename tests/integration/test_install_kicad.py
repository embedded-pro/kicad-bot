"""Integration test: run ``scripts/install-kicad.sh`` with stubbed system tools.

The script runs for real, but ``add-apt-repository``, ``apt-get``, ``dpkg`` and
``kicad-cli`` are stubs that record their arguments, and ``sudo`` just runs its
command. The PPA source files live in a temporary directory (``APT_SOURCES_DIR``).

This guards the Ubuntu 26.04 regression: on amd64v3 runners apt ignored the
KiCad PPA's amd64-only builds and installed Ubuntu's KiCad 9 even when KiCad 10
was requested, and nothing noticed. The script must pin the PPA source to the
dpkg architecture and fail when ``kicad-cli`` reports another major version.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "install-kicad.sh"

_LOG = 'echo "$(basename "$0") $*" >> "$KICAD_BOT_CALLS"\n'
_STUBS = {
    "sudo": "#!/usr/bin/env bash\n" + _LOG + 'exec "$@"\n',
    "add-apt-repository": "#!/usr/bin/env bash\n" + _LOG + "exit 0\n",
    "apt-get": "#!/usr/bin/env bash\n" + _LOG + "exit 0\n",
    "dpkg": "#!/usr/bin/env bash\n" + _LOG + 'echo "${FAKE_DPKG_ARCH:-amd64}"\n',
    "kicad-cli": "#!/usr/bin/env bash\n" + _LOG + 'echo "$FAKE_KICAD_VERSION"\n',
}

PPA_SOURCE = """Types: deb
URIs: https://ppa.launchpadcontent.net/kicad/kicad-10.0-releases/ubuntu/
Suites: resolute
Components: main
Signed-By: /etc/apt/keyrings/kicad.gpg
"""


@dataclass
class Run:
    returncode: int
    stdout: str
    stderr: str
    calls: list[str]


@pytest.fixture
def sources_dir(tmp_path: Path) -> Path:
    path = tmp_path / "sources.list.d"
    path.mkdir()
    return path


@pytest.fixture
def run_script(tmp_path: Path, sources_dir: Path):
    if shutil.which("bash") is None:
        pytest.skip("bash not available; skipping install-script integration test")

    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name, body in _STUBS.items():
        path = bindir / name
        path.write_text(body, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    calls = tmp_path / "calls.log"

    def _run(*args: str, kicad_version: str) -> Run:
        env = dict(os.environ)
        env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"
        env["KICAD_BOT_CALLS"] = str(calls)
        env["APT_SOURCES_DIR"] = str(sources_dir)
        env["FAKE_KICAD_VERSION"] = kicad_version
        calls.unlink(missing_ok=True)
        proc = subprocess.run(["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True)
        lines = calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []
        return Run(proc.returncode, proc.stdout, proc.stderr, lines)

    return _run


def test_adds_the_requested_ppa(run_script) -> None:
    run = run_script("10", kicad_version="10.0.8")
    assert run.returncode == 0, run.stderr
    assert "add-apt-repository --yes ppa:kicad/kicad-10.0-releases" in run.calls


def test_default_install_is_kicad_without_recommends(run_script) -> None:
    run = run_script("10", kicad_version="10.0.8")
    assert "apt-get install --yes --no-install-recommends kicad" in run.calls


def test_extra_arguments_replace_the_default_install(run_script) -> None:
    run = run_script("9", "kicad", "xvfb", kicad_version="9.0.8")
    assert run.returncode == 0, run.stderr
    assert "apt-get install --yes kicad xvfb" in run.calls


def test_pins_the_ppa_source_to_the_dpkg_architecture(run_script, sources_dir: Path) -> None:
    source = sources_dir / "kicad-ubuntu-kicad-10_0-releases-resolute.sources"
    source.write_text(PPA_SOURCE, encoding="utf-8")

    run = run_script("10", kicad_version="10.0.8")

    assert run.returncode == 0, run.stderr
    lines = source.read_text(encoding="utf-8").splitlines()
    assert lines[:2] == ["Types: deb", "Architectures: amd64"]
    # The pin is written before apt reads the indexes.
    pin = next(i for i, line in enumerate(run.calls) if line.startswith("sudo sed "))
    update = run.calls.index("apt-get update")
    assert pin < update


def test_pin_is_idempotent(run_script, sources_dir: Path) -> None:
    source = sources_dir / "kicad-ubuntu-kicad-10_0-releases-resolute.sources"
    source.write_text(PPA_SOURCE, encoding="utf-8")

    run_script("10", kicad_version="10.0.8")
    run_script("10", kicad_version="10.0.8")

    assert source.read_text(encoding="utf-8").count("Architectures:") == 1


def test_uses_the_machine_architecture(run_script, sources_dir: Path, monkeypatch) -> None:
    monkeypatch.setenv("FAKE_DPKG_ARCH", "arm64")
    source = sources_dir / "kicad-ubuntu-kicad-10_0-releases-resolute.sources"
    source.write_text(PPA_SOURCE, encoding="utf-8")

    run_script("10", kicad_version="10.0.8")

    assert "Architectures: arm64" in source.read_text(encoding="utf-8")


def test_leaves_other_sources_alone(run_script, sources_dir: Path) -> None:
    ubuntu = sources_dir / "ubuntu.sources"
    ubuntu.write_text("Types: deb\nURIs: http://archive.ubuntu.com/ubuntu/\nSuites: resolute\n", encoding="utf-8")
    other_kicad = sources_dir / "kicad-ubuntu-kicad-9_0-releases-resolute.sources"
    other_kicad.write_text(PPA_SOURCE.replace("10.0", "9.0"), encoding="utf-8")
    before = {path: path.read_text(encoding="utf-8") for path in (ubuntu, other_kicad)}

    run_script("10", kicad_version="10.0.8")

    assert {path: path.read_text(encoding="utf-8") for path in before} == before


def test_keeps_an_existing_architectures_line(run_script, sources_dir: Path) -> None:
    source = sources_dir / "kicad-ubuntu-kicad-10_0-releases-resolute.sources"
    pinned = PPA_SOURCE.replace("Types: deb\n", "Types: deb\nArchitectures: amd64 i386\n")
    source.write_text(pinned, encoding="utf-8")

    run = run_script("10", kicad_version="10.0.8")

    assert source.read_text(encoding="utf-8") == pinned
    assert not any(line.startswith("sudo sed ") for line in run.calls)


def test_fails_when_another_kicad_major_is_installed(run_script) -> None:
    # The Ubuntu 26.04 regression: KiCad 10 requested, the distribution's 9.0.8 installed.
    run = run_script("10", kicad_version="9.0.8")
    assert run.returncode == 1
    assert "::error::kicad-bot asked for KiCad 10, but kicad-cli reports 9.0.8." in run.stderr


def test_reports_the_installed_version(run_script) -> None:
    run = run_script("10", kicad_version="10.0.8")
    assert run.returncode == 0, run.stderr
    assert "install-kicad: KiCad 10.0.8" in run.stdout
