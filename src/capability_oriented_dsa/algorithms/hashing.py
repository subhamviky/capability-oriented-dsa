"""Hashing patterns: trade O(n) memory for O(1) average lookups.

The hash map itself is Python's ``dict``/``set``; no state wrapper is needed.
These kernels are the recurring *patterns* built on it.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Hashable, Sequence
from typing import Any


class HashingAlgorithms:
    @staticmethod
    def has_duplicate(values: Sequence[Hashable]) -> bool:
        seen: set[Hashable] = set()
        for value in values:
            if value in seen:
                return True
            seen.add(value)
        return False

    @staticmethod
    def frequency(values: Sequence[Hashable]) -> dict[Hashable, int]:
        """Counts in first-seen order."""
        return dict(Counter(values))

    @staticmethod
    def group_anagrams(words: Sequence[str]) -> list[list[str]]:
        """Group words made of the same letters; groups and members in first-seen order."""
        groups: dict[tuple[str, ...], list[str]] = {}
        for word in words:
            groups.setdefault(tuple(sorted(word)), []).append(word)
        return list(groups.values())

    @staticmethod
    def longest_consecutive(values: Sequence[int]) -> int:
        """Length of the longest run of consecutive integers, in O(n) without sorting."""
        members = set(values)
        best = 0
        for value in members:
            if value - 1 not in members:
                end = value
                while end + 1 in members:
                    end += 1
                best = max(best, end - value + 1)
        return best

    @staticmethod
    def subarray_sum_count(values: Sequence[int], target: int) -> int:
        """Number of contiguous subarrays summing to ``target`` (prefix sums + hash map)."""
        seen: dict[int, int] = {0: 1}
        running = count = 0
        for value in values:
            running += value
            count += seen.get(running - target, 0)
            seen[running] = seen.get(running, 0) + 1
        return count

    @staticmethod
    def first_unique(values: Sequence[Any]) -> int | None:
        """Index of the first value that occurs exactly once."""
        counts = Counter(values)
        for index, value in enumerate(values):
            if counts[value] == 1:
                return index
        return None
