"""Results, messages, errors, metrics and the request-scoped execution context."""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

from .errors import error_code

T = TypeVar("T")


class Status(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL = "PARTIAL"
    NOT_FOUND = "NOT_FOUND"


@dataclass(slots=True)
class Message:
    level: str
    code: str
    text: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ErrorDetail:
    code: str
    message: str
    error_type: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MetricsState:
    comparisons: int = 0
    reads: int = 0
    writes: int = 0
    swaps: int = 0
    iterations: int = 0
    nodes_visited: int = 0
    edges_examined: int = 0
    queue_operations: int = 0
    stack_operations: int = 0
    recursion_depth: int = 0
    max_recursion_depth: int = 0
    elapsed_seconds: float = 0.0


@dataclass(slots=True)
class OperationResult(Generic[T]):
    status: Status
    operation: str
    data: T | None = None
    affected_count: int = 0
    found: bool | None = None
    messages: list[Message] = field(default_factory=list)
    errors: list[ErrorDetail] = field(default_factory=list)
    metrics: MetricsState = field(default_factory=MetricsState)
    metadata: dict[str, Any] = field(default_factory=dict)
    complete: bool = True
    """False when a bound (enumeration_limit, max_nodes, ...) cut the work short: the data is a
    correct partial answer, not proof that nothing else exists (v0.3, S-2)."""

    @property
    def successful(self) -> bool:
        """True for SUCCESS and PARTIAL. NOT_FOUND is a valid, unsuccessful outcome."""
        return self.status in {Status.SUCCESS, Status.PARTIAL}


@dataclass(slots=True)
class ValidationReport:
    valid: bool
    violations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DSAExecutionContext:
    operation_id: str
    structure_type: str
    capability: str
    operation: str
    state: Any
    config: Mapping[str, Any]
    messages: list[Message] = field(default_factory=list)
    errors: list[ErrorDetail] = field(default_factory=list)
    metrics: MetricsState = field(default_factory=MetricsState)
    metadata: dict[str, Any] = field(default_factory=dict)
    affected_count: int = 0
    #: Set by handlers: False turns a success into a NOT_FOUND result.
    found: bool | None = None
    #: Request-scoped identifiers supplied by the caller and passed through unchanged.
    correlation_id: str | None = None
    tenant_id: str | None = None
    idempotency_key: str | None = None

    def info(self, code: str, text: str, **context: Any) -> None:
        self.messages.append(Message("INFO", code, text, dict(context)))

    def warn(self, code: str, text: str, **context: Any) -> None:
        self.messages.append(Message("WARNING", code, text, dict(context)))


def propagation_metadata(
    correlation_id: str | None, tenant_id: str | None, idempotency_key: str | None
) -> dict[str, str]:
    """The identifiers the caller supplied, or an empty dict when there are none."""
    supplied = {
        "correlation_id": correlation_id,
        "tenant_id": tenant_id,
        "idempotency_key": idempotency_key,
    }
    return {name: value for name, value in supplied.items() if value is not None}


class ResultBuilder:
    @staticmethod
    def _envelope(context: DSAExecutionContext | None) -> dict[str, Any]:
        if context is None:
            return {"messages": [], "errors": [], "metrics": MetricsState(), "metadata": {}}
        return {
            "messages": context.messages,
            "errors": list(context.errors),
            "metrics": context.metrics,
            "metadata": context.metadata,
            "complete": not (context.metadata.get("truncated") or context.metadata.get("incomplete")),
        }

    @staticmethod
    def success(
        operation: str,
        data: Any = None,
        affected_count: int = 0,
        found: bool | None = None,
        context: DSAExecutionContext | None = None,
    ) -> OperationResult[Any]:
        return OperationResult(
            Status.SUCCESS, operation, data, affected_count, found, **ResultBuilder._envelope(context)
        )

    @staticmethod
    def partial(
        operation: str, data: Any = None, affected_count: int = 0, context: DSAExecutionContext | None = None
    ) -> OperationResult[Any]:
        return OperationResult(
            Status.PARTIAL, operation, data, affected_count, None, **ResultBuilder._envelope(context)
        )

    @staticmethod
    def not_found(
        operation: str, context: DSAExecutionContext | None = None, data: Any = None
    ) -> OperationResult[Any]:
        return OperationResult(
            Status.NOT_FOUND, operation, data, 0, False, **ResultBuilder._envelope(context)
        )

    @staticmethod
    def failure(
        operation: str, error: BaseException, context: DSAExecutionContext | None = None
    ) -> OperationResult[Any]:
        envelope = ResultBuilder._envelope(context)
        envelope["errors"].append(ErrorDetail(error_code(error), str(error), type(error).__name__))
        return OperationResult(Status.FAILURE, operation, **envelope)


class MetricsUtility:
    @staticmethod
    def start_timer() -> float:
        return time.perf_counter()

    @staticmethod
    def stop_timer(metrics: MetricsState, started: float) -> None:
        metrics.elapsed_seconds += time.perf_counter() - started

    @staticmethod
    def record(metrics: MetricsState, field_name: str, count: int = 1) -> None:
        setattr(metrics, field_name, getattr(metrics, field_name) + count)
