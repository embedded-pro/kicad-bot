"""``kicad-bot-fab`` -- fabrication/documentation output package (KiBot).

Phase 4. Generates the configured KiBot output set (gerbers, drill, position,
BOM, 3D, schematic PDF), packages it as a zip, and applies
``fail-on-missing-output``. Implemented in a later build phase.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    print(
        "kicad-bot-fab is not available in this build yet (Phase 4).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
