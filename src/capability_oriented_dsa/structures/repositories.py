"""Natural structure operations.

Contract: every method validates its inputs *before* its first write, so a
raised exception leaves the state untouched (atomic). Missing keys raise
``NotFoundError``; duplicate identifiers raise ``DuplicateKeyError`` unless an
``on_duplicate`` policy says otherwise.
"""

from __future__ import annotations

import math
import uuid
from typing import TypeVar

from ..core.errors import DuplicateKeyError, InvalidInputError, NotFoundError
from ..core.utilities import CapacityUtility
from .states import GraphState, LinkedListState, LinkedNode, QueueState, SequenceState, StackState, TreeState

T = TypeVar("T")


def _check_duplicate_policy(on_duplicate: str) -> None:
    if on_duplicate not in {"reject", "ignore", "replace"}:
        raise InvalidInputError("on_duplicate must be one of ['ignore', 'reject', 'replace']")


class SequenceRepository:
    def create(self, state: SequenceState[T], value: T, index: int | None = None) -> SequenceState[T]:
        if index is None:
            state.values.append(value)
        else:
            state.values.insert(index, value)
        return state

    def read(self, state: SequenceState[T], index: int) -> T:
        self._require_index(state, index)
        return state.values[index]

    def update(self, state: SequenceState[T], index: int, value: T) -> SequenceState[T]:
        self._require_index(state, index)
        state.values[index] = value
        return state

    def delete(self, state: SequenceState[T], index: int) -> T:
        self._require_index(state, index)
        return state.values.pop(index)

    @staticmethod
    def _require_index(state: SequenceState[T], index: int) -> None:
        if not -len(state.values) <= index < len(state.values):
            raise NotFoundError(f"index out of range: {index}")


class LinkedListRepository:
    def append(self, state: LinkedListState[T], value: T, node_id: str | None = None) -> str:
        node_id = self._new_id(state, node_id)
        state.nodes[node_id] = LinkedNode(node_id, value, previous_id=state.tail_id)
        if state.tail_id is not None:
            state.nodes[state.tail_id].next_id = node_id
        else:
            state.head_id = node_id
        state.tail_id = node_id
        state.size += 1
        return node_id

    def prepend(self, state: LinkedListState[T], value: T, node_id: str | None = None) -> str:
        node_id = self._new_id(state, node_id)
        state.nodes[node_id] = LinkedNode(node_id, value, next_id=state.head_id)
        if state.head_id is not None:
            state.nodes[state.head_id].previous_id = node_id
        else:
            state.tail_id = node_id
        state.head_id = node_id
        state.size += 1
        return node_id

    def delete(self, state: LinkedListState[T], node_id: str) -> LinkedNode[T]:
        if node_id not in state.nodes:
            raise NotFoundError(f"unknown node: {node_id}")
        node = state.nodes[node_id]
        if node.previous_id is not None:
            state.nodes[node.previous_id].next_id = node.next_id
        else:
            state.head_id = node.next_id
        if node.next_id is not None:
            state.nodes[node.next_id].previous_id = node.previous_id
        else:
            state.tail_id = node.previous_id
        del state.nodes[node_id]
        state.size -= 1
        node.next_id = node.previous_id = None
        return node

    @staticmethod
    def _new_id(state: LinkedListState[T], node_id: str | None) -> str:
        new_id = node_id if node_id is not None else str(uuid.uuid4())
        if new_id in state.nodes:
            raise DuplicateKeyError(f"duplicate node id: {new_id}")
        return new_id


class StackRepository:
    def push(self, state: StackState[T], value: T, *, capacity: int | None = None) -> None:
        bound = state.capacity if capacity is None or state.capacity >= 0 else capacity
        CapacityUtility.require_space(len(state.values), bound)
        state.values.append(value)

    def pop(self, state: StackState[T]) -> T:
        CapacityUtility.require_not_empty(len(state.values))
        return state.values.pop()

    def peek(self, state: StackState[T]) -> T:
        CapacityUtility.require_not_empty(len(state.values))
        return state.values[-1]


class QueueRepository:
    def enqueue(self, state: QueueState[T], value: T, *, capacity: int | None = None) -> None:
        bound = state.capacity if capacity is None or state.capacity >= 0 else capacity
        CapacityUtility.require_space(len(state.values), bound)
        state.values.append(value)

    def dequeue(self, state: QueueState[T]) -> T:
        CapacityUtility.require_not_empty(len(state.values))
        return state.values.popleft()

    def peek(self, state: QueueState[T]) -> T:
        CapacityUtility.require_not_empty(len(state.values))
        return state.values[0]


class TreeRepository:
    def add_root(self, state: TreeState[T], node_id: str, value: T) -> None:
        if state.root_id is not None or state.values:
            raise InvalidInputError("tree already has a root")
        state.values[node_id] = value
        state.children[node_id] = []
        state.parent[node_id] = None
        state.root_id = node_id

    def add_child(
        self, state: TreeState[T], parent_id: str, node_id: str, value: T, *, on_duplicate: str = "reject"
    ) -> bool:
        """Attach a new leaf. Returns False when an existing node was ignored/replaced."""
        _check_duplicate_policy(on_duplicate)
        if parent_id not in state.values:
            raise NotFoundError(f"unknown parent: {parent_id}")
        if node_id in state.values:
            if on_duplicate == "reject":
                raise DuplicateKeyError(f"duplicate node: {node_id}")
            if on_duplicate == "replace":
                state.values[node_id] = value
            return False
        state.values[node_id] = value
        state.children[node_id] = []
        state.parent[node_id] = parent_id
        state.children.setdefault(parent_id, []).append(node_id)
        return True

    def delete_subtree(self, state: TreeState[T], node_id: str) -> list[str]:
        """Remove ``node_id`` and its descendants iteratively. Returns post-order ids."""
        if node_id not in state.values:
            raise NotFoundError(f"unknown node: {node_id}")
        removed: list[str] = []
        stack: list[tuple[str, bool]] = [(node_id, False)]
        while stack:
            current, expanded = stack.pop()
            if expanded:
                removed.append(current)
                continue
            stack.append((current, True))
            stack.extend((child, False) for child in reversed(state.children.get(current, [])))
        parent = state.parent.get(node_id)
        if parent is not None:
            state.children[parent].remove(node_id)
        for current in removed:
            state.children.pop(current, None)
            state.parent.pop(current, None)
            state.values.pop(current, None)
        if state.root_id == node_id:
            state.root_id = None
        return removed


class GraphRepository:
    def add_vertex(
        self, state: GraphState[T], vertex_id: str, value: T, *, on_duplicate: str = "reject"
    ) -> bool:
        _check_duplicate_policy(on_duplicate)
        if vertex_id in state.values:
            if on_duplicate == "reject":
                raise DuplicateKeyError(f"duplicate vertex: {vertex_id}")
            if on_duplicate == "replace":
                state.values[vertex_id] = value
            return False
        state.values[vertex_id] = value
        state.adjacency[vertex_id] = {}
        return True

    def add_edge(self, state: GraphState[T], source: str, target: str, weight: float = 1.0) -> None:
        missing = [v for v in (source, target) if v not in state.values]
        if missing:
            raise NotFoundError(f"unknown vertices: {missing}")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or math.isnan(weight):
            raise InvalidInputError(f"edge weight must be a number, got {weight!r}")
        state.adjacency.setdefault(source, {})[target] = weight
        if not state.directed:
            state.adjacency.setdefault(target, {})[source] = weight

    def remove_edge(self, state: GraphState[T], source: str, target: str) -> None:
        if target not in state.adjacency.get(source, {}):
            raise NotFoundError(f"unknown edge: {source}->{target}")
        del state.adjacency[source][target]
        if not state.directed:
            state.adjacency.get(target, {}).pop(source, None)

    def remove_vertex(self, state: GraphState[T], vertex_id: str) -> None:
        if vertex_id not in state.values:
            raise NotFoundError(f"unknown vertex: {vertex_id}")
        del state.values[vertex_id]
        state.adjacency.pop(vertex_id, None)
        for targets in state.adjacency.values():
            targets.pop(vertex_id, None)
