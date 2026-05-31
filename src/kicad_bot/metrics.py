"""Machine-readable metrics emitted by every kicad-bot capability.

A single ``kicad_bot_metrics.json`` accumulates results across the capabilities
that run in one job. Each capability merges its own section in (rather than
overwriting the file) so a combined ``verify`` + ``bom`` + ``diff`` run yields a
single document downstream tooling can consume.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import __version__

METRICS_FILENAME = "kicad_bot_metrics.json"
METRICS_SCHEMA = "kicad-bot/metrics/v1"


@dataclass
class Gate:
    """The outcome of a single CI gate (e.g. ``fail-on-drc``)."""

    name: str
    enabled: bool
    passed: bool
    count: int = 0
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "passed": self.passed,
            "count": self.count,
            "detail": self.detail,
        }


@dataclass
class CapabilityResult:
    """One capability's contribution to the metrics document."""

    name: str
    summary: dict[str, Any] = field(default_factory=dict)
    gates: list[Gate] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """A capability passes when none of its *enabled* gates failed."""
        return all(g.passed for g in self.gates if g.enabled)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "summary": self.summary,
            "gates": {g.name: g.to_dict() for g in self.gates},
        }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def load_metrics(path: str | Path) -> dict[str, Any]:
    """Load an existing metrics document, or return a fresh skeleton."""
    p = Path(path)
    if p.is_file():
        try:
            with p.open(encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "schema": METRICS_SCHEMA,
        "tool_version": __version__,
        "generated_at": _now_iso(),
        "project": {},
        "capabilities": {},
    }


def merge_capability(
    metrics: dict[str, Any],
    result: CapabilityResult,
    *,
    project: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge a capability result into the metrics document, in place."""
    metrics.setdefault("schema", METRICS_SCHEMA)
    metrics.setdefault("tool_version", __version__)
    metrics["generated_at"] = _now_iso()
    if project:
        metrics.setdefault("project", {}).update(project)
    metrics.setdefault("capabilities", {})[result.name] = result.to_dict()
    metrics["passed"] = all(cap.get("passed", True) for cap in metrics["capabilities"].values())
    return metrics


def write_metrics(metrics: dict[str, Any], output_dir: str | Path) -> Path:
    """Write the metrics document to ``output_dir/kicad_bot_metrics.json``."""
    path = Path(output_dir) / METRICS_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def update_metrics_file(
    output_dir: str | Path,
    result: CapabilityResult,
    *,
    project: dict[str, Any] | None = None,
) -> Path:
    """Load → merge one capability → write, the common single-call path."""
    path = Path(output_dir) / METRICS_FILENAME
    metrics = load_metrics(path)
    merge_capability(metrics, result, project=project)
    return write_metrics(metrics, output_dir)
