"""Property-based tests: postconditions and invariants over generated inputs."""

from __future__ import annotations

import bisect
from types import ModuleType

from hypothesis import given, settings
from hypothesis import strategies as st

from .conftest import EDITIONS

ints = st.lists(st.integers(-1000, 1000), max_size=200)
edition = st.sampled_from(EDITIONS)


@given(edition, ints)
def test_every_sort_matches_sorted(dsa: ModuleType, values: list[int]) -> None:
    for name in ("bubble", "merge", "quick"):
        assert getattr(dsa.SortAlgorithms, name)(values) == sorted(values)


@given(edition, st.lists(st.tuples(st.integers(0, 5), st.integers()), max_size=100))
def test_stable_sorts_match_python_stable_sort(dsa: ModuleType, records: list[tuple[int, int]]) -> None:
    expected = sorted(records, key=lambda r: r[0])
    assert dsa.SortAlgorithms.merge(records, key=lambda r: r[0]) == expected
    assert dsa.SortAlgorithms.bubble(records, key=lambda r: r[0]) == expected


@given(edition, ints, st.integers(-1000, 1000))
def test_binary_search_and_lower_bound(dsa: ModuleType, values: list[int], target: int) -> None:
    values = sorted(values)
    assert dsa.SearchAlgorithms.lower_bound(values, target) == bisect.bisect_left(values, target)
    index = dsa.SearchAlgorithms.binary(values, target)
    assert (index is None) == (target not in values)
    if index is not None:
        assert values[index] == target


@settings(max_examples=60)
@given(edition, st.lists(st.integers(0, 300), max_size=120), st.lists(st.integers(0, 300), max_size=60))
def test_avl_insert_delete_keeps_invariants(dsa: ModuleType, inserts: list[int], deletes: list[int]) -> None:
    state = dsa.BSTState()
    expected: set[int] = set()
    for value in inserts:
        dsa.BSTAlgorithms.insert_avl(state, value, on_duplicate="ignore")
        expected.add(value)
    for value in deletes:
        if value in expected:
            dsa.BSTAlgorithms.delete(state, value, rebalance=True)
            expected.discard(value)
    assert dsa.BSTAlgorithms.inorder(state) == sorted(expected)
    assert dsa.BSTAlgorithms.is_avl_balanced(state)
    assert dsa.BSTValidator().validate(state).valid


@settings(max_examples=60)
@given(edition, st.lists(st.integers(0, 300), max_size=120), st.lists(st.integers(0, 300), max_size=60))
def test_plain_bst_insert_delete_keeps_ordering(
    dsa: ModuleType, inserts: list[int], deletes: list[int]
) -> None:
    state = dsa.BSTState()
    expected: set[int] = set()
    for value in inserts:
        dsa.BSTAlgorithms.insert(state, value, on_duplicate="ignore")
        expected.add(value)
    for value in deletes:
        if value in expected:
            dsa.BSTAlgorithms.delete(state, value)
            expected.discard(value)
    assert dsa.BSTAlgorithms.inorder(state) == sorted(expected)
    assert dsa.BSTValidator().validate(state).valid


@given(
    edition,
    st.lists(st.text("abc", max_size=6), max_size=40),
    st.lists(st.text("abc", max_size=6), max_size=20),
)
def test_trie_behaves_like_a_set(dsa: ModuleType, inserts: list[str], deletes: list[str]) -> None:
    state = dsa.TrieState()
    words: set[str] = set()
    for word in inserts:
        assert dsa.TrieAlgorithms.insert(state, word) == (word not in words)
        words.add(word)
    for word in deletes:
        assert dsa.TrieAlgorithms.delete(state, word) == (word in words)
        words.discard(word)
    assert dsa.TrieAlgorithms.autocomplete(state, "") == sorted(words)
    assert dsa.TrieValidator().validate(state).valid


@given(edition, st.lists(st.tuples(st.integers(0, 15), st.integers(0, 15)), max_size=60), st.booleans())
def test_graph_traversals_visit_each_reachable_vertex_once(
    dsa: ModuleType, edges: list[tuple[int, int]], directed: bool
) -> None:
    state = dsa.GraphState(directed=directed)
    repo = dsa.GraphRepository()
    for vertex in range(16):
        repo.add_vertex(state, str(vertex), vertex)
    for source, target in edges:
        repo.add_edge(state, str(source), str(target))
    adapter = dsa.GraphAdapter(state)
    bfs = dsa.TraversalAlgorithms.bfs(adapter, "0")
    dfs = dsa.TraversalAlgorithms.dfs(adapter, "0")
    assert len(bfs) == len(set(bfs)) and set(bfs) == set(dfs)
    assert dsa.GraphValidator().validate(state).valid
    for target in bfs:
        path = dsa.GraphAlgorithms.shortest_unweighted_path(state, "0", target)
        distance, weighted = dsa.GraphAlgorithms.dijkstra(state, "0", target)
        assert path[0] == "0" and path[-1] == target and distance == len(path) - 1
        assert len(weighted) == len(path)
