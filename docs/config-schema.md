# Config schema (`kicad-bot.json`)

All capabilities read a single optional config file (default `kicad-bot.json` in
the project directory). Everything in it has a sensible default, so the file is
entirely optional — action inputs and CLI flags can override the verify gates.
The machine-readable schema lives at
[`kicad-bot.schema.json`](kicad-bot.schema.json); point your editor at it for
completion and validation:

```json
{
  "$schema": "https://raw.githubusercontent.com/embedded-pro/kicad-bot/main/docs/kicad-bot.schema.json"
}
```

## Full example

```json
{
  "$schema": "https://raw.githubusercontent.com/embedded-pro/kicad-bot/main/docs/kicad-bot.schema.json",
  "kicad_version": 9,
  "verify": {
    "schematic_parity": true,
    "drc_severity": "error",
    "exclusions": ["silk_overlap"]
  },
  "bom": {
    "distributors": ["Mouser", "Digi-Key"],
    "board_quantity": 100,
    "fail_on_lifecycle": ["obsolete", "nrnd"],
    "fail_on_unavailable": true
  },
  "diff": {
    "baseline_ref": ""
  },
  "fab": {
    "outputs": ["gerbers", "drill", "position", "bom", "schematic_pdf", "step"],
    "format": "zip"
  }
}
```

## Fields

### Top level

| Key | Type | Default | Description |
| --- | ---- | ------- | ----------- |
| `kicad_version` | integer (`8`\|`9`\|`10`) | `9` | KiCad major version the project targets. |
| `verify` | object | — | Verify (ERC/DRC) settings. |
| `bom` | object | — | BOM availability settings. |
| `diff` | object | — | Visual-diff settings. |
| `fab` | object | — | Fabrication-output settings. |

### `verify`

| Key | Type | Default | Description |
| --- | ---- | ------- | ----------- |
| `schematic_parity` | boolean | `true` | Run schematic-parity checks during DRC. |
| `drc_severity` | `error`\|`warning`\|`all` | `error` | Minimum severity that gates the build. |
| `exclusions` | string[] | `[]` | Violation type identifiers excluded from gating. |

### `bom`

| Key | Type | Default | Description |
| --- | ---- | ------- | ----------- |
| `distributors` | string[] | `["Mouser","Digi-Key"]` | Distributors to query. |
| `board_quantity` | integer | `1` | Quantity used for price breaks. |
| `fail_on_lifecycle` | string[] | `[]` | Lifecycle states (`nrnd`, `obsolete`, `eol`, …) that fail the build. |
| `fail_on_unavailable` | boolean | `false` | Fail when any part is out of stock. |

### `diff`

| Key | Type | Default | Description |
| --- | ---- | ------- | ----------- |
| `baseline_ref` | string | _(PR base)_ | Git ref to diff against. |

### `fab`

| Key | Type | Default | Description |
| --- | ---- | ------- | ----------- |
| `outputs` | string[] | _(all)_ | KiBot output set (`gerbers`, `drill`, `position`, `bom`, `schematic_pdf`, `step`, `render_3d`). |
| `format` | `zip`\|`directory` | `zip` | Packaging format. |

## Precedence

For the verify gates, **CLI flags / action inputs win over the config file**,
which wins over the built-in defaults. The config file is the right home for
settings that have no flag (e.g. `verify.exclusions`, `bom.board_quantity`,
`fab.outputs`).
