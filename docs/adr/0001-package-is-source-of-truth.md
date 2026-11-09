# ADR 0001: The package is the source of truth; the single file is generated

- Status: accepted

## Context

The framework must be usable two ways: as an installable, layered package, and
as a single file that can be copied into another codebase. Maintaining two
hand-edited copies would let them drift, and a byte-equality check between
them would force the package to stay a single module.

## Decision

`src/capability_oriented_dsa/` is layered into `core`, `structures`,
`validation`, `algorithms` and `capabilities`, plus `facade.py`.
`tools/build_standalone.py` concatenates the modules in dependency order,
removes intra-package imports, merges stdlib imports, rejects module-level
name collisions, and appends `__all__` and `__version__`. The generated file
is committed so it can be copied straight from GitHub.

## Consequences

- CI runs `build_standalone.py --check`. A stale file fails the build.
- Every test using the `dsa` fixture runs against both editions, so parity is
  behavioural, not textual.
- A new module must be added to `MODULES` in the tool, which fails loudly if
  it is forgotten.
- Module-level names must be unique across modules (except type variables).
