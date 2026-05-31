"""Unit tests for report and PR-comment rendering."""

from __future__ import annotations

from pathlib import Path

from kicad_bot.metrics import CapabilityResult, Gate, load_metrics, update_metrics_file
from kicad_bot.pr_comment import COMMENT_MARKER
from kicad_bot.report import render_pr_comment, render_report, write_reports


def _metrics(tmp_path: Path, passed: bool) -> dict:
    result = CapabilityResult(
        name="verify",
        summary={"erc_violations": 0 if passed else 2, "drc_violations": 0},
        gates=[
            Gate(name="fail-on-erc", enabled=True, passed=passed, count=0 if passed else 2),
            Gate(name="fail-on-drc", enabled=True, passed=True, count=0),
        ],
    )
    path = update_metrics_file(tmp_path, result, project={"name": "demo"})
    return load_metrics(path)


def test_pr_comment_has_marker(tmp_path: Path) -> None:
    body = render_pr_comment(_metrics(tmp_path, passed=True))
    assert COMMENT_MARKER in body
    assert "all checks passed" in body


def test_report_reflects_failure(tmp_path: Path) -> None:
    report = render_report(_metrics(tmp_path, passed=False))
    assert "FAIL" in report
    assert "fail-on-erc" in report
    assert "demo" in report


def test_write_reports_creates_files(tmp_path: Path) -> None:
    metrics = _metrics(tmp_path, passed=True)
    report_path, comment_path = write_reports(metrics, str(tmp_path))
    assert Path(report_path).is_file()
    assert Path(comment_path).is_file()
    assert COMMENT_MARKER in Path(comment_path).read_text(encoding="utf-8")
