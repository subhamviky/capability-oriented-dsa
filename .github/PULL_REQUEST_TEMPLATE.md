## What and why

<!-- One or two sentences. Link the issue if there is one. -->

## Contract impact

- [ ] No public API change
- [ ] Public API change, recorded under "Unreleased" in CHANGELOG.md
- [ ] New or changed config key, documented in docs/configuration.md
- [ ] New operation, declared with a descriptor and listed in docs/architecture.md

## Checks

- [ ] `ruff check . && ruff format --check . && mypy`
- [ ] `python tools/build_standalone.py` (standalone regenerated and committed)
- [ ] `pytest` (new behaviour has tests taking the `dsa` fixture)
