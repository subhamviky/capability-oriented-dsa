"""Three enterprise-shaped problems solved with governed capabilities.

Each section pairs with a section of docs/enterprise-bridge.md.

Run: python examples/enterprise_bridge.py
"""

from __future__ import annotations

from types import ModuleType
from typing import Any

# A scale-style table: (upper_limit, rate). A quantity belongs to the first band
# whose upper limit is >= the quantity.
SCALE = [(100, 5.00), (500, 4.20), (2000, 3.50)]

# Calculation dependencies: an edge A -> B means "A must be computed before B".
CHARGE_DEPENDENCIES = [
    ("BASE_FREIGHT", "FUEL_SURCHARGE"),
    ("BASE_FREIGHT", "VOLUME_DISCOUNT"),
    ("FUEL_SURCHARGE", "TOTAL"),
    ("VOLUME_DISCOUNT", "TOTAL"),
]

# A location hierarchy: (parent, child).
HIERARCHY = [
    (None, "EMEA"),
    ("EMEA", "DE"),
    ("EMEA", "FR"),
    ("DE", "PLANT_1000"),
    ("DE", "PLANT_2000"),
    ("FR", "PLANT_3000"),
]


def scale_lookup(dsa: ModuleType) -> dict[str, Any]:
    """Which band does a quantity fall in? Sorted table + LOWER_BOUND.

    LOWER_BOUND reports NOT_FOUND whenever the quantity is not *exactly* an upper
    limit, and still carries the insertion point in ``data``. For a band lookup
    that insertion point is the answer: it is valid whenever it is < len(rows).
    """
    facade = dsa.DSAFacade()

    def band(quantity: int, rows: list[tuple[int, float]]) -> Any:
        return facade.execute(
            structure_type="SEQUENCE",
            capability="SEARCH",
            operation="LOWER_BOUND",
            state=dsa.SequenceState(rows),
            target=quantity,
            key=lambda row: row[0],
            config={"validation_mode": "result"},
        )

    inside = band(350, SCALE)
    exact = band(500, SCALE)
    above = band(2500, SCALE)  # beyond the last band: NOT_FOUND, index = len(SCALE)
    unsorted = band(350, [SCALE[1], SCALE[0], SCALE[2]])
    return {
        "inside": (inside.status.value, inside.data, SCALE[inside.data][1]),
        "exact": (exact.status.value, exact.data, SCALE[exact.data][1]),
        "above": (above.status.value, above.data),
        "unsorted": (unsorted.status.value, unsorted.errors[0].code),
    }


def calculation_order(dsa: ModuleType) -> dict[str, Any]:
    """In which order can dependent items be computed? DAG + TOPOLOGICAL_SORT."""
    facade = dsa.DSAFacade()

    def build(dependencies: list[tuple[str, str]]) -> Any:
        graph = dsa.GraphState(directed=True)
        for name in sorted({item for edge in dependencies for item in edge}):
            facade.execute(
                structure_type="GRAPH",
                capability="MUTATION",
                operation="ADD_VERTEX",
                state=graph,
                vertex_id=name,
                value=name,
            )
        for source, target in dependencies:
            facade.execute(
                structure_type="GRAPH",
                capability="MUTATION",
                operation="ADD_EDGE",
                state=graph,
                source=source,
                target=target,
                weight=1,
            )
        return graph

    def query(operation: str, graph: Any) -> Any:
        return facade.execute(
            structure_type="GRAPH",
            capability="QUERY",
            operation=operation,
            state=graph,
            config={"validation_mode": "result"},
        )

    acyclic = build(CHARGE_DEPENDENCIES)
    cyclic = build([*CHARGE_DEPENDENCIES, ("TOTAL", "BASE_FREIGHT")])
    order = query("TOPOLOGICAL_SORT", acyclic)
    broken = query("TOPOLOGICAL_SORT", cyclic)
    return {
        "order": order.data,
        "acyclic_has_cycle": query("HAS_CYCLE", acyclic).data,
        "cyclic_has_cycle": query("HAS_CYCLE", cyclic).data,
        "cyclic_status": broken.status.value,
    }


def shared_scope(dsa: ModuleType) -> dict[str, Any]:
    """Which node do two entries share? Tree + ANCESTORS / LOWEST_COMMON_ANCESTOR."""
    facade = dsa.DSAFacade()
    tree = dsa.TreeState()
    for parent, child in HIERARCHY:
        facade.execute(
            structure_type="TREE",
            capability="MUTATION",
            operation="ADD_ROOT" if parent is None else "ADD_CHILD",
            state=tree,
            **({} if parent is None else {"parent_id": parent}),
            node_id=child,
            value=child,
        )

    def query(operation: str, **args: str) -> Any:
        return facade.execute(
            structure_type="TREE", capability="QUERY", operation=operation, state=tree, **args
        ).data

    return {
        "ancestors": query("ANCESTORS", node_id="PLANT_1000"),
        "same_country": query("LOWEST_COMMON_ANCESTOR", left="PLANT_1000", right="PLANT_2000"),
        "cross_country": query("LOWEST_COMMON_ANCESTOR", left="PLANT_1000", right="PLANT_3000"),
    }


def run(dsa: ModuleType) -> dict[str, dict[str, Any]]:
    return {
        "scale_lookup": scale_lookup(dsa),
        "calculation_order": calculation_order(dsa),
        "shared_scope": shared_scope(dsa),
    }


if __name__ == "__main__":
    import capability_oriented_dsa

    for section, outcome in run(capability_oriented_dsa).items():
        print(section)
        for name, value in outcome.items():
            print(f"  {name}: {value}")
