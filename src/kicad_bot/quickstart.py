"""``kicad-bot-quickstart`` -- zero-config auto-detection and run.

Phase 5. Auto-detects ``*.kicad_sch`` / ``*.kicad_pcb``, generates a default
``kicad-bot.json``, and runs all enabled stages. Implemented in a later build
phase.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    print(
        "kicad-bot-quickstart is not available in this build yet (Phase 5).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
