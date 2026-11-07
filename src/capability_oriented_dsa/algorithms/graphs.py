"""Graph kernels over adjacency maps. All iterative."""

from __future__ import annotations

import heapq
from collections import deque
from typing import Any

from ..core.errors import AlgorithmPreconditionError, InvalidInputError, InvariantViolationError
from ..core.utilities import PathUtility
from ..structures.adapters import GraphAdapter
from ..structures.states import GraphState

DIJKSTRA_POLICIES = frozenset({"eager", "lazy", "assume_non_negative"})


class GraphAlgorithms:
    @staticmethod
    def _require_vertices(state: GraphState[Any], *vertices: str) -> None:
        missing = [v for v in vertices if v not in state.values]
        if missing:
            raise InvalidInputError(f"unknown vertices: {missing}")

    @staticmethod
    def shortest_unweighted_path(state: GraphState[Any], source: str, target: str) -> list[str]:
        """BFS shortest path by edge count; [] if unreachable."""
        GraphAlgorithms._require_vertices(state, source, target)
        adapter = GraphAdapter(state)
        queue = deque([source])
        parent: dict[str, str | None] = {source: None}
        while queue:
            current = queue.popleft()
            if current == target:
                return PathUtility.reconstruct(parent, target)
            for neighbour in adapter.neighbours(current):
                if neighbour not in parent:
                    parent[neighbour] = current
                    queue.append(neighbour)
        return []

    @staticmethod
    def dijkstra(
        state: GraphState[Any], source: str, target: str, *, negative_weight_policy: str = "eager"
    ) -> tuple[float, list[str]]:
        """Shortest weighted path with an explicit negative-weight policy.

        eager: validate every edge first; safe default; early exit at target.
        lazy: validate only inspected edges; no early exit, because an
              undiscovered negative edge could invalidate greedy finalisation.
        assume_non_negative: no validation, early exit; caller owns the precondition.
        """
        GraphAlgorithms._require_vertices(state, source, target)
        if negative_weight_policy not in DIJKSTRA_POLICIES:
            raise InvalidInputError(f"negative_weight_policy must be one of {sorted(DIJKSTRA_POLICIES)}")
        if negative_weight_policy == "eager":
            for edges in state.adjacency.values():
                if any(weight < 0 for weight in edges.values()):
                    raise AlgorithmPreconditionError("Dijkstra requires non-negative weights")
        inf = float("inf")
        distances: dict[str, float] = {source: 0.0}
        parent: dict[str, str | None] = {source: None}
        queue: list[tuple[float, str]] = [(0.0, source)]
        while queue:
            distance, node = heapq.heappop(queue)
            if distance > distances.get(node, inf):
                continue
            if node == target and negative_weight_policy != "lazy":
                break
            for neighbour, weight in state.adjacency.get(node, {}).items():
                if negative_weight_policy == "lazy" and weight < 0:
                    raise AlgorithmPreconditionError("Dijkstra requires non-negative weights")
                if neighbour not in state.values:
                    raise InvariantViolationError(f"edge {node}->{neighbour} targets unknown vertex")
                candidate = distance + weight
                if candidate < distances.get(neighbour, inf):
                    distances[neighbour] = candidate
                    parent[neighbour] = node
                    heapq.heappush(queue, (candidate, neighbour))
        if target not in distances:
            return inf, []
        return distances[target], PathUtility.reconstruct(parent, target)

    @staticmethod
    def all_simple_paths(
        state: GraphState[Any], source: str, target: str, *, maximum_paths: int = 1000
    ) -> list[list[str]]:
        """Enumerate simple paths (no repeated vertex), bounded by ``maximum_paths``.

        Iterative DFS; worst case is exponential, which is why the bound exists.
        """
        GraphAlgorithms._require_vertices(state, source, target)
        paths: list[list[str]] = []
        stack: list[tuple[str, list[str]]] = [(source, [source])]
        while stack and not (0 <= maximum_paths <= len(paths)):
            node, path = stack.pop()
            if node == target:
                paths.append(path)
                continue
            on_path = set(path)
            for neighbour in reversed(list(state.adjacency.get(node, {}))):
                if neighbour not in on_path:
                    stack.append((neighbour, path + [neighbour]))
        return paths

    @staticmethod
    def has_cycle(state: GraphState[Any]) -> bool:
        """Directed: three-colour DFS. Undirected: DFS tracking the tree edge used."""
        if state.directed:
            white, grey, black = 0, 1, 2
            colour = dict.fromkeys(state.values, white)
            for root in state.values:
                if colour[root] != white:
                    continue
                colour[root] = grey
                stack = [(root, iter(state.adjacency.get(root, {})))]
                while stack:
                    node, neighbours = stack[-1]
                    advanced = False
                    for neighbour in neighbours:
                        state_of = colour.get(neighbour, white)
                        if state_of == grey:
                            return True
                        if state_of == white:
                            colour[neighbour] = grey
                            stack.append((neighbour, iter(state.adjacency.get(neighbour, {}))))
                            advanced = True
                            break
                    if not advanced:
                        colour[node] = black
                        stack.pop()
            return False
        visited: set[str] = set()
        for root in state.values:
            if root in visited:
                continue
            visited.add(root)
            pending: list[tuple[str, str | None]] = [(root, None)]
            while pending:
                node, came_from = pending.pop()
                for neighbour in state.adjacency.get(node, {}):
                    if neighbour == came_from:
                        continue
                    if neighbour in visited:
                        return True
                    visited.add(neighbour)
                    pending.append((neighbour, node))
        return False

    @staticmethod
    def topological_sort(state: GraphState[Any]) -> list[str]:
        """Kahn's algorithm; raises if the graph is undirected or cyclic."""
        if not state.directed:
            raise AlgorithmPreconditionError("topological sort requires a directed graph")
        indegree = dict.fromkeys(state.values, 0)
        for source, targets in state.adjacency.items():
            for target in targets:
                if target not in indegree:
                    raise InvariantViolationError(f"edge {source}->{target} targets unknown vertex")
                indegree[target] += 1
        queue = deque(node for node, degree in indegree.items() if degree == 0)
        result: list[str] = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbour in state.adjacency.get(node, {}):
                indegree[neighbour] -= 1
                if indegree[neighbour] == 0:
                    queue.append(neighbour)
        if len(result) != len(state.values):
            raise AlgorithmPreconditionError("graph contains a cycle")
        return result
