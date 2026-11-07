"""Topology-neutral traversal kernels over any NavigableAdapter."""

from __future__ import annotations

from collections import deque
from typing import TypeVar

from ..core.errors import InvalidInputError
from ..core.results import MetricsState
from ..structures.adapters import NavigableAdapter

K = TypeVar("K")


class TraversalAlgorithms:
    @staticmethod
    def bfs(
        adapter: NavigableAdapter[K],
        start: K,
        *,
        track_visited: bool = True,
        maximum_depth: int = -1,
        maximum_results: int = -1,
        metrics: MetricsState | None = None,
    ) -> list[K]:
        """Breadth-first order from ``start``.

        With ``track_visited=False`` on a cyclic topology the walk only
        terminates if ``maximum_depth`` or ``maximum_results`` bounds it; the
        governed TraversalService enforces that.
        """
        if not adapter.contains(start):
            raise InvalidInputError(f"unknown start node: {start}")
        m = metrics or MetricsState()
        result: list[K] = []
        queue: deque[tuple[K, int]] = deque([(start, 0)])
        visited: set[K] = {start} if track_visited else set()
        while queue:
            node, depth = queue.popleft()
            m.queue_operations += 1
            result.append(node)
            m.nodes_visited += 1
            if 0 <= maximum_results <= len(result):
                break
            if 0 <= maximum_depth <= depth:
                continue
            for neighbour in adapter.neighbours(node):
                m.edges_examined += 1
                if not track_visited or neighbour not in visited:
                    if track_visited:
                        visited.add(neighbour)
                    queue.append((neighbour, depth + 1))
                    m.queue_operations += 1
        return result

    @staticmethod
    def dfs(
        adapter: NavigableAdapter[K],
        start: K,
        *,
        track_visited: bool = True,
        maximum_depth: int = -1,
        maximum_results: int = -1,
        metrics: MetricsState | None = None,
    ) -> list[K]:
        """Iterative pre-order depth-first walk; neighbours visited in adapter order."""
        if not adapter.contains(start):
            raise InvalidInputError(f"unknown start node: {start}")
        m = metrics or MetricsState()
        result: list[K] = []
        stack: list[tuple[K, int]] = [(start, 0)]
        visited: set[K] = set()
        while stack:
            node, depth = stack.pop()
            m.stack_operations += 1
            if track_visited and node in visited:
                continue
            if track_visited:
                visited.add(node)
            result.append(node)
            m.nodes_visited += 1
            if 0 <= maximum_results <= len(result):
                break
            if 0 <= maximum_depth <= depth:
                continue
            for neighbour in reversed(list(adapter.neighbours(node))):
                m.edges_examined += 1
                if not track_visited or neighbour not in visited:
                    stack.append((neighbour, depth + 1))
                    m.stack_operations += 1
        return result
