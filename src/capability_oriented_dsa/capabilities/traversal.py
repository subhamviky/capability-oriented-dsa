"""TRAVERSAL capability: one BFS/DFS implementation for trees and graphs."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ..algorithms.traversal import TraversalAlgorithms
from ..core.errors import AlgorithmPreconditionError
from ..core.metadata import describe
from ..core.results import DSAExecutionContext
from ..structures.adapters import GraphAdapter, NavigableAdapter, OrderedAdapter, TreeAdapter
from .base import BaseDSACapability, operation

#: Data-driven adapter selection; extend by registering a new structure here.
ADAPTER_FACTORIES: dict[str, Callable[[Any], NavigableAdapter[Any]]] = {
    "TREE": TreeAdapter,
    "GRAPH": GraphAdapter,
}


class TraversalService(BaseDSACapability):
    capability = "TRAVERSAL"

    def _walk(
        self, context: DSAExecutionContext, args: Mapping[str, Any], kernel: Callable[..., list[Any]]
    ) -> list[Any]:
        scope = f"{context.structure_type.title()}Traversal"
        track = self._setting(context, "track_visited", args, scope=scope)
        depth = self._setting(context, "maximum_depth", args)
        limit = self._setting(context, "maximum_results", args)
        if not track and context.structure_type == "GRAPH" and depth < 0 and limit < 0:
            raise AlgorithmPreconditionError(
                "track_visited=False on a graph needs maximum_depth or maximum_results >= 0; "
                "otherwise any cycle makes the traversal unbounded"
            )
        adapter = OrderedAdapter(
            ADAPTER_FACTORIES[context.structure_type](context.state),
            self._setting(context, "neighbour_order", args),
        )
        start = args.get("start")
        if start is None:
            start = next(iter(adapter.start_nodes()), None)
        if start is None:
            context.found = False
            return []
        return kernel(
            adapter,
            start,
            track_visited=track,
            maximum_depth=depth,
            maximum_results=limit,
            metrics=self._metrics(context, args),
        )

    @operation(describe("BFS", capability, {"TREE", "GRAPH"}, "O(V+E)", "O(V)"))
    def _bfs(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[Any]:
        return self._walk(context, args, TraversalAlgorithms.bfs)

    @operation(describe("DFS", capability, {"TREE", "GRAPH"}, "O(V+E)", "O(V)"))
    def _dfs(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[Any]:
        return self._walk(context, args, TraversalAlgorithms.dfs)
