"""Search kernels. Pure functions over Python lists."""

from __future__ import annotations

import operator
from collections.abc import Callable, Iterable, Sequence
from itertools import pairwise, starmap
from typing import Any, TypeVar

from ..core.results import MetricsState
from ..core.utilities import KeyResolver

T = TypeVar("T")


class SearchAlgorithms:
    @staticmethod
    def linear(
        values: Sequence[T],
        target: Any,
        *,
        key: Callable[[T], Any] | None = None,
        metrics: MetricsState | None = None,
    ) -> int | None:
        """Index of the first element whose key equals ``target``, else None."""
        m = metrics or MetricsState()
        for index, value in enumerate(values):
            m.iterations += 1
            m.reads += 1
            m.comparisons += 1
            if KeyResolver.resolve(value, key_function=key) == target:
                return index
        return None

    @staticmethod
    def binary(
        values: Sequence[T],
        target: Any,
        *,
        key: Callable[[T], Any] | None = None,
        metrics: MetricsState | None = None,
    ) -> int | None:
        """Index of *an* element whose key equals ``target``. Input must be sorted by key."""
        m = metrics or MetricsState()
        left, right = 0, len(values) - 1
        while left <= right:
            m.iterations += 1
            middle = (left + right) // 2
            current = KeyResolver.resolve(values[middle], key_function=key)
            m.reads += 1
            m.comparisons += 1
            if current == target:
                return middle
            m.comparisons += 1
            if current < target:
                left = middle + 1
            else:
                right = middle - 1
        return None

    @staticmethod
    def lower_bound(
        values: Sequence[T],
        target: Any,
        *,
        key: Callable[[T], Any] | None = None,
        metrics: MetricsState | None = None,
    ) -> int:
        """First index whose key is >= ``target`` (``len(values)`` if none).

        Use this when duplicates exist and the *first* occurrence matters.
        """
        m = metrics or MetricsState()
        left, right = 0, len(values)
        while left < right:
            m.iterations += 1
            m.reads += 1
            m.comparisons += 1
            middle = (left + right) // 2
            if KeyResolver.resolve(values[middle], key_function=key) < target:
                left = middle + 1
            else:
                right = middle
        return left

    @staticmethod
    def is_sorted(values: Sequence[T], *, key: Callable[[T], Any] | None = None) -> bool:
        """Non-decreasing by key. O(n), early exit, iterated at C level (no auxiliary list)."""
        keys: Iterable[Any] = values if key is None else map(key, values)
        return all(starmap(operator.le, pairwise(keys)))
