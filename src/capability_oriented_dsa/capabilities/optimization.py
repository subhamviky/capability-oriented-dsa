"""OPTIMIZATION capability: derived approaches that pick the best answer.

Dynamic programming and greedy algorithms add no new structure. They solve a
problem over a sequence by reusing smaller answers (DP) or by committing to the
locally best choice (greedy), and each descriptor says which.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..algorithms.dynamic import DynamicProgrammingAlgorithms
from ..algorithms.greedy import GreedyAlgorithms
from ..core.metadata import describe
from ..core.results import DSAExecutionContext
from .base import BaseDSACapability, operation


class OptimizationService(BaseDSACapability):
    capability = "OPTIMIZATION"

    def _cells(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        limit: int = self._setting(context, "dp_max_cells", args)
        return limit

    # -- dynamic programming
    @operation(describe("HOUSE_ROBBER", capability, "SEQUENCE", "O(n)", "O(1)", postconditions=("DP",)))
    def _house_robber(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        return DynamicProgrammingAlgorithms.house_robber(context.state.values)

    @operation(
        describe(
            "LONGEST_INCREASING_SUBSEQUENCE",
            capability,
            "SEQUENCE",
            "O(n log n)",
            "O(n)",
            postconditions=("DP with lower bound; length of a strictly increasing subsequence",),
        )
    )
    def _lis(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        return DynamicProgrammingAlgorithms.longest_increasing_subsequence(context.state.values)

    @operation(
        describe(
            "COIN_CHANGE",
            capability,
            "SEQUENCE",
            "O(amount * coins)",
            "O(amount)",
            preconditions=("coins positive", "amount >= 0"),
            postconditions=("DP; fewest coins, or NOT_FOUND if the amount cannot be made",),
        ),
        requires=("amount",),
    )
    def _coin_change(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int | None:
        count = DynamicProgrammingAlgorithms.coin_change(
            context.state.values, args["amount"], max_cells=self._cells(context, args)
        )
        context.found = count is not None
        return count

    @operation(
        describe(
            "KNAPSACK_01",
            capability,
            "SEQUENCE",
            "O(items * capacity)",
            "O(capacity)",
            preconditions=("values are (weight, value) pairs of non-negative integers",),
            postconditions=("DP; best total value",),
        ),
        requires=("capacity",),
    )
    def _knapsack(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        return DynamicProgrammingAlgorithms.knapsack_01(
            context.state.values, args["capacity"], max_cells=self._cells(context, args)
        )

    @operation(
        describe(
            "LONGEST_COMMON_SUBSEQUENCE",
            capability,
            "SEQUENCE",
            "O(n * m)",
            "O(m)",
            postconditions=("DP; length against the `other` sequence",),
        ),
        requires=("other",),
    )
    def _lcs(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        return DynamicProgrammingAlgorithms.longest_common_subsequence(
            context.state.values, args["other"], max_cells=self._cells(context, args)
        )

    @operation(
        describe(
            "EDIT_DISTANCE",
            capability,
            "SEQUENCE",
            "O(n * m)",
            "O(m)",
            postconditions=("DP; Levenshtein distance to the `other` sequence",),
        ),
        requires=("other",),
    )
    def _edit_distance(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        return DynamicProgrammingAlgorithms.edit_distance(
            context.state.values, args["other"], max_cells=self._cells(context, args)
        )

    # -- greedy
    @operation(
        describe(
            "MERGE_INTERVALS",
            capability,
            "SEQUENCE",
            "O(n log n)",
            "O(n)",
            preconditions=("values are (start, end) pairs with start <= end",),
            postconditions=("greedy; disjoint intervals in order",),
        )
    )
    def _merge_intervals(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[Any]:
        return GreedyAlgorithms.merge_intervals(context.state.values)

    @operation(
        describe(
            "MAX_NON_OVERLAPPING",
            capability,
            "SEQUENCE",
            "O(n log n)",
            "O(n)",
            preconditions=("values are (start, end) pairs with start <= end",),
            postconditions=("greedy by earliest end; a largest set of non-overlapping intervals",),
        )
    )
    def _max_non_overlapping(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[Any]:
        return GreedyAlgorithms.max_non_overlapping(context.state.values)

    @operation(
        describe(
            "CAN_JUMP",
            capability,
            "SEQUENCE",
            "O(n)",
            "O(1)",
            preconditions=("jump lengths non-negative",),
            postconditions=("greedy furthest reach",),
        )
    )
    def _can_jump(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        return GreedyAlgorithms.can_jump(context.state.values)
