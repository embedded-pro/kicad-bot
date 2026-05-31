"""End-to-end integration tests for ``kicad-bot-verify`` against real kicad-cli.

These exercise the full pipeline -- argparse -> kicad-cli subprocess -> JSON
parse -> gate evaluation -> metrics/report -> exit code -- on the checked-in
example projects. They require a real ``kicad-cli`` on PATH and are skipped
automatically (via the ``kicad_cli`` fixture) when KiCad is not installed, so
the unit suite stays hermetic. In CI the ``integration`` job installs KiCad and
runs them for real; that job is a good candidate for a required status check.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from kicad_bot import verify
from kicad_bot.metrics import METRICS_FILENAME, load_metrics


def _run_verify_inproc(project_dir: Path, output_dir: Path, *extra: str) -> int:
    argv = [
        "--project-dir",
        str(project_dir),
        "--output-dir",
        str(output_dir),
        "--no-pr-comment",
        *extra,
    ]
    return verify.run(argv)


@pytest.mark.usefixtures("kicad_cli")
def test_minimal_project_passes(examples_dir: Path, tmp_path: Path) -> None:
    """The clean minimal project produces zero violations and exits 0."""
    out = tmp_path / "out"
    rc = _run_verify_inproc(examples_dir / "minimal", out)

    assert rc == 0
    assert (out / "erc.json").is_file()
    assert (out / "drc.json").is_file()
    assert (out / "report.md").is_file()

    metrics = load_metrics(out / METRICS_FILENAME)
    assert metrics["passed"] is True
    assert metrics["capabilities"]["verify"]["passed"] is True


@pytest.mark.usefixtures("kicad_cli")
def test_drc_violation_project_fails(examples_dir: Path, tmp_path: Path) -> None:
    """The shorting-tracks board trips the DRC gate and exits 1."""
    out = tmp_path / "out"
    rc = _run_verify_inproc(examples_dir / "drc-violation", out)

    assert rc == 1
    drc = json.loads((out / "drc.json").read_text(encoding="utf-8"))
    # kicad-cli reported at least one violation in its raw output...
    raw_count = len(drc.get("violations", [])) + len(drc.get("unconnected_items", []))
    assert raw_count > 0

    # ...and our gate counted it.
    metrics = load_metrics(out / METRICS_FILENAME)
    verify_caps = metrics["capabilities"]["verify"]
    assert verify_caps["passed"] is False
    assert verify_caps["gates"]["fail-on-drc"]["count"] > 0


@pytest.mark.usefixtures("kicad_cli")
def test_drc_violation_passes_when_gate_disabled(examples_dir: Path, tmp_path: Path) -> None:
    """With --no-fail-on-drc the same board reports but does not fail the build."""
    out = tmp_path / "out"
    rc = _run_verify_inproc(examples_dir / "drc-violation", out, "--no-fail-on-drc")
    assert rc == 0
    metrics = load_metrics(out / METRICS_FILENAME)
    # Gate is disabled, so it does not fail; the violation count is still recorded.
    assert metrics["capabilities"]["verify"]["gates"]["fail-on-drc"]["enabled"] is False


@pytest.mark.usefixtures("kicad_cli")
def test_console_entry_point_runs(examples_dir: Path, tmp_path: Path) -> None:
    """The packaged module entry point works as a real subprocess."""
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "kicad_bot.verify",
            "--project-dir",
            str(examples_dir / "minimal"),
            "--output-dir",
            str(out),
            "--no-pr-comment",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert (out / METRICS_FILENAME).is_file()
