"""Dynamic programming kernels: overlapping subproblems solved once, bottom-up.

All are iterative. Table-based ones accept ``max_cells`` and refuse inputs whose
table would exceed it, so a caller cannot ask for an unbounded allocation.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
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


def scaled_integers(values: Sequence[Any], scale: int | None) -> list[int]:
    """Integers from ints, or from Decimals with a declared scale (v0.3, S-5). A value with
    more fraction digits than the scale is refused, never rounded."""
    if scale is None:
        if any(isinstance(v, Decimal) and v != v.to_integral_value() for v in values):
            raise InvalidInputError("Decimal values need a scale (for example scale=2 for money)")
        return [int(v) for v in values]
    if scale < 0:
        raise InvalidInputError("scale must be >= 0")
    factor = Decimal(10) ** scale
    out = []
    for v in values:
        d = Decimal(str(v)) * factor
        if d != d.to_integral_value():
            raise InvalidInputError(f"{v} has more than {scale} fraction digits")
        out.append(int(d))
    return out


class SubsetSum:
    """Smallest subset (fewest elements; ties: lowest indices) of non-negative integers that
    adds up exactly to a target, each element used at most once (v0.3, S-3). Iterative
    deepening on the subset size with sum bounds; `max_nodes` caps the states visited."""

    def __init__(self, values: Sequence[int], target: int, max_nodes: int = -1) -> None:
        if target < 0 or any(v < 0 for v in values):
            raise InvalidInputError("values and target must be non-negative")
        self.values, self.target, self.max_nodes = list(values), target, max_nodes
        self.visited, self.exhausted = 0, False
        n = len(self.values)
        # for each start position: the remaining values sorted, for the k-largest / k-smallest bounds
        self._sorted = [sorted(self.values[i:]) for i in range(n + 1)]

    def _bounds(self, start: int, k: int) -> tuple[int, int]:
        rest = self._sorted[start]
        return sum(rest[:k]), sum(rest[len(rest) - k :]) if k else 0

    def solve(self) -> tuple[int, ...] | None:
        if self.target == 0:
            return ()
        for size in range(1, len(self.values) + 1):
            found = self._search(0, size, 0, [])
            if found is not None or self.exhausted:
                return found
        return None

    def _search(self, start: int, k: int, total: int, chosen: list[int]) -> tuple[int, ...] | None:
        if k == 0:
            return tuple(chosen) if total == self.target else None
        if len(self.values) - start < k:
            return None
        low, high = self._bounds(start, k)
        if total + low > self.target or total + high < self.target:
            return None
        for i in range(start, len(self.values) - k + 1):
            self.visited += 1
            if 0 <= self.max_nodes < self.visited:
                self.exhausted = True
                return None
            chosen.append(i)
            found = self._search(i + 1, k - 1, total + self.values[i], chosen)
            chosen.pop()
            if found is not None or self.exhausted:
                return found
        return None
