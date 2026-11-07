"""Governed lifecycle, configuration policies and the facade."""

from __future__ import annotations

from collections.abc import Mapping
from types import ModuleType
from typing import Any

import pytest

from .conftest import build_graph


def run(facade: Any, structure: str, capability: str, operation: str, state: Any, **kwargs: Any) -> Any:
    return facade.execute(
        structure_type=structure, capability=capability, operation=operation, state=state, **kwargs
    )


class TestConfiguration:
    def test_precedence(self, dsa: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
        assert dsa.resolve_config("maximum_depth") == -1
        monkeypatch.setenv("DSA_MAXIMUM_DEPTH", "3")
        assert dsa.resolve_config("maximum_depth") == 3
        assert dsa.resolve_config("maximum_depth", config={"maximum_depth": "4"}) == 4
        assert (
            dsa.resolve_config("maximum_depth", config={"maximum_depth": 4}, kwargs={"maximum_depth": 5}) == 5
        )

    def test_scoped_default(self, dsa: ModuleType) -> None:
        assert dsa.resolve_config("track_visited", scope="TreeTraversal") is False
        assert dsa.resolve_config("track_visited", scope="GraphTraversal") is True

    def test_bad_values(self, dsa: ModuleType) -> None:
        with pytest.raises(dsa.ConfigurationError):
            dsa.resolve_config("strict_mode", config={"strict_mode": "maybe"})
        with pytest.raises(dsa.ConfigurationError):
            dsa.resolve_config("maximum_depth", config={"maximum_depth": True})
        with pytest.raises(dsa.ConfigurationError):
            dsa.resolve_config("not_a_key")

    def test_register_conflict(self, dsa: ModuleType) -> None:
        spec = dsa.DSA_CONFIG["capacity"]
        assert dsa.register_config_key(spec) is spec
        clone = dsa.ConfigKey(spec.key, spec.env, 99, spec.cast, spec.group, spec.used_by)
        with pytest.raises(dsa.ConfigurationError):
            dsa.register_config_key(clone)


class TestResults:
    def test_success_and_not_found(self, facade: Any, dsa: ModuleType) -> None:
        state = dsa.SequenceState([10, 20, 30])
        hit = run(facade, "SEQUENCE", "SEARCH", "BINARY", state, target=20)
        assert (hit.status, hit.data, hit.found) == (dsa.Status.SUCCESS, 1, True)
        assert hit.metrics.comparisons > 0 and hit.metrics.elapsed_seconds > 0
        miss = run(facade, "SEQUENCE", "SEARCH", "LINEAR", state, target=99)
        assert (miss.status, miss.found, miss.successful) == (dsa.Status.NOT_FOUND, False, False)
        insertion = run(facade, "SEQUENCE", "SEARCH", "LOWER_BOUND", state, target=25)
        assert (insertion.status, insertion.data) == (dsa.Status.NOT_FOUND, 2)

    def test_failure_codes_in_result_mode(self, facade: Any, dsa: ModuleType) -> None:
        result = run(
            facade,
            "SEQUENCE",
            "SEARCH",
            "BINARY",
            dsa.SequenceState([3, 1, 2]),
            target=2,
            config={"validation_mode": "result"},
        )
        assert result.status is dsa.Status.FAILURE
        assert result.errors[0].code == "PRECONDITION_FAILED"

    def test_required_inputs(self, facade: Any, dsa: ModuleType) -> None:
        with pytest.raises(dsa.InvalidInputError, match="target"):
            run(facade, "SEQUENCE", "SEARCH", "LINEAR", dsa.SequenceState([1]))

    def test_enum_and_case_insensitive_names(self, facade: Any, dsa: ModuleType) -> None:
        result = run(
            facade,
            dsa.StructureType.SEQUENCE,
            dsa.CapabilityName.ORDERING,
            "merge",
            dsa.SequenceState([2, 1]),
        )
        assert result.data == [1, 2]

    def test_track_metrics_off(self, facade: Any, dsa: ModuleType) -> None:
        result = run(
            facade, "SEQUENCE", "ORDERING", "QUICK", dsa.SequenceState([3, 2, 1]), track_metrics=False
        )
        assert result.metrics.comparisons == 0 and result.metrics.elapsed_seconds > 0


class TestPolicies:
    def test_mutate_in_place(self, facade: Any, dsa: ModuleType) -> None:
        state = dsa.SequenceState([3, 1, 2])
        run(facade, "SEQUENCE", "ORDERING", "MERGE", state)
        assert state.values == [3, 1, 2]
        result = run(facade, "SEQUENCE", "ORDERING", "MERGE", state, mutate_in_place=True)
        assert state.values == [1, 2, 3] and result.affected_count == 3

    def test_missing_key_policy(self, facade: Any, dsa: ModuleType) -> None:
        state = dsa.LinkedListState()
        result = run(facade, "LINKED_LIST", "MUTATION", "DELETE", state, node_id="x")
        assert result.status is dsa.Status.NOT_FOUND
        with pytest.raises(dsa.NotFoundError):
            run(facade, "LINKED_LIST", "MUTATION", "DELETE", state, node_id="x", missing_key_policy="raise")

    def test_duplicate_policy(self, facade: Any, dsa: ModuleType) -> None:
        state = dsa.GraphState()
        run(facade, "GRAPH", "MUTATION", "ADD_VERTEX", state, vertex_id="a", value=1)
        with pytest.raises(dsa.DuplicateKeyError):
            run(facade, "GRAPH", "MUTATION", "ADD_VERTEX", state, vertex_id="a", value=2)
        ignored = run(
            facade,
            "GRAPH",
            "MUTATION",
            "ADD_VERTEX",
            state,
            vertex_id="a",
            value=2,
            duplicate_policy="ignore",
        )
        assert ignored.affected_count == 0 and state.values["a"] == 1
        run(
            facade,
            "GRAPH",
            "MUTATION",
            "ADD_VERTEX",
            state,
            vertex_id="a",
            value=3,
            duplicate_policy="replace",
        )
        assert state.values["a"] == 3

    def test_bst_balance_policy(self, facade: Any, dsa: ModuleType) -> None:
        plain, avl = dsa.BSTState(), dsa.BSTState()
        for value in range(64):
            run(facade, "BST", "MUTATION", "INSERT", plain, value=value)
            run(facade, "BST", "MUTATION", "INSERT", avl, value=value, bst_balance_policy="avl")
        assert plain.nodes[plain.root_id].height == 64
        assert avl.nodes[avl.root_id].height <= 7
        lookup = run(facade, "BST", "SEARCH", "LOOKUP", avl, target=10)
        assert lookup.data.value == 10

    def test_copy_on_read(self, facade: Any, dsa: ModuleType) -> None:
        state = dsa.StackState([{"v": 1}])
        copied = run(facade, "STACK", "QUERY", "PEEK", state)
        assert copied.data == {"v": 1} and copied.data is not state.values[-1]
        aliased = run(facade, "STACK", "QUERY", "PEEK", state, copy_on_read=False)
        assert aliased.data is state.values[-1]

    def test_capacity_fallback(self, facade: Any, dsa: ModuleType) -> None:
        state = dsa.QueueState()
        run(facade, "QUEUE", "MUTATION", "ENQUEUE", state, value=1, capacity=1)
        with pytest.raises(dsa.CapacityExceededError):
            run(facade, "QUEUE", "MUTATION", "ENQUEUE", state, value=2, capacity=1)

    def test_traversal_config(self, facade: Any, dsa: ModuleType) -> None:
        state = build_graph(dsa, [("a", "c", 1), ("a", "b", 1), ("b", "d", 1)])
        natural = run(facade, "GRAPH", "TRAVERSAL", "BFS", state, start="a")
        ordered = run(facade, "GRAPH", "TRAVERSAL", "BFS", state, start="a", neighbour_order="sorted")
        limited = run(facade, "GRAPH", "TRAVERSAL", "DFS", state, start="a", maximum_results=2)
        assert natural.data == ["a", "c", "b", "d"]
        assert ordered.data == ["a", "b", "c", "d"]
        assert limited.data == ["a", "c"]

    def test_all_paths_truncation_message(self, facade: Any, dsa: ModuleType) -> None:
        state = build_graph(dsa, [("A", "B", 1), ("A", "C", 1), ("B", "D", 1), ("C", "D", 1)])
        result = run(
            facade, "GRAPH", "PATH", "ALL_SIMPLE_PATHS", state, source="A", target="D", maximum_paths=1
        )
        assert len(result.data) == 1 and result.messages[0].code == "TRUNCATED"

    def test_dijkstra_policy_from_config(self, facade: Any, dsa: ModuleType) -> None:
        state = build_graph(dsa, [("A", "B", 1), ("X", "Y", -1)])
        with pytest.raises(dsa.AlgorithmPreconditionError):
            run(facade, "GRAPH", "PATH", "DIJKSTRA", state, source="A", target="B")
        result = run(
            facade,
            "GRAPH",
            "PATH",
            "DIJKSTRA",
            state,
            source="A",
            target="B",
            config={"dijkstra_negative_weight_policy": "lazy"},
        )
        assert result.data == (1.0, ["A", "B"])


class TestInvariantsAndRollback:
    def test_verify_invariants_rejects_corrupt_input(self, facade: Any, dsa: ModuleType) -> None:
        state = dsa.TreeState(
            values={"a": 1, "b": 2},
            children={"a": ["b"], "b": ["a"]},
            parent={"a": None, "b": "a"},
            root_id="a",
        )
        with pytest.raises(dsa.InvariantViolationError):
            run(facade, "TREE", "TRAVERSAL", "DFS", state, verify_invariants=True, track_visited=False)

    def test_rollback_of_non_atomic_extension(self, dsa: ModuleType) -> None:
        class Faulty(dsa.MutationService):
            @dsa.operation(
                dsa.describe(
                    "APPEND_TWICE_THEN_FAIL",
                    "MUTATION",
                    "SEQUENCE",
                    "O(1)",
                    "O(1)",
                    mutates=True,
                    atomic=False,
                )
            )
            def _faulty(self, ctx: Any, args: Mapping[str, Any]) -> None:
                ctx.state.values.append(1)
                ctx.state.values.append(2)
                raise RuntimeError("boom")

        state = dsa.SequenceState([0])
        result = Faulty().execute(
            operation="APPEND_TWICE_THEN_FAIL",
            structure_type="SEQUENCE",
            state=state,
            config={"validation_mode": "result"},
        )
        assert state.values == [0]
        assert result.errors[0].code == "EXECUTION_FAILED"
        assert result.messages[0].code == "ROLLED_BACK"


class TestHooks:
    def test_lifecycle_order(self, dsa: ModuleType) -> None:
        calls: list[str] = []

        class Traced(dsa.OrderingService):
            def _validate_preconditions(self, context: Any, **kwargs: Any) -> None:
                calls.append("pre")
                super()._validate_preconditions(context, **kwargs)

            def _before_execute(self, context: Any, **kwargs: Any) -> None:
                calls.append("before")

            def _validate_postconditions(self, context: Any, data: Any, **kwargs: Any) -> None:
                calls.append("post")

            def _after_execute(self, context: Any, data: Any, **kwargs: Any) -> None:
                calls.append("after")

        Traced().execute(operation="MERGE", structure_type="SEQUENCE", state=dsa.SequenceState([1]))
        assert calls == ["pre", "before", "post", "after"]
