# Contributing to kicad-bot

Thanks for your interest in improving kicad-bot! This project is part of the
[embedded-pro](https://github.com/embedded-pro) family of CI actions and follows
the same conventions as its sibling repos.

## Development setup

```bash
python -m venv .venv
. .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Running the KiCad-backed capabilities locally also requires a KiCad 8+ install
(for `kicad-cli`) and, for BOM/diff/fab, the KiBot stack. See
[docs/troubleshooting.md](docs/troubleshooting.md) for the headless setup.

## Checks

Every change must pass the same gates CI runs:

```bash
ruff check .            # lint
ruff format --check .   # formatting
mypy                    # type-check
pytest tests/unit       # hermetic unit tests (no KiCad needed)
pytest tests/integration # end-to-end tests (require kicad-cli; auto-skip if absent)
```

### Test layout

| Layer | Location | What it covers | Needs |
| ----- | -------- | -------------- | ----- |
| Unit | `tests/unit/` | Parsers, gates, metrics, report/PR-comment rendering — pure Python | nothing |
| Integration | `tests/integration/` | Full `kicad-bot-verify` pipeline against the `examples/` projects | real `kicad-cli` |
| Self-test | `.github/workflows/self-test.yml` | The composite action end-to-end on `examples/minimal` | the action |

Integration tests are skipped automatically when `kicad-cli` is not on PATH, so
the unit suite stays hermetic on machines without KiCad. In CI the `integration`
job installs KiCad and runs them for real — it is a good required status check
alongside `lint` and `unit`.

## Commit messages

This repo releases via **release-please**, which derives version bumps and the
changelog from [Conventional Commits](https://www.conventionalcommits.org/).
Use prefixes such as:

- `feat:` — a new capability or input (minor bump)
- `fix:` — a bug fix (patch bump)
- `docs:`, `test:`, `chore:`, `refactor:`, `ci:` — no release on their own
- `feat!:` / `fix!:` or a `BREAKING CHANGE:` footer — major bump

## Architecture

See [docs/architecture.md](docs/architecture.md) for the module layout and data
flow. In short: each capability is a self-contained module under
`src/kicad_bot/` exposing a `main()` console-script entry point, sharing argparse
plumbing from `cli.py` and output helpers from `report.py`, `pr_comment.py`, and
`metrics.py`.

## Adding a capability

1. Add `src/kicad_bot/<capability>.py` with a `main()` entry point.
2. Register the console script in `pyproject.toml` (`kicad-bot-<capability>`).
3. Add the `run-<capability>` toggle and any gates to `action.yml`.
4. Add a runnable project under `examples/` and wire it into `self-test.yml`.
5. Document it in `docs/capabilities.md` and `docs/usage.md`.

By contributing you agree your contributions are licensed under the project's
[Apache-2.0](LICENSE) license.
