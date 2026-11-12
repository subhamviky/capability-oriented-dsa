"""v0.3 (wave C note C-03): the complete flag, SUBSET_SUM, ADD_ALL / GROUP_BY_KEYS and
Decimal values with a declared scale. Property tests compare with brute force."""

from __future__ import annotations

import itertools
import time
from decimal import Decimal
from types import ModuleType
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import capability_oriented_dsa as dsa_package

D = dsa_package.DSAFacade()


def subset_sum(values: list[Any], target: Any, **kw: Any) -> Any:
    return D.execute(
        structure_type="SEQUENCE",
        capability="OPTIMIZATION",
        operation="SUBSET_SUM",
        state=dsa_package.SequenceState(values),
        target=target,
        **kw,
    )


def brute_force(values: list[int], target: int) -> tuple[int, ...] | None:
    for size in range(len(values) + 1):
        for combo in itertools.combinations(range(len(values)), size):
            if sum(values[i] for i in combo) == target:
                return combo  # combinations come in lexicographic order
    return None


@settings(max_examples=150, deadline=None)
@given(st.lists(st.integers(0, 40), max_size=9), st.integers(0, 120))
def test_subset_sum_matches_brute_force(values: list[int], target: int) -> None:
    result = subset_sum(values, target)
    expected = brute_force(values, target)
    assert result.complete
    assert (result.data if result.found else None) == expected
    if expected is not None:
        assert len(set(result.data)) == len(result.data)  # no element reused


def test_subset_sum_prefers_the_smallest_then_the_oldest() -> None:
    assert subset_sum([5, 4, 1, 9], 9).data == (3,)  # one item beats two
    assert subset_sum([1, 8, 2, 7], 9).data == (0, 1)  # ties: lowest indices


def test_a_bounded_search_says_it_is_incomplete(dsa: ModuleType) -> None:
    values = list(range(2, 52, 2))  # 25 even values: an odd target is unreachable
    result = dsa.DSAFacade().execute(
        structure_type="SEQUENCE",
        capability="OPTIMIZATION",
        operation="SUBSET_SUM",
        state=dsa.SequenceState(values),
        target=301,
        max_nodes=50,
    )
    assert result.complete is False and result.found is False
    assert any(m.code == "INCOMPLETE" for m in result.messages)


def test_truncated_enumeration_is_not_complete(dsa: ModuleType) -> None:
    result = dsa.DSAFacade().execute(
        structure_type="SEQUENCE",
        capability="ENUMERATION",
        operation="SUBSETS",
        state=dsa.SequenceState([1, 2, 3, 4]),
        enumeration_limit=3,
    )
    assert result.complete is False and result.metadata["truncated"]
    full = dsa.DSAFacade().execute(
        structure_type="SEQUENCE",
        capability="ENUMERATION",
        operation="SUBSETS",
        state=dsa.SequenceState([1, 2]),
    )
    assert full.complete is True


def test_money_as_decimal_with_a_scale() -> None:
    amounts = [Decimal("10.10"), Decimal("0.15"), Decimal("4.75"), Decimal("5.35")]
    assert subset_sum(amounts, Decimal("10.10"), scale=2).data == (0,)
    assert subset_sum(amounts, Decimal("5.50"), scale=2).data == (1, 3)
    with pytest.raises(dsa_package.InvalidInputError, match="fraction digits"):  # refused, never rounded
        subset_sum([Decimal("1.005")], Decimal("1.00"), scale=2)
    with pytest.raises(dsa_package.InvalidInputError, match="scale"):
        subset_sum([Decimal("1.50")], Decimal("1.50"))
    best = D.execute(
        structure_type="SEQUENCE",
        capability="OPTIMIZATION",
        operation="KNAPSACK_01",
        state=dsa_package.SequenceState(
            [(Decimal("1.50"), Decimal("1.50")), (Decimal("2.25"), Decimal("2.25"))]
        ),
        capacity=Decimal("3.00"),
        scale=2,
    )
    assert best.data == Decimal("2.25")


def pairwise_groups(items: list[tuple[int, set[str]]]) -> set[frozenset[int]]:
    uf = dsa_package.UnionFindState()
    for i, _ in items:
        dsa_package.UnionFindAlgorithms.make_set(uf, i)
    for (i, a), (j, b) in itertools.combinations(items, 2):
        if a & b:
            dsa_package.UnionFindAlgorithms.union(uf, i, j)
    groups: dict[Any, set[int]] = {}
    for i, _ in items:
        groups.setdefault(dsa_package.UnionFindAlgorithms.find(uf, i), set()).add(i)
    return {frozenset(g) for g in groups.values()}


@settings(max_examples=100, deadline=None)
@given(st.lists(st.sets(st.sampled_from("abcdefgh"), max_size=3), max_size=12))
def test_group_by_keys_equals_pairwise_unions(key_sets: list[set[str]]) -> None:
    items = list(enumerate(key_sets))
    result = D.execute(
        structure_type="UNION_FIND",
        capability="MUTATION",
        operation="GROUP_BY_KEYS",
        state=dsa_package.UnionFindState(),
        elements=items,
        keys=lambda item: sorted(item[1]),
        element_id=lambda item: item[0],
    )
    assert {frozenset(i for i, _ in g) for g in result.data} == pairwise_groups(items)


def test_group_by_keys_is_linear() -> None:
    n = 20000
    items = [(i, f"txn-{i // 2}", f"ref-{i % 997}") for i in range(n)]
    started = time.perf_counter()
    result = D.execute(
        structure_type="UNION_FIND",
        capability="MUTATION",
        operation="GROUP_BY_KEYS",
        state=dsa_package.UnionFindState(),
        elements=items,
        keys=lambda e: [("txn", e[1])],
        element_id=lambda e: e[0],
    )
    assert len(result.data) == n // 2
    assert time.perf_counter() - started < 5  # pairwise would be 2e8 comparisons


def test_add_all(dsa: ModuleType) -> None:
    state = dsa.UnionFindState()
    result = dsa.DSAFacade().execute(
        structure_type="UNION_FIND",
        capability="MUTATION",
        operation="ADD_ALL",
        state=state,
        elements=["a", "b", "a"],
    )
    assert result.data == 2 and state.components == 2
