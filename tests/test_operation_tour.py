"""Every registered operation, executed through the facade on a representative state.

``test_tour_covers_every_registered_operation`` fails when an operation is
registered without being added here.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from types import ModuleType
from typing import Any

import pytest

Case = tuple[str, str, str, Callable[[ModuleType], Any], dict[str, Any], Callable[[Any, Any], bool]]


def seq(dsa: ModuleType) -> Any:
    return dsa.SequenceState([4, -1, 2, 1, 7, 3])


def sorted_seq(dsa: ModuleType) -> Any:
    return dsa.SequenceState([1, 3, 5, 7])


def linked(dsa: ModuleType) -> Any:
    state = dsa.LinkedListState()
    for value in "abc":
        dsa.LinkedListRepository().append(state, value, node_id=value)
    return state


def tree(dsa: ModuleType) -> Any:
    state = dsa.TreeState()
    repo = dsa.TreeRepository()
    repo.add_root(state, "r", 0)
    for parent, child in [("r", "a"), ("r", "b"), ("a", "c")]:
        repo.add_child(state, parent, child, 0)
    return state


def bst(dsa: ModuleType) -> Any:
    state = dsa.BSTState()
    for value in (5, 3, 8):
        dsa.BSTAlgorithms.insert_avl(state, value)
    return state


def trie(dsa: ModuleType) -> Any:
    state = dsa.TrieState()
    for word in ("car", "cat"):
        dsa.TrieAlgorithms.insert(state, word)
    return state


def graph(dsa: ModuleType) -> Any:
    return dsa.GraphState(
        values={"a": 1, "b": 2, "c": 3},
        adjacency={"a": {"b": 1.0}, "b": {"c": 2.0}, "c": {}},
        directed=True,
    )


def heap(dsa: Any) -> Any:
    return dsa.HeapAlgorithms.heapify([5, 1, 4, 2])


def dsu(dsa: Any) -> Any:
    state = dsa.UnionFindState()
    for element in "abcd":
        dsa.UnionFindAlgorithms.make_set(state, element)
    dsa.UnionFindAlgorithms.union(state, "a", "b")
    return state


def ok(expected: Any) -> Callable[[Any, Any], bool]:
    return lambda data, _state: data == expected


CASES: list[Case] = [
    ("SEQUENCE", "SEARCH", "LINEAR", seq, {"target": 2}, ok(2)),
    ("SEQUENCE", "SEARCH", "BINARY", sorted_seq, {"target": 5}, ok(2)),
    ("SEQUENCE", "SEARCH", "LOWER_BOUND", sorted_seq, {"target": 5}, ok(2)),
    ("SEQUENCE", "ORDERING", "BUBBLE", seq, {}, ok([-1, 1, 2, 3, 4, 7])),
    ("SEQUENCE", "ORDERING", "MERGE", seq, {}, ok([-1, 1, 2, 3, 4, 7])),
    ("SEQUENCE", "ORDERING", "QUICK", seq, {}, ok([-1, 1, 2, 3, 4, 7])),
    ("SEQUENCE", "QUERY", "READ", seq, {"index": 1}, ok(-1)),
    ("SEQUENCE", "QUERY", "TWO_SUM", seq, {"target": 6}, ok((0, 2))),
    ("SEQUENCE", "QUERY", "MAXIMUM_SUBARRAY", seq, {}, ok(16)),
    ("SEQUENCE", "QUERY", "PREFIX_SUMS", seq, {}, ok([0, 4, 3, 5, 6, 13, 16])),
    ("SEQUENCE", "QUERY", "NEXT_GREATER", seq, {}, ok([7, 2, 7, 7, -1, -1])),
    ("SEQUENCE", "QUERY", "SLIDING_WINDOW_MAXIMUM", seq, {"window": 3}, ok([4, 2, 7, 7])),
    ("SEQUENCE", "MUTATION", "INSERT", seq, {"value": 9, "index": 0}, lambda d, s: s.values[0] == 9),
    ("SEQUENCE", "MUTATION", "UPDATE", seq, {"index": 0, "value": 0}, lambda d, s: s.values[0] == 0),
    ("SEQUENCE", "MUTATION", "DELETE", seq, {"index": -1}, lambda d, s: d == 3 and len(s.values) == 5),
    ("SEQUENCE", "VALIDATION", "VALIDATE", seq, {}, lambda d, s: d.valid),
    ("LINKED_LIST", "QUERY", "MIDDLE", linked, {}, lambda d, s: d.node_id == "b"),
    ("LINKED_LIST", "QUERY", "HAS_CYCLE", linked, {}, ok(False)),
    (
        "LINKED_LIST",
        "MUTATION",
        "APPEND",
        linked,
        {"value": "d", "node_id": "d"},
        lambda d, s: s.tail_id == "d",
    ),
    (
        "LINKED_LIST",
        "MUTATION",
        "PREPEND",
        linked,
        {"value": "z", "node_id": "z"},
        lambda d, s: s.head_id == "z",
    ),
    ("LINKED_LIST", "MUTATION", "DELETE", linked, {"node_id": "b"}, lambda d, s: s.size == 2),
    ("LINKED_LIST", "MUTATION", "REVERSE", linked, {}, lambda d, s: s.head_id == "c"),
    ("LINKED_LIST", "VALIDATION", "VALIDATE", linked, {}, lambda d, s: d.valid),
    ("STACK", "QUERY", "PEEK", lambda dsa: dsa.StackState([1, 2]), {}, ok(2)),
    (
        "STACK",
        "MUTATION",
        "PUSH",
        lambda dsa: dsa.StackState([1]),
        {"value": 2},
        lambda d, s: s.values == [1, 2],
    ),
    ("STACK", "MUTATION", "POP", lambda dsa: dsa.StackState([1, 2]), {}, ok(2)),
    ("STACK", "VALIDATION", "VALIDATE", lambda dsa: dsa.StackState([1], 1), {}, lambda d, s: d.valid),
    ("QUEUE", "QUERY", "PEEK", lambda dsa: dsa.QueueState(deque([1, 2])), {}, ok(1)),
    (
        "QUEUE",
        "MUTATION",
        "ENQUEUE",
        lambda dsa: dsa.QueueState(),
        {"value": 1},
        lambda d, s: list(s.values) == [1],
    ),
    ("QUEUE", "MUTATION", "DEQUEUE", lambda dsa: dsa.QueueState(deque([1, 2])), {}, ok(1)),
    ("QUEUE", "VALIDATION", "VALIDATE", lambda dsa: dsa.QueueState(), {}, lambda d, s: d.valid),
    ("TREE", "TRAVERSAL", "BFS", tree, {}, ok(["r", "a", "b", "c"])),
    ("TREE", "TRAVERSAL", "DFS", tree, {}, ok(["r", "a", "c", "b"])),
    ("TREE", "QUERY", "HEIGHT", tree, {}, ok(3)),
    ("TREE", "QUERY", "DIAMETER", tree, {}, ok(3)),
    ("TREE", "QUERY", "ANCESTORS", tree, {"node_id": "c"}, ok(["r", "a"])),
    ("TREE", "QUERY", "LOWEST_COMMON_ANCESTOR", tree, {"left": "c", "right": "b"}, ok("r")),
    (
        "TREE",
        "MUTATION",
        "ADD_ROOT",
        lambda dsa: dsa.TreeState(),
        {"node_id": "r", "value": 1},
        lambda d, s: s.root_id == "r",
    ),
    ("TREE", "MUTATION", "ADD_CHILD", tree, {"parent_id": "b", "node_id": "d", "value": 0}, ok(True)),
    ("TREE", "MUTATION", "DELETE_SUBTREE", tree, {"node_id": "a"}, ok(["c", "a"])),
    ("TREE", "VALIDATION", "VALIDATE", tree, {}, lambda d, s: d.valid),
    ("BST", "SEARCH", "LOOKUP", bst, {"target": 8}, lambda d, s: d.value == 8),
    ("BST", "QUERY", "INORDER", bst, {}, ok([3, 5, 8])),
    ("BST", "QUERY", "IS_AVL_BALANCED", bst, {}, ok(True)),
    ("BST", "MUTATION", "INSERT", bst, {"value": 9}, lambda d, s: len(s.nodes) == 4),
    ("BST", "MUTATION", "DELETE", bst, {"target": 5}, lambda d, s: d.value == 5 and len(s.nodes) == 2),
    ("BST", "VALIDATION", "VALIDATE", bst, {}, lambda d, s: d.valid),
    ("TRIE", "SEARCH", "CONTAINS", trie, {"word": "cat"}, ok(True)),
    ("TRIE", "SEARCH", "PREFIX", trie, {"prefix": "ca"}, ok(["car", "cat"])),
    ("TRIE", "MUTATION", "INSERT", trie, {"word": "cab"}, lambda d, s: s.word_count == 3),
    ("TRIE", "MUTATION", "DELETE", trie, {"word": "car"}, lambda d, s: s.word_count == 1),
    ("TRIE", "VALIDATION", "VALIDATE", trie, {}, lambda d, s: d.valid),
    ("GRAPH", "TRAVERSAL", "BFS", graph, {"start": "a"}, ok(["a", "b", "c"])),
    ("GRAPH", "TRAVERSAL", "DFS", graph, {"start": "a"}, ok(["a", "b", "c"])),
    ("GRAPH", "PATH", "SHORTEST_UNWEIGHTED", graph, {"source": "a", "target": "c"}, ok(["a", "b", "c"])),
    ("GRAPH", "PATH", "DIJKSTRA", graph, {"source": "a", "target": "c"}, ok((3.0, ["a", "b", "c"]))),
    ("GRAPH", "PATH", "ALL_SIMPLE_PATHS", graph, {"source": "a", "target": "c"}, ok([["a", "b", "c"]])),
    ("GRAPH", "QUERY", "HAS_CYCLE", graph, {}, ok(False)),
    ("GRAPH", "QUERY", "TOPOLOGICAL_SORT", graph, {}, ok(["a", "b", "c"])),
    ("GRAPH", "MUTATION", "ADD_VERTEX", graph, {"vertex_id": "d", "value": 4}, ok(True)),
    (
        "GRAPH",
        "MUTATION",
        "ADD_EDGE",
        graph,
        {"source": "c", "target": "a", "weight": 2},
        lambda d, s: s.adjacency["c"] == {"a": 2},
    ),
    (
        "GRAPH",
        "MUTATION",
        "REMOVE_EDGE",
        graph,
        {"source": "a", "target": "b"},
        lambda d, s: s.adjacency["a"] == {},
    ),
    (
        "GRAPH",
        "MUTATION",
        "REMOVE_VERTEX",
        graph,
        {"vertex_id": "b"},
        lambda d, s: "b" not in s.adjacency["a"],
    ),
    ("GRAPH", "VALIDATION", "VALIDATE", graph, {}, lambda d, s: d.valid),
    ("SEQUENCE", "SEARCH", "FIRST_TRUE", sorted_seq, {"predicate": lambda v: v >= 4}, ok(2)),
    ("SEQUENCE", "QUERY", "HAS_DUPLICATE", lambda dsa: dsa.SequenceState([1, 2, 1]), {}, ok(True)),
    ("SEQUENCE", "QUERY", "FREQUENCY", lambda dsa: dsa.SequenceState(list("aab")), {}, ok({"a": 2, "b": 1})),
    (
        "SEQUENCE",
        "QUERY",
        "GROUP_ANAGRAMS",
        lambda dsa: dsa.SequenceState(["eat", "tea", "tan", "ate"]),
        {},
        ok([["eat", "tea", "ate"], ["tan"]]),
    ),
    (
        "SEQUENCE",
        "QUERY",
        "LONGEST_CONSECUTIVE",
        lambda dsa: dsa.SequenceState([100, 4, 200, 1, 3, 2]),
        {},
        ok(4),
    ),
    (
        "SEQUENCE",
        "QUERY",
        "SUBARRAY_SUM_COUNT",
        lambda dsa: dsa.SequenceState([1, 1, 1]),
        {"target": 2},
        ok(2),
    ),
    ("SEQUENCE", "QUERY", "FIRST_UNIQUE", lambda dsa: dsa.SequenceState(list("aabc")), {}, ok(2)),
    ("SEQUENCE", "QUERY", "PAIR_SUM_SORTED", sorted_seq, {"target": 8}, ok((0, 3))),
    (
        "SEQUENCE",
        "QUERY",
        "LONGEST_UNIQUE_WINDOW",
        lambda dsa: dsa.SequenceState(list("abcabcbb")),
        {},
        ok(3),
    ),
    (
        "SEQUENCE",
        "QUERY",
        "MIN_SUBARRAY_LENGTH",
        lambda dsa: dsa.SequenceState([2, 3, 1, 2, 4, 3]),
        {"target": 7},
        ok(2),
    ),
    ("SEQUENCE", "QUERY", "MAX_AREA", lambda dsa: dsa.SequenceState([1, 8, 6, 2, 5, 4, 8, 3, 7]), {}, ok(49)),
    ("SEQUENCE", "QUERY", "TOP_K", seq, {"k": 2}, ok([7, 4])),
    (
        "SEQUENCE",
        "QUERY",
        "MERGE_SORTED",
        lambda dsa: dsa.SequenceState([[1, 4], [2, 3]]),
        {},
        ok([1, 2, 3, 4]),
    ),
    ("HEAP", "QUERY", "PEEK", heap, {}, ok(1)),
    ("HEAP", "MUTATION", "PUSH", heap, {"value": 0}, lambda d, s: s.values[0] == 0 and d == 5),
    ("HEAP", "MUTATION", "POP", heap, {}, lambda d, s: d == 1 and s.values[0] == 2),
    ("HEAP", "VALIDATION", "VALIDATE", heap, {}, lambda d, s: d.valid),
    ("UNION_FIND", "QUERY", "FIND", dsu, {"element": "b"}, ok("a")),
    ("UNION_FIND", "QUERY", "CONNECTED", dsu, {"left": "a", "right": "b"}, ok(True)),
    ("UNION_FIND", "QUERY", "COMPONENT_COUNT", dsu, {}, ok(3)),
    ("UNION_FIND", "MUTATION", "ADD", dsu, {"element": "e"}, lambda d, s: d is True and s.components == 4),
    (
        "UNION_FIND",
        "MUTATION",
        "UNION",
        dsu,
        {"left": "c", "right": "d"},
        lambda d, s: d is True and s.components == 2,
    ),
    ("UNION_FIND", "VALIDATION", "VALIDATE", dsu, {}, lambda d, s: d.valid),
    (
        "UNION_FIND",
        "MUTATION",
        "ADD_ALL",
        dsu,
        {"elements": ["d", "e", "f"]},
        lambda d, s: d == 2 and s.components == 5,
    ),
    (
        "UNION_FIND",
        "MUTATION",
        "GROUP_BY_KEYS",
        lambda dsa: dsa.UnionFindState(),
        {"elements": ["ab", "bc", "xy", "cd"], "keys": list},
        ok([["ab", "bc", "cd"], ["xy"]]),
    ),
    ("SEQUENCE", "OPTIMIZATION", "HOUSE_ROBBER", lambda dsa: dsa.SequenceState([2, 7, 9, 3, 1]), {}, ok(12)),
    (
        "SEQUENCE",
        "OPTIMIZATION",
        "LONGEST_INCREASING_SUBSEQUENCE",
        lambda dsa: dsa.SequenceState([10, 9, 2, 5, 3, 7, 101, 18]),
        {},
        ok(4),
    ),
    (
        "SEQUENCE",
        "OPTIMIZATION",
        "COIN_CHANGE",
        lambda dsa: dsa.SequenceState([1, 2, 5]),
        {"amount": 11},
        ok(3),
    ),
    (
        "SEQUENCE",
        "OPTIMIZATION",
        "KNAPSACK_01",
        lambda dsa: dsa.SequenceState([(1, 1), (3, 4), (4, 5), (5, 7)]),
        {"capacity": 7},
        ok(9),
    ),
    (
        "SEQUENCE",
        "OPTIMIZATION",
        "SUBSET_SUM",
        lambda dsa: dsa.SequenceState([5, 3, 9, 4, 2]),
        {"target": 9},
        ok((2,)),
    ),
    (
        "SEQUENCE",
        "OPTIMIZATION",
        "LONGEST_COMMON_SUBSEQUENCE",
        lambda dsa: dsa.SequenceState(list("abcde")),
        {"other": list("ace")},
        ok(3),
    ),
    (
        "SEQUENCE",
        "OPTIMIZATION",
        "EDIT_DISTANCE",
        lambda dsa: dsa.SequenceState(list("kitten")),
        {"other": list("sitting")},
        ok(3),
    ),
    (
        "SEQUENCE",
        "OPTIMIZATION",
        "MERGE_INTERVALS",
        lambda dsa: dsa.SequenceState([(1, 3), (2, 6), (8, 10)]),
        {},
        ok([(1, 6), (8, 10)]),
    ),
    (
        "SEQUENCE",
        "OPTIMIZATION",
        "MAX_NON_OVERLAPPING",
        lambda dsa: dsa.SequenceState([(1, 2), (2, 3), (3, 4), (1, 3)]),
        {},
        ok([(1, 2), (2, 3), (3, 4)]),
    ),
    ("SEQUENCE", "OPTIMIZATION", "CAN_JUMP", lambda dsa: dsa.SequenceState([2, 3, 1, 1, 4]), {}, ok(True)),
    (
        "SEQUENCE",
        "ENUMERATION",
        "SUBSETS",
        lambda dsa: dsa.SequenceState([1, 2]),
        {},
        ok([(), (1,), (1, 2), (2,)]),
    ),
    (
        "SEQUENCE",
        "ENUMERATION",
        "PERMUTATIONS",
        lambda dsa: dsa.SequenceState([1, 2, 3]),
        {},
        lambda d, s: len(d) == 6,
    ),
    (
        "SEQUENCE",
        "ENUMERATION",
        "COMBINATIONS",
        lambda dsa: dsa.SequenceState([1, 2, 3]),
        {"k": 2},
        ok([(1, 2), (1, 3), (2, 3)]),
    ),
    (
        "SEQUENCE",
        "ENUMERATION",
        "COMBINATION_SUM",
        lambda dsa: dsa.SequenceState([2, 3, 6, 7]),
        {"target": 7},
        ok([(2, 2, 3), (7,)]),
    ),
]


@pytest.mark.parametrize("case", CASES, ids=["/".join(c[:3]) for c in CASES])
def test_operation(dsa: ModuleType, case: Case) -> None:
    structure, capability, operation, factory, kwargs, check = case
    state = factory(dsa)
    result = dsa.DSAFacade().execute(
        structure_type=structure,
        capability=capability,
        operation=operation,
        state=state,
        verify_invariants=True,
        **kwargs,
    )
    assert result.status is dsa.Status.SUCCESS, result
    assert check(result.data, state), result.data
    assert result.metadata["algorithm"]["name"] == operation


def test_tour_covers_every_registered_operation(dsa: ModuleType) -> None:
    assert sorted(c[:3] for c in CASES) == dsa.DSAFacade().capabilities()
