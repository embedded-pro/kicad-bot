# Architecture

kicad-bot is a thin, well-tested orchestration layer over upstream KiCad tooling.
It does not reimplement ERC/DRC, BOM sourcing, diffing, or fab output — it wraps
`kicad-cli`, KiBot, KiCost, and KiDiff and adds the CI ergonomics: gates,
reports, idempotent PR comments, and machine-readable metrics.

## Module layout

```
src/kicad_bot/
├── __init__.py     # package version
├── cli.py          # shared argparse plumbing, config load, project discovery,
│                   #   subprocess wrapper, $GITHUB_OUTPUT / step-summary helpers
├── verify.py       # kicad-cli ERC/DRC wrapper + gate evaluation   (kicad-bot-verify)
├── bom.py          # KiBot/KiCost wrapper + lifecycle/stock gates   (kicad-bot-bom)
├── diff.py         # KiDiff/KiBot diff wrapper                      (kicad-bot-diff)
├── fab.py          # KiBot fabrication output generation            (kicad-bot-fab)
├── quickstart.py   # project auto-detection + run enabled stages    (kicad-bot-quickstart)
├── report.py       # markdown report + PR-comment rendering (pure functions)
├── pr_comment.py   # idempotent PR comment via GitHub REST (stdlib only)
└── metrics.py      # kicad_bot_metrics.json accumulator
```

Each capability is a self-contained module exposing a `main()` console-script
entry point. The shared modules (`cli`, `report`, `pr_comment`, `metrics`) carry
no KiCad-specific logic and are unit-testable without any external tools.

## Data flow

```
            ┌──────────────┐
  inputs →  │  cli.py       │  parse args, load kicad-bot.json,
            │  (per cmd)    │  discover schematic/board
            └──────┬───────┘
                   │  Project
                   ▼
            ┌──────────────┐  subprocess (run_command)
            │ verify / bom  │ ───────────────────────────►  kicad-cli / KiBot /
            │ diff  / fab   │ ◄───────────────────────────   KiCost / KiDiff
            └──────┬───────┘  raw JSON / xlsx / pdf / fab
                   │  CapabilityResult (summary + Gate[])
                   ▼
            ┌──────────────┐
            │  metrics.py   │  merge into kicad_bot_metrics.json
            └──────┬───────┘
                   │  metrics dict
                   ▼
            ┌──────────────┐   report.md + pr_comment.md
            │  report.py    │ ──┐
            └──────────────┘   │
            ┌──────────────┐   ├─► $GITHUB_STEP_SUMMARY, $GITHUB_OUTPUT
            │ pr_comment.py │ ◄─┘   PR comment (upsert by marker)
            └──────────────┘
```

### Metrics accumulation

Several capabilities can run in one job. Rather than each overwriting the output,
every capability **merges** its section into a single `kicad_bot_metrics.json`
via `metrics.update_metrics_file()` (load → merge one `CapabilityResult` →
write). The document's top-level `passed` is the AND of every capability's
enabled gates. `report.py` then renders both the full report and the compact PR
comment as pure functions of that document, so rendering is identical regardless
of which capabilities ran.

### Idempotent PR comments

`pr_comment.py` embeds a stable marker (`<!-- kicad-bot:report -->`) in the
comment body, finds an existing comment carrying that marker via the GitHub REST
API, and **updates it in place** — so a PR never accumulates duplicate comments.
It uses only `urllib` (no third-party HTTP dependency) and silently no-ops when
there is no token or the run is not a pull request.

### Exit codes

`0` = all enabled gates passed · `1` = a gate tripped · `2` = a usage or tooling
error (e.g. `kicad-cli` not found, malformed config). The composite action runs
each enabled capability, preserves the first non-zero exit, and still uploads the
artifact via `if: always()`.

## The composite action

`action.yml` is the GitHub wrapper. It sets up Python, installs kicad-bot from
the action's own checkout (`github.action_path`), conditionally installs system
dependencies **only for the capabilities that are enabled** (just `kicad-cli` for
verify; the full KiCad + KiBot stack + `xvfb` for bom/diff/fab), runs each
enabled CLI, and uploads the output directory as an artifact.

## Design principles

- **Wrap, don't reimplement.** Upstream tools are the source of truth.
- **Pure core, effectful edges.** Parsing/rendering are pure and unit-tested;
  subprocess and network calls live at the boundary.
- **Dependency-free runtime.** The package itself has no Python dependencies;
  the heavy tools are system/CLI dependencies installed on demand.
- **CI-first.** Every capability is exit-code driven and emits machine-readable
  metrics for downstream tooling.
