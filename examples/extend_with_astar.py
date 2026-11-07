"""Add A* search without editing any framework file.

Steps: kernel -> config key -> service with a descriptor -> registration.
Run: python examples/extend_with_astar.py
"""

from __future__ import annotations

import heapq
from collections.abc import Callable, Mapping
from typing import Any

from capability_oriented_dsa import (
    AlgorithmPreconditionError,
    BaseDSACapability,
    ConfigKey,
    DSAExecutionContext,
    DSAFacade,
    GraphRepository,
    GraphState,
    PathUtility,
    build_default_registry,
    describe,
    operation,
    register_config_key,
)


# 1. Kernel: plain function over explicit state.
def a_star(
    state: GraphState[Any], source: str, target: str, heuristic: Callable[[str], float]
) -> tuple[float, list[str]]:
    best = {source: 0.0}
    parent: dict[str, str | None] = {source: None}
    frontier = [(heuristic(source), source)]
    while frontier:
        _, node = heapq.heappop(frontier)
        if node == target:
            return best[node], PathUtility.reconstruct(parent, target)
        for neighbour, weight in state.adjacency.get(node, {}).items():
            if weight < 0:
                raise AlgorithmPreconditionError("A* requires non-negative weights")
            candidate = best[node] + weight
            if candidate < best.get(neighbour, float("inf")):
                best[neighbour] = candidate
                parent[neighbour] = node
                heapq.heappush(frontier, (candidate + heuristic(neighbour), neighbour))
    return float("inf"), []


# 2. A tuning knob is a registered key, not a module constant.
register_config_key(
    ConfigKey(
        key="astar_heuristic_scale",
        env="DSA_ASTAR_HEURISTIC_SCALE",
        default=1.0,
        cast=float,
        group="Path",
        used_by="PATH A_STAR",
        description="Multiplier on the heuristic; > 1 trades optimality for speed.",
    )
)


# 3. A service declares the operation with its contract.
class AStarPathService(BaseDSACapability):
    capability = "PATH"

    @operation(
        describe(
            "A_STAR",
            capability,
            "GRAPH",
            "O(E log V) with a consistent heuristic",
            "O(V)",
            preconditions=("non-negative weights", "admissible heuristic for optimality"),
        ),
        requires=("source", "target", "heuristic"),
    )
    def _a_star(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> tuple[float, list[str]]:
        scale = self._setting(context, "astar_heuristic_scale", args)
        distance, path = a_star(
            context.state, args["source"], args["target"], lambda node: scale * args["heuristic"](node)
        )
        context.found = bool(path)
        return distance, path


# 4. Register next to the defaults and call through the same facade.
registry = build_default_registry()
registry.register_service(AStarPathService())
facade = DSAFacade(registry)

grid = GraphState[tuple[int, int]](directed=False)
repo = GraphRepository()
coordinates = {f"{x},{y}": (x, y) for x in range(4) for y in range(4)}
for name, xy in coordinates.items():
    repo.add_vertex(grid, name, xy)
for name, (x, y) in coordinates.items():
    for dx, dy in ((1, 0), (0, 1)):
        neighbour = f"{x + dx},{y + dy}"
        if neighbour in coordinates:
            repo.add_edge(grid, name, neighbour, 1)


def manhattan(node: str) -> float:
    x, y = coordinates[node]
    return abs(3 - x) + abs(3 - y)


result = facade.execute(
    structure_type="GRAPH",
    capability="PATH",
    operation="A_STAR",
    state=grid,
    source="0,0",
    target="3,3",
    heuristic=manhattan,
)
print("A*:", result.status.value, result.data)
print("descriptor:", facade.describe("GRAPH", "PATH", "A_STAR").preconditions)
assert result.data[0] == 6.0
