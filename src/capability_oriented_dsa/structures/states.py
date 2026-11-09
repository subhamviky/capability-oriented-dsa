"""Explicit structure state contracts.

State is plain data. Behaviour lives in repositories (natural operations),
kernels (algorithms) and validators (invariants).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class StructureType(str, Enum):
    SEQUENCE = "SEQUENCE"
    LINKED_LIST = "LINKED_LIST"
    STACK = "STACK"
    QUEUE = "QUEUE"
    TREE = "TREE"
    BST = "BST"
    TRIE = "TRIE"
    GRAPH = "GRAPH"
    HEAP = "HEAP"
    UNION_FIND = "UNION_FIND"


class CapabilityName(str, Enum):
    SEARCH = "SEARCH"
    ORDERING = "ORDERING"
    TRAVERSAL = "TRAVERSAL"
    PATH = "PATH"
    QUERY = "QUERY"
    MUTATION = "MUTATION"
    VALIDATION = "VALIDATION"
    OPTIMIZATION = "OPTIMIZATION"
    ENUMERATION = "ENUMERATION"


@dataclass(slots=True)
class SequenceState(Generic[T]):
    values: list[T] = field(default_factory=list)


@dataclass(slots=True)
class LinkedNode(Generic[T]):
    node_id: str
    value: T
    next_id: str | None = None
    previous_id: str | None = None


@dataclass(slots=True)
class LinkedListState(Generic[T]):
    nodes: dict[str, LinkedNode[T]] = field(default_factory=dict)
    head_id: str | None = None
    tail_id: str | None = None
    size: int = 0


@dataclass(slots=True)
class StackState(Generic[T]):
    values: list[T] = field(default_factory=list)
    capacity: int = -1


@dataclass(slots=True)
class QueueState(Generic[T]):
    values: deque[T] = field(default_factory=deque)
    capacity: int = -1


@dataclass(slots=True)
class TreeState(Generic[T]):
    values: dict[str, T] = field(default_factory=dict)
    children: dict[str, list[str]] = field(default_factory=dict)
    parent: dict[str, str | None] = field(default_factory=dict)
    root_id: str | None = None


@dataclass(slots=True)
class BSTNode(Generic[T]):
    node_id: str
    value: T
    left_id: str | None = None
    right_id: str | None = None
    parent_id: str | None = None
    height: int = 1


@dataclass(slots=True)
class BSTState(Generic[T]):
    nodes: dict[str, BSTNode[T]] = field(default_factory=dict)
    root_id: str | None = None


@dataclass(slots=True)
class TrieNode:
    children: dict[str, TrieNode] = field(default_factory=dict)
    terminal: bool = False


@dataclass(slots=True)
class TrieState:
    root: TrieNode = field(default_factory=TrieNode)
    word_count: int = 0


@dataclass(slots=True)
class GraphState(Generic[T]):
    values: dict[str, T] = field(default_factory=dict)
    adjacency: dict[str, dict[str, float]] = field(default_factory=dict)
    directed: bool = False


@dataclass(slots=True)
class HeapState(Generic[T]):
    """Binary heap in array form. ``values[0]`` is the minimum (or maximum if ``max_heap``).

    Order is by the values themselves; to order by a priority, store
    ``(priority, item)`` tuples.
    """

    values: list[T] = field(default_factory=list)
    max_heap: bool = False


@dataclass(slots=True)
class UnionFindState:
    """Disjoint sets: ``parent`` links each element towards its root; ``size`` is kept for roots."""

    parent: dict[Any, Any] = field(default_factory=dict)
    size: dict[Any, int] = field(default_factory=dict)
    components: int = 0


#: The state contract each structure type must satisfy at the governed boundary.
STATE_TYPES: dict[str, type[Any]] = {
    StructureType.SEQUENCE.value: SequenceState,
    StructureType.LINKED_LIST.value: LinkedListState,
    StructureType.STACK.value: StackState,
    StructureType.QUEUE.value: QueueState,
    StructureType.TREE.value: TreeState,
    StructureType.BST.value: BSTState,
    StructureType.TRIE.value: TrieState,
    StructureType.GRAPH.value: GraphState,
    StructureType.HEAP.value: HeapState,
    StructureType.UNION_FIND.value: UnionFindState,
}


def normalise_name(value: str | Enum) -> str:
    """Accept enum members or strings in any case."""
    return (value.value if isinstance(value, Enum) else str(value)).upper()
