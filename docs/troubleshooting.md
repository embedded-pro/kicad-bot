# Troubleshooting

## `kicad-cli: command not found` / "Required tool not found on PATH"

kicad-bot wraps KiCad's own CLI; it does not bundle it. Install **KiCad 8+** so
that `kicad-cli` is on your PATH.

- **GitHub Actions:** the composite action installs `kicad-cli` for you when
  `run-verify` (or `quickstart`) is enabled, via the
  `ppa:kicad/kicad-<version>.0-releases` PPA.
- **Locally:** install KiCad from <https://www.kicad.org/download/>. On macOS
  the binary lives at
  `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`.
- Override the executable name/path with the `KICAD_CLI` environment variable.

## "did not produce an ERC/DRC report"

`kicad-cli` ran but wrote no JSON. Usual causes:

- The schematic/board failed to load (wrong KiCad version vs. file format). Open
  and re-save the file in a matching KiCad version, or set `kicad-version`.
- A path with spaces or a missing file — pass `--schematic` / `--board`
  explicitly and check `--project-dir`.
- Run with `-v` / `--verbose` (or set `RUNNER_DEBUG=1` in Actions) to see the
  exact `kicad-cli` invocation and its stderr.

## Found N schematic/board files — pass `--schematic`/`--board`

Auto-detection found more than one root design file and none matched the
directory name. Disambiguate with the explicit flag (or `schematic:` / `board:`
action inputs).

## Headless errors from BOM / diff / fab (KiAuto)

The KiBot-based capabilities drive the KiCad GUI tools headlessly and need a
virtual display:

- The action runs them under `xvfb-run` automatically.
- Locally: `xvfb-run -a kicad-bot-fab ...` on Linux.
- Symptoms of a missing display: `cannot open display`, Qt "xcb plugin" errors,
  or hangs.

## Fonts / missing glyphs in rendered PDFs

Schematic/PCB PDF and diff rendering needs fonts installed in the environment.
On a minimal CI image install a base font set (e.g. `fonts-dejavu-core`) before
running diff/fab. The official `kicad/kicad` Docker images already include them.

## Apple Silicon (local runs)

The KiCad/KiBot Docker images are `linux/amd64`. On Apple-Silicon Macs run them
with `--platform linux/amd64` (emulated) to match CI exactly.

## Distributor API failures in BOM check

- `401/403`: missing or wrong keys — see [secrets.md](secrets.md). Confirm the
  secret names match the env vars kicad-bot expects.
- Timeouts: you enabled a distributor you have no key for. Trim `distributors`
  to just the ones you have configured.
- Fork PRs: secrets are unavailable to fork-triggered workflows; the BOM check is
  skipped. Keep `run-verify` as the fork-safe required gate.

## The PR comment isn't appearing

- The job needs `permissions: pull-requests: write`.
- Comments only post on `pull_request` events, not on `push`.
- Fork PRs have a read-only `GITHUB_TOKEN`; the comment step no-ops rather than
  failing the build.

## DRC fails on a board with no outline

An empty board with no `Edge.Cuts` outline can raise a board-outline DRC error.
Add a closed outline on the `Edge.Cuts` layer (see `examples/minimal`).
