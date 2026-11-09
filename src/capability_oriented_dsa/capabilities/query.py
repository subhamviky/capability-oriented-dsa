"""QUERY capability: read-only structure-native operations and analyses."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..algorithms.bst import BSTAlgorithms
from ..algorithms.graphs import GraphAlgorithms
from ..algorithms.hashing import HashingAlgorithms
from ..algorithms.heaps import HeapAlgorithms
from ..algorithms.linked_list import LinkedListAlgorithms
from ..algorithms.search import SearchAlgorithms
from ..algorithms.sequences import QueueAlgorithms, SequenceAlgorithms, StackAlgorithms
from ..algorithms.trees import TreeAlgorithms
from ..algorithms.union_find import UnionFindAlgorithms
from ..algorithms.windows import WindowAlgorithms
from ..core.errors import AlgorithmPreconditionError
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

    # -- hashing patterns (sequence)
    @operation(
        describe("HAS_DUPLICATE", capability, "SEQUENCE", "O(n)", "O(n)", preconditions=("hashable values",))
    )
    def _has_duplicate(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        return HashingAlgorithms.has_duplicate(context.state.values)

    @operation(
        describe("FREQUENCY", capability, "SEQUENCE", "O(n)", "O(n)", preconditions=("hashable values",))
    )
    def _frequency(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> dict[Any, int]:
        return HashingAlgorithms.frequency(context.state.values)

    @operation(
        describe(
            "GROUP_ANAGRAMS",
            capability,
            "SEQUENCE",
            "O(n * L log L)",
            "O(n * L)",
            preconditions=("string values",),
        )
    )
    def _group_anagrams(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[list[str]]:
        return HashingAlgorithms.group_anagrams(context.state.values)

    @operation(
        describe(
            "LONGEST_CONSECUTIVE", capability, "SEQUENCE", "O(n)", "O(n)", preconditions=("integer values",)
        )
    )
    def _longest_consecutive(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        return HashingAlgorithms.longest_consecutive(context.state.values)

    @operation(
        describe(
            "SUBARRAY_SUM_COUNT", capability, "SEQUENCE", "O(n)", "O(n)", preconditions=("integer values",)
        ),
        requires=("target",),
    )
    def _subarray_sum_count(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        return HashingAlgorithms.subarray_sum_count(context.state.values, args["target"])

    @operation(
        describe("FIRST_UNIQUE", capability, "SEQUENCE", "O(n)", "O(n)", preconditions=("hashable values",))
    )
    def _first_unique(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int | None:
        index = HashingAlgorithms.first_unique(context.state.values)
        context.found = index is not None
        return index

    # -- two pointers and windows (sequence)
    @operation(
        describe(
            "PAIR_SUM_SORTED",
            capability,
            "SEQUENCE",
            "O(n)",
            "O(1)",
            preconditions=("sequence sorted ascending",),
        ),
        requires=("target",),
    )
    def _pair_sum_sorted(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        if not SearchAlgorithms.is_sorted(context.state.values):
            raise AlgorithmPreconditionError("PAIR_SUM_SORTED requires a sorted sequence")
        pair = WindowAlgorithms.pair_sum_sorted(context.state.values, args["target"])
        context.found = pair is not None
        return pair

    @operation(
        describe(
            "LONGEST_UNIQUE_WINDOW",
            capability,
            "SEQUENCE",
            "O(n)",
            "O(n)",
            preconditions=("hashable values",),
        )
    )
    def _longest_unique_window(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        return WindowAlgorithms.longest_unique_window(context.state.values)

    @operation(
        describe(
            "MIN_SUBARRAY_LENGTH",
            capability,
            "SEQUENCE",
            "O(n)",
            "O(1)",
            preconditions=("non-negative integers",),
        ),
        requires=("target",),
    )
    def _min_subarray_length(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        return WindowAlgorithms.min_subarray_length(context.state.values, args["target"])

    @operation(
        describe("MAX_AREA", capability, "SEQUENCE", "O(n)", "O(1)", preconditions=("non-negative heights",))
    )
    def _max_area(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        return WindowAlgorithms.max_area(context.state.values)

    # -- heap patterns (sequence) and the heap itself
    @operation(
        describe(
            "TOP_K",
            capability,
            "SEQUENCE",
            "O(n log k)",
            "O(k)",
            preconditions=("mutually comparable values",),
        ),
        requires=("k",),
    )
    def _top_k(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[Any]:
        return HeapAlgorithms.top_k(context.state.values, args["k"], largest=bool(args.get("largest", True)))

    @operation(
        describe(
            "MERGE_SORTED",
            capability,
            "SEQUENCE",
            "O(N log k)",
            "O(N)",
            preconditions=("each value is itself a sorted list",),
        )
    )
    def _merge_sorted(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[Any]:
        return HeapAlgorithms.merge_sorted(context.state.values)

    @operation(describe("PEEK", capability, "HEAP", "O(1)", "O(1)", returns_internal_reference=True))
    def _heap_peek(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        return HeapAlgorithms.peek(context.state)

    # -- union-find
    @operation(describe("FIND", capability, "UNION_FIND", "O(log n)", "O(1)"), requires=("element",))
    def _uf_find(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        return UnionFindAlgorithms.find(context.state, args["element"], compress=False)

    @operation(
        describe("CONNECTED", capability, "UNION_FIND", "O(log n)", "O(1)"), requires=("left", "right")
    )
    def _uf_connected(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        return UnionFindAlgorithms.connected(context.state, args["left"], args["right"], compress=False)

    @operation(describe("COMPONENT_COUNT", capability, "UNION_FIND", "O(1)", "O(1)"))
    def _uf_components(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        count: int = context.state.components
        return count
