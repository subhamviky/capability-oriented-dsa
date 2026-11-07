"""Direct kernel behaviour, independent of the governed layer."""

from __future__ import annotations

import math
from types import ModuleType

import pytest

from .conftest import build_chain_tree, build_graph


class TestSearchAndSort:
    def test_search(self, dsa: ModuleType) -> None:
        values = [1, 3, 3, 3, 7]
        assert dsa.SearchAlgorithms.linear(values, 3) == 1
        assert values[dsa.SearchAlgorithms.binary(values, 3)] == 3
        assert dsa.SearchAlgorithms.lower_bound(values, 3) == 1
        assert dsa.SearchAlgorithms.lower_bound(values, 8) == 5
        assert dsa.SearchAlgorithms.binary(values, 4) is None
        assert dsa.SearchAlgorithms.binary([], 4) is None

    @pytest.mark.parametrize("name", ["bubble", "merge", "quick"])
    def test_sort_does_not_mutate_input(self, dsa: ModuleType, name: str) -> None:
        original = [5, 1, 5, 2, 4, 3]
        assert getattr(dsa.SortAlgorithms, name)(original) == [1, 2, 3, 4, 5, 5]
        assert original == [5, 1, 5, 2, 4, 3]

    @pytest.mark.parametrize("name", ["bubble", "merge"])
    def test_stable_sorts_keep_equal_keys_in_order(self, dsa: ModuleType, name: str) -> None:
        records = [("b", 1), ("a", 0), ("c", 1), ("d", 0)]
        result = getattr(dsa.SortAlgorithms, name)(records, key=lambda r: r[1])
        assert result == [("a", 0), ("d", 0), ("b", 1), ("c", 1)]

    def test_quicksort_stack_depth_is_logarithmic(self, dsa: ModuleType) -> None:
        """Hardening: smaller-side recursion bounds the stack at O(log n) for any input."""
        metrics = dsa.MetricsState()
        dsa.SortAlgorithms.quick([5] * 5000 + list(range(5000)), metrics=metrics)
        assert metrics.max_recursion_depth <= 14  # ceil(log2 10000)


class TestTraversal:
    def test_tree_bfs_dfs(self, dsa: ModuleType) -> None:
        state = dsa.TreeState()
        repo = dsa.TreeRepository()
        repo.add_root(state, "r", 0)
        for parent, child in [("r", "a"), ("r", "b"), ("a", "c"), ("b", "d")]:
            repo.add_child(state, parent, child, 0)
        adapter = dsa.TreeAdapter(state)
        assert dsa.TraversalAlgorithms.bfs(adapter, "r") == ["r", "a", "b", "c", "d"]
        assert dsa.TraversalAlgorithms.dfs(adapter, "r") == ["r", "a", "c", "b", "d"]
        assert dsa.TraversalAlgorithms.bfs(adapter, "r", maximum_depth=1) == ["r", "a", "b"]
        assert dsa.TraversalAlgorithms.dfs(adapter, "r", maximum_results=2) == ["r", "a"]

    def test_unknown_start(self, dsa: ModuleType) -> None:
        with pytest.raises(dsa.InvalidInputError):
            dsa.TraversalAlgorithms.bfs(dsa.TreeAdapter(dsa.TreeState()), "x")


class TestSequenceStackQueue:
    def test_sequence(self, dsa: ModuleType) -> None:
        assert dsa.SequenceAlgorithms.two_sum([2, 7, 11, 15], 9) == (0, 1)
        assert dsa.SequenceAlgorithms.two_sum([1, 2], 9) is None
        assert dsa.SequenceAlgorithms.maximum_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6
        assert dsa.SequenceAlgorithms.prefix_sums([1, 2, 3]) == [0, 1, 3, 6]

    def test_stack_and_queue_algorithms(self, dsa: ModuleType) -> None:
        assert dsa.StackAlgorithms.balanced_brackets("{[()]}()")
        assert not dsa.StackAlgorithms.balanced_brackets("([)]")
        assert dsa.StackAlgorithms.evaluate_postfix(["3", "4", "+", "2", "*"]) == 14.0
        assert dsa.StackAlgorithms.next_greater([4, 5, 2, 25]) == [5, 25, 25, -1]
        assert dsa.QueueAlgorithms.generate_binary_numbers(5) == ["1", "10", "11", "100", "101"]
        assert dsa.QueueAlgorithms.sliding_window_maximum([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]

    def test_bounded_containers(self, dsa: ModuleType) -> None:
        stack = dsa.StackState(capacity=1)
        dsa.StackRepository().push(stack, 1)
        with pytest.raises(dsa.CapacityExceededError):
            dsa.StackRepository().push(stack, 2)
        queue = dsa.QueueState()
        with pytest.raises(dsa.InvalidInputError):
            dsa.QueueRepository().dequeue(queue)


class TestLinkedList:
    def _list(self, dsa: ModuleType, size: int) -> object:
        state = dsa.LinkedListState()
        for value in range(size):
            dsa.LinkedListRepository().append(state, value, node_id=str(value))
        return state

    def test_reverse_middle_cycle(self, dsa: ModuleType) -> None:
        state = self._list(dsa, 4)
        assert dsa.LinkedListAlgorithms.middle(state).value == 2
        dsa.LinkedListAlgorithms.reverse(state)
        assert (state.head_id, state.tail_id, state.size) == ("3", "0", 4)
        assert dsa.LinkedListValidator().validate(state).valid
        assert not dsa.LinkedListAlgorithms.has_cycle(state)
        state.nodes["0"].next_id = "2"
        assert dsa.LinkedListAlgorithms.has_cycle(state)

    def test_reverse_rejects_corrupt_input_without_writing(self, dsa: ModuleType) -> None:
        state = self._list(dsa, 3)
        state.size = 99
        with pytest.raises(dsa.InvariantViolationError):
            dsa.LinkedListAlgorithms.reverse(state)
        assert state.head_id == "0"

    def test_delete_unknown_is_not_found(self, dsa: ModuleType) -> None:
        with pytest.raises(dsa.NotFoundError):
            dsa.LinkedListRepository().delete(self._list(dsa, 1), "zz")


class TestTrees:
    def test_tree_queries(self, dsa: ModuleType) -> None:
        state = dsa.TreeState()
        repo = dsa.TreeRepository()
        repo.add_root(state, "r", 0)
        for parent, child in [("r", "a"), ("r", "b"), ("a", "c"), ("a", "d"), ("c", "e")]:
            repo.add_child(state, parent, child, 0)
        assert dsa.TreeAlgorithms.height(state) == 4
        assert dsa.TreeAlgorithms.diameter(state) == 4  # e-c-a-r-b
        assert dsa.TreeAlgorithms.ancestors(state, "e") == ["r", "a", "c"]
        assert dsa.TreeAlgorithms.lowest_common_ancestor(state, "e", "d") == "a"
        assert dsa.TreeRepository().delete_subtree(state, "a") == ["e", "c", "d", "a"]
        assert dsa.TreeValidator().validate(state).valid

    def test_deep_tree_diameter(self, dsa: ModuleType) -> None:
        assert dsa.TreeAlgorithms.diameter(build_chain_tree(dsa, 1500)) == 1499


class TestBST:
    def test_avl_insert_and_delete(self, dsa: ModuleType) -> None:
        state = dsa.BSTState()
        for value in range(1, 101):
            dsa.BSTAlgorithms.insert_avl(state, value, node_id=str(value))
        assert dsa.BSTAlgorithms.is_avl_balanced(state)
        for value in range(1, 101, 3):
            dsa.BSTAlgorithms.delete(state, value, rebalance=True)
        assert dsa.BSTAlgorithms.is_avl_balanced(state)
        assert dsa.BSTAlgorithms.inorder(state) == [v for v in range(1, 101) if (v - 1) % 3]
        assert dsa.BSTValidator().validate(state).valid

    def test_duplicate_policies(self, dsa: ModuleType) -> None:
        state = dsa.BSTState()
        first = dsa.BSTAlgorithms.insert(state, {"k": 1, "v": "a"}, key=lambda r: r["k"])
        with pytest.raises(dsa.DuplicateKeyError):
            dsa.BSTAlgorithms.insert(state, {"k": 1, "v": "b"}, key=lambda r: r["k"])
        assert (
            dsa.BSTAlgorithms.insert(state, {"k": 1, "v": "b"}, key=lambda r: r["k"], on_duplicate="replace")
            == first
        )
        assert state.nodes[first].value["v"] == "b"

    def test_delete_missing(self, dsa: ModuleType) -> None:
        with pytest.raises(dsa.NotFoundError):
            dsa.BSTAlgorithms.delete(dsa.BSTState(), 1)


class TestTrie:
    def test_trie(self, dsa: ModuleType) -> None:
        state = dsa.TrieState()
        for word in ["car", "cart", "care", "dog", "car"]:
            dsa.TrieAlgorithms.insert(state, word)
        assert state.word_count == 4
        assert dsa.TrieAlgorithms.autocomplete(state, "car") == ["car", "care", "cart"]
        assert dsa.TrieAlgorithms.autocomplete(state, "car", limit=2) == ["car", "care"]
        assert dsa.TrieAlgorithms.delete(state, "cart")
        assert not dsa.TrieAlgorithms.search(state, "cart")
        assert dsa.TrieAlgorithms.starts_with(state, "ca")
        assert dsa.TrieValidator().validate(state).valid


class TestGraphs:
    def test_dijkstra_policies(self, dsa: ModuleType) -> None:
        state = build_graph(dsa, [("A", "B", 1), ("B", "C", 2), ("C", "D", 1), ("A", "D", 10)])
        for policy in ("eager", "lazy", "assume_non_negative"):
            assert dsa.GraphAlgorithms.dijkstra(state, "A", "D", negative_weight_policy=policy) == (
                4.0,
                ["A", "B", "C", "D"],
            )

    def test_dijkstra_negative_edges(self, dsa: ModuleType) -> None:
        state = build_graph(dsa, [("A", "B", 1), ("X", "Y", -1)])
        with pytest.raises(dsa.AlgorithmPreconditionError):
            dsa.GraphAlgorithms.dijkstra(state, "A", "B")
        # lazy only inspects reachable edges, so an unreachable negative edge is tolerated
        assert dsa.GraphAlgorithms.dijkstra(state, "A", "B", negative_weight_policy="lazy")[0] == 1.0

    def test_unreachable(self, dsa: ModuleType) -> None:
        state = build_graph(dsa, [("A", "B", 1)], vertices="C")
        assert dsa.GraphAlgorithms.dijkstra(state, "A", "C") == (math.inf, [])
        assert dsa.GraphAlgorithms.shortest_unweighted_path(state, "A", "C") == []

    def test_all_simple_paths_bounded(self, dsa: ModuleType) -> None:
        state = build_graph(dsa, [("A", "B", 1), ("A", "C", 1), ("B", "D", 1), ("C", "D", 1)])
        assert dsa.GraphAlgorithms.all_simple_paths(state, "A", "D") == [["A", "B", "D"], ["A", "C", "D"]]
        assert len(dsa.GraphAlgorithms.all_simple_paths(state, "A", "D", maximum_paths=1)) == 1

    def test_topological_sort_and_cycles(self, dsa: ModuleType) -> None:
        dag = build_graph(dsa, [("a", "b", 1), ("a", "c", 1), ("b", "d", 1), ("c", "d", 1)])
        assert dsa.GraphAlgorithms.topological_sort(dag) == ["a", "b", "c", "d"]
        assert not dsa.GraphAlgorithms.has_cycle(dag)
        cyclic = build_graph(dsa, [("a", "b", 1), ("b", "a", 1)])
        with pytest.raises(dsa.AlgorithmPreconditionError):
            dsa.GraphAlgorithms.topological_sort(cyclic)
        tree = build_graph(dsa, [("a", "b", 1), ("a", "c", 1)], directed=False)
        assert not dsa.GraphAlgorithms.has_cycle(tree)
        triangle = build_graph(dsa, [("a", "b", 1), ("b", "c", 1), ("c", "a", 1)], directed=False)
        assert dsa.GraphAlgorithms.has_cycle(triangle)

    def test_repository_rejects_bad_weight(self, dsa: ModuleType) -> None:
        state = build_graph(dsa, [], vertices="ab")
        with pytest.raises(dsa.InvalidInputError):
            dsa.GraphRepository().add_edge(state, "a", "b", float("nan"))
