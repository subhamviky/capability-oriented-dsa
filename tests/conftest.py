"""Every test that takes the ``dsa`` fixture runs against both editions."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest

import capability_oriented_dsa as package

ROOT = Path(__file__).resolve().parents[1]


def _load_standalone() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "dsa_framework_standalone", ROOT / "standalone" / "dsa_framework.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


STANDALONE = _load_standalone()
EDITIONS = [package, STANDALONE]


@pytest.fixture(params=EDITIONS, ids=["package", "standalone"])
def dsa(request: pytest.FixtureRequest) -> ModuleType:
    return request.param  # type: ignore[no-any-return]


@pytest.fixture(autouse=True)
def _isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ambient DSA_* variables must never change test outcomes."""
    for name in list(os.environ):
        if name.startswith("DSA_"):
            monkeypatch.delenv(name)


@pytest.fixture
def facade(dsa: ModuleType) -> object:
    return dsa.DSAFacade()


def build_graph(
    dsa: ModuleType, edges: list[tuple[str, str, float]], *, directed: bool = True, vertices: str = ""
) -> object:
    state = dsa.GraphState(directed=directed)
    repo = dsa.GraphRepository()
    names = sorted(set(vertices) | {v for edge in edges for v in edge[:2]})
    for name in names:
        repo.add_vertex(state, name, name)
    for source, target, weight in edges:
        repo.add_edge(state, source, target, weight)
    return state


def build_chain_tree(dsa: ModuleType, size: int) -> object:
    state = dsa.TreeState()
    repo = dsa.TreeRepository()
    repo.add_root(state, "0", 0)
    for value in range(1, size):
        repo.add_child(state, str(value - 1), str(value), value)
    return state
