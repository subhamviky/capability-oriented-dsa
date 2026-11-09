"""ENUMERATION capability: backtracking over a tree of decisions.

Results are bounded twice: ``enumeration_limit`` caps how many solutions are
returned (the result is flagged truncated), and ``enumeration_max_nodes`` caps
the states visited, which is what protects a search that finds few solutions.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from ..algorithms.backtracking import BacktrackingAlgorithms
from ..core.metadata import describe
from ..core.results import DSAExecutionContext
from .base import BaseDSACapability, operation


class EnumerationService(BaseDSACapability):
    capability = "ENUMERATION"

    def _collect(
        self,
        context: DSAExecutionContext,
        args: Mapping[str, Any],
        build: Any,
    ) -> list[tuple[Any, ...]]:
        limit: int = self._setting(context, "enumeration_limit", args)
        max_nodes: int = self._setting(context, "enumeration_max_nodes", args)
        stream: Iterator[tuple[Any, ...]] = build(max_nodes)
        found: list[tuple[Any, ...]] = []
        for solution in stream:
            if 0 <= limit <= len(found):
                context.metadata["truncated"] = True
                context.warn("TRUNCATED", f"stopped at enumeration_limit={limit}; more solutions exist")
                break
            found.append(solution)
        context.found = bool(found)
        context.affected_count = 0
        return found

    @operation(
        describe(
            "SUBSETS",
            capability,
            "SEQUENCE",
            "O(2^n)",
            "O(n)",
            postconditions=("backtracking; every subset, positions treated as distinct",),
        )
    )
    def _subsets(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[tuple[Any, ...]]:
        return self._collect(
            context, args, lambda m: BacktrackingAlgorithms.subsets(context.state.values, max_nodes=m)
        )

    @operation(
        describe(
            "PERMUTATIONS",
            capability,
            "SEQUENCE",
            "O(n!)",
            "O(n)",
            postconditions=("backtracking; every ordering, positions treated as distinct",),
        )
    )
    def _permutations(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[tuple[Any, ...]]:
        return self._collect(
            context, args, lambda m: BacktrackingAlgorithms.permutations(context.state.values, max_nodes=m)
        )

    @operation(
        describe("COMBINATIONS", capability, "SEQUENCE", "O(C(n, k))", "O(k)"),
        requires=("k",),
    )
    def _combinations(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[tuple[Any, ...]]:
        return self._collect(
            context,
            args,
            lambda m: BacktrackingAlgorithms.combinations(context.state.values, args["k"], max_nodes=m),
        )

    @operation(
        describe(
            "COMBINATION_SUM",
            capability,
            "SEQUENCE",
            "exponential in target / smallest candidate",
            "O(target / smallest candidate)",
            preconditions=("candidates positive",),
            postconditions=("backtracking; reusable candidates summing to target",),
        ),
        requires=("target",),
    )
    def _combination_sum(
        self, context: DSAExecutionContext, args: Mapping[str, Any]
    ) -> list[tuple[Any, ...]]:
        return self._collect(
            context,
            args,
            lambda m: BacktrackingAlgorithms.combination_sum(
                context.state.values, args["target"], max_nodes=m
            ),
        )
