"""Shared CLI plumbing for the kicad-bot console scripts.

Every capability (``verify``, ``bom``, ``diff``, ``fab``, ``quickstart``) is a
small module exposing a ``main()`` entry point. They share the helpers here:
common argparse options, ``kicad-bot.json`` config loading, project file
discovery, and a thin subprocess wrapper so the wrapped upstream tools
(``kicad-cli``, KiBot, ...) are invoked consistently.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LOG = logging.getLogger("kicad_bot")

DEFAULT_OUTPUT_DIR = "kicad-bot-output"
DEFAULT_CONFIG_PATH = "kicad-bot.json"


class KicadBotError(RuntimeError):
    """A user-facing error that should print cleanly and exit non-zero."""


def configure_logging(verbose: bool = False) -> None:
    """Configure root logging once, honouring ``$RUNNER_DEBUG`` from Actions."""
    if logging.getLogger().handlers:
        return
    debug = verbose or os.environ.get("RUNNER_DEBUG") == "1"
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Register the options shared by every capability."""
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Directory containing the KiCad project (default: current dir).",
    )
    parser.add_argument(
        "--config-path",
        default=DEFAULT_CONFIG_PATH,
        help="Path to kicad-bot.json (relative to --project-dir if not absolute).",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for reports and artifacts (default: %(default)s).",
    )
    parser.add_argument(
        "--kicad-version",
        default="9",
        help="Major KiCad version the project targets (8 | 9 | 10).",
    )
    parser.add_argument(
        "--schematic",
        default=None,
        help="Path to the .kicad_sch file (auto-detected if omitted).",
    )
    parser.add_argument(
        "--board",
        default=None,
        help="Path to the .kicad_pcb file (auto-detected if omitted).",
    )
    parser.add_argument(
        "--pr-comment",
        dest="pr_comment",
        action="store_true",
        default=True,
        help="Render and upsert a PR comment (default: on).",
    )
    parser.add_argument(
        "--no-pr-comment",
        dest="pr_comment",
        action="store_false",
        help="Disable PR comment rendering.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )


def load_config(config_path: str | os.PathLike[str], project_dir: str | os.PathLike[str]) -> dict[str, Any]:
    """Load ``kicad-bot.json`` if present, returning ``{}`` when absent.

    A relative ``config_path`` is resolved against ``project_dir``.
    """
    path = Path(config_path)
    if not path.is_absolute():
        path = Path(project_dir) / path
    if not path.is_file():
        LOG.debug("No config file at %s; using defaults.", path)
        return {}
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise KicadBotError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise KicadBotError(f"{path} must contain a JSON object at the top level.")
    LOG.debug("Loaded config from %s", path)
    return data


@dataclass(frozen=True)
class Project:
    """A resolved KiCad project: its directory and the relevant design files."""

    directory: Path
    schematic: Path | None
    board: Path | None

    @property
    def name(self) -> str:
        for candidate in (self.schematic, self.board):
            if candidate is not None:
                return candidate.stem
        return self.directory.name


def _pick_one(paths: list[Path], kind: str) -> Path | None:
    if not paths:
        return None
    if len(paths) == 1:
        return paths[0]
    # Prefer a file whose stem matches the directory (the conventional layout).
    parent = paths[0].parent
    for candidate in paths:
        if candidate.stem == parent.name:
            LOG.debug("Multiple %s files; picking %s by directory-name match.", kind, candidate.name)
            return candidate
    raise KicadBotError(
        f"Found {len(paths)} {kind} files in {parent}; pass --{kind} to disambiguate: "
        + ", ".join(p.name for p in paths)
    )


def discover_project(
    project_dir: str | os.PathLike[str],
    schematic: str | None = None,
    board: str | None = None,
) -> Project:
    """Resolve the schematic/board for ``project_dir``.

    Explicit ``schematic``/``board`` paths win; otherwise the project directory
    is scanned for a single ``*.kicad_sch`` / ``*.kicad_pcb`` (root sheets only,
    not the per-sheet files in subdirectories).
    """
    directory = Path(project_dir).resolve()
    if not directory.is_dir():
        raise KicadBotError(f"--project-dir does not exist: {directory}")

    def _resolve(explicit: str | None, suffix: str, kind: str) -> Path | None:
        if explicit:
            path = Path(explicit)
            if not path.is_absolute():
                path = directory / path
            if not path.is_file():
                raise KicadBotError(f"--{kind} not found: {path}")
            return path
        found = sorted(directory.glob(f"*{suffix}"))
        return _pick_one(found, kind)

    return Project(
        directory=directory,
        schematic=_resolve(schematic, ".kicad_sch", "schematic"),
        board=_resolve(board, ".kicad_pcb", "board"),
    )


def ensure_output_dir(output_dir: str | os.PathLike[str]) -> Path:
    """Create (idempotently) and return the output directory as a Path."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class CommandResult:
    """Outcome of a wrapped subprocess call."""

    args: list[str]
    returncode: int
    stdout: str
    stderr: str


def run_command(
    args: Sequence[str],
    *,
    cwd: str | os.PathLike[str] | None = None,
    check: bool = False,
    env: dict[str, str] | None = None,
) -> CommandResult:
    """Run a subprocess, capturing output and logging the invocation.

    ``check=True`` raises :class:`KicadBotError` on a non-zero exit. Note that
    several wrapped tools deliberately use non-zero exit codes to signal
    violations, so callers usually leave ``check=False`` and inspect the result.
    """
    argv = [str(a) for a in args]
    LOG.debug("Running: %s (cwd=%s)", " ".join(argv), cwd or os.getcwd())
    try:
        # argv is a constructed list (never a shell string), so this is safe.
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise KicadBotError(
            f"Required tool not found on PATH: {argv[0]}. Is it installed? See docs/troubleshooting.md."
        ) from exc
    result = CommandResult(argv, completed.returncode, completed.stdout, completed.stderr)
    if check and result.returncode != 0:
        raise KicadBotError(f"Command failed ({result.returncode}): {' '.join(argv)}\n{result.stderr.strip()}")
    return result


def tool_available(name: str) -> bool:
    """Return True if an executable named ``name`` is on PATH."""
    return shutil.which(name) is not None


def kicad_cli_name() -> str:
    """Name of the kicad-cli executable (overridable via ``$KICAD_CLI``)."""
    return os.environ.get("KICAD_CLI", "kicad-cli")


def add_bool_flag(parser: argparse.ArgumentParser, name: str, *, default: bool, help: str) -> None:
    """Register a ``--flag`` / ``--no-flag`` pair backed by one dest."""
    dest = name.replace("-", "_")
    parser.add_argument(f"--{name}", dest=dest, action="store_true", default=default, help=help)
    parser.add_argument(f"--no-{name}", dest=dest, action="store_false", help=argparse.SUPPRESS)


def append_step_summary(markdown: str) -> None:
    """Append markdown to ``$GITHUB_STEP_SUMMARY`` when running in Actions."""
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    try:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(markdown.rstrip() + "\n\n")
    except OSError as exc:  # pragma: no cover - environment dependent
        LOG.debug("Could not write step summary: %s", exc)


def set_output(name: str, value: object) -> None:
    """Set a GitHub Actions step output via ``$GITHUB_OUTPUT``."""
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        LOG.debug("GITHUB_OUTPUT unset; output %s=%s not exported.", name, value)
        return
    try:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")
    except OSError as exc:  # pragma: no cover - environment dependent
        LOG.debug("Could not write output %s: %s", name, exc)
