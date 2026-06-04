"""Unit tests for PR-comment detection and the skip path (no network)."""

from __future__ import annotations

import json
from pathlib import Path

from kicad_bot.pr_comment import detect_pr_number, upsert_pr_comment


def test_detect_pr_number_from_event(tmp_path: Path) -> None:
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"number": 42}}), encoding="utf-8")
    assert detect_pr_number(str(event)) == 42


def test_detect_pr_number_absent_for_push(tmp_path: Path) -> None:
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"ref": "refs/heads/main"}), encoding="utf-8")
    assert detect_pr_number(str(event)) is None


def test_detect_pr_number_missing_file() -> None:
    assert detect_pr_number("/no/such/event.json") is None


def test_upsert_skips_without_token(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    # No token -> skipped, returns False, never touches the network.
    assert upsert_pr_comment("body", repo="o/r", pr_number=1, token=None) is False


def test_upsert_skips_when_not_a_pr(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    assert upsert_pr_comment("body", repo="o/r", pr_number=None, token="t") is False
