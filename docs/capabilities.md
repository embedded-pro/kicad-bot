# Capabilities

kicad-bot is organised as a small set of independent capabilities. Each is a
console script (`kicad-bot-<capability>`) and a `run-<capability>` action toggle.
They share project discovery, config loading, reporting, and metrics, and they
all merge into a single `kicad_bot_metrics.json` and `report.md` per run.

| Capability | Toggle | CLI | Backed by | Gates |
| ---------- | ------ | --- | --------- | ----- |
| Verify | `run-verify` | `kicad-bot-verify` | `kicad-cli` | `fail-on-erc`, `fail-on-drc`, `drc-severity` |
| BOM check | `run-bom-check` | `kicad-bot-bom` | KiBot + KiCost | `fail-on-eol`, `fail-on-unavailable` |
| Diff | `run-diff` | `kicad-bot-diff` | KiDiff / KiBot diff | _(non-gating)_ |
| Fabrication | `run-fab` | `kicad-bot-fab` | KiBot outputs | `fail-on-missing-output` |
| Quickstart | `quickstart` | `kicad-bot-quickstart` | auto-detect | n/a |

## Verify

Runs `kicad-cli sch erc` and `kicad-cli pcb drc` against the project's schematic
and board, emits the raw `erc.json` / `drc.json`, and applies the ERC/DRC gates
at the configured severity (`error` < `warning` < `all`). Excluded violations
(KiCad exclusions) never gate. DRC `--schematic-parity` is enabled when both a
schematic and a board are present and `verify.schematic_parity` is not disabled.

This is the MVP gate: deterministic and network-free, so it is safe to make
required on every PR.

## BOM check

Drives KiBot's KiCost integration to fetch distributor pricing, availability,
and lifecycle status, writes a colour-coded `bom.xlsx`, and applies the
`fail-on-eol` / `fail-on-unavailable` gates. Distributor API keys come from
environment variables, never a committed file — see [secrets.md](secrets.md).

BOM availability is a **snapshot** at run time, not a guarantee of stock at order
time.

## Diff

Resolves a baseline git ref (defaulting to the PR base), renders a graphical
schematic/PCB diff to `diff.pdf`, and attaches a summary to the PR comment. This
capability is informational and does not gate the build. Visual diffs surface
geometric/electrical changes but do not perform semantic net-level reasoning.

## Fabrication

Generates the configured KiBot output set (gerbers, drill, position, BOM, 3D,
schematic PDF), packages it as a zip, and applies `fail-on-missing-output` so a
broken output config fails loudly. Intended to run on tags/releases and attach
the package to a GitHub Release.

## Quickstart

Auto-detects `*.kicad_sch` / `*.kicad_pcb`, generates a default `kicad-bot.json`,
and runs every enabled stage with zero configuration — the fastest way to try
kicad-bot on an existing project.
