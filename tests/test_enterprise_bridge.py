"""The worked examples in docs/enterprise-bridge.md, executed against both editions."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "enterprise_bridge.py"


def load_example() -> ModuleType:
    spec = importlib.util.spec_from_file_location("enterprise_bridge", EXAMPLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["enterprise_bridge"] = module
    spec.loader.exec_module(module)
    return module


def test_scale_lookup(dsa: ModuleType) -> None:
    outcome = load_example().scale_lookup(dsa)
    assert outcome["inside"] == ("NOT_FOUND", 1, 4.2)  # insertion point is the band
    assert outcome["exact"] == ("SUCCESS", 1, 4.2)
    assert outcome["above"] == ("NOT_FOUND", 3)  # == len(SCALE): beyond the last band
    assert outcome["unsorted"] == ("FAILURE", "PRECONDITION_FAILED")


def test_calculation_order(dsa: ModuleType) -> None:
    outcome = load_example().calculation_order(dsa)
    order = outcome["order"]
    assert order[0] == "BASE_FREIGHT" and order[-1] == "TOTAL"
    assert outcome["acyclic_has_cycle"] is False
    assert outcome["cyclic_has_cycle"] is True
    assert outcome["cyclic_status"] == "FAILURE"


def test_shared_scope(dsa: ModuleType) -> None:
    outcome = load_example().shared_scope(dsa)
    assert outcome["ancestors"] == ["EMEA", "DE"]
    assert outcome["same_country"] == "DE"
    assert outcome["cross_country"] == "EMEA"
