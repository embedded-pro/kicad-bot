"""kicad-bot: a CI quality gate for KiCad projects.

Wraps battle-tested upstream tooling (kicad-cli, KiBot, KiCost, KiDiff) behind a
small set of CI-friendly console scripts and a GitHub composite action:

* ``kicad-bot-verify``     -- headless ERC/DRC via kicad-cli, with fail gates.
* ``kicad-bot-bom``        -- BOM availability / lifecycle gates via KiBot+KiCost.
* ``kicad-bot-diff``       -- graphical schematic/PCB diff against a baseline ref.
* ``kicad-bot-fab``        -- fabrication/documentation output package via KiBot.
* ``kicad-bot-quickstart`` -- auto-detect a project and run the enabled stages.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.3"
