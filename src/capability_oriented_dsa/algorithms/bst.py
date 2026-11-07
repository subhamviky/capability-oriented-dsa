"""Binary search tree kernels with optional AVL balancing.

Heights are maintained by *every* mutating kernel (plain and AVL), so
``is_avl_balanced`` and ``BSTValidator`` stay meaningful regardless of which
insert/delete variant built the tree.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, TypeVar

from ..core.errors import DuplicateKeyError, InvalidInputError, NotFoundError
from ..core.utilities import KeyResolver
from ..structures.states import BSTNode, BSTState

T = TypeVar("T")

DUPLICATE_POLICIES = frozenset({"reject", "ignore", "replace"})


class BSTAlgorithms:
    # ----------------------------------------------------------------- reads
    @staticmethod
    def search(
        state: BSTState[T], target: Any, *, key: Callable[[T], Any] | None = None
    ) -> BSTNode[T] | None:
        current = state.root_id
        while current is not None:
            node = state.nodes[current]
            value = KeyResolver.resolve(node.value, key_function=key)
            if value == target:
                return node
            current = node.left_id if target < value else node.right_id
        return None

    @staticmethod
    def inorder(state: BSTState[T]) -> list[T]:
        """Iterative in-order values (sorted by key)."""
        result: list[T] = []
        stack: list[str] = []
        current = state.root_id
        while stack or current is not None:
            while current is not None:
                stack.append(current)
                current = state.nodes[current].left_id
            node = state.nodes[stack.pop()]
            result.append(node.value)
            current = node.right_id
        return result

    @staticmethod
    def is_avl_balanced(state: BSTState[T]) -> bool:
        """Stored heights are correct and every balance factor is within [-1, 1]."""
        if state.root_id is None:
            return True
        calculated: dict[str, int] = {}
        stack: list[tuple[str, bool]] = [(state.root_id, False)]
        while stack:
            node_id, expanded = stack.pop()
            node = state.nodes[node_id]
            if not expanded:
                stack.append((node_id, True))
                if node.right_id is not None:
                    stack.append((node.right_id, False))
                if node.left_id is not None:
                    stack.append((node.left_id, False))
                continue
            left_h = calculated[node.left_id] if node.left_id is not None else 0
            right_h = calculated[node.right_id] if node.right_id is not None else 0
            actual = 1 + max(left_h, right_h)
            if abs(left_h - right_h) > 1 or node.height != actual:
                return False
            calculated[node_id] = actual
        return True

    # ------------------------------------------------------------- mutations
    @staticmethod
    def insert(
        state: BSTState[T],
        value: T,
        *,
        key: Callable[[T], Any] | None = None,
        node_id: str | None = None,
        on_duplicate: str = "reject",
    ) -> str:
        """Unbalanced insert. Returns the id of the inserted (or existing) node."""
        if on_duplicate not in DUPLICATE_POLICIES:
            raise InvalidInputError(f"on_duplicate must be one of {sorted(DUPLICATE_POLICIES)}")
        new_id = node_id if node_id is not None else str(uuid.uuid4())
        if new_id in state.nodes:
            raise DuplicateKeyError(f"duplicate node id: {new_id}")
        new_key = KeyResolver.resolve(value, key_function=key)
        if state.root_id is None:
            state.nodes[new_id] = BSTNode(new_id, value)
            state.root_id = new_id
            return new_id
        current = state.root_id
        while True:
            node = state.nodes[current]
            node_key = KeyResolver.resolve(node.value, key_function=key)
            if new_key == node_key:
                if on_duplicate == "reject":
                    raise DuplicateKeyError(f"duplicate BST key: {new_key}")
                if on_duplicate == "replace":
                    node.value = value
                return current
            side = "left_id" if new_key < node_key else "right_id"
            child = getattr(node, side)
            if child is None:
                state.nodes[new_id] = BSTNode(new_id, value, parent_id=current)
                setattr(node, side, new_id)
                BSTAlgorithms._refresh_path(state, current)
                return new_id
            current = child

    @staticmethod
    def insert_avl(
        state: BSTState[T],
        value: T,
        *,
        key: Callable[[T], Any] | None = None,
        node_id: str | None = None,
        on_duplicate: str = "reject",
    ) -> str:
        """Insert, then restore the AVL property with rotations."""
        size_before = len(state.nodes)
        inserted_id = BSTAlgorithms.insert(state, value, key=key, node_id=node_id, on_duplicate=on_duplicate)
        if len(state.nodes) > size_before:
            BSTAlgorithms._rebalance_from(state, state.nodes[inserted_id].parent_id)
        return inserted_id

    @staticmethod
    def delete(
        state: BSTState[T], target: Any, *, key: Callable[[T], Any] | None = None, rebalance: bool = False
    ) -> BSTNode[T]:
        """Remove the node whose key equals ``target`` by relinking (node ids are stable).

        Returns the detached node. With ``rebalance=True`` the AVL property is
        restored on the way back to the root.
        """
        z = BSTAlgorithms.search(state, target, key=key)
        if z is None:
            raise NotFoundError(f"BST key not found: {target!r}")
        nodes = state.nodes
        start: str | None
        if z.left_id is None:
            start = z.parent_id
            BSTAlgorithms._transplant(state, z.node_id, z.right_id)
        elif z.right_id is None:
            start = z.parent_id
            BSTAlgorithms._transplant(state, z.node_id, z.left_id)
        else:
            y_id = z.right_id
            while nodes[y_id].left_id is not None:
                y_id = nodes[y_id].left_id  # type: ignore[assignment]
            y = nodes[y_id]
            if y.parent_id != z.node_id:
                start = y.parent_id
                BSTAlgorithms._transplant(state, y_id, y.right_id)
                y.right_id = z.right_id
                nodes[y.right_id].parent_id = y_id
            else:
                start = y_id
            BSTAlgorithms._transplant(state, z.node_id, y_id)
            y.left_id = z.left_id
            nodes[y.left_id].parent_id = y_id
        del nodes[z.node_id]
        z.left_id = z.right_id = z.parent_id = None
        z.height = 1
        if rebalance:
            BSTAlgorithms._rebalance_from(state, start)
        else:
            BSTAlgorithms._refresh_path(state, start)
        return z

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _height(state: BSTState[T], node_id: str | None) -> int:
        return 0 if node_id is None else state.nodes[node_id].height

    @staticmethod
    def _refresh_height(state: BSTState[T], node_id: str) -> None:
        node = state.nodes[node_id]
        node.height = 1 + max(
            BSTAlgorithms._height(state, node.left_id), BSTAlgorithms._height(state, node.right_id)
        )

    @staticmethod
    def _refresh_path(state: BSTState[T], node_id: str | None) -> None:
        current = node_id
        while current is not None:
            BSTAlgorithms._refresh_height(state, current)
            current = state.nodes[current].parent_id

    @staticmethod
    def _transplant(state: BSTState[T], old_id: str, new_id: str | None) -> None:
        """Replace the subtree rooted at ``old_id`` with the one at ``new_id``."""
        parent_id = state.nodes[old_id].parent_id
        if parent_id is None:
            state.root_id = new_id
        elif state.nodes[parent_id].left_id == old_id:
            state.nodes[parent_id].left_id = new_id
        else:
            state.nodes[parent_id].right_id = new_id
        if new_id is not None:
            state.nodes[new_id].parent_id = parent_id

    @staticmethod
    def _rotate_left(state: BSTState[T], root_id: str) -> str:
        root = state.nodes[root_id]
        pivot_id = root.right_id
        if pivot_id is None:
            return root_id
        pivot = state.nodes[pivot_id]
        moved_id = pivot.left_id
        BSTAlgorithms._transplant(state, root_id, pivot_id)
        pivot.left_id = root_id
        root.parent_id = pivot_id
        root.right_id = moved_id
        if moved_id is not None:
            state.nodes[moved_id].parent_id = root_id
        BSTAlgorithms._refresh_height(state, root_id)
        BSTAlgorithms._refresh_height(state, pivot_id)
        return pivot_id

    @staticmethod
    def _rotate_right(state: BSTState[T], root_id: str) -> str:
        root = state.nodes[root_id]
        pivot_id = root.left_id
        if pivot_id is None:
            return root_id
        pivot = state.nodes[pivot_id]
        moved_id = pivot.right_id
        BSTAlgorithms._transplant(state, root_id, pivot_id)
        pivot.right_id = root_id
        root.parent_id = pivot_id
        root.left_id = moved_id
        if moved_id is not None:
            state.nodes[moved_id].parent_id = root_id
        BSTAlgorithms._refresh_height(state, root_id)
        BSTAlgorithms._refresh_height(state, pivot_id)
        return pivot_id

    @staticmethod
    def _rebalance_from(state: BSTState[T], node_id: str | None) -> None:
        """Walk to the root refreshing heights and rotating where |balance| > 1.

        Covers insertion and deletion (a child with balance 0 selects the
        single rotation, which is the correct deletion case).
        """
        current = node_id
        while current is not None:
            BSTAlgorithms._refresh_height(state, current)
            node = state.nodes[current]
            balance = BSTAlgorithms._height(state, node.left_id) - BSTAlgorithms._height(state, node.right_id)
            if balance > 1 and node.left_id is not None:
                left = state.nodes[node.left_id]
                if BSTAlgorithms._height(state, left.left_id) < BSTAlgorithms._height(state, left.right_id):
                    BSTAlgorithms._rotate_left(state, node.left_id)
                current = state.nodes[BSTAlgorithms._rotate_right(state, current)].parent_id
            elif balance < -1 and node.right_id is not None:
                right = state.nodes[node.right_id]
                if BSTAlgorithms._height(state, right.right_id) < BSTAlgorithms._height(state, right.left_id):
                    BSTAlgorithms._rotate_right(state, node.right_id)
                current = state.nodes[BSTAlgorithms._rotate_left(state, current)].parent_id
            else:
                current = node.parent_id
