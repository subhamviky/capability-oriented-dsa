#!/usr/bin/env python3
"""Generate standalone/dsa_framework.py from the package sources.

The package under src/ is the only source of truth. This tool concatenates its
modules in dependency order, drops intra-package imports, merges stdlib
imports, and appends the package's ``__all__`` and ``__version__``.

    python tools/build_standalone.py          # write the file
    python tools/build_standalone.py --check  # exit 1 if the file is stale (CI)
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "capability_oriented_dsa"
OUTPUT = ROOT / "standalone" / "dsa_framework.py"

#: Dependency order. A new module must be added here (the tool fails otherwise).
MODULES = [
    "core/errors.py",
    "core/config.py",
    "core/results.py",
    "core/idempotency.py",
    "core/metadata.py",
    "core/utilities.py",
    "structures/states.py",
    "structures/adapters.py",
    "structures/repositories.py",
    "validation/validators.py",
    "algorithms/search.py",
    "algorithms/sorting.py",
    "algorithms/traversal.py",
    "algorithms/sequences.py",
    "algorithms/linked_list.py",
    "algorithms/trees.py",
    "algorithms/bst.py",
    "algorithms/trie.py",
    "algorithms/graphs.py",
    "capabilities/base.py",
    "capabilities/search.py",
    "capabilities/ordering.py",
    "capabilities/traversal.py",
    "capabilities/path.py",
    "capabilities/query.py",
    "capabilities/mutation.py",
    "capabilities/validation.py",
    "facade.py",
]
#: Module-level names that may be defined identically in several modules.
SHARED_NAMES = {"T", "K", "F", "S_contra"}

HEADER = '''"""Capability-Oriented DSA - portable single-file edition.

GENERATED FILE - DO NOT EDIT. Source of truth: src/capability_oriented_dsa/.
Regenerate with: python tools/build_standalone.py

Copy this file into another codebase to use the framework without installing
the package. Keep the licence notice, record the version below, and do not
import this module and the installed package in the same process (their
classes and configuration registries would be distinct objects).

SPDX-License-Identifier: MIT
"""
from __future__ import annotations
'''


def _module_parts(path: Path) -> tuple[list[ast.stmt], list[str]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines()
    drop: set[int] = set()
    imports: list[ast.stmt] = []
    for index, node in enumerate(tree.body):
        is_docstring = (
            index == 0
            and isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
        if is_docstring or isinstance(node, (ast.Import, ast.ImportFrom)):
            drop.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(node)
    body = [line for number, line in enumerate(lines, start=1) if number not in drop]
    while body and not body[0].strip():
        body.pop(0)
    return imports, body


def _defined_names(body: list[str]) -> set[str]:
    tree = ast.parse("\n".join(body))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names.update(t.id for t in targets if isinstance(t, ast.Name))
    return names


def build() -> str:
    on_disk = {p.relative_to(PACKAGE).as_posix() for p in PACKAGE.rglob("*.py") if p.name != "__init__.py"}
    if on_disk != set(MODULES):
        raise SystemExit(
            f"MODULES out of sync with package: missing={sorted(on_disk - set(MODULES))} "
            f"extra={sorted(set(MODULES) - on_disk)}"
        )
    plain: set[str] = set()
    from_imports: dict[str, set[str]] = defaultdict(set)
    sections: list[str] = []
    owners: dict[str, str] = {}
    for relative in MODULES:
        imports, body = _module_parts(PACKAGE / relative)
        for node in imports:
            if isinstance(node, ast.Import):
                plain.update(ast.unparse(alias) for alias in node.names)
            elif node.level == 0 and node.module != "__future__":
                from_imports[node.module or ""].update(ast.unparse(a) for a in node.names)
        for name in _defined_names(body) - SHARED_NAMES:
            if name in owners:
                raise SystemExit(f"name collision: {name!r} defined in {owners[name]} and {relative}")
            owners[name] = relative
        banner = f"# {'=' * 76}\n# {relative}\n# {'=' * 76}"
        sections.append(banner + "\n" + "\n".join(body).rstrip() + "\n")

    init_tree = ast.parse((PACKAGE / "__init__.py").read_text(encoding="utf-8"))
    exported: list[str] = []
    version = "0.0.0"
    for node in init_tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id == "__all__":
                exported = list(ast.literal_eval(node.value))
            elif node.targets[0].id == "__version__":
                version = ast.literal_eval(node.value)
    missing = sorted(set(exported) - set(owners) - {"__version__"})
    if missing:
        raise SystemExit(f"__all__ names not defined in amalgamation: {missing}")

    import_block = [f"import {name}" for name in sorted(plain)]
    import_block += [
        f"from {module} import {', '.join(sorted(names))}" for module, names in sorted(from_imports.items())
    ]
    all_block = "__all__ = [\n" + "".join(f"    {name!r},\n" for name in exported) + "]\n"
    return (
        HEADER
        + "\n"
        + "\n".join(import_block)
        + "\n\n"
        + f"__version__ = {version!r}\n\n\n"
        + "\n\n".join(sections)
        + "\n\n"
        + all_block
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the committed file is stale")
    args = parser.parse_args()
    generated = build()
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != generated:
            print(
                f"{OUTPUT.relative_to(ROOT)} is stale; run: python tools/build_standalone.py", file=sys.stderr
            )
            return 1
        print(f"{OUTPUT.relative_to(ROOT)} is up to date")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(generated, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({generated.count(chr(10))} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
