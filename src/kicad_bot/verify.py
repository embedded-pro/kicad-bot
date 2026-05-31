"""``kicad-bot-verify`` -- headless ERC/DRC via ``kicad-cli``.

Runs ``kicad-cli sch erc`` and ``kicad-cli pcb drc`` against the project's
schematic and board, parses the JSON reports, and applies the ``fail-on-erc`` /
``fail-on-drc`` gates at the configured severity. Designed to be the MVP gate:
deterministic, network-free, and exit-code driven for CI.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import cli
from .cli import KicadBotError
from .metrics import CapabilityResult, Gate, update_metrics_file
from .report import write_reports

#: Severity ordering used to evaluate the ``--drc-severity`` threshold.
SEVERITY_RANK = {"ignore": 0, "warning": 1, "error": 2}

#: Which severities a threshold *gates on*.
_THRESHOLD_SETS = {
    "error": {"error"},
    "warning": {"error", "warning"},
    "all": {"error", "warning", "ignore"},
}


@dataclass(frozen=True)
class Violation:
    """A single ERC/DRC violation, normalised across kicad-cli report shapes."""

    severity: str
    type: str
    description: str
    excluded: bool = False


@dataclass
class CheckReport:
    """Parsed result of one ERC or DRC report."""

    kind: str  # "erc" | "drc"
    source: str
    violations: list[Violation]

    def counts_by_severity(self) -> dict[str, int]:
        counts = {"error": 0, "warning": 0, "ignore": 0}
        for v in self.violations:
            if v.excluded:
                continue
            counts[v.severity] = counts.get(v.severity, 0) + 1
        return counts

    def gated_count(self, severity: str) -> int:
        """Number of non-excluded violations at or above ``severity``."""
        selected = _THRESHOLD_SETS.get(severity, _THRESHOLD_SETS["error"])
        return sum(1 for v in self.violations if not v.excluded and v.severity in selected)


def _coerce_violation(raw: dict[str, Any], default_severity: str = "error") -> Violation:
    severity = str(raw.get("severity", default_severity)).lower()
    if severity not in SEVERITY_RANK:
        severity = default_severity
    return Violation(
        severity=severity,
        type=str(raw.get("type", "")),
        description=str(raw.get("description") or raw.get("message") or ""),
        excluded=bool(raw.get("excluded", False)),
    )


def parse_report(data: dict[str, Any], kind: str) -> CheckReport:
    """Parse a kicad-cli ERC/DRC JSON document into a :class:`CheckReport`.

    Handles the several shapes kicad-cli emits: a top-level ``violations`` list,
    per-sheet ``sheets[].violations`` (ERC), and the DRC-only
    ``unconnected_items`` / ``schematic_parity`` lists (counted as errors).
    """
    violations: list[Violation] = []

    for raw in data.get("violations", []) or []:
        if isinstance(raw, dict):
            violations.append(_coerce_violation(raw))

    for sheet in data.get("sheets", []) or []:
        if not isinstance(sheet, dict):
            continue
        for raw in sheet.get("violations", []) or []:
            if isinstance(raw, dict):
                violations.append(_coerce_violation(raw))

    for raw in data.get("unconnected_items", []) or []:
        if isinstance(raw, dict):
            violations.append(_coerce_violation({**raw, "type": raw.get("type", "unconnected")}))

    for raw in data.get("schematic_parity", []) or []:
        if isinstance(raw, dict):
            violations.append(_coerce_violation({**raw, "type": raw.get("type", "schematic_parity")}))

    return CheckReport(kind=kind, source=str(data.get("source", "")), violations=violations)


def parse_report_file(path: str | Path, kind: str) -> CheckReport:
    """Load and parse a kicad-cli JSON report from disk."""
    p = Path(path)
    with p.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise KicadBotError(f"Unexpected {kind} report shape in {p}")
    return parse_report(data, kind)


def _run_erc(project: cli.Project, out_path: Path, severity: str) -> CheckReport | None:
    if project.schematic is None:
        return None
    args = [
        cli.kicad_cli_name(),
        "sch",
        "erc",
        str(project.schematic),
        "--output",
        str(out_path),
        "--format",
        "json",
        "--severity-all",
    ]
    result = cli.run_command(args, cwd=project.directory)
    if not out_path.is_file():
        raise KicadBotError(f"kicad-cli did not produce an ERC report.\n{result.stderr.strip()}")
    report = parse_report_file(out_path, "erc")
    cli.LOG.info("ERC: %s", report.counts_by_severity())
    return report


def _run_drc(project: cli.Project, out_path: Path, severity: str, schematic_parity: bool) -> CheckReport | None:
    if project.board is None:
        return None
    args = [
        cli.kicad_cli_name(),
        "pcb",
        "drc",
        str(project.board),
        "--output",
        str(out_path),
        "--format",
        "json",
        "--severity-all",
    ]
    if schematic_parity and project.schematic is not None:
        args.append("--schematic-parity")
    result = cli.run_command(args, cwd=project.directory)
    if not out_path.is_file():
        raise KicadBotError(f"kicad-cli did not produce a DRC report.\n{result.stderr.strip()}")
    report = parse_report_file(out_path, "drc")
    cli.LOG.info("DRC: %s", report.counts_by_severity())
    return report


def build_result(
    erc: CheckReport | None,
    drc: CheckReport | None,
    *,
    fail_on_erc: bool,
    fail_on_drc: bool,
    severity: str,
) -> CapabilityResult:
    """Evaluate gates and assemble the verify capability result."""
    gates: list[Gate] = []
    summary: dict[str, Any] = {}

    erc_count = erc.gated_count(severity) if erc else 0
    drc_count = drc.gated_count(severity) if drc else 0

    summary["erc_violations"] = erc_count if erc else "n/a (no schematic)"
    summary["drc_violations"] = drc_count if drc else "n/a (no board)"
    summary["severity_threshold"] = severity

    gates.append(
        Gate(
            name="fail-on-erc",
            enabled=fail_on_erc and erc is not None,
            passed=not (fail_on_erc and erc is not None and erc_count > 0),
            count=erc_count,
            detail=f"{erc_count} ERC violation(s) ≥ {severity}" if erc else "no schematic",
        )
    )
    gates.append(
        Gate(
            name="fail-on-drc",
            enabled=fail_on_drc and drc is not None,
            passed=not (fail_on_drc and drc is not None and drc_count > 0),
            count=drc_count,
            detail=f"{drc_count} DRC violation(s) ≥ {severity}" if drc else "no board",
        )
    )
    return CapabilityResult(name="verify", summary=summary, gates=gates)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kicad-bot-verify",
        description="Run headless ERC/DRC and apply CI gates.",
    )
    cli.add_common_args(parser)
    cli.add_bool_flag(parser, "fail-on-erc", default=True, help="Fail on ERC violations.")
    cli.add_bool_flag(parser, "fail-on-drc", default=True, help="Fail on DRC violations.")
    parser.add_argument(
        "--drc-severity",
        choices=["error", "warning", "all"],
        default="error",
        help="Minimum severity that gates the build (default: error).",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cli.configure_logging(args.verbose)

    config = cli.load_config(args.config_path, args.project_dir)
    verify_cfg = config.get("verify", {}) if isinstance(config.get("verify"), dict) else {}
    severity = args.drc_severity or verify_cfg.get("drc_severity", "error")
    schematic_parity = bool(verify_cfg.get("schematic_parity", True))

    project = cli.discover_project(args.project_dir, args.schematic, args.board)
    if project.schematic is None and project.board is None:
        raise KicadBotError(
            f"No .kicad_sch or .kicad_pcb found in {project.directory}. "
            "Pass --schematic/--board or check --project-dir."
        )

    out_dir = cli.ensure_output_dir(args.output_dir)
    erc = _run_erc(project, out_dir / "erc.json", severity)
    drc = _run_drc(project, out_dir / "drc.json", severity, schematic_parity)

    result = build_result(
        erc,
        drc,
        fail_on_erc=args.fail_on_erc,
        fail_on_drc=args.fail_on_drc,
        severity=severity,
    )

    metrics_path = update_metrics_file(
        out_dir,
        result,
        project={"name": project.name, "directory": str(project.directory)},
    )
    from .metrics import load_metrics

    metrics = load_metrics(metrics_path)
    report_path, comment_path = write_reports(metrics, str(out_dir))

    passed = result.passed
    cli.set_output("erc-violations", result.summary["erc_violations"])
    cli.set_output("drc-violations", result.summary["drc_violations"])
    cli.set_output("report-path", report_path)
    cli.set_output("metrics-path", str(metrics_path))
    cli.set_output("passed", "true" if passed else "false")
    cli.append_step_summary(Path(report_path).read_text(encoding="utf-8"))

    if args.pr_comment:
        try:
            from .pr_comment import upsert_pr_comment

            upsert_pr_comment(Path(comment_path).read_text(encoding="utf-8"))
        except Exception as exc:  # never fail the build on comment errors
            cli.LOG.warning("PR comment failed (non-fatal): %s", exc)

    cli.LOG.info("verify: %s", "PASS" if passed else "FAIL")
    return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    """Console-script entry point: run the capability, mapping errors to codes."""
    try:
        return run(argv)
    except KicadBotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
