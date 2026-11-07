"""Hardening: deep inputs, malformed structures, policy enforcement and edge cases."""

from __future__ import annotations

from types import ModuleType

import pytest

from .conftest import build_chain_tree, build_graph

DEEP = 3000  # comfortably above CPython's default recursion limit of 1000


def test_all_does_not_leak_stdlib_names(dsa: ModuleType) -> None:
    leaked = {"os", "copy", "heapq", "time", "uuid", "deque", "dataclass", "Any"} & set(dsa.__all__)
    assert not leaked


def test_linked_list_validator_detects_wrong_tail(dsa: ModuleType) -> None:
    state = dsa.LinkedListState()
    repo = dsa.LinkedListRepository()
    for node_id in "abc":
        repo.append(state, node_id, node_id=node_id)
    state.tail_id = "b"
    report = dsa.LinkedListValidator().validate(state)
    assert not report.valid
    assert any("tail_id" in v for v in report.violations)


def test_plain_bst_insert_maintains_heights(dsa: ModuleType) -> None:
    state = dsa.BSTState()
    for value in (2, 1, 3):
        dsa.BSTAlgorithms.insert(state, value)
    assert dsa.BSTAlgorithms.is_avl_balanced(state)
    assert dsa.BSTValidator().validate(state).valid


@pytest.mark.parametrize("operation", ["height", "delete_subtree"])
def test_deep_tree_operations_are_iterative(dsa: ModuleType, operation: str) -> None:
    state = build_chain_tree(dsa, DEEP)
    if operation == "height":
        assert dsa.TreeAlgorithms.height(state) == DEEP
    else:
        assert len(dsa.TreeRepository().delete_subtree(state, "0")) == DEEP


def test_deep_bst_inorder_is_iterative(dsa: ModuleType) -> None:
    state = dsa.BSTState()
    for value in range(DEEP):  # sorted input: an unbalanced BST degenerates to a list
        dsa.BSTAlgorithms.insert(state, value)
    assert dsa.BSTAlgorithms.inorder(state) == list(range(DEEP))


def test_graph_cycle_detection_is_iterative(dsa: ModuleType) -> None:
    edges = [(f"{i:05d}", f"{i + 1:05d}", 1.0) for i in range(DEEP)]
    assert dsa.GraphAlgorithms.has_cycle(build_graph(dsa, edges)) is False
    assert dsa.GraphAlgorithms.has_cycle(build_graph(dsa, edges + [(f"{DEEP:05d}", "00000", 1.0)]))


def test_stable_sort_required_rejects_quick(facade: object, dsa: ModuleType) -> None:
    with pytest.raises(dsa.AlgorithmPreconditionError):
        facade.execute(
            structure_type="SEQUENCE",
            capability="ORDERING",
            operation="QUICK",
            state=dsa.SequenceState([3, 1, 2]),
            stable_sort_required=True,
        )


def test_binary_search_precondition_is_linear_and_optional(facade: object, dsa: ModuleType) -> None:
    """Strict mode verifies sortedness in one O(n) pass; trusted mode stays O(log n)."""
    calls = 0

    def key(value: int) -> int:
        nonlocal calls
        calls += 1
        return value

    values = list(range(4096))
    for strict, budget in ((True, 4096 + 13), (False, 13)):  # n + log2(n) + 1, then log2(n) + 1
        calls = 0
        facade.execute(
            structure_type="SEQUENCE",
            capability="SEARCH",
            operation="BINARY",
            state=dsa.SequenceState(values),
            target=5,
            key=key,
            strict_mode=strict,
        )
        assert calls <= budget


def test_config_values_are_cast_and_checked(dsa: ModuleType) -> None:
    assert dsa.resolve_config("mutate_in_place", config={"mutate_in_place": "false"}) is False
    with pytest.raises(dsa.ConfigurationError):
        dsa.resolve_config("validation_mode", config={"validation_mode": "silent"})


def test_unknown_config_key_rejected_in_strict_mode(facade: object, dsa: ModuleType) -> None:
    with pytest.raises(dsa.ConfigurationError):
        facade.execute(
            structure_type="SEQUENCE",
            capability="ORDERING",
            operation="MERGE",
            state=dsa.SequenceState([2, 1]),
            config={"mutate_inplace": True},
        )


def test_undirected_mismatch_reported_once(dsa: ModuleType) -> None:
    state = dsa.GraphState(values={"a": 1, "b": 1}, adjacency={"a": {"b": 1}, "b": {"a": 2}})
    assert len(dsa.GraphValidator().validate(state).violations) == 1


def test_every_routable_operation_has_a_descriptor(facade: object) -> None:
    for key in facade.capabilities():
        assert facade.describe(*key).name == key[2]


def test_wrong_state_type_is_a_contract_error(dsa: ModuleType) -> None:
    result = dsa.TraversalService().execute(
        operation="BFS",
        structure_type="GRAPH",
        state=dsa.SequenceState([1]),
        config={"validation_mode": "result"},
    )
    assert result.errors[0].code == "INVALID_INPUT"
    assert "GraphState" in result.errors[0].message


@pytest.mark.parametrize("tokens", [["1", "0", "+"], ["5", "0", "-"], ["2", "0", "*"]])
def test_postfix_zero_operand_is_not_a_division(dsa: ModuleType, tokens: list[str]) -> None:
    assert dsa.StackAlgorithms.evaluate_postfix(tokens) == {"+": 1.0, "-": 5.0, "*": 0.0}[tokens[2]]


def test_postfix_division_by_zero_is_a_framework_error(dsa: ModuleType) -> None:
    with pytest.raises(dsa.InvalidInputError):
        dsa.StackAlgorithms.evaluate_postfix(["1", "0", "/"])


def test_found_is_not_taken_from_caller_kwargs(facade: object, dsa: ModuleType) -> None:
    result = facade.execute(
        structure_type="SEQUENCE",
        capability="ORDERING",
        operation="MERGE",
        state=dsa.SequenceState([2, 1]),
        found=True,
    )
    assert result.found is None


def test_falsy_start_node_is_respected(facade: object, dsa: ModuleType) -> None:
    state = dsa.GraphState(directed=True)
    repo = dsa.GraphRepository()
    for vertex in ("a", "", "z"):  # "" is not the first vertex, so a fallback would start at "a"
        repo.add_vertex(state, vertex, vertex)
    repo.add_edge(state, "", "z")
    result = facade.execute(
        structure_type="GRAPH", capability="TRAVERSAL", operation="BFS", state=state, start=""
    )
    assert result.data == ["", "z"]


def test_routing_failure_honours_result_mode(facade: object, dsa: ModuleType) -> None:
    result = facade.execute(
        structure_type="SEQUENCE",
        capability="SEARCH",
        operation="TELEPORT",
        state=dsa.SequenceState([]),
        config={"validation_mode": "result"},
    )
    assert result.status is dsa.Status.FAILURE
    assert result.errors[0].code == "UNSUPPORTED_OPERATION"


def test_unbounded_graph_walk_without_visited_tracking_is_refused(facade: object, dsa: ModuleType) -> None:
    state = build_graph(dsa, [("a", "b", 1.0)], directed=False)
    with pytest.raises(dsa.AlgorithmPreconditionError):
        facade.execute(
            structure_type="GRAPH", capability="TRAVERSAL", operation="BFS", state=state, track_visited=False
        )
    bounded = facade.execute(
        structure_type="GRAPH",
        capability="TRAVERSAL",
        operation="BFS",
        state=state,
        track_visited=False,
        maximum_depth=2,
    )
    assert bounded.data == ["a", "b", "a"]
