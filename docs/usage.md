# Usage

kicad-bot is usable two ways: as a **GitHub composite action** (the common case)
and as a set of **console scripts** you can run locally or in any CI.

## As a GitHub Action

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

### Action inputs

| Input | Default | Description |
| ----- | ------- | ----------- |
| `run-verify` | `true` | Run headless ERC/DRC verification. |
| `run-bom-check` | `false` | Run BOM availability/lifecycle check. |
| `run-diff` | `false` | Render a visual schematic/PCB diff. |
| `run-fab` | `false` | Generate the fabrication output package. |
| `quickstart` | `false` | Auto-detect the project and run enabled stages. |
| `project-dir` | `.` | Directory containing the KiCad project. |
| `schematic` | _(auto)_ | Path to the `.kicad_sch` file. |
| `board` | _(auto)_ | Path to the `.kicad_pcb` file. |
| `kicad-version` | `9` | Major KiCad version to install/use (8 \| 9 \| 10). |
| `config-path` | `kicad-bot.json` | Path to the config file. |
| `fail-on-erc` | `true` | Fail on ERC violations. |
| `fail-on-drc` | `true` | Fail on DRC violations. |
| `drc-severity` | `error` | Gate severity (`error` \| `warning` \| `all`). |
| `fail-on-eol` | `false` | Fail when any part is EOL/NRND/obsolete. |
| `fail-on-unavailable` | `false` | Fail when any part is out of stock. |
| `distributors` | `Mouser,Digi-Key` | Comma-separated distributor list. |
| `kicost-config` | _(none)_ | Path to an existing KiCost config. |
| `diff-baseline-ref` | _(PR base)_ | Git ref to diff against. |
| `output-dir` | `kicad-bot-output` | Output directory for reports/artifacts. |
| `pr-comment` | `true` | Render and upsert an idempotent PR comment. |
| `upload-artifact` | `true` | Upload the output directory as an artifact. |
| `artifact-name` | `kicad-bot-output` | Name of the uploaded artifact. |

### Action outputs

| Output | Description |
| ------ | ----------- |
| `erc-violations` | ERC violation count. |
| `drc-violations` | DRC violation count. |
| `eol-parts` | Count of EOL/NRND parts. |
| `unavailable-parts` | Count of out-of-stock parts. |
| `report-path` | Path to the markdown report. |
| `metrics-path` | Path to `kicad_bot_metrics.json`. |
| `passed` | `true` when every enabled gate passed. |

## As console scripts

```bash
pip install kicad-bot      # plus KiCad 8+ for kicad-cli

kicad-bot-verify --project-dir . --drc-severity error
kicad-bot-bom    --project-dir . --fail-on-eol
kicad-bot-diff   --project-dir . --baseline-ref origin/main
kicad-bot-fab    --project-dir .
kicad-bot-quickstart --project-dir .
```

Common flags shared by every command:

| Flag | Description |
| ---- | ----------- |
| `--project-dir` | Directory containing the KiCad project. |
| `--config-path` | Path to `kicad-bot.json`. |
| `--output-dir` | Output directory (default `kicad-bot-output`). |
| `--schematic` / `--board` | Explicit design files (else auto-detected). |
| `--kicad-version` | Major KiCad version (8 \| 9 \| 10). |
| `--no-pr-comment` | Disable PR comment rendering. |
| `-v`, `--verbose` | Debug logging. |

### `kicad-bot-verify`

| Flag | Default | Description |
| ---- | ------- | ----------- |
| `--fail-on-erc` / `--no-fail-on-erc` | on | Gate on ERC violations. |
| `--fail-on-drc` / `--no-fail-on-drc` | on | Gate on DRC violations. |
| `--drc-severity` | `error` | Minimum gating severity. |

Exit codes: `0` pass, `1` a gate tripped, `2` a usage/tooling error.

## Outputs on disk

Every run populates `output-dir`:

```
kicad-bot-output/
├── report.md                 # full human report
├── pr_comment.md             # compact PR comment (idempotent marker)
├── kicad_bot_metrics.json    # machine-readable summary
├── erc.json / drc.json       # raw kicad-cli reports
├── bom.xlsx                  # with run-bom-check
├── diff.pdf                  # with run-diff
└── fab/                      # with run-fab
```

See [config-schema.md](config-schema.md) for the `kicad-bot.json` reference and
[secrets.md](secrets.md) for distributor API keys.
