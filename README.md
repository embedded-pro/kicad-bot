# kicad-bot

[![CI](https://github.com/embedded-pro/kicad-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/embedded-pro/kicad-bot/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/kicad-bot.svg)](https://pypi.org/project/kicad-bot/)
[![Python versions](https://img.shields.io/pypi/pyversions/kicad-bot.svg)](https://pypi.org/project/kicad-bot/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**A CI quality gate for KiCad projects** — ERC/DRC verification, BOM availability
checks, visual diffs, and fabrication-output generation. CI-friendly and
framework-agnostic.

kicad-bot runs your KiCad project through automated quality gates on every push
and pull request, and produces a fabrication/documentation package on release.
It catches electrical (ERC) and design-rule (DRC) violations before they reach
`main`, flags BOM parts that have gone end-of-life or out of stock, generates
visual schematic/PCB diffs for reviewers, and emits a reproducible fab package on
tag — so the board that ships is always **verified, sourceable, and
reproducible**.

It wraps battle-tested upstream tooling rather than reinventing it:

| Tool | Used for |
| ---- | -------- |
| [`kicad-cli`](https://docs.kicad.org/) (KiCad 8+) | headless ERC/DRC (`--exit-code-violations`, `--schematic-parity`) |
| [KiBot](https://github.com/INTI-CMNB/KiBot) | fabrication/documentation output generation & orchestration |
| [KiCost](https://github.com/INTI-CMNB/KiCost) (via KiBot) | distributor-API pricing, availability, lifecycle status |
| [KiDiff](https://github.com/INTI-CMNB/KiDiff) / KiBot diff | graphical schematic & PCB diffs |

## Capabilities

| Capability | Action flag | CLI entry point | Backed by | Gates |
| ---------- | ----------- | --------------- | --------- | ----- |
| **Verify** | `run-verify` | `kicad-bot-verify` | `kicad-cli sch erc` / `pcb drc` | `fail-on-erc`, `fail-on-drc`, `drc-severity` |
| **BOM check** | `run-bom-check` | `kicad-bot-bom` | KiBot + KiCost | `fail-on-eol`, `fail-on-unavailable` |
| **Diff** | `run-diff` | `kicad-bot-diff` | KiDiff / KiBot diff | _(non-gating, informational)_ |
| **Fabrication** | `run-fab` | `kicad-bot-fab` | KiBot outputs | `fail-on-missing-output` |
| **Quickstart** | `quickstart` | `kicad-bot-quickstart` | auto-detect + run enabled stages | n/a |

## Quick start

```yaml
name: kicad-bot
on:
  push:
    paths: ["**.kicad_sch", "**.kicad_pcb"]
  pull_request:
    paths: ["**.kicad_sch", "**.kicad_pcb"]

jobs:
  kicad-bot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: embedded-pro/kicad-bot@v0
        with:
          run-verify: "true"
          fail-on-drc: "true"
```

Enabling more capabilities is just more flags:

```yaml
      - uses: embedded-pro/kicad-bot@v0
        with:
          run-verify: "true"
          run-bom-check: "true"
          run-diff: "true"
          fail-on-drc: "true"
          fail-on-eol: "true"
          distributors: "Mouser,Digi-Key"
        env:
          MOUSER_KEY: ${{ secrets.MOUSER_KEY }}
          DIGIKEY_CLIENT_ID: ${{ secrets.DIGIKEY_CLIENT_ID }}
          DIGIKEY_CLIENT_SECRET: ${{ secrets.DIGIKEY_CLIENT_SECRET }}
```

> **Path filters** keep kicad-bot from running on unrelated commits. Restrict the
> workflow to changes that touch `**.kicad_sch` / `**.kicad_pcb` as shown above.

## Outputs

Each run writes to `output-dir` (default `kicad-bot-output/`) and uploads it as a
build artifact:

| File | Purpose |
| ---- | ------- |
| `report.md` | Full report: ERC/DRC summary, BOM table, diff thumbnails |
| `pr_comment.md` | Compact PR comment (idempotent marker) |
| `kicad_bot_metrics.json` | Machine-readable summary (counts, pass/fail per gate) |
| `erc.json` / `drc.json` | Raw `kicad-cli` JSON reports |
| `bom.xlsx` | KiCost spreadsheet (cost/availability/lifecycle) — with `run-bom-check` |
| `diff.pdf` | Schematic/PCB visual diff — with `run-diff` |
| `fab/` | Gerbers, drill, position, BOM, 3D, schematic PDF — with `run-fab` |

## Documentation

- [Usage](docs/usage.md) — every CLI flag and action input/output
- [Config schema](docs/config-schema.md) — the `kicad-bot.json` reference
- [Capabilities](docs/capabilities.md) — what verify / bom / diff / fab each do
- [Secrets](docs/secrets.md) — distributor API key handling
- [Architecture](docs/architecture.md) — internal module layout & data flow
- [Troubleshooting](docs/troubleshooting.md) — headless, fonts, common errors

## Scope & limitations

- kicad-bot is a **CI guardrail**, not a substitute for design review or sign-off.
- BOM availability is a **snapshot** of distributor data at run time, not a
  guarantee of stock at order time.
- Visual diffs surface geometric/electrical changes but do not perform semantic
  net-level reasoning.
- Git remains unsuitable for merging concurrent board edits; kicad-bot verifies,
  it does not resolve layout conflicts.

## License

[Apache-2.0](LICENSE)
