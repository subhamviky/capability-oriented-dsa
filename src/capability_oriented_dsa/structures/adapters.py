"""Structure-neutral navigation port and its adapters."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, TypeVar, runtime_checkable

from ..core.errors import ConfigurationError
from .states import GraphState, TreeState

K = TypeVar("K")


@runtime_checkable
class NavigableAdapter(Protocol[K]):
    def contains(self, node: K) -> bool: ...
    def start_nodes(self) -> Iterable[K]: ...
    def neighbours(self, node: K) -> Iterable[K]: ...


class TreeAdapter:
    def __init__(self, state: TreeState[Any]) -> None:
        self.state = state

    def contains(self, node: str) -> bool:
        return node in self.state.values

    def start_nodes(self) -> Iterable[str]:
        return [] if self.state.root_id is None else [self.state.root_id]

    def neighbours(self, node: str) -> Iterable[str]:
        return self.state.children.get(node, [])


class GraphAdapter:
    def __init__(self, state: GraphState[Any]) -> None:
        self.state = state

    def contains(self, node: str) -> bool:
        return node in self.state.values

    def start_nodes(self) -> Iterable[str]:
        return self.state.values.keys()

    def neighbours(self, node: str) -> Iterable[str]:
        return self.state.adjacency.get(node, {}).keys()

    def edge_weight(self, source: str, target: str) -> float:
        return self.state.adjacency[source][target]


class OrderedAdapter:
    """Decorates any NavigableAdapter with a deterministic neighbour order."""

    ORDERS = frozenset({"natural", "sorted", "reversed"})

    def __init__(self, inner: NavigableAdapter[Any], order: str = "natural") -> None:
        if order not in self.ORDERS:
            raise ConfigurationError(f"neighbour_order must be one of {sorted(self.ORDERS)}")
        self.inner = inner
        self.order = order

    def contains(self, node: Any) -> bool:
        return self.inner.contains(node)

    def start_nodes(self) -> Iterable[Any]:
        return self.inner.start_nodes()

    def neighbours(self, node: Any) -> Iterable[Any]:
        items = self.inner.neighbours(node)
        if self.order == "sorted":
            return sorted(items)
        if self.order == "reversed":
            return list(items)[::-1]
        return items
