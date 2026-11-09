"""Two-pointer and sliding-window kernels over a sequence."""

from __future__ import annotations

from collections.abc import Hashable, Sequence

from ..core.errors import InvalidInputError


class WindowAlgorithms:
    @staticmethod
    def pair_sum_sorted(values: Sequence[int], target: int) -> tuple[int, int] | None:
        """Indexes of two entries summing to ``target`` in a sorted sequence; O(n), O(1) space."""
        low, high = 0, len(values) - 1
        while low < high:
            total = values[low] + values[high]
            if total == target:
                return low, high
            if total < target:
                low += 1
            else:
                high -= 1
        return None

    @staticmethod
    def longest_unique_window(values: Sequence[Hashable]) -> int:
        """Length of the longest window with no repeated value (variable window + last-seen map)."""
        last_seen: dict[Hashable, int] = {}
        start = best = 0
        for index, value in enumerate(values):
            if last_seen.get(value, -1) >= start:
                start = last_seen[value] + 1
            last_seen[value] = index
            best = max(best, index - start + 1)
        return best

    @staticmethod
    def min_subarray_length(values: Sequence[int], target: int) -> int:
        """Shortest contiguous subarray with sum >= ``target``; 0 if none. Needs non-negative values."""
        if any(value < 0 for value in values):
            raise InvalidInputError("values must be non-negative")
        best = len(values) + 1
        start = total = 0
        for end, value in enumerate(values):
            total += value
            while total >= target and start <= end:
                best = min(best, end - start + 1)
                total -= values[start]
                start += 1
        return 0 if best == len(values) + 1 else best

    @staticmethod
    def max_area(heights: Sequence[int]) -> int:
        """Largest water area between two bars (container problem); O(n) two pointers."""
        if any(h < 0 for h in heights):
            raise InvalidInputError("heights must be non-negative")
        low, high, best = 0, len(heights) - 1, 0
        while low < high:
            best = max(best, (high - low) * min(heights[low], heights[high]))
            if heights[low] < heights[high]:
                low += 1
            else:
                high -= 1
        return best
