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

    @staticmethod
    def add_all(state: UnionFindState, elements: Any) -> int:
        """Add every element as its own set; returns how many were new (v0.3, S-4)."""
        return sum(1 for e in elements if UnionFindAlgorithms.make_set(state, e))

    @staticmethod
    def group_by_keys(
        state: UnionFindState, elements: Any, keys: Any, element_id: Any = None
    ) -> list[list[Any]]:
        """Connect elements that share ANY key (keys(e) returns several), in O(n * k) with a
        key index instead of comparing every pair; return the groups, each in input order,
        ordered by their first element (v0.3, S-4)."""
        ident = element_id or (lambda e: e)
        items = list(elements)
        first_with: dict[Any, Any] = {}
        for e in items:
            eid = ident(e)
            UnionFindAlgorithms.make_set(state, eid)
            for key in keys(e):
                if key in first_with:
                    UnionFindAlgorithms.union(state, first_with[key], eid)
                else:
                    first_with[key] = eid
        groups: dict[Any, list[Any]] = {}
        for e in items:
            groups.setdefault(UnionFindAlgorithms.find(state, ident(e)), []).append(e)
        return list(groups.values())
