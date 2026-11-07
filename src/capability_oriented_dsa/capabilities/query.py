"""QUERY capability: read-only structure-native operations and analyses."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..algorithms.bst import BSTAlgorithms
from ..algorithms.graphs import GraphAlgorithms
from ..algorithms.linked_list import LinkedListAlgorithms
from ..algorithms.sequences import QueueAlgorithms, SequenceAlgorithms, StackAlgorithms
from ..algorithms.trees import TreeAlgorithms
from ..core.metadata import describe
from ..core.results import DSAExecutionContext
from ..structures.repositories import QueueRepository, SequenceRepository, StackRepository
from .base import BaseDSACapability, operation


class QueryService(BaseDSACapability):
    capability = "QUERY"

    # -- sequence
    @operation(
        describe("READ", capability, "SEQUENCE", "O(1)", "O(1)", returns_internal_reference=True),
        requires=("index",),
    )
    def _read(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        return SequenceRepository().read(context.state, args["index"])

    @operation(describe("TWO_SUM", capability, "SEQUENCE", "O(n)", "O(n)"), requires=("target",))
    def _two_sum(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        pair = SequenceAlgorithms.two_sum(context.state.values, args["target"])
        context.found = pair is not None
        return pair

    @operation(describe("MAXIMUM_SUBARRAY", capability, "SEQUENCE", "O(n)", "O(1)"))
    def _maximum_subarray(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        return SequenceAlgorithms.maximum_subarray(context.state.values)

    @operation(describe("PREFIX_SUMS", capability, "SEQUENCE", "O(n)", "O(n)"))
    def _prefix_sums(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[int]:
        return SequenceAlgorithms.prefix_sums(context.state.values)

    @operation(describe("NEXT_GREATER", capability, "SEQUENCE", "O(n)", "O(n)"))
    def _next_greater(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[int]:
        return StackAlgorithms.next_greater(context.state.values)

    @operation(
        describe("SLIDING_WINDOW_MAXIMUM", capability, "SEQUENCE", "O(n)", "O(k)"), requires=("window",)
    )
    def _sliding_window_maximum(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[int]:
        return QueueAlgorithms.sliding_window_maximum(context.state.values, args["window"])

    # -- containers
    @operation(describe("PEEK", capability, "STACK", "O(1)", "O(1)", returns_internal_reference=True))
    def _stack_peek(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        return StackRepository().peek(context.state)

    @operation(describe("PEEK", capability, "QUEUE", "O(1)", "O(1)", returns_internal_reference=True))
    def _queue_peek(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        return QueueRepository().peek(context.state)

    # -- linked list
    @operation(describe("MIDDLE", capability, "LINKED_LIST", "O(n)", "O(1)", returns_internal_reference=True))
    def _middle(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        node = LinkedListAlgorithms.middle(context.state)
        context.found = node is not None
        return node

    @operation(describe("HAS_CYCLE", capability, "LINKED_LIST", "O(n)", "O(1)"))
    def _list_has_cycle(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        return LinkedListAlgorithms.has_cycle(context.state)

    # -- tree
    @operation(
        describe(
            "HEIGHT", capability, "TREE", "O(n)", "O(n)", postconditions=("height in nodes; empty tree = 0",)
        )
    )
    def _height(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        return TreeAlgorithms.height(context.state, args.get("node_id"))

    @operation(
        describe("DIAMETER", capability, "TREE", "O(n)", "O(n)", postconditions=("longest path in edges",))
    )
    def _diameter(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        return TreeAlgorithms.diameter(context.state)

    @operation(describe("ANCESTORS", capability, "TREE", "O(depth)", "O(depth)"), requires=("node_id",))
    def _ancestors(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[str]:
        return TreeAlgorithms.ancestors(context.state, args["node_id"])

    @operation(
        describe("LOWEST_COMMON_ANCESTOR", capability, "TREE", "O(depth)", "O(depth)"),
        requires=("left", "right"),
    )
    def _lca(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> str | None:
        return TreeAlgorithms.lowest_common_ancestor(context.state, args["left"], args["right"])

    # -- BST
    @operation(describe("INORDER", capability, "BST", "O(n)", "O(h)"))
    def _inorder(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[Any]:
        return BSTAlgorithms.inorder(context.state)

    @operation(describe("IS_AVL_BALANCED", capability, "BST", "O(n)", "O(n)"))
    def _is_avl_balanced(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        return BSTAlgorithms.is_avl_balanced(context.state)

    # -- graph
    @operation(describe("HAS_CYCLE", capability, "GRAPH", "O(V+E)", "O(V)"))
    def _graph_has_cycle(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        return GraphAlgorithms.has_cycle(context.state)

    @operation(
        describe(
            "TOPOLOGICAL_SORT",
            capability,
            "GRAPH",
            "O(V+E)",
            "O(V)",
            preconditions=("directed acyclic graph",),
        )
    )
    def _topological_sort(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[str]:
        return GraphAlgorithms.topological_sort(context.state)
