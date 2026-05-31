"""``kicad-bot-diff`` -- graphical schematic/PCB diff (KiDiff / KiBot diff).

Phase 3. Resolves a baseline ref (defaulting to the PR base), renders a visual
diff to ``diff.pdf``, and attaches it to the PR comment. Implemented in a later
build phase.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    print(
        "kicad-bot-diff is not available in this build yet (Phase 3).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
