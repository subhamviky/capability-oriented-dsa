"""Disjoint-set (union-find) kernels: union by size, optional path compression."""

from __future__ import annotations

from typing import Any

from ..core.errors import NotFoundError
from ..structures.states import UnionFindState


class UnionFindAlgorithms:
    @staticmethod
    def make_set(state: UnionFindState, element: Any) -> bool:
        """Add ``element`` as its own set. Returns False if it already exists."""
        if element in state.parent:
            return False
        state.parent[element] = element
        state.size[element] = 1
        state.components += 1
        return True

    @staticmethod
    def find(state: UnionFindState, element: Any, *, compress: bool = True) -> Any:
        """Root of ``element``'s set; iterative. ``compress=False`` leaves the state untouched."""
        if element not in state.parent:
            raise NotFoundError(f"unknown element: {element!r}")
        root = element
        while state.parent[root] != root:
            root = state.parent[root]
        if compress:
            while state.parent[element] != root:
                state.parent[element], element = root, state.parent[element]
        return root

    @staticmethod
    def union(state: UnionFindState, left: Any, right: Any) -> bool:
        """Merge two sets. Returns False if they were already one set."""
        a = UnionFindAlgorithms.find(state, left)
        b = UnionFindAlgorithms.find(state, right)
        if a == b:
            return False
        if state.size[a] < state.size[b]:
            a, b = b, a
        state.parent[b] = a
        state.size[a] += state.size.pop(b)
        state.components -= 1
        return True

    @staticmethod
    def connected(state: UnionFindState, left: Any, right: Any, *, compress: bool = True) -> bool:
        return bool(
            UnionFindAlgorithms.find(state, left, compress=compress)
            == UnionFindAlgorithms.find(state, right, compress=compress)
        )
