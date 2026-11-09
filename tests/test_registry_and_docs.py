"""Registry consistency, extension, edition parity and doc coverage."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

import capability_oriented_dsa as package

from .conftest import ROOT, STANDALONE


def test_registry_metadata_is_complete(dsa: ModuleType) -> None:
    facade = dsa.DSAFacade()
    metadata = dsa.build_algorithm_metadata()
    for structure, capability, operation in facade.capabilities():
        descriptor = metadata.get(operation, capability=capability, structure=structure)
        assert descriptor.capability == capability and structure in descriptor.supported_structures


def test_metadata_requires_disambiguation(dsa: ModuleType) -> None:
    metadata = dsa.build_algorithm_metadata()
    with pytest.raises(dsa.UnsupportedOperationError, match="ambiguous"):
        metadata.get("HAS_CYCLE")
    assert metadata.get("HAS_CYCLE", structure="GRAPH").supported_structures == {"GRAPH"}


def test_every_structure_is_validatable(dsa: ModuleType) -> None:
    facade = dsa.DSAFacade()
    for structure in dsa.StructureType:
        assert facade.registry.supports(structure, "VALIDATION", "VALIDATE")


def test_conflicting_registration_rejected(dsa: ModuleType) -> None:
    registry = dsa.build_default_registry()

    class OtherSearch(dsa.SearchService):
        pass

    with pytest.raises(ValueError, match="registered differently"):
        registry.register("SEQUENCE", "SEARCH", "LINEAR", OtherSearch())
    registry.register("SEQUENCE", "SEARCH", "LINEAR", OtherSearch(), replace=True)
    with pytest.raises(ValueError, match="declares no operation"):
        registry.register("GRAPH", "SEARCH", "LINEAR", OtherSearch())


def test_extension_without_editing_framework(dsa: ModuleType) -> None:
    """The design doc's A* example: new kernel + descriptor + registration only."""

    class GreedyPathService(dsa.PathService):
        @dsa.operation(
            dsa.describe("FEWEST_HOPS_SORTED", "PATH", "GRAPH", "O(V+E)", "O(V)"),
            requires=("source", "target"),
        )
        def _fewest(self, ctx: Any, args: Mapping[str, Any]) -> list[str]:
            return dsa.GraphAlgorithms.shortest_unweighted_path(ctx.state, args["source"], args["target"])

    registry = dsa.build_default_registry()
    registry.register("GRAPH", "PATH", "FEWEST_HOPS_SORTED", GreedyPathService())
    state = dsa.GraphState(values={"a": 1, "b": 1}, adjacency={"a": {"b": 1.0}, "b": {}}, directed=True)
    result = dsa.DSAFacade(registry).execute(
        structure_type="GRAPH",
        capability="PATH",
        operation="FEWEST_HOPS_SORTED",
        state=state,
        source="a",
        target="b",
    )
    assert result.data == ["a", "b"]


def test_editions_export_the_same_api() -> None:
    assert package.__all__ == STANDALONE.__all__
    assert package.__version__ == STANDALONE.__version__
    assert package.DSAFacade().capabilities() == STANDALONE.DSAFacade().capabilities()


def test_standalone_is_regenerated() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_standalone.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_configuration_reference_lists_every_key() -> None:
    text = Path(ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
    missing = [key for key in package.DSA_CONFIG if f"`{key}`" not in text]
    assert not missing, f"document these keys in docs/configuration.md: {missing}"


def test_version_matches_pyproject() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{package.__version__}"' in pyproject


def test_enums_cover_every_registered_name(dsa: ModuleType) -> None:
    keys = dsa.DSAFacade().capabilities()
    assert {k[0] for k in keys} == {s.value for s in dsa.StructureType}
    assert {k[1] for k in keys} == {c.value for c in dsa.CapabilityName}


def test_interview_patterns_index_lists_every_operation(dsa: ModuleType) -> None:
    text = Path(ROOT / "docs" / "interview-patterns.md").read_text(encoding="utf-8")
    rows = {
        line.split("|")[1].strip().strip("`"): line
        for line in text.splitlines()
        if line.startswith("| `") and " / " in line.split("|")[1]
    }
    missing = [
        f"{structure} / {capability} / {operation}"
        for structure, capability, operation in dsa.DSAFacade().capabilities()
        if f"`{operation}`" not in rows.get(f"{structure} / {capability}", "")
    ]
    assert not missing, f"add these to the operation index in docs/interview-patterns.md: {missing}"
