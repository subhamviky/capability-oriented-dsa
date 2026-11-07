"""General (n-ary) tree kernels. All iterative."""

from __future__ import annotations

from typing import Any

from ..core.errors import InvariantViolationError, NotFoundError
from ..structures.states import TreeState
from ..validation.validators import TreeValidator


class TreeAlgorithms:
    @staticmethod
    def height(state: TreeState[Any], node_id: str | None = None) -> int:
        """Height measured in **nodes** (empty tree = 0, single node = 1)."""
        start = state.root_id if node_id is None else node_id
        if start is None:
            return 0
        if start not in state.values:
            raise NotFoundError(f"unknown node: {start}")
        best = 0
        stack: list[tuple[str, int]] = [(start, 1)]
        seen: set[str] = set()
        while stack:
            node, depth = stack.pop()
            if node in seen:
                raise InvariantViolationError(f"cycle or shared child at {node}")
            seen.add(node)
            best = max(best, depth)
            stack.extend((child, depth + 1) for child in state.children.get(node, []))
        return best

    @staticmethod
    def ancestors(state: TreeState[Any], node_id: str) -> list[str]:
        """Root-first list of ancestors (excluding ``node_id``)."""
        if node_id not in state.values:
            raise NotFoundError(f"unknown node: {node_id}")
        result: list[str] = []
        seen = {node_id}
        current = state.parent.get(node_id)
        while current is not None:
            if current in seen:
                raise InvariantViolationError(f"cycle in parent links at {current}")
            seen.add(current)
            result.append(current)
            current = state.parent.get(current)
        result.reverse()
        return result

    @staticmethod
    def lowest_common_ancestor(state: TreeState[Any], left: str, right: str) -> str | None:
        left_path = TreeAlgorithms.ancestors(state, left) + [left]
        right_path = TreeAlgorithms.ancestors(state, right) + [right]
        lca = None
        for a, b in zip(left_path, right_path, strict=False):
            if a != b:
                break
            lca = a
        return lca

    @staticmethod
    def diameter(state: TreeState[Any]) -> int:
        """Longest path measured in **edges**. Validates the tree first."""
        if state.root_id is None:
            return 0
        TreeValidator().validate(state, raise_on_error=True)
        heights: dict[str, int] = {}
        best = 0
        stack: list[tuple[str, bool]] = [(state.root_id, False)]
        while stack:
            node, expanded = stack.pop()
            if not expanded:
                stack.append((node, True))
                stack.extend((child, False) for child in reversed(state.children.get(node, [])))
                continue
            first = second = 0
            for child in state.children.get(node, []):
                child_height = heights[child]
                if child_height > first:
                    first, second = child_height, first
                elif child_height > second:
                    second = child_height
            best = max(best, first + second)
            heights[node] = first + 1
        return best

    @staticmethod
    def subtree_ids(state: TreeState[Any], node_id: str) -> list[str]:
        """Post-order ids of ``node_id`` and all its descendants."""
        if node_id not in state.values:
            raise NotFoundError(f"unknown node: {node_id}")
        out: list[str] = []
        stack: list[tuple[str, bool]] = [(node_id, False)]
        while stack:
            node, expanded = stack.pop()
            if expanded:
                out.append(node)
                continue
            stack.append((node, True))
            stack.extend((child, False) for child in reversed(state.children.get(node, [])))
        return out
