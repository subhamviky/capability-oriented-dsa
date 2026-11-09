"""Heap, union-find, hashing, window, DP, greedy and backtracking kernels and their governed limits."""

from __future__ import annotations

import heapq
import itertools
from types import ModuleType

import pytest
from hypothesis import given
from hypothesis import strategies as st

from .conftest import EDITIONS

ints = st.lists(st.integers(-50, 50), max_size=30)
edition = st.sampled_from(EDITIONS)


# ------------------------------------------------------------------ heap
@given(edition, ints, st.booleans())
def test_heap_pops_in_order(dsa: ModuleType, values: list[int], max_heap: bool) -> None:
    state = dsa.HeapState(max_heap=max_heap)
    for value in values:
        dsa.HeapAlgorithms.push(state, value)
    assert dsa.VALIDATORS["HEAP"].validate(state).valid
    popped = [dsa.HeapAlgorithms.pop(state) for _ in values]
    assert popped == sorted(values, reverse=max_heap)


@given(edition, ints)
def test_heapify_matches_heapq(dsa: ModuleType, values: list[int]) -> None:
    state = dsa.HeapAlgorithms.heapify(values)
    assert dsa.VALIDATORS["HEAP"].validate(state).valid
    assert dsa.HeapAlgorithms.heapify(values, max_heap=True).values[:1] == sorted(values)[-1:]


@given(edition, ints, st.integers(0, 35), st.booleans())
def test_top_k_matches_sorted(dsa: ModuleType, values: list[int], k: int, largest: bool) -> None:
    expected = sorted(values, reverse=largest)[:k]
    assert dsa.HeapAlgorithms.top_k(values, k, largest=largest) == expected


@given(edition, st.lists(ints, max_size=5))
def test_merge_sorted_matches_heapq(dsa: ModuleType, lists: list[list[int]]) -> None:
    ordered = [sorted(items) for items in lists]
    assert dsa.HeapAlgorithms.merge_sorted(ordered) == list(heapq.merge(*ordered))


def test_heap_errors(dsa: ModuleType) -> None:
    with pytest.raises(dsa.InvalidInputError):
        dsa.HeapAlgorithms.pop(dsa.HeapState())
    with pytest.raises(dsa.InvalidInputError):
        dsa.HeapAlgorithms.top_k([1], -1)
    with pytest.raises(dsa.AlgorithmPreconditionError):
        dsa.HeapAlgorithms.merge_sorted([[2, 1]])
    broken = dsa.HeapState([3, 1])
    assert not dsa.VALIDATORS["HEAP"].validate(broken).valid


# ----------------------------------------------------------- union-find
@given(edition, st.lists(st.tuples(st.integers(0, 12), st.integers(0, 12)), max_size=30))
def test_union_find_matches_reachability(dsa: ModuleType, pairs: list[tuple[int, int]]) -> None:
    state = dsa.UnionFindState()
    for element in range(13):
        dsa.UnionFindAlgorithms.make_set(state, element)
    groups = [{i} for i in range(13)]
    for a, b in pairs:
        dsa.UnionFindAlgorithms.union(state, a, b)
        ga = next(g for g in groups if a in g)
        gb = next(g for g in groups if b in g)
        if ga is not gb:
            ga |= gb
            groups.remove(gb)
    assert state.components == len(groups)
    assert dsa.VALIDATORS["UNION_FIND"].validate(state).valid
    for a, b in itertools.combinations(range(13), 2):
        assert dsa.UnionFindAlgorithms.connected(state, a, b) == any(a in g and b in g for g in groups)


def test_union_find_edges_and_validator(dsa: ModuleType) -> None:
    state = dsa.UnionFindState()
    assert dsa.UnionFindAlgorithms.make_set(state, "a") and not dsa.UnionFindAlgorithms.make_set(state, "a")
    with pytest.raises(dsa.NotFoundError):
        dsa.UnionFindAlgorithms.find(state, "zzz")
    state.parent["a"] = "ghost"
    assert not dsa.VALIDATORS["UNION_FIND"].validate(state).valid
    cyclic = dsa.UnionFindState({"a": "b", "b": "a"}, {}, 1)
    assert not dsa.VALIDATORS["UNION_FIND"].validate(cyclic).valid


def test_find_governed_does_not_mutate(dsa: ModuleType) -> None:
    state = dsa.UnionFindState()
    for name in "abcd":
        dsa.UnionFindAlgorithms.make_set(state, name)
    for pair in ("ab", "cd", "ac"):
        dsa.UnionFindAlgorithms.union(state, pair[0], pair[1])
    before = dict(state.parent)
    result = dsa.DSAFacade().execute(
        structure_type="UNION_FIND", capability="QUERY", operation="FIND", state=state, element="d"
    )
    assert result.data == dsa.UnionFindAlgorithms.find(state, "a", compress=False)
    assert state.parent == before


def test_governed_union_find_unknown_element_is_not_found(dsa: ModuleType) -> None:
    result = dsa.DSAFacade().execute(
        structure_type="UNION_FIND",
        capability="MUTATION",
        operation="UNION",
        state=dsa.UnionFindState(),
        left="x",
        right="y",
    )
    assert result.status is dsa.Status.NOT_FOUND


# -------------------------------------------------------------- hashing
@given(edition, ints, st.integers(-20, 20))
def test_subarray_sum_count_matches_brute_force(dsa: ModuleType, values: list[int], target: int) -> None:
    expected = sum(
        1 for i in range(len(values)) for j in range(i, len(values)) if sum(values[i : j + 1]) == target
    )
    assert dsa.HashingAlgorithms.subarray_sum_count(values, target) == expected


@given(edition, ints)
def test_longest_consecutive_matches_sorted_scan(dsa: ModuleType, values: list[int]) -> None:
    unique = sorted(set(values))
    best = run = 0
    for index, value in enumerate(unique):
        run = run + 1 if index and value == unique[index - 1] + 1 else 1
        best = max(best, run)
    assert dsa.HashingAlgorithms.longest_consecutive(values) == best


@given(edition, ints)
def test_duplicate_and_frequency(dsa: ModuleType, values: list[int]) -> None:
    assert dsa.HashingAlgorithms.has_duplicate(values) == (len(set(values)) != len(values))
    assert dsa.HashingAlgorithms.frequency(values) == {v: values.count(v) for v in dict.fromkeys(values)}


def test_first_unique_and_anagrams(dsa: ModuleType) -> None:
    assert dsa.HashingAlgorithms.first_unique("aabbc") == 4
    assert dsa.HashingAlgorithms.first_unique("aabb") is None
    assert dsa.HashingAlgorithms.group_anagrams(["b", "a", "b"]) == [["b", "b"], ["a"]]


# --------------------------------------------------------------- windows
@given(edition, ints)
def test_pair_sum_sorted_finds_a_valid_pair_iff_one_exists(dsa: ModuleType, values: list[int]) -> None:
    ordered = sorted(values)
    for target in range(-20, 21, 5):
        pair = dsa.WindowAlgorithms.pair_sum_sorted(ordered, target)
        exists = any(a + b == target for a, b in itertools.combinations(ordered, 2))
        assert (pair is not None) == exists
        if pair:
            assert pair[0] < pair[1] and ordered[pair[0]] + ordered[pair[1]] == target


@given(edition, st.lists(st.integers(0, 4), max_size=25))
def test_longest_unique_window_matches_brute_force(dsa: ModuleType, values: list[int]) -> None:
    best = 0
    for i in range(len(values)):
        for j in range(i, len(values)):
            if len(set(values[i : j + 1])) == j - i + 1:
                best = max(best, j - i + 1)
    assert dsa.WindowAlgorithms.longest_unique_window(values) == best


@given(edition, st.lists(st.integers(0, 9), max_size=20), st.integers(1, 30))
def test_min_subarray_length_matches_brute_force(dsa: ModuleType, values: list[int], target: int) -> None:
    lengths = [
        j - i + 1
        for i in range(len(values))
        for j in range(i, len(values))
        if sum(values[i : j + 1]) >= target
    ]
    assert dsa.WindowAlgorithms.min_subarray_length(values, target) == min(lengths, default=0)


@given(edition, st.lists(st.integers(0, 20), max_size=20))
def test_max_area_matches_brute_force(dsa: ModuleType, heights: list[int]) -> None:
    best = max(
        ((j - i) * min(heights[i], heights[j]) for i, j in itertools.combinations(range(len(heights)), 2)),
        default=0,
    )
    assert dsa.WindowAlgorithms.max_area(heights) == best


def test_window_input_errors(dsa: ModuleType) -> None:
    for call in (
        lambda: dsa.WindowAlgorithms.min_subarray_length([-1], 1),
        lambda: dsa.WindowAlgorithms.max_area([-1]),
    ):
        with pytest.raises(dsa.InvalidInputError):
            call()


# ------------------------------------------------------------ DP / greedy
@given(edition, st.lists(st.integers(0, 20), max_size=15))
def test_house_robber_matches_brute_force(dsa: ModuleType, values: list[int]) -> None:
    best = 0
    for mask in range(1 << len(values)):
        if mask & (mask >> 1):
            continue
        best = max(best, sum(v for i, v in enumerate(values) if mask >> i & 1))
    assert dsa.DynamicProgrammingAlgorithms.house_robber(values) == best


@given(edition, st.lists(st.integers(-20, 20), max_size=14))
def test_lis_matches_quadratic_dp(dsa: ModuleType, values: list[int]) -> None:
    table = [1] * len(values)
    for i in range(len(values)):
        for j in range(i):
            if values[j] < values[i]:
                table[i] = max(table[i], table[j] + 1)
    assert dsa.DynamicProgrammingAlgorithms.longest_increasing_subsequence(values) == max(table, default=0)


@given(edition, st.lists(st.integers(1, 6), min_size=1, max_size=4), st.integers(0, 25))
def test_coin_change_matches_brute_force(dsa: ModuleType, coins: list[int], amount: int) -> None:
    best: dict[int, int] = {0: 0}
    for total in range(1, amount + 1):
        options = [best[total - c] + 1 for c in coins if total - c in best]
        if options:
            best[total] = min(options)
    assert dsa.DynamicProgrammingAlgorithms.coin_change(coins, amount) == best.get(amount)


@given(edition, st.lists(st.tuples(st.integers(0, 6), st.integers(0, 9)), max_size=8), st.integers(0, 15))
def test_knapsack_matches_subset_enumeration(
    dsa: ModuleType, items: list[tuple[int, int]], capacity: int
) -> None:
    best = 0
    for mask in range(1 << len(items)):
        chosen = [items[i] for i in range(len(items)) if mask >> i & 1]
        if sum(w for w, _ in chosen) <= capacity:
            best = max(best, sum(v for _, v in chosen))
    assert dsa.DynamicProgrammingAlgorithms.knapsack_01(items, capacity) == best


def test_lcs_and_edit_distance_known_values(dsa: ModuleType) -> None:
    dp = dsa.DynamicProgrammingAlgorithms
    assert dp.longest_common_subsequence("AGGTAB", "GXTXAYB") == 4
    assert dp.edit_distance("", "abc") == 3 and dp.edit_distance("flaw", "lawn") == 2
    assert dp.edit_distance("same", "same") == 0


def test_dp_table_is_bounded(dsa: ModuleType) -> None:
    with pytest.raises(dsa.InvalidInputError, match="limit"):
        dsa.DynamicProgrammingAlgorithms.edit_distance("a" * 100, "b" * 100, max_cells=1000)
    result = dsa.DSAFacade().execute(
        structure_type="SEQUENCE",
        capability="OPTIMIZATION",
        operation="COIN_CHANGE",
        state=dsa.SequenceState([1, 2]),
        amount=10_000,
        config={"dp_max_cells": 100, "validation_mode": "result"},
    )
    assert result.status is dsa.Status.FAILURE and result.errors[0].code == "INVALID_INPUT"


def test_coin_change_impossible_is_not_found(dsa: ModuleType) -> None:
    result = dsa.DSAFacade().execute(
        structure_type="SEQUENCE",
        capability="OPTIMIZATION",
        operation="COIN_CHANGE",
        state=dsa.SequenceState([2]),
        amount=3,
    )
    assert result.status is dsa.Status.NOT_FOUND


@given(
    edition,
    st.lists(st.tuples(st.integers(0, 15), st.integers(0, 15)).map(lambda p: tuple(sorted(p))), max_size=10),
)
def test_intervals(dsa: ModuleType, intervals: list[tuple[int, int]]) -> None:
    merged = dsa.GreedyAlgorithms.merge_intervals(intervals)
    assert all(a[1] < b[0] for a, b in itertools.pairwise(merged))
    covered = {x for s, e in intervals for x in range(s, e + 1)}
    assert covered == {x for s, e in merged for x in range(s, e + 1)}
    chosen = dsa.GreedyAlgorithms.max_non_overlapping(intervals)
    assert all(a[1] <= b[0] for a, b in itertools.pairwise(chosen))
    best = 0
    for size in range(len(intervals), 0, -1):
        if any(
            all(a[1] <= b[0] for a, b in itertools.pairwise(sorted(combo, key=lambda i: (i[1], i[0]))))
            for combo in itertools.combinations(intervals, size)
        ):
            best = size
            break
    assert len(chosen) == best


@given(edition, st.lists(st.integers(0, 4), max_size=10))
def test_can_jump_matches_reachability(dsa: ModuleType, steps: list[int]) -> None:
    reachable = {0} if steps else set()
    for index in sorted(reachable | set(range(len(steps)))):
        if index in reachable:
            reachable |= {index + k for k in range(1, steps[index] + 1) if index + k < len(steps)}
    assert dsa.GreedyAlgorithms.can_jump(steps) == (not steps or len(steps) - 1 in reachable)


def test_interval_errors(dsa: ModuleType) -> None:
    with pytest.raises(dsa.InvalidInputError):
        dsa.GreedyAlgorithms.merge_intervals([(3, 1)])
    with pytest.raises(dsa.InvalidInputError):
        dsa.GreedyAlgorithms.can_jump([-1])


# ----------------------------------------------------------- backtracking
@given(edition, st.lists(st.integers(), max_size=7, unique=True))
def test_subsets_permutations_combinations_match_itertools(dsa: ModuleType, values: list[int]) -> None:
    bt = dsa.BacktrackingAlgorithms
    assert sorted(bt.subsets(values)) == sorted(
        c for r in range(len(values) + 1) for c in itertools.combinations(values, r)
    )
    assert sorted(bt.permutations(values)) == sorted(itertools.permutations(values))
    for k in range(len(values) + 1):
        assert sorted(bt.combinations(values, k)) == sorted(itertools.combinations(values, k))


def test_combination_sum_and_n_queens_known_counts(dsa: ModuleType) -> None:
    bt = dsa.BacktrackingAlgorithms
    assert sorted(bt.combination_sum([2, 3, 6, 7], 7)) == [(2, 2, 3), (7,)]
    assert [len(list(bt.n_queens(n))) for n in range(1, 8)] == [1, 0, 0, 2, 10, 4, 40]
    with pytest.raises(dsa.InvalidInputError):
        list(bt.combination_sum([0], 3))


def test_backtracking_is_lazy_and_bounded(dsa: ModuleType) -> None:
    bt = dsa.BacktrackingAlgorithms
    assert next(bt.permutations(range(30))) == tuple(range(30))
    with pytest.raises(dsa.CapacityExceededError):
        list(bt.subsets(range(20), max_nodes=1000))


def test_governed_enumeration_truncates_and_says_so(dsa: ModuleType) -> None:
    result = dsa.DSAFacade().execute(
        structure_type="SEQUENCE",
        capability="ENUMERATION",
        operation="PERMUTATIONS",
        state=dsa.SequenceState(list(range(8))),
        config={"enumeration_limit": 5},
    )
    assert len(result.data) == 5 and result.metadata["truncated"] is True
    assert any(m.code == "TRUNCATED" for m in result.messages)


def test_governed_enumeration_work_is_bounded(dsa: ModuleType) -> None:
    result = dsa.DSAFacade().execute(
        structure_type="SEQUENCE",
        capability="ENUMERATION",
        operation="COMBINATION_SUM",
        state=dsa.SequenceState([1]),
        target=100,
        config={"enumeration_max_nodes": 50, "validation_mode": "result"},
    )
    assert result.status is dsa.Status.FAILURE and result.errors[0].code == "CAPACITY_EXCEEDED"


def test_governed_enumeration_deep_input_does_not_overflow_stack(dsa: ModuleType) -> None:
    result = dsa.DSAFacade().execute(
        structure_type="SEQUENCE",
        capability="ENUMERATION",
        operation="COMBINATIONS",
        state=dsa.SequenceState(list(range(3000))),
        k=3000,
    )
    assert len(result.data) == 1 and len(result.data[0]) == 3000


# ------------------------------------------------------------- governed
def test_first_true_finds_smallest_feasible(dsa: ModuleType) -> None:
    capacities = dsa.SequenceState(list(range(1, 101)))
    result = dsa.DSAFacade().execute(
        structure_type="SEQUENCE",
        capability="SEARCH",
        operation="FIRST_TRUE",
        state=capacities,
        predicate=lambda c: c * c >= 50,
    )
    assert capacities.values[result.data] == 8
    none = dsa.DSAFacade().execute(
        structure_type="SEQUENCE",
        capability="SEARCH",
        operation="FIRST_TRUE",
        state=capacities,
        predicate=lambda c: False,
    )
    assert none.status is dsa.Status.NOT_FOUND and none.data == 100


def test_pair_sum_sorted_checks_precondition(dsa: ModuleType) -> None:
    result = dsa.DSAFacade().execute(
        structure_type="SEQUENCE",
        capability="QUERY",
        operation="PAIR_SUM_SORTED",
        state=dsa.SequenceState([3, 1, 2]),
        target=3,
        config={"validation_mode": "result"},
    )
    assert result.status is dsa.Status.FAILURE and result.errors[0].code == "PRECONDITION_FAILED"
