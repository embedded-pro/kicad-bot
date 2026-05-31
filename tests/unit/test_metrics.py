"""Unit tests for the metrics accumulator."""

from __future__ import annotations

from pathlib import Path

from kicad_bot.metrics import (
    CapabilityResult,
    Gate,
    load_metrics,
    update_metrics_file,
)


def _result(name: str, passed: bool) -> CapabilityResult:
    return CapabilityResult(
        name=name,
        summary={"k": "v"},
        gates=[Gate(name="g", enabled=True, passed=passed, count=0 if passed else 3)],
    )


def test_update_metrics_file_roundtrip(tmp_path: Path) -> None:
    path = update_metrics_file(tmp_path, _result("verify", True), project={"name": "demo"})
    metrics = load_metrics(path)
    assert metrics["project"]["name"] == "demo"
    assert metrics["capabilities"]["verify"]["passed"] is True
    assert metrics["passed"] is True


def test_merge_preserves_prior_capabilities(tmp_path: Path) -> None:
    update_metrics_file(tmp_path, _result("verify", True))
    path = update_metrics_file(tmp_path, _result("bom", False))
    metrics = load_metrics(path)
    assert set(metrics["capabilities"]) == {"verify", "bom"}
    # One failing capability fails the whole document.
    assert metrics["passed"] is False


def test_capability_passed_ignores_disabled_gates() -> None:
    result = CapabilityResult(
        name="verify",
        gates=[
            Gate(name="a", enabled=False, passed=False, count=5),
            Gate(name="b", enabled=True, passed=True),
        ],
    )
    assert result.passed is True
