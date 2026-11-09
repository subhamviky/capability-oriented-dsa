"""Greedy kernels: a locally best choice that is provably globally best for these problems."""

from __future__ import annotations

from collections.abc import Sequence

from ..core.errors import InvalidInputError

Interval = tuple[int, int]


def _check(intervals: Sequence[Interval]) -> None:
    for start, end in intervals:
        if start > end:
            raise InvalidInputError(f"interval start exceeds end: {(start, end)}")


class GreedyAlgorithms:
    @staticmethod
    def merge_intervals(intervals: Sequence[Interval]) -> list[Interval]:
        """Merge overlapping or touching intervals; sort by start, then sweep."""
        _check(intervals)
        merged: list[Interval] = []
        for start, end in sorted(intervals):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return merged

    @staticmethod
    def max_non_overlapping(intervals: Sequence[Interval]) -> list[Interval]:
        """Largest set of pairwise non-overlapping intervals (touching is allowed).

        Choosing the interval that ends first keeps the most room for the rest.
        """
        _check(intervals)
        chosen: list[Interval] = []
        last_end: int | None = None
        for start, end in sorted(intervals, key=lambda item: (item[1], item[0])):
            if last_end is None or start >= last_end:
                chosen.append((start, end))
                last_end = end
        return chosen

    @staticmethod
    def can_jump(steps: Sequence[int]) -> bool:
        """Whether the last index is reachable when ``steps[i]`` is the longest jump from ``i``."""
        if any(step < 0 for step in steps):
            raise InvalidInputError("jump lengths must be non-negative")
        reach = 0
        for index, step in enumerate(steps):
            if index > reach:
                return False
            reach = max(reach, index + step)
        return True
