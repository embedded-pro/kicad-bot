"""Unit tests for the shared CLI plumbing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kicad_bot import cli
from kicad_bot.cli import KicadBotError


def test_discover_single_project(tmp_path: Path) -> None:
    (tmp_path / "board.kicad_sch").write_text("(kicad_sch)", encoding="utf-8")
    (tmp_path / "board.kicad_pcb").write_text("(kicad_pcb)", encoding="utf-8")
    project = cli.discover_project(str(tmp_path))
    assert project.schematic is not None and project.schematic.name == "board.kicad_sch"
    assert project.board is not None and project.board.name == "board.kicad_pcb"
    assert project.name == "board"


def test_discover_ambiguous_raises(tmp_path: Path) -> None:
    (tmp_path / "a.kicad_sch").write_text("", encoding="utf-8")
    (tmp_path / "b.kicad_sch").write_text("", encoding="utf-8")
    with pytest.raises(KicadBotError):
        cli.discover_project(str(tmp_path))


def test_discover_prefers_dirname_match(tmp_path: Path) -> None:
    proj = tmp_path / "widget"
    proj.mkdir()
    (proj / "widget.kicad_pcb").write_text("", encoding="utf-8")
    (proj / "panel.kicad_pcb").write_text("", encoding="utf-8")
    project = cli.discover_project(str(proj))
    assert project.board is not None and project.board.name == "widget.kicad_pcb"


def test_load_config_missing_returns_empty(tmp_path: Path) -> None:
    assert cli.load_config("kicad-bot.json", str(tmp_path)) == {}


def test_load_config_reads_json(tmp_path: Path) -> None:
    (tmp_path / "kicad-bot.json").write_text(json.dumps({"verify": {"drc_severity": "warning"}}), encoding="utf-8")
    cfg = cli.load_config("kicad-bot.json", str(tmp_path))
    assert cfg["verify"]["drc_severity"] == "warning"


def test_load_config_invalid_json_raises(tmp_path: Path) -> None:
    (tmp_path / "kicad-bot.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(KicadBotError):
        cli.load_config("kicad-bot.json", str(tmp_path))


def test_set_output_and_step_summary(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "out.txt"
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    cli.set_output("erc-violations", 3)
    cli.append_step_summary("# hello")
    assert "erc-violations=3" in out.read_text(encoding="utf-8")
    assert "# hello" in summary.read_text(encoding="utf-8")


def test_tool_available_for_missing() -> None:
    assert cli.tool_available("definitely-not-a-real-tool-xyz") is False
