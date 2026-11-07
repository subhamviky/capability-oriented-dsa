"""Structural invariant validators.

All validators are iterative, so arbitrarily deep structures cannot exhaust the
Python recursion limit.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any, Protocol, TypeVar

from ..core.errors import InvariantViolationError
from ..core.results import ValidationReport
from ..core.utilities import KeyResolver
from ..structures.states import (
    BSTState,
    GraphState,
    LinkedListState,
    QueueState,
    SequenceState,
    StackState,
    TreeState,
    TrieNode,
    TrieState,
)

S_contra = TypeVar("S_contra", contravariant=True)


class Validator(Protocol[S_contra]):
    def validate(self, state: S_contra, *, raise_on_error: bool = False) -> ValidationReport: ...


def _finish_validation(violations: list[str], raise_on_error: bool) -> ValidationReport:
    report = ValidationReport(not violations, violations)
    if violations and raise_on_error:
        raise InvariantViolationError("; ".join(violations))
    return report


class SequenceValidator:
    def validate(self, state: SequenceState[Any], *, raise_on_error: bool = False) -> ValidationReport:
        violations: list[str] = [] if isinstance(state.values, list) else ["values must be a list"]
        return _finish_validation(violations, raise_on_error)


class ContainerValidator:
    """Stack and queue: bounded size when a capacity is set."""

    def validate(
        self, state: StackState[Any] | QueueState[Any], *, raise_on_error: bool = False
    ) -> ValidationReport:
        v: list[str] = []
        if state.capacity < -1:
            v.append("capacity must be -1 (unbounded) or >= 0")
        if state.capacity >= 0 and len(state.values) > state.capacity:
            v.append(f"size {len(state.values)} exceeds capacity {state.capacity}")
        return _finish_validation(v, raise_on_error)


class LinkedListValidator:
    def validate(self, state: LinkedListState[Any], *, raise_on_error: bool = False) -> ValidationReport:
        v: list[str] = []
        if state.size != len(state.nodes):
            v.append("size does not match node count")
        if not state.nodes and (state.head_id is not None or state.tail_id is not None):
            v.append("empty list must have no head or tail")
        if state.nodes and (state.head_id not in state.nodes or state.tail_id not in state.nodes):
            v.append("non-empty list requires valid head and tail")
        for node_id, node in state.nodes.items():
            if node.node_id != node_id:
                v.append(f"node key {node_id!r} does not match node_id {node.node_id!r}")
        visited: set[str] = set()
        current = state.head_id
        previous: str | None = None
        while current is not None:
            if current in visited:
                v.append("cycle detected in ordinary linked list")
                break
            if current not in state.nodes:
                v.append(f"missing node reference: {current}")
                break
            visited.add(current)
            node = state.nodes[current]
            if node.previous_id != previous:
                v.append(f"previous link mismatch at {current}")
            previous, current = current, node.next_id
        else:
            if previous != state.tail_id:
                v.append(f"tail_id {state.tail_id!r} is not the last reachable node {previous!r}")
        if len(visited) != len(state.nodes):
            v.append("not all nodes are reachable from head")
        return _finish_validation(v, raise_on_error)


class TreeValidator:
    def validate(self, state: TreeState[Any], *, raise_on_error: bool = False) -> ValidationReport:
        v: list[str] = []
        if not state.values:
            if state.root_id is not None:
                v.append("empty tree must have no root")
            return _finish_validation(v, raise_on_error)
        if state.root_id not in state.values:
            v.append("root is missing")
            return _finish_validation(v, raise_on_error)
        if state.parent.get(state.root_id) is not None:
            v.append("root parent must be None")
        for orphan in sorted(set(state.parent) - set(state.values)):
            v.append(f"parent entry for unknown node: {orphan}")
        for orphan in sorted(set(state.children) - set(state.values)):
            v.append(f"children entry for unknown node: {orphan}")
        visited: set[str] = set()
        active: set[str] = set()
        stack: list[tuple[str, bool]] = [(state.root_id, False)]
        while stack:
            node, exiting = stack.pop()
            if exiting:
                active.discard(node)
                continue
            if node in active:
                v.append("cycle detected")
                continue
            if node in visited:
                v.append(f"node has multiple incoming paths: {node}")
                continue
            active.add(node)
            visited.add(node)
            stack.append((node, True))
            for child in reversed(state.children.get(node, [])):
                if child not in state.values:
                    v.append(f"missing child: {child}")
                    continue
                if state.parent.get(child) != node:
                    v.append(f"parent mismatch for {child}")
                stack.append((child, False))
        if visited != set(state.values):
            v.append("not all nodes are reachable from root")
        return _finish_validation(v, raise_on_error)


class BSTValidator:
    """Strict key ordering, parent links, reachability and stored heights."""

    def __init__(self, key: Callable[[Any], Any] | None = None) -> None:
        self.key = key

    def validate(self, state: BSTState[Any], *, raise_on_error: bool = False) -> ValidationReport:
        v: list[str] = []
        if state.root_id is None:
            if state.nodes:
                v.append("nodes exist but root is None")
            return _finish_validation(v, raise_on_error)
        if state.root_id not in state.nodes:
            return _finish_validation(["root is missing"], raise_on_error)
        if state.nodes[state.root_id].parent_id is not None:
            v.append("root parent must be None")
        visited: set[str] = set()
        heights: dict[str, int] = {}
        previous_value: Any = None
        has_previous = False
        # Iterative in-order walk checks strict ordering; post-order height check below.
        stack: list[str] = []
        current: str | None = state.root_id
        while stack or current is not None:
            while current is not None:
                if current in visited:
                    return _finish_validation(v + [f"cycle at {current}"], raise_on_error)
                if current not in state.nodes:
                    return _finish_validation(v + [f"missing node: {current}"], raise_on_error)
                visited.add(current)
                node = state.nodes[current]
                for child in (node.left_id, node.right_id):
                    if child is not None and child in state.nodes and state.nodes[child].parent_id != current:
                        v.append(f"parent mismatch for {child}")
                stack.append(current)
                current = node.left_id
            node = state.nodes[stack.pop()]
            node_key = KeyResolver.resolve(node.value, key_function=self.key)
            if has_previous and not previous_value < node_key:
                v.append(f"ordering violated at {node.node_id}")
            previous_value, has_previous = node_key, True
            current = node.right_id
        if visited != set(state.nodes):
            v.append("not all nodes are reachable from root")
        post: list[tuple[str, bool]] = [(state.root_id, False)]
        while post:
            node_id, expanded = post.pop()
            node = state.nodes[node_id]
            if not expanded:
                post.append((node_id, True))
                post.extend((c, False) for c in (node.left_id, node.right_id) if c is not None)
                continue
            left_h = heights[node.left_id] if node.left_id is not None else 0
            right_h = heights[node.right_id] if node.right_id is not None else 0
            actual = 1 + max(left_h, right_h)
            heights[node_id] = actual
            if node.height != actual:
                v.append(f"stored height {node.height} != actual {actual} at {node_id}")
        return _finish_validation(v, raise_on_error)


class TrieValidator:
    def validate(self, state: TrieState, *, raise_on_error: bool = False) -> ValidationReport:
        v: list[str] = []
        terminals = 0
        stack: list[TrieNode] = [state.root]
        seen: set[int] = set()
        while stack:
            node = stack.pop()
            if id(node) in seen:
                v.append("trie node shared between paths")
                break
            seen.add(id(node))
            terminals += node.terminal
            for char, child in node.children.items():
                if len(char) != 1:
                    v.append(f"edge label must be one character, got {char!r}")
                stack.append(child)
        if terminals != state.word_count:
            v.append(f"word_count {state.word_count} != terminal nodes {terminals}")
        return _finish_validation(v, raise_on_error)


class GraphValidator:
    def validate(self, state: GraphState[Any], *, raise_on_error: bool = False) -> ValidationReport:
        v: list[str] = []
        for source, targets in state.adjacency.items():
            if source not in state.values:
                v.append(f"adjacency source missing: {source}")
            for target, weight in targets.items():
                if target not in state.values:
                    v.append(f"edge target missing: {target}")
                if isinstance(weight, bool) or not isinstance(weight, (int, float)) or math.isnan(weight):
                    v.append(f"edge weight is not a number: {source}->{target}")
                if (
                    not state.directed
                    and source <= target
                    and state.adjacency.get(target, {}).get(source) != weight
                ):
                    v.append(f"undirected reverse edge mismatch: {source}<->{target}")
                if not state.directed and source > target and source not in state.adjacency.get(target, {}):
                    v.append(f"undirected reverse edge mismatch: {target}<->{source}")
        return _finish_validation(v, raise_on_error)


def validator_for(structure_type: str, key: Callable[[Any], Any] | None = None) -> Any:
    """Validator for a structure; BST ordering honours the caller's key function."""
    if structure_type == "BST":
        return BSTValidator(key)
    return VALIDATORS.get(structure_type)


VALIDATORS: dict[str, Any] = {
    "SEQUENCE": SequenceValidator(),
    "LINKED_LIST": LinkedListValidator(),
    "STACK": ContainerValidator(),
    "QUEUE": ContainerValidator(),
    "TREE": TreeValidator(),
    "BST": BSTValidator(),
    "TRIE": TrieValidator(),
    "GRAPH": GraphValidator(),
}
