"""Sort kernels. Every kernel returns a new list and never mutates its input."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from ..core.results import MetricsState
from ..core.utilities import KeyResolver

T = TypeVar("T")


class SortAlgorithms:
    @staticmethod
    def bubble(
        values: Sequence[T], *, key: Callable[[T], Any] | None = None, metrics: MetricsState | None = None
    ) -> list[T]:
        """Stable, O(n^2), early exit when a pass makes no swap."""
        m = metrics or MetricsState()
        out = list(values)
        for end in range(len(out) - 1, 0, -1):
            swapped = False
            for i in range(end):
                m.iterations += 1
                m.comparisons += 1
                m.reads += 2
                if KeyResolver.resolve(out[i], key_function=key) > KeyResolver.resolve(
                    out[i + 1], key_function=key
                ):
                    out[i], out[i + 1] = out[i + 1], out[i]
                    m.swaps += 1
                    m.writes += 2
                    swapped = True
            if not swapped:
                break
        return out

    @staticmethod
    def merge(
        values: Sequence[T], *, key: Callable[[T], Any] | None = None, metrics: MetricsState | None = None
    ) -> list[T]:
        """Stable top-down merge sort. Recursion depth is ceil(log2 n)."""
        m = metrics or MetricsState()

        def sort(items: list[T], depth: int) -> list[T]:
            if len(items) <= 1:
                return items
            m.recursion_depth = depth
            m.max_recursion_depth = max(m.max_recursion_depth, depth)
            mid = len(items) // 2
            left, right = sort(items[:mid], depth + 1), sort(items[mid:], depth + 1)
            result: list[T] = []
            i = j = 0
            while i < len(left) and j < len(right):
                m.comparisons += 1
                m.reads += 2
                m.iterations += 1
                if KeyResolver.resolve(left[i], key_function=key) <= KeyResolver.resolve(
                    right[j], key_function=key
                ):
                    result.append(left[i])
                    i += 1
                else:
                    result.append(right[j])
                    j += 1
                m.writes += 1
            result.extend(left[i:])
            result.extend(right[j:])
            m.writes += len(left) - i + len(right) - j
            return result

        out = sort(list(values), 1)
        m.recursion_depth = 0
        return out

    @staticmethod
    def quick(
        values: Sequence[T], *, key: Callable[[T], Any] | None = None, metrics: MetricsState | None = None
    ) -> list[T]:
        """Unstable quicksort with Hoare partitioning on one O(n) working copy.

        Recurses into the smaller partition and loops on the larger one, so the
        call stack is O(log n) even on adversarial input (time stays O(n^2)
        worst case, O(n log n) expected).
        """
        m = metrics or MetricsState()
        out = list(values)

        def value_key(index: int) -> Any:
            m.reads += 1
            return KeyResolver.resolve(out[index], key_function=key)

        def partition(low: int, high: int) -> int:
            pivot = value_key((low + high) // 2)
            i, j = low - 1, high + 1
            while True:
                i += 1
                while value_key(i) < pivot:
                    m.comparisons += 1
                    m.iterations += 1
                    i += 1
                m.comparisons += 1
                j -= 1
                while value_key(j) > pivot:
                    m.comparisons += 1
                    m.iterations += 1
                    j -= 1
                m.comparisons += 1
                if i >= j:
                    return j
                out[i], out[j] = out[j], out[i]
                m.swaps += 1
                m.writes += 2

        def sort_range(low: int, high: int, depth: int) -> None:
            while low < high:
                m.recursion_depth = depth
                m.max_recursion_depth = max(m.max_recursion_depth, depth)
                split = partition(low, high)
                if split - low < high - split:
                    sort_range(low, split, depth + 1)
                    low = split + 1
                else:
                    sort_range(split + 1, high, depth + 1)
                    high = split

        sort_range(0, len(out) - 1, 1)
        m.recursion_depth = 0
        return out
