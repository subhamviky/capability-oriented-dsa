"""Linked-list kernels over explicit node maps."""

from __future__ import annotations

from typing import TypeVar

from ..structures.states import LinkedListState, LinkedNode
from ..validation.validators import LinkedListValidator

T = TypeVar("T")


class LinkedListAlgorithms:
    @staticmethod
    def reverse(state: LinkedListState[T]) -> LinkedListState[T]:
        """Reverse links in place. Corrupt input is rejected before any write."""
        LinkedListValidator().validate(state, raise_on_error=True)
        current = state.head_id
        while current is not None:
            node = state.nodes[current]
            node.next_id, node.previous_id = node.previous_id, node.next_id
            current = node.previous_id
        state.head_id, state.tail_id = state.tail_id, state.head_id
        return state

    @staticmethod
    def middle(state: LinkedListState[T]) -> LinkedNode[T] | None:
        """Slow/fast pointers. For even sizes returns the second middle node."""
        slow = fast = state.head_id
        while fast is not None and state.nodes[fast].next_id is not None:
            assert slow is not None
            slow = state.nodes[slow].next_id
            first = state.nodes[fast].next_id
            fast = state.nodes[first].next_id if first is not None else None
        return state.nodes[slow] if slow is not None else None

    @staticmethod
    def has_cycle(state: LinkedListState[T]) -> bool:
        """Floyd's tortoise and hare over ``next_id``; dangling ids end the walk."""

        def step(node_id: str | None) -> str | None:
            if node_id is None or node_id not in state.nodes:
                return None
            return state.nodes[node_id].next_id

        slow = fast = state.head_id
        while True:
            slow = step(slow)
            fast = step(step(fast))
            if fast is None or slow is None:
                return False
            if slow == fast:
                return True
