"""PATH capability: graph path finding."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..algorithms.graphs import GraphAlgorithms
from ..core.metadata import describe
from ..core.results import DSAExecutionContext
from .base import BaseDSACapability, operation

ENDPOINTS = ("source", "target")


class PathService(BaseDSACapability):
    """Unreachable targets yield NOT_FOUND; the empty path is still returned as data."""

    capability = "PATH"

    @operation(
        describe(
            "SHORTEST_UNWEIGHTED",
            capability,
            "GRAPH",
            "O(V+E)",
            "O(V)",
            postconditions=("minimum edge-count path or NOT_FOUND",),
        ),
        requires=ENDPOINTS,
    )
    def _shortest_unweighted(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[str]:
        path = GraphAlgorithms.shortest_unweighted_path(context.state, args["source"], args["target"])
        context.found = bool(path)
        return path

    @operation(
        describe(
            "DIJKSTRA",
            capability,
            "GRAPH",
            "O((V+E) log V)",
            "O(V)",
            preconditions=("all edge weights are non-negative",),
            postconditions=("(distance, path) or NOT_FOUND with (inf, [])",),
        ),
        requires=ENDPOINTS,
    )
    def _dijkstra(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> tuple[float, list[str]]:
        policy = self._setting(context, "dijkstra_negative_weight_policy", args)
        distance, path = GraphAlgorithms.dijkstra(
            context.state, args["source"], args["target"], negative_weight_policy=policy
        )
        context.found = bool(path)
        return distance, path

    @operation(
        describe(
            "ALL_SIMPLE_PATHS",
            capability,
            "GRAPH",
            "O(paths * V) bounded by maximum_paths",
            "O(V) stack per path",
        ),
        requires=ENDPOINTS,
    )
    def _all_simple_paths(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[list[str]]:
        bound = self._setting(context, "maximum_paths", args)
        paths = GraphAlgorithms.all_simple_paths(
            context.state, args["source"], args["target"], maximum_paths=bound
        )
        if 0 <= bound <= len(paths):
            context.warn("TRUNCATED", f"stopped after maximum_paths={bound}")
        context.found = bool(paths)
        return paths
