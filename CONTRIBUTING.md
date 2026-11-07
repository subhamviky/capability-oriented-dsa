# Contributing

## Setup

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Before every pull request

```bash
ruff check . && ruff format --check .
mypy
python tools/build_standalone.py     # regenerate the single-file edition, then commit it
pytest --cov
```

CI runs the same commands and fails if `standalone/dsa_framework.py` is stale.

## Rules of the codebase

1. **Edit `src/` only.** `standalone/dsa_framework.py` is generated. A new module goes into `MODULES` in `tools/build_standalone.py`, in dependency order.
2. **Respect the layers.** `core` imports only the stdlib. `structures` → `core`. `validation` → `structures`, `core`. `algorithms` → the three below it. `capabilities` → everything. `facade.py` sits on top.
3. **Kernels stay direct.** No config lookups, result objects or logging inside an algorithm. Accept an optional `metrics: MetricsState | None` and return plain data.
4. **Kernels are iterative** wherever depth depends on input size. CPython's default recursion limit is 1000.
5. **Mutations are atomic.** Validate inputs before the first write. If you cannot, declare `atomic=False` in the descriptor.
6. **Every operation has a descriptor.** Declare it with `@operation(describe(...), requires=(...))`, never with an `if operation == ...` branch.
7. **Every tunable is a registered `ConfigKey`** and appears in `docs/configuration.md` (a test enforces this).
8. **Tests take the `dsa` fixture**, so they run against both editions. Bug fixes add a test that fails without the fix.

## Commits and versioning

- Conventional-style subjects help the changelog: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `ci:`.
- Record user-visible changes under `## [Unreleased]` in `CHANGELOG.md`.
- Semantic Versioning. Before 1.0, a minor bump may break the API, and it must be listed under **Breaking**.

## Releasing

1. Move `Unreleased` entries under a new `## [X.Y.Z] - YYYY-MM-DD` heading.
2. Bump `version` in `pyproject.toml`, `__version__` in `src/capability_oriented_dsa/__init__.py` and `CITATION.cff`, then run `python tools/build_standalone.py`.
3. Commit, then `git tag -a vX.Y.Z -m "vX.Y.Z" && git push --follow-tags`. Creating the release from the GitHub web UI ("Draft a new release", new tag on publish) works too.
4. `release.yml` verifies the tag matches the version, tests, builds, and publishes a GitHub Release with the wheel, sdist and standalone file, or attaches them to a release that already exists.
5. Optional PyPI: create a PyPI project with a *trusted publisher* for this repository and workflow, add a `pypi` environment in repo settings, and uncomment the `pypi` job.
