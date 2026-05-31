# Example: `drc-violation`

A KiCad 9 board that **deliberately fails DRC**. Two copper tracks on `F.Cu`
belong to different nets (`NET_A` and `NET_B`) and cross at the same point,
creating a short / clearance violation:

```
NET_A:  (5,5) ──────────────── (15,5)
                     │
NET_B:           (10,0)
                     │
                  (10,10)        ← crosses NET_A at (10,5)
```

This is the negative fixture for the integration tests and a demonstration of
the verify gate tripping. Running kicad-bot here exits non-zero with at least one
DRC violation.

## Files

| File | Purpose |
| ---- | ------- |
| `drc-violation.kicad_pro` | KiCad project file |
| `drc-violation.kicad_sch` | Empty root schematic (ERC is clean) |
| `drc-violation.kicad_pcb` | Board with two shorting tracks |
| `kicad-bot.json` | Verify config (`schematic_parity` off — no components) |

## Run it locally

```bash
pip install kicad-bot          # plus KiCad 9 for kicad-cli
kicad-bot-verify --project-dir examples/drc-violation
echo "exit code: $?"           # -> 1 (a gate tripped)
```

Expected: `kicad-bot-output/drc.json` lists the clearance/short violation, the
report shows **FAIL**, and the process exits `1`.

> **Note:** these files are hand-authored minimal fixtures. If KiCad reports a
> format mismatch on your version, open and re-save them in the KiCad GUI to
> upgrade the on-disk format.
