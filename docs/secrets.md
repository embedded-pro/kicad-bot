# Distributor API secrets

The BOM check (`run-bom-check`) queries distributor APIs through KiCost for
pricing, availability, and lifecycle status. Those APIs need credentials. The
single most important rule:

> **Never commit distributor API keys.** On a public repo a committed KiCost
> config leaks them to the world.

kicad-bot follows the upstream KiCost CI guidance:

1. **Keys come from environment variables**, sourced from
   `${{ secrets.* }}` in your workflow.
2. **The KiCost config is generated at run time** from those env vars; secrets
   are never written to a tracked file.
3. **Unused distributor APIs are disabled by default** to avoid timeouts and
   spurious failures — only the distributors you list are queried.

## Workflow setup

Add your keys as repository (or organisation) secrets, then pass them as `env`:

```yaml
- uses: embedded-pro/kicad-bot@v0
  with:
    run-bom-check: "true"
    fail-on-eol: "true"
    fail-on-unavailable: "true"
    distributors: "Mouser,Digi-Key"
  env:
    MOUSER_KEY: ${{ secrets.MOUSER_KEY }}
    DIGIKEY_CLIENT_ID: ${{ secrets.DIGIKEY_CLIENT_ID }}
    DIGIKEY_CLIENT_SECRET: ${{ secrets.DIGIKEY_CLIENT_SECRET }}
```

## Supported distributors and their env vars

| Distributor | Environment variables |
| ----------- | --------------------- |
| Mouser | `MOUSER_KEY` |
| Digi-Key | `DIGIKEY_CLIENT_ID`, `DIGIKEY_CLIENT_SECRET` |
| TME | `TME_TOKEN`, `TME_APP_SECRET` |
| Nexar / Octopart | `NEXAR_CLIENT_ID`, `NEXAR_CLIENT_SECRET` |

Only distributors named in `distributors` (or `bom.distributors`) are enabled,
and a distributor whose keys are missing is skipped with a warning rather than
failing the build.

## Forked pull requests

Secrets are **not** available to workflows triggered by pull requests from
forks. For those events, run BOM checks in a `pull_request_target` workflow (with
the usual caution) or restrict `run-bom-check` to `push` on your own branches and
keep `run-verify` as the fork-safe required gate.

## Using your own KiCost config

If you already maintain a KiCost config, pass `kicost-config: path/to/config`.
kicad-bot will use it as-is and will **not** inject env-var credentials — make
sure that file does not contain committed secrets.
