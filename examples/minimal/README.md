# Example: `minimal`

A single-board KiCad 9 project with an empty schematic and a 20 × 20 mm empty
board outline. It is intentionally clean — no parts, no nets — so ERC and DRC
both pass with **zero violations**. This is the fixture the self-test workflow
runs the verify-only configuration against.

## Files

| File | Purpose |
| ---- | ------- |
| `minimal.kicad_pro` | KiCad project file |
| `minimal.kicad_sch` | Empty root schematic |
| `minimal.kicad_pcb` | Empty board with a rectangular `Edge.Cuts` outline |
| `kicad-bot.json` | Verify-only kicad-bot config |

## Run it locally

With KiCad 8+ installed (so `kicad-cli` is on your PATH):

```bash
pip install kicad-bot
kicad-bot-verify --project-dir examples/minimal
```

Expected: a `kicad-bot-output/` directory containing `report.md`,
`kicad_bot_metrics.json`, `erc.json`, and `drc.json`, and an exit code of `0`.

## Use it in a workflow

```yaml
name: kicad-bot
on:
  pull_request:
    paths: ["**.kicad_sch", "**.kicad_pcb"]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: embedded-pro/kicad-bot@v0
        with:
          run-verify: "true"
          project-dir: examples/minimal
```

> **Note:** these board/schematic files are hand-authored minimal fixtures. If
> KiCad reports a format mismatch on your version, open and re-save them in the
> KiCad GUI to upgrade the on-disk format.
