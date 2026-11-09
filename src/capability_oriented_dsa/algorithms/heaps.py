"""Binary heap kernels: the structure itself, plus the patterns built on it."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ..core.errors import AlgorithmPreconditionError, InvalidInputError
from ..structures.states import HeapState


class HeapAlgorithms:
    @staticmethod
    def _before(left: Any, right: Any, max_heap: bool) -> bool:
        """True if ``left`` must sit above ``right``."""
        return bool(left > right) if max_heap else bool(left < right)

    @staticmethod
    def push(state: HeapState[Any], value: Any) -> None:
        values = state.values
        values.append(value)
        child = len(values) - 1
        while child > 0:
            parent = (child - 1) // 2
            if not HeapAlgorithms._before(values[child], values[parent], state.max_heap):
                break
            values[child], values[parent] = values[parent], values[child]
            child = parent

    @staticmethod
    def peek(state: HeapState[Any]) -> Any:
        if not state.values:
            raise InvalidInputError("heap is empty")
        return state.values[0]

    @staticmethod
    def pop(state: HeapState[Any]) -> Any:
        """Remove and return the top element."""
        values = state.values
        if not values:
            raise InvalidInputError("heap is empty")
        top = values[0]
        last = values.pop()
        if values:
            values[0] = last
            HeapAlgorithms._sift_down(values, 0, state.max_heap)
        return top

    @staticmethod
    def _sift_down(values: list[Any], index: int, max_heap: bool) -> None:
        size = len(values)
        while True:
            best = index
            for child in (2 * index + 1, 2 * index + 2):
                if child < size and HeapAlgorithms._before(values[child], values[best], max_heap):
                    best = child
            if best == index:
                return
            values[index], values[best] = values[best], values[index]
            index = best

    @staticmethod
    def heapify(values: Sequence[Any], *, max_heap: bool = False) -> HeapState[Any]:
        """Build a heap bottom-up in O(n)."""
        state: HeapState[Any] = HeapState(list(values), max_heap)
        for index in range(len(state.values) // 2 - 1, -1, -1):
            HeapAlgorithms._sift_down(state.values, index, max_heap)
        return state

    @staticmethod
    def top_k(values: Sequence[Any], k: int, *, largest: bool = True) -> list[Any]:
        """The ``k`` largest (or smallest) values, best first, using a heap of size ``k``."""
        if k < 0:
            raise InvalidInputError("k must be non-negative")
        if k == 0:
            return []
        kept: HeapState[Any] = HeapState(max_heap=not largest)
        for value in values:
            if len(kept.values) < k:
                HeapAlgorithms.push(kept, value)
            elif HeapAlgorithms._before(value, kept.values[0], largest):
                HeapAlgorithms.pop(kept)
                HeapAlgorithms.push(kept, value)
        return sorted(kept.values, reverse=largest)

    @staticmethod
    def merge_sorted(lists: Sequence[Sequence[Any]]) -> list[Any]:
        """k-way merge of individually sorted lists in O(N log k)."""
        for index, items in enumerate(lists):
            if any(items[i] > items[i + 1] for i in range(len(items) - 1)):
                raise AlgorithmPreconditionError(f"list {index} is not sorted")
        frontier: HeapState[tuple[Any, int, int]] = HeapState()
        for index, items in enumerate(lists):
            if items:
                HeapAlgorithms.push(frontier, (items[0], index, 0))
        merged: list[Any] = []
        while frontier.values:
            value, index, position = HeapAlgorithms.pop(frontier)
            merged.append(value)
            if position + 1 < len(lists[index]):
                HeapAlgorithms.push(frontier, (lists[index][position + 1], index, position + 1))
        return merged
