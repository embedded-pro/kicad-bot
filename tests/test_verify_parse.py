"""Unit tests for the kicad-cli ERC/DRC report parser and gate logic."""

from __future__ import annotations

import json
from pathlib import Path

from kicad_bot.verify import build_result, parse_report, parse_report_file

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_parse_erc_groups_sheet_violations() -> None:
    data = json.loads((FIXTURES / "erc_sample.json").read_text())
    report = parse_report(data, "erc")
    counts = report.counts_by_severity()
    # The excluded warning is dropped from severity counts.
    assert counts == {"error": 1, "warning": 1, "ignore": 0}


def test_parse_drc_counts_unconnected_as_error() -> None:
    report = parse_report_file(FIXTURES / "drc_sample.json", "drc")
    counts = report.counts_by_severity()
    # 1 explicit error + 1 unconnected item (error); excluded warning dropped.
    assert counts["error"] == 2
    assert counts["warning"] == 0


def test_gated_count_respects_threshold() -> None:
    report = parse_report_file(FIXTURES / "erc_sample.json", "erc")
    assert report.gated_count("error") == 1
    assert report.gated_count("warning") == 2  # error + warning
    assert report.gated_count("all") == 2  # no ignore-severity items here


def test_excluded_violations_never_gate() -> None:
    data = {
        "source": "x.kicad_pcb",
        "violations": [{"severity": "error", "type": "clearance", "description": "x", "excluded": True}],
    }
    report = parse_report(data, "drc")
    assert report.gated_count("error") == 0


def test_build_result_fails_when_gate_tripped() -> None:
    erc = parse_report_file(FIXTURES / "erc_sample.json", "erc")
    drc = parse_report_file(FIXTURES / "drc_sample.json", "drc")
    result = build_result(erc, drc, fail_on_erc=True, fail_on_drc=True, severity="error")
    assert result.passed is False
    gates = {g.name: g for g in result.gates}
    assert gates["fail-on-erc"].count == 1
    assert gates["fail-on-drc"].count == 2


def test_build_result_passes_when_gate_disabled() -> None:
    erc = parse_report_file(FIXTURES / "erc_sample.json", "erc")
    drc = parse_report_file(FIXTURES / "drc_sample.json", "drc")
    result = build_result(erc, drc, fail_on_erc=False, fail_on_drc=False, severity="error")
    assert result.passed is True


def test_build_result_handles_missing_board() -> None:
    erc = parse_report_file(FIXTURES / "erc_sample.json", "erc")
    result = build_result(erc, None, fail_on_erc=True, fail_on_drc=True, severity="error")
    gates = {g.name: g for g in result.gates}
    # DRC gate is disabled when there is no board to check.
    assert gates["fail-on-drc"].enabled is False
    assert result.summary["drc_violations"] == "n/a (no board)"
