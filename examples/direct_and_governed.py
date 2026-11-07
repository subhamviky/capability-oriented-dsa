"""The same problems solved directly and through the governed facade.

Run: python examples/direct_and_governed.py
"""

from __future__ import annotations

from capability_oriented_dsa import (
    DSAFacade,
    GraphAlgorithms,
    GraphState,
    SearchAlgorithms,
    SequenceState,
    Status,
)

facade = DSAFacade()

# 1. Direct kernel: the interview answer, nothing else.
print("direct binary search:", SearchAlgorithms.binary([10, 20, 30, 40], 30))

# 2. Governed: same kernel, plus precondition check, metrics and a structured result.
result = facade.execute(
    structure_type="SEQUENCE",
    capability="SEARCH",
    operation="BINARY",
    state=SequenceState([10, 20, 30, 40]),
    target=30,
)
print("governed:", result.status.value, result.data, "comparisons =", result.metrics.comparisons)

# 3. A failed precondition, returned as data instead of raised.
unsorted = facade.execute(
    structure_type="SEQUENCE",
    capability="SEARCH",
    operation="BINARY",
    state=SequenceState([3, 1, 2]),
    target=2,
    config={"validation_mode": "result"},
)
print("unsorted input:", unsorted.status.value, unsorted.errors[0].code)

# 4. Build a graph through governed mutations, then find a path.
graph = GraphState[str](directed=True)
for vertex in "ABCD":
    facade.execute(
        structure_type="GRAPH",
        capability="MUTATION",
        operation="ADD_VERTEX",
        state=graph,
        vertex_id=vertex,
        value=vertex,
    )
for source, target, weight in [("A", "B", 1), ("B", "C", 2), ("C", "D", 1), ("A", "D", 10)]:
    facade.execute(
        structure_type="GRAPH",
        capability="MUTATION",
        operation="ADD_EDGE",
        state=graph,
        source=source,
        target=target,
        weight=weight,
    )

path = facade.execute(
    structure_type="GRAPH", capability="PATH", operation="DIJKSTRA", state=graph, source="A", target="D"
)
assert path.status is Status.SUCCESS
print("dijkstra:", path.data, "| direct:", GraphAlgorithms.dijkstra(graph, "A", "D"))

# 5. Every routable operation is self-describing.
descriptor = facade.describe("GRAPH", "PATH", "DIJKSTRA")
print("descriptor:", descriptor.time_complexity, descriptor.preconditions)
print("registered operations:", len(facade.capabilities()))
