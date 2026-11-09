"""Backtracking: depth-first search over a tree of partial decisions.

``explore`` is the one engine; every enumeration below only supplies how a
state expands and when it is a solution. It is iterative, so the number of
decisions is not limited by Python's recursion limit, and lazy, so callers can
stop after the first results. ``max_nodes`` bounds the total work.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import Any, TypeVar, cast

from ..core.errors import CapacityExceededError, InvalidInputError

S = TypeVar("S")
_start: tuple[int, tuple[Any, ...]] = (0, ())


class BacktrackingAlgorithms:
    @staticmethod
    def explore(
        root: S,
        children: Callable[[S], Iterable[S]],
        is_solution: Callable[[S], bool],
        *,
        max_nodes: int = -1,
    ) -> Iterator[S]:
        """Yield solution states in depth-first order, visiting at most ``max_nodes`` states."""
        visited = 1
        if is_solution(root):
            yield root
        stack: list[Iterator[S]] = [iter(children(root))]
        while stack:
            try:
                child = next(stack[-1])
            except StopIteration:
                stack.pop()
                continue
            visited += 1
            if 0 <= max_nodes < visited:
                raise CapacityExceededError(f"search visited more than {max_nodes} states")
            if is_solution(child):
                yield child
            stack.append(iter(children(child)))

    @staticmethod
    def subsets(values: Sequence[Any], *, max_nodes: int = -1) -> Iterator[tuple[Any, ...]]:
        """Every subset (positions are distinct, so equal values are not de-duplicated)."""
        count = len(values)
        for _, chosen in BacktrackingAlgorithms.explore(
            _start,
            lambda s: ((i + 1, (*s[1], values[i])) for i in range(s[0], count)),
            lambda s: True,
            max_nodes=max_nodes,
        ):
            yield chosen

    @staticmethod
    def permutations(values: Sequence[Any], *, max_nodes: int = -1) -> Iterator[tuple[Any, ...]]:
        count = len(values)
        for _, chosen in BacktrackingAlgorithms.explore(
            _start,
            lambda s: ((s[0] | (1 << i), (*s[1], values[i])) for i in range(count) if not s[0] >> i & 1),
            lambda s: len(s[1]) == count,
            max_nodes=max_nodes,
        ):
            yield chosen

    @staticmethod
    def combinations(values: Sequence[Any], k: int, *, max_nodes: int = -1) -> Iterator[tuple[Any, ...]]:
        """Every ``k``-element selection, in input order."""
        if k < 0:
            raise InvalidInputError("k must be non-negative")
        count = len(values)
        for _, chosen in BacktrackingAlgorithms.explore(
            _start,
            lambda s: (
                (i + 1, (*s[1], values[i]))
                for i in range(s[0], count - (k - len(s[1])) + 1 if len(s[1]) < k else 0)
            ),
            lambda s: len(s[1]) == k,
            max_nodes=max_nodes,
        ):
            yield chosen

    @staticmethod
    def combination_sum(
        candidates: Sequence[int], target: int, *, max_nodes: int = -1
    ) -> Iterator[tuple[int, ...]]:
        """Multisets of candidates (each reusable) summing to ``target``; candidates must be positive."""
        if any(c <= 0 for c in candidates):
            raise InvalidInputError("candidates must be positive")
        ordered = sorted(set(candidates))
        for _, chosen, _remaining in BacktrackingAlgorithms.explore(
            (0, cast(tuple[int, ...], ()), target),
            lambda s: (
                (i, (*s[1], ordered[i]), s[2] - ordered[i])
                for i in range(s[0], len(ordered))
                if ordered[i] <= s[2]
            ),
            lambda s: s[2] == 0 and bool(s[1]),
            max_nodes=max_nodes,
        ):
            yield chosen

    @staticmethod
    def n_queens(n: int, *, max_nodes: int = -1) -> Iterator[tuple[int, ...]]:
        """Placements as a tuple of column per row, with no two queens attacking."""
        if n < 1:
            raise InvalidInputError("n must be >= 1")

        def safe(placed: tuple[int, ...], column: int) -> bool:
            row = len(placed)
            return all(column != c and abs(column - c) != row - r for r, c in enumerate(placed))

        yield from BacktrackingAlgorithms.explore(
            cast(tuple[int, ...], ()),
            lambda s: ((*s, c) for c in range(n) if safe(s, c)),
            lambda s: len(s) == n,
            max_nodes=max_nodes,
        )
