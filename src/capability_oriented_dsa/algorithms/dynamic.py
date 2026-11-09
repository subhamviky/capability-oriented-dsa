"""Dynamic programming kernels: overlapping subproblems solved once, bottom-up.

All are iterative. Table-based ones accept ``max_cells`` and refuse inputs whose
table would exceed it, so a caller cannot ask for an unbounded allocation.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ..core.errors import InvalidInputError
from .search import SearchAlgorithms


def _require_cells(cells: int, max_cells: int | None) -> None:
    if max_cells is not None and max_cells >= 0 and cells > max_cells:
        raise InvalidInputError(f"table needs {cells} cells, over the limit of {max_cells}")


class DynamicProgrammingAlgorithms:
    @staticmethod
    def house_robber(values: Sequence[int]) -> int:
        """Maximum sum of non-adjacent elements (skipping is always allowed)."""
        take = skip = 0
        for value in values:
            take, skip = skip + value, max(take, skip)
        return max(take, skip)

    @staticmethod
    def longest_increasing_subsequence(values: Sequence[Any]) -> int:
        """Length of the longest strictly increasing subsequence in O(n log n).

        ``tails[i]`` is the smallest tail of an increasing subsequence of length ``i + 1``;
        it stays sorted, so the position for each value is a core ``lower_bound``.
        """
        tails: list[Any] = []
        for value in values:
            position = SearchAlgorithms.lower_bound(tails, value)
            if position == len(tails):
                tails.append(value)
            else:
                tails[position] = value
        return len(tails)

    @staticmethod
    def coin_change(coins: Sequence[int], amount: int, *, max_cells: int | None = None) -> int | None:
        """Fewest coins (unlimited supply) making ``amount``; None if impossible."""
        if amount < 0 or any(coin <= 0 for coin in coins):
            raise InvalidInputError("amount must be >= 0 and coins positive")
        _require_cells((amount + 1) * max(len(coins), 1), max_cells)
        unreachable = amount + 1
        best = [0] + [unreachable] * amount
        for total in range(1, amount + 1):
            for coin in coins:
                if coin <= total and best[total - coin] + 1 < best[total]:
                    best[total] = best[total - coin] + 1
        return None if best[amount] == unreachable else best[amount]

    @staticmethod
    def knapsack_01(items: Sequence[tuple[int, int]], capacity: int, *, max_cells: int | None = None) -> int:
        """Best total value of ``(weight, value)`` items within ``capacity``, each used once."""
        if capacity < 0 or any(weight < 0 or value < 0 for weight, value in items):
            raise InvalidInputError("capacity, weights and values must be non-negative")
        _require_cells(len(items) * (capacity + 1), max_cells)
        best = [0] * (capacity + 1)
        for weight, value in items:
            for room in range(capacity, weight - 1, -1):
                best[room] = max(best[room], best[room - weight] + value)
        return best[capacity]

    @staticmethod
    def longest_common_subsequence(
        left: Sequence[Any], right: Sequence[Any], *, max_cells: int | None = None
    ) -> int:
        _require_cells(len(left) * len(right), max_cells)
        previous = [0] * (len(right) + 1)
        for a in left:
            current = [0]
            for j, b in enumerate(right, start=1):
                current.append(previous[j - 1] + 1 if a == b else max(previous[j], current[j - 1]))
            previous = current
        return previous[-1]

    @staticmethod
    def edit_distance(left: Sequence[Any], right: Sequence[Any], *, max_cells: int | None = None) -> int:
        """Levenshtein distance: fewest insertions, deletions and substitutions."""
        _require_cells(len(left) * len(right), max_cells)
        previous = list(range(len(right) + 1))
        for i, a in enumerate(left, start=1):
            current = [i]
            for j, b in enumerate(right, start=1):
                current.append(
                    min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (0 if a == b else 1))
                )
            previous = current
        return previous[-1]
