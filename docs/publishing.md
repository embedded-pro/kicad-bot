# Publishing to PyPI

This project uses **OIDC trusted publishing** to upload releases to PyPI
without long-lived API tokens. The release workflow
(`.github/workflows/release.yml`) is invoked by
`.github/workflows/release-please.yml` when release-please creates a release.

## One-time PyPI setup

1. **Create the project on PyPI** (if it doesn't exist yet):
   - Go to <https://pypi.org/manage/account/publishing/>
   - Or, if using a custom/private PyPI registry, go to the equivalent admin
     page on your instance.

2. **Add a trusted publisher**:
   - Navigate to your project on PyPI → *Settings* → *Publishing* →
     *Add a new publisher*.
   - Fill in:
     | Field | Value |
     | ----- | ----- |
     | Owner | `embedded-pro` |
     | Repository | `kicad-bot` |
     | Workflow name | `release.yml` |
     | Environment name | `pypi` |
   - Click *Add*.

3. **Create a GitHub environment**:
   - In the repository, go to *Settings* → *Environments* → *New environment*.
   - Name it **`pypi`** (must match the `environment.name` in
     `release.yml`).
   - Optionally add protection rules (e.g. required reviewers) to gate
     publishing.

## How it works

```
release-please.yml (release_created=true) ──► release.yml(tag_name)
                                               │
                                               ├─ build job:  python -m build → upload artifact
                                               │
                                               ├─ publish job: download artifact → pypa/gh-action-pypi-publish (OIDC)
                                               │
                                               └─ github-release job: upload dist files to the existing GitHub Release
```

The `pypa/gh-action-pypi-publish` action exchanges a short-lived OIDC token
with PyPI — no `PYPI_TOKEN` secret is needed.

## Publishing to a private/custom PyPI registry

If you host a private registry (e.g. Artifactory, Nexus, Cloudsmith):

1. In your `pypi` GitHub environment, add a secret named
   `REPOSITORY_URL` containing your registry's upload URL
   (e.g. `https://your-registry.example.com/simple/`).

2. Update the publish step in `release.yml`:

   ```yaml
   - name: Publish via OIDC
     uses: pypa/gh-action-pypi-publish@v1
     with:
       repository-url: ${{ secrets.REPOSITORY_URL }}
   ```

   If your registry does not support OIDC, add a `password` secret instead:

   ```yaml
   - name: Publish
     uses: pypa/gh-action-pypi-publish@v1
     with:
       repository-url: ${{ secrets.REPOSITORY_URL }}
       password: ${{ secrets.PYPI_API_TOKEN }}
   ```

## Versioning

Versions are managed automatically by **release-please**:

- Merging PRs with Conventional Commit messages (`feat:`, `fix:`, etc.) to
  `main` causes release-please to open/update a release PR.
- Merging that release PR bumps the version in `pyproject.toml`, updates
  `CHANGELOG.md`, creates the git tag and GitHub Release, then invokes
  `release.yml` to publish to PyPI and upload release assets.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for commit-message conventions.
