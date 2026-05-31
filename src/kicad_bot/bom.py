"""``kicad-bot-bom`` -- BOM availability / lifecycle gate (KiBot + KiCost).

Phase 2. Drives KiBot's KiCost integration to fetch distributor pricing,
availability, and lifecycle status, then applies the ``fail-on-eol`` /
``fail-on-unavailable`` gates. Implemented in a later build phase.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    print(
        "kicad-bot-bom is not available in this build yet (Phase 2).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
