# v0.8.0 distribution and publication preparation

Baseline: `main b0fe3aae70cfe9e8abec6a761bef5fd50bb4e901`.
Branch: `release/v0.8.0`. Package metadata: `pyproject.toml`, version `0.8.0`.
This branch prepares publication only. Do not merge, create a tag or create a
GitHub Release without separate authorization. No PyPI upload is included.

## Publication text

Use [v080_github_release.md](v080_github_release.md) verbatim as the proposed
GitHub Release body, title **CS2 Balancer v0.8.0 — Engine Contract Hardening**.
Its tag-based links are intentionally prospective and resolve after authorized
tag publication. Review the same files on this branch before publication.
The [release notes](../RELEASE_NOTES.md) retain the historical v0.7 and older notes.

## Distribution validation

Run from a clean checkout with Python >=3.11:

```text
python -m pip install -e ".[dev]" build
python -m pytest
python -m ruff check .
python -m build --outdir dist
```

`python -m build` creates the sdist and builds the wheel from that sdist in isolated
build environments. `MANIFEST.in` explicitly retains docs, release text, tests,
JSON/CSV fixtures, pytest config and config.yaml; runtime modules use the existing
package discovery. No local generated rosters, credentials, caches or environments
belong in either artifact. The wheel is runtime-only; documentation/tests are in
the source archive, not installed as public packages.

Validate wheel `*.dist-info/METADATA` and sdist `PKG-INFO`: Name `cs2-balancer`,
Version `0.8.0`, Requires-Python `>=3.11`. Inspect archive members for all runtime
Python modules, `main.py`, README, pyproject, manifest, migration guide, release
notes and required fixtures. Extract the sdist and rebuild without checkout imports.

Create a fresh venv without system-site-packages, install the wheel normally with
its declared dependencies, run `python -m pip check`, then run imports from outside
the checkout with isolated mode (`python -I`). Verify `importlib.metadata.version`
is `0.8.0`, imported modules come from that venv, and exercise FAST/STABLE/GLOBAL
with a small offline roster using production factories. Import the tournament
report API and report types as well. An editable checkout install is not evidence
of a valid wheel.

Artifact hashes, archive checks, clean-install output, pytest/coverage and actual
Python 3.11/3.12 CI job links are recorded in the release PR. Coverage from an older
engine acceptance PR is historical evidence, not a substitute for release-head CI.

## Publication gate

Clean-wheel validation found an unresolved presentation defect: a no-incumbent
GLOBAL result has `improvement=None`, and `HtmlExporterV2._build_header` formats
it with `+.2f`, raising `TypeError`. Reproduce with the migration example's
no-incumbent config and `create_reporting_components(config).exporter.export`.
FAST/STABLE/default incumbent-enabled GLOBAL export normally. This is an existing
engine-to-presentation issue, not a packaging failure. Resolve it or explicitly
accept the documented limitation before authorizing publication; this preparation
does not change production rendering code.

On 2026-10-26, `git ls-remote --tags origin refs/tags/v0.8.0` returned no tag and
the connected GitHub release listing contained only v0.5.0, v0.6.0 and v0.7.0.
Recheck both immediately before any future authorized publication; absence now
does not reserve the name. After review, the eventual tag must identify the approved
release commit, not an assumed candidate SHA. Rebuild/verify artifacts if source
changes. No tag or GitHub Release was created during this preparation.

Known build-tool debt: the existing TOML license table is accepted but deprecated
by current setuptools. Migrating licensing metadata requires a separate deliberate
update; this release does not change its existing MIT declaration or build minimum.
