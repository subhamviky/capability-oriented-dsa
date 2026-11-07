"""Request-scoped identifiers: correlation_id, tenant_id and idempotency_key."""

from __future__ import annotations

from types import ModuleType
from typing import Any

import pytest


def graph_call(dsa: ModuleType, facade: Any, state: Any, vertex: str, **extra: Any) -> Any:
    extra.setdefault("config", {"validation_mode": "result"})
    return facade.execute(
        structure_type="GRAPH",
        capability="MUTATION",
        operation="ADD_VERTEX",
        state=state,
        vertex_id=vertex,
        value=vertex,
        **extra,
    )


def test_no_identifiers_leaves_results_unchanged(dsa: ModuleType) -> None:
    result = graph_call(dsa, dsa.DSAFacade(), dsa.GraphState(), "A")
    assert "propagation" not in result.metadata
    assert "replayed" not in result.metadata


def test_identifiers_are_echoed_on_success_and_failure(dsa: ModuleType) -> None:
    facade, state = dsa.DSAFacade(), dsa.GraphState()
    ok = graph_call(dsa, facade, state, "A", correlation_id="req-1", tenant_id="t1")
    assert ok.metadata["propagation"] == {"correlation_id": "req-1", "tenant_id": "t1"}
    duplicate = graph_call(dsa, facade, state, "A", correlation_id="req-2", tenant_id="t1")
    assert duplicate.status.value == "FAILURE"
    assert duplicate.metadata["propagation"]["correlation_id"] == "req-2"


def test_identifiers_are_echoed_on_routing_failure(dsa: ModuleType) -> None:
    result = dsa.DSAFacade().execute(
        structure_type="GRAPH",
        capability="NOPE",
        operation="X",
        state=dsa.GraphState(),
        correlation_id="req-9",
        config={"validation_mode": "result"},
    )
    assert result.errors[0].code == "UNSUPPORTED_OPERATION"
    assert result.metadata["propagation"] == {"correlation_id": "req-9"}


@pytest.mark.parametrize("field", ["correlation_id", "tenant_id", "idempotency_key"])
@pytest.mark.parametrize("bad", ["", "   "])
def test_blank_identifiers_are_rejected(dsa: ModuleType, field: str, bad: str) -> None:
    result = graph_call(dsa, dsa.DSAFacade(), dsa.GraphState(), "A", **{field: bad})
    assert result.status.value == "FAILURE"
    assert result.errors[0].code == "INVALID_INPUT"


def test_key_on_read_only_operation_is_only_echoed(dsa: ModuleType) -> None:
    facade = dsa.DSAFacade()
    for _ in range(2):
        result = facade.execute(
            structure_type="SEQUENCE",
            capability="SEARCH",
            operation="LINEAR",
            state=dsa.SequenceState([1, 2, 3]),
            target=2,
            idempotency_key="k",
        )
        assert result.data == 1
        assert result.metadata["propagation"] == {"idempotency_key": "k"}
        assert "replayed" not in result.metadata
    assert len(facade.idempotency_store) == 0


def test_keyed_mutation_is_applied_once(dsa: ModuleType) -> None:
    facade, state = dsa.DSAFacade(), dsa.GraphState()
    first = graph_call(dsa, facade, state, "A", idempotency_key="k1", correlation_id="try-1")
    again = graph_call(dsa, facade, state, "A", idempotency_key="k1", correlation_id="try-2")
    assert first.status.value == again.status.value == "SUCCESS"  # not DUPLICATE_KEY
    assert "replayed" not in first.metadata
    assert again.metadata["replayed"] is True
    assert again.metadata["propagation"]["correlation_id"] == "try-2"
    assert [m.code for m in again.messages][-1] == "IDEMPOTENT_REPLAY"
    assert [m.code for m in first.messages] == [m.code for m in again.messages[:-1]]
    assert list(state.values) == ["A"]


def test_same_key_with_different_arguments_conflicts(dsa: ModuleType) -> None:
    facade, state = dsa.DSAFacade(), dsa.GraphState()
    graph_call(dsa, facade, state, "A", idempotency_key="k1")
    clash = graph_call(dsa, facade, state, "B", idempotency_key="k1")
    assert clash.status.value == "FAILURE"
    assert clash.errors[0].code == "IDEMPOTENCY_CONFLICT"
    assert list(state.values) == ["A"]


def test_same_key_on_a_different_state_conflicts(dsa: ModuleType) -> None:
    facade = dsa.DSAFacade()
    graph_call(dsa, facade, dsa.GraphState(), "A", idempotency_key="k1")
    other = dsa.GraphState()
    clash = graph_call(dsa, facade, other, "A", idempotency_key="k1")
    assert clash.errors[0].code == "IDEMPOTENCY_CONFLICT"
    assert not other.values


def test_conflict_raises_by_default(dsa: ModuleType) -> None:
    facade, state = dsa.DSAFacade(), dsa.GraphState()
    kwargs = {"structure_type": "GRAPH", "capability": "MUTATION", "operation": "ADD_VERTEX", "state": state}
    facade.execute(vertex_id="A", value="A", idempotency_key="k1", **kwargs)
    with pytest.raises(dsa.IdempotencyConflictError):
        facade.execute(vertex_id="B", value="B", idempotency_key="k1", **kwargs)


def test_tenant_namespaces_the_key(dsa: ModuleType) -> None:
    facade, state = dsa.DSAFacade(), dsa.GraphState()
    one = graph_call(dsa, facade, state, "A", idempotency_key="k", tenant_id="t1")
    two = graph_call(dsa, facade, state, "B", idempotency_key="k", tenant_id="t2")
    assert one.status.value == two.status.value == "SUCCESS"
    assert list(state.values) == ["A", "B"]


def test_failed_attempt_is_not_recorded_and_can_be_retried(dsa: ModuleType) -> None:
    facade, state = dsa.DSAFacade(), dsa.QueueState(capacity=1)
    state.values.append("occupied")

    def enqueue() -> Any:
        return facade.execute(
            structure_type="QUEUE",
            capability="MUTATION",
            operation="ENQUEUE",
            state=state,
            value="job",
            idempotency_key="job-1",
            config={"validation_mode": "result"},
        )

    assert enqueue().errors[0].code == "CAPACITY_EXCEEDED"
    state.values.clear()
    retry = enqueue()
    assert retry.status.value == "SUCCESS"
    assert "replayed" not in retry.metadata
    assert list(state.values) == ["job"]


def test_store_is_bounded_and_evicts_the_oldest(dsa: ModuleType) -> None:
    store = dsa.InMemoryIdempotencyStore()
    facade, state = dsa.DSAFacade(idempotency_store=store), dsa.GraphState()
    for index, vertex in enumerate("ABC"):
        result = graph_call(
            dsa,
            facade,
            state,
            vertex,
            idempotency_key=f"k{index}",
            config={"idempotency_max_entries": 2, "validation_mode": "result"},
        )
        assert result.status.value == "SUCCESS"
    assert len(store) == 2
    assert store.get((None, "k0")) is None
    assert store.get((None, "k2")) is not None


def test_invalid_store_size_is_rejected_before_mutating(dsa: ModuleType) -> None:
    facade, state = dsa.DSAFacade(), dsa.GraphState()
    result = facade.execute(
        structure_type="GRAPH",
        capability="MUTATION",
        operation="ADD_VERTEX",
        state=state,
        vertex_id="A",
        value="A",
        idempotency_key="k",
        config={"idempotency_max_entries": 0, "validation_mode": "result"},
    )
    assert result.errors[0].code == "INVALID_CONFIGURATION"
    assert not state.values


def test_service_without_a_store_refuses_a_keyed_mutation(dsa: ModuleType) -> None:
    result = dsa.MutationService().execute(
        operation="ADD_VERTEX",
        structure_type="GRAPH",
        state=dsa.GraphState(),
        vertex_id="A",
        value="A",
        idempotency_key="k",
        config={"validation_mode": "result"},
    )
    assert result.errors[0].code == "INVALID_CONFIGURATION"
