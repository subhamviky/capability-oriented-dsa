"""Capability-Oriented DSA - portable single-file edition.

GENERATED FILE - DO NOT EDIT. Source of truth: src/capability_oriented_dsa/.
Regenerate with: python tools/build_standalone.py

Copy this file into another codebase to use the framework without installing
the package. Keep the licence notice, record the version below, and do not
import this module and the installed package in the same process (their
classes and configuration registries would be distinct objects).

SPDX-License-Identifier: MIT
"""
from __future__ import annotations

import copy
import heapq
import math
import operator
import os
import threading
import time
import uuid
from collections import OrderedDict, deque
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from itertools import pairwise, starmap
from types import MappingProxyType
from typing import Any, ClassVar, Generic, Protocol, TypeVar, runtime_checkable

__version__ = '0.1.0'


# ============================================================================
# core/errors.py
# ============================================================================
class DSAError(Exception):
    """Base framework exception."""

    code: ClassVar[str] = "DSA_ERROR"


class InvalidInputError(DSAError):
    """Caller supplied missing, malformed, or out-of-range input."""

    code = "INVALID_INPUT"


class NotFoundError(InvalidInputError):
    """A referenced key, node, vertex, or edge does not exist.

    Subclasses ``InvalidInputError`` so existing ``except InvalidInputError``
    sites keep working. Governed execution maps it according to
    ``missing_key_policy``.
    """

    code = "NOT_FOUND"


class DuplicateKeyError(InvalidInputError):
    """A key or identifier already exists and ``duplicate_policy`` is ``reject``."""

    code = "DUPLICATE_KEY"


class IdempotencyConflictError(InvalidInputError):
    """An idempotency key was reused for a different request."""

    code = "IDEMPOTENCY_CONFLICT"


class InvariantViolationError(DSAError):
    """A structural invariant does not hold."""

    code = "INVARIANT_VIOLATION"


class UnsupportedOperationError(DSAError):
    """No capability is registered for the requested combination."""

    code = "UNSUPPORTED_OPERATION"


class CapacityExceededError(DSAError):
    """A bounded container is full."""

    code = "CAPACITY_EXCEEDED"


class AlgorithmPreconditionError(DSAError):
    """An algorithm-specific precondition does not hold."""

    code = "PRECONDITION_FAILED"


class ConfigurationError(DSAError):
    """A configuration key is unknown or a value is outside its allowed set."""

    code = "INVALID_CONFIGURATION"


def error_code(error: BaseException) -> str:
    """Return the stable error code for any exception."""
    return error.code if isinstance(error, DSAError) else "EXECUTION_FAILED"


# ============================================================================
# core/config.py
# ============================================================================
UNSET: Any = object()


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    raise ConfigurationError(f"cannot interpret {value!r} as a boolean")


def _to_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ConfigurationError(f"expected an integer, got {value!r}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"expected an integer, got {value!r}") from exc


def _to_str(value: Any) -> str:
    return str(value).strip().lower()


@dataclass(frozen=True, slots=True)
class ConfigKey:
    key: str
    env: str | None
    default: Any
    cast: Callable[[Any], Any]
    group: str
    used_by: str
    scoped_defaults: Mapping[str, Any] = field(default_factory=dict)
    choices: frozenset[Any] | None = None
    description: str = ""

    def coerce(self, value: Any) -> Any:
        result = self.cast(value)
        if self.choices is not None and result not in self.choices:
            raise ConfigurationError(f"{self.key}={result!r} is not one of {sorted(self.choices)}")
        return result


def _ck(
    key: str,
    default: Any,
    cast: Callable[[Any], Any],
    group: str,
    used_by: str,
    description: str,
    *,
    choices: Iterable[Any] | None = None,
    scoped: Mapping[str, Any] | None = None,
) -> ConfigKey:
    return ConfigKey(
        key,
        f"DSA_{key.upper()}",
        default,
        cast,
        group,
        used_by,
        dict(scoped or {}),
        frozenset(choices) if choices else None,
        description,
    )


DSA_CONFIG: dict[str, ConfigKey] = {
    c.key: c
    for c in [
        _ck(
            "strict_mode",
            True,
            _to_bool,
            "Common",
            "all capabilities",
            "Reject unknown config keys and verify cheap-to-moderate preconditions "
            "(e.g. O(n) sortedness check before governed binary search).",
        ),
        _ck(
            "validation_mode",
            "raise",
            _to_str,
            "Common",
            "all capabilities",
            "'raise' re-raises failures; 'result' returns a FAILURE OperationResult.",
            choices={"raise", "result"},
        ),
        _ck(
            "track_metrics",
            True,
            _to_bool,
            "Common",
            "all capabilities",
            "Record operation counters in OperationResult.metrics. Elapsed time is always recorded.",
        ),
        _ck(
            "verify_invariants",
            False,
            _to_bool,
            "Common",
            "mutation, traversal, analysis",
            "Run the full structural validator before reads and after mutations. O(n) per call.",
        ),
        _ck(
            "mutate_in_place",
            False,
            _to_bool,
            "Mutation",
            "ORDERING",
            "Write the sorted output back into SequenceState.values.",
        ),
        _ck(
            "idempotency_max_entries",
            1024,
            _to_int,
            "Mutation",
            "MUTATION with an idempotency_key",
            "Recorded idempotent results kept per store; the oldest is evicted beyond this. Must be >= 1.",
        ),
        _ck(
            "copy_on_read",
            True,
            _to_bool,
            "Mutation",
            "operations returning internal references",
            "Deep-copy nodes/values that alias internal state before returning them.",
        ),
        _ck(
            "rollback_on_failure",
            True,
            _to_bool,
            "Mutation",
            "MUTATION",
            "Restore the pre-operation state when a non-atomic mutation fails.",
        ),
        _ck(
            "duplicate_policy",
            "reject",
            _to_str,
            "Mutation",
            "MUTATION insert/add operations",
            "'reject' raises DuplicateKeyError; 'ignore' leaves state unchanged; "
            "'replace' overwrites the stored value.",
            choices={"reject", "ignore", "replace"},
        ),
        _ck(
            "missing_key_policy",
            "result",
            _to_str,
            "Mutation",
            "lookups and deletes",
            "'result' returns NOT_FOUND; 'raise' treats a missing key as a failure.",
            choices={"result", "raise"},
        ),
        _ck(
            "track_visited",
            True,
            _to_bool,
            "Traversal",
            "TRAVERSAL",
            "Skip already-visited nodes. Disabling it on a graph requires maximum_depth >= 0.",
            scoped={"TreeTraversal": False, "GraphTraversal": True},
        ),
        _ck(
            "neighbour_order",
            "natural",
            _to_str,
            "Traversal",
            "TRAVERSAL",
            "Order in which neighbours are expanded.",
            choices={"natural", "sorted", "reversed"},
        ),
        _ck(
            "maximum_depth",
            -1,
            _to_int,
            "Traversal",
            "TRAVERSAL",
            "Stop expanding below this depth; -1 means unbounded.",
        ),
        _ck(
            "maximum_results",
            -1,
            _to_int,
            "Traversal",
            "TRAVERSAL, autocomplete",
            "Stop after emitting this many results; -1 means unbounded.",
        ),
        _ck(
            "maximum_paths",
            1000,
            _to_int,
            "Path",
            "PATH ALL_SIMPLE_PATHS",
            "Upper bound on enumerated paths; enumeration is exponential in the worst case.",
        ),
        _ck(
            "capacity",
            -1,
            _to_int,
            "Container",
            "STACK/QUEUE MUTATION",
            "Fallback bound applied when the container state's own capacity is -1.",
        ),
        _ck(
            "stable_sort_required",
            False,
            _to_bool,
            "Ordering",
            "ORDERING",
            "Reject sort algorithms whose descriptor is not stable.",
        ),
        _ck(
            "dijkstra_negative_weight_policy",
            "eager",
            _to_str,
            "Path",
            "PATH DIJKSTRA",
            "'eager' scans all edges first; 'lazy' checks inspected edges and disables early exit; "
            "'assume_non_negative' skips checks.",
            choices={"eager", "lazy", "assume_non_negative"},
        ),
        _ck(
            "bst_balance_policy",
            "unbalanced",
            _to_str,
            "Tree",
            "BST MUTATION",
            "'avl' rebalances after insert/delete; 'unbalanced' does not.",
            choices={"unbalanced", "avl"},
        ),
    ]
}


def register_config_key(spec: ConfigKey) -> ConfigKey:
    """Register an extension key. Re-registering an identical spec is a no-op."""
    existing = DSA_CONFIG.get(spec.key)
    if existing is not None and existing != spec:
        raise ConfigurationError(f"config key {spec.key!r} is already registered differently")
    DSA_CONFIG[spec.key] = spec
    return spec


def resolve_config(
    key: str,
    config: Mapping[str, Any] | None = None,
    kwargs: Mapping[str, Any] | None = None,
    scope: str | None = None,
) -> Any:
    """Resolve kwargs > config > environment variable > scoped default > default."""
    spec = DSA_CONFIG.get(key)
    if spec is None:
        raise ConfigurationError(f"Unregistered DSA config key: {key}")
    for source in (kwargs, config):
        if source is not None and key in source and source[key] is not UNSET:
            return spec.coerce(source[key])
    if spec.env and (raw := os.getenv(spec.env)) is not None:
        return spec.coerce(raw)
    if scope and scope in spec.scoped_defaults:
        return spec.scoped_defaults[scope]
    return spec.default


def unknown_config_keys(config: Mapping[str, Any] | None) -> list[str]:
    return sorted(k for k in (config or {}) if k not in DSA_CONFIG)


# ============================================================================
# core/results.py
# ============================================================================
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


# ============================================================================
# core/idempotency.py
# ============================================================================
#: ``(tenant_id, idempotency_key)``; the tenant namespaces the key.
IdempotencyScope = tuple[str | None, str]


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    """What a first successful call left behind."""

    fingerprint: str
    #: Held so a repeat is only honoured against the very same state object.
    state: Any
    result: OperationResult[Any]


class IdempotencyStore(Protocol):
    def get(self, scope: IdempotencyScope) -> IdempotencyRecord | None: ...

    def put(self, scope: IdempotencyScope, record: IdempotencyRecord, *, max_entries: int) -> None: ...


class InMemoryIdempotencyStore:
    """Insertion-ordered store that evicts the oldest entry beyond ``max_entries``."""

    def __init__(self) -> None:
        self._records: OrderedDict[IdempotencyScope, IdempotencyRecord] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, scope: IdempotencyScope) -> IdempotencyRecord | None:
        with self._lock:
            return self._records.get(scope)

    def put(self, scope: IdempotencyScope, record: IdempotencyRecord, *, max_entries: int) -> None:
        with self._lock:
            self._records[scope] = record
            self._records.move_to_end(scope)
            while len(self._records) > max_entries:
                self._records.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)


# ============================================================================
# core/metadata.py
# ============================================================================
@dataclass(frozen=True, slots=True)
class AlgorithmDescriptor:
    name: str
    capability: str
    supported_structures: frozenset[str]
    time_complexity: str
    space_complexity: str
    mutates_state: bool
    stable: bool | None = None
    preconditions: tuple[str, ...] = ()
    postconditions: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    #: Kernel validates before its first write, so a failure leaves state untouched.
    atomic: bool = True
    #: Result aliases internal state (a node object, a stored value).
    returns_internal_reference: bool = False


class AlgorithmMetadataRegistry:
    """Descriptors keyed by (capability, name, supported structures).

    The same operation name may exist for different structures with different
    kernels (e.g. QUERY/HAS_CYCLE for LINKED_LIST and for GRAPH); pass
    ``structure`` or ``capability`` to disambiguate.
    """

    def __init__(self) -> None:
        self._items: dict[tuple[str, str, frozenset[str]], AlgorithmDescriptor] = {}

    def register(self, descriptor: AlgorithmDescriptor) -> None:
        key = (descriptor.capability, descriptor.name, descriptor.supported_structures)
        existing = self._items.get(key)
        if existing is not None and existing != descriptor:
            raise ValueError(f"Algorithm already registered differently: {key[:2]}")
        self._items[key] = descriptor

    def get(
        self, name: str, capability: str | None = None, structure: str | None = None
    ) -> AlgorithmDescriptor:
        matches = [
            d
            for d in self._items.values()
            if d.name == name.upper()
            and (capability is None or d.capability == capability.upper())
            and (structure is None or structure.upper() in d.supported_structures)
        ]
        if not matches:
            raise UnsupportedOperationError(f"Unknown algorithm: {name}")
        if len(matches) > 1:
            options = sorted(f"{d.capability}/{sorted(d.supported_structures)}" for d in matches)
            raise UnsupportedOperationError(
                f"Algorithm name {name!r} is ambiguous ({options}); pass capability or structure"
            )
        return matches[0]

    def list_by_capability(self, capability: str) -> list[AlgorithmDescriptor]:
        return [d for d in self.all() if d.capability == capability.upper()]

    def all(self) -> list[AlgorithmDescriptor]:
        return sorted(
            self._items.values(), key=lambda d: (d.capability, d.name, sorted(d.supported_structures))
        )


def describe(
    name: str,
    capability: str,
    structures: str | set[str],
    time_complexity: str,
    space_complexity: str,
    *,
    mutates: bool = False,
    stable: bool | None = None,
    preconditions: tuple[str, ...] = (),
    postconditions: tuple[str, ...] = (),
    invariants: tuple[str, ...] = (),
    atomic: bool = True,
    returns_internal_reference: bool = False,
) -> AlgorithmDescriptor:
    """Compact descriptor constructor used by capability services."""
    supported = frozenset({structures} if isinstance(structures, str) else structures)
    return AlgorithmDescriptor(
        name,
        capability,
        supported,
        time_complexity,
        space_complexity,
        mutates,
        stable,
        preconditions,
        postconditions,
        invariants,
        atomic,
        returns_internal_reference,
    )


# ============================================================================
# core/utilities.py
# ============================================================================
T = TypeVar("T")


class KeyResolver:
    @staticmethod
    def resolve(
        value: Any, field_name: str | None = None, key_function: Callable[[Any], Any] | None = None
    ) -> Any:
        if key_function is not None:
            return key_function(value)
        if field_name is None:
            return value
        if isinstance(value, Mapping):
            return value[field_name]
        return getattr(value, field_name)


class PredicateUtility:
    @staticmethod
    def matches(
        value: Any,
        predicate: Callable[[Any], bool] | None = None,
        target: Any = UNSET,
        key: Callable[[Any], Any] | None = None,
    ) -> bool:
        if predicate is not None:
            return bool(predicate(value))
        if target is UNSET:
            raise InvalidInputError("predicate or target is required")
        return bool(KeyResolver.resolve(value, key_function=key) == target)


class CopyUtility:
    @staticmethod
    def snapshot(value: T) -> T:
        return copy.deepcopy(value)

    @staticmethod
    def restore(target: Any, snapshot: Any) -> None:
        """Copy every slot/field of ``snapshot`` back into ``target`` in place."""
        names = getattr(type(target), "__slots__", None) or vars(target).keys()
        for name in names:
            setattr(target, name, getattr(snapshot, name))


class CapacityUtility:
    @staticmethod
    def require_space(size: int, capacity: int) -> None:
        if capacity >= 0 and size >= capacity:
            raise CapacityExceededError(f"capacity {capacity} exceeded")

    @staticmethod
    def require_not_empty(size: int) -> None:
        if size == 0:
            raise InvalidInputError("structure is empty")


class PathUtility:
    @staticmethod
    def reconstruct(parent: Mapping[T, T | None], target: T) -> list[T]:
        path: list[T] = []
        seen: set[T] = set()
        current: T | None = target
        while current is not None:
            if current in seen:
                raise InvariantViolationError("cycle in parent map during path reconstruction")
            seen.add(current)
            path.append(current)
            current = parent.get(current)
        path.reverse()
        return path


# ============================================================================
# structures/states.py
# ============================================================================
T = TypeVar("T")


class StructureType(str, Enum):
    SEQUENCE = "SEQUENCE"
    LINKED_LIST = "LINKED_LIST"
    STACK = "STACK"
    QUEUE = "QUEUE"
    TREE = "TREE"
    BST = "BST"
    TRIE = "TRIE"
    GRAPH = "GRAPH"


class CapabilityName(str, Enum):
    SEARCH = "SEARCH"
    ORDERING = "ORDERING"
    TRAVERSAL = "TRAVERSAL"
    PATH = "PATH"
    QUERY = "QUERY"
    MUTATION = "MUTATION"
    VALIDATION = "VALIDATION"


@dataclass(slots=True)
class SequenceState(Generic[T]):
    values: list[T] = field(default_factory=list)


@dataclass(slots=True)
class LinkedNode(Generic[T]):
    node_id: str
    value: T
    next_id: str | None = None
    previous_id: str | None = None


@dataclass(slots=True)
class LinkedListState(Generic[T]):
    nodes: dict[str, LinkedNode[T]] = field(default_factory=dict)
    head_id: str | None = None
    tail_id: str | None = None
    size: int = 0


@dataclass(slots=True)
class StackState(Generic[T]):
    values: list[T] = field(default_factory=list)
    capacity: int = -1


@dataclass(slots=True)
class QueueState(Generic[T]):
    values: deque[T] = field(default_factory=deque)
    capacity: int = -1


@dataclass(slots=True)
class TreeState(Generic[T]):
    values: dict[str, T] = field(default_factory=dict)
    children: dict[str, list[str]] = field(default_factory=dict)
    parent: dict[str, str | None] = field(default_factory=dict)
    root_id: str | None = None


@dataclass(slots=True)
class BSTNode(Generic[T]):
    node_id: str
    value: T
    left_id: str | None = None
    right_id: str | None = None
    parent_id: str | None = None
    height: int = 1


@dataclass(slots=True)
class BSTState(Generic[T]):
    nodes: dict[str, BSTNode[T]] = field(default_factory=dict)
    root_id: str | None = None


@dataclass(slots=True)
class TrieNode:
    children: dict[str, TrieNode] = field(default_factory=dict)
    terminal: bool = False


@dataclass(slots=True)
class TrieState:
    root: TrieNode = field(default_factory=TrieNode)
    word_count: int = 0


@dataclass(slots=True)
class GraphState(Generic[T]):
    values: dict[str, T] = field(default_factory=dict)
    adjacency: dict[str, dict[str, float]] = field(default_factory=dict)
    directed: bool = False


#: The state contract each structure type must satisfy at the governed boundary.
STATE_TYPES: dict[str, type[Any]] = {
    StructureType.SEQUENCE.value: SequenceState,
    StructureType.LINKED_LIST.value: LinkedListState,
    StructureType.STACK.value: StackState,
    StructureType.QUEUE.value: QueueState,
    StructureType.TREE.value: TreeState,
    StructureType.BST.value: BSTState,
    StructureType.TRIE.value: TrieState,
    StructureType.GRAPH.value: GraphState,
}


def normalise_name(value: str | Enum) -> str:
    """Accept enum members or strings in any case."""
    return (value.value if isinstance(value, Enum) else str(value)).upper()


# ============================================================================
# structures/adapters.py
# ============================================================================
K = TypeVar("K")


@runtime_checkable
class NavigableAdapter(Protocol[K]):
    def contains(self, node: K) -> bool: ...
    def start_nodes(self) -> Iterable[K]: ...
    def neighbours(self, node: K) -> Iterable[K]: ...


class TreeAdapter:
    def __init__(self, state: TreeState[Any]) -> None:
        self.state = state

    def contains(self, node: str) -> bool:
        return node in self.state.values

    def start_nodes(self) -> Iterable[str]:
        return [] if self.state.root_id is None else [self.state.root_id]

    def neighbours(self, node: str) -> Iterable[str]:
        return self.state.children.get(node, [])


class GraphAdapter:
    def __init__(self, state: GraphState[Any]) -> None:
        self.state = state

    def contains(self, node: str) -> bool:
        return node in self.state.values

    def start_nodes(self) -> Iterable[str]:
        return self.state.values.keys()

    def neighbours(self, node: str) -> Iterable[str]:
        return self.state.adjacency.get(node, {}).keys()

    def edge_weight(self, source: str, target: str) -> float:
        return self.state.adjacency[source][target]


class OrderedAdapter:
    """Decorates any NavigableAdapter with a deterministic neighbour order."""

    ORDERS = frozenset({"natural", "sorted", "reversed"})

    def __init__(self, inner: NavigableAdapter[Any], order: str = "natural") -> None:
        if order not in self.ORDERS:
            raise ConfigurationError(f"neighbour_order must be one of {sorted(self.ORDERS)}")
        self.inner = inner
        self.order = order

    def contains(self, node: Any) -> bool:
        return self.inner.contains(node)

    def start_nodes(self) -> Iterable[Any]:
        return self.inner.start_nodes()

    def neighbours(self, node: Any) -> Iterable[Any]:
        items = self.inner.neighbours(node)
        if self.order == "sorted":
            return sorted(items)
        if self.order == "reversed":
            return list(items)[::-1]
        return items


# ============================================================================
# structures/repositories.py
# ============================================================================
T = TypeVar("T")


def _check_duplicate_policy(on_duplicate: str) -> None:
    if on_duplicate not in {"reject", "ignore", "replace"}:
        raise InvalidInputError("on_duplicate must be one of ['ignore', 'reject', 'replace']")


class SequenceRepository:
    def create(self, state: SequenceState[T], value: T, index: int | None = None) -> SequenceState[T]:
        if index is None:
            state.values.append(value)
        else:
            state.values.insert(index, value)
        return state

    def read(self, state: SequenceState[T], index: int) -> T:
        self._require_index(state, index)
        return state.values[index]

    def update(self, state: SequenceState[T], index: int, value: T) -> SequenceState[T]:
        self._require_index(state, index)
        state.values[index] = value
        return state

    def delete(self, state: SequenceState[T], index: int) -> T:
        self._require_index(state, index)
        return state.values.pop(index)

    @staticmethod
    def _require_index(state: SequenceState[T], index: int) -> None:
        if not -len(state.values) <= index < len(state.values):
            raise NotFoundError(f"index out of range: {index}")


class LinkedListRepository:
    def append(self, state: LinkedListState[T], value: T, node_id: str | None = None) -> str:
        node_id = self._new_id(state, node_id)
        state.nodes[node_id] = LinkedNode(node_id, value, previous_id=state.tail_id)
        if state.tail_id is not None:
            state.nodes[state.tail_id].next_id = node_id
        else:
            state.head_id = node_id
        state.tail_id = node_id
        state.size += 1
        return node_id

    def prepend(self, state: LinkedListState[T], value: T, node_id: str | None = None) -> str:
        node_id = self._new_id(state, node_id)
        state.nodes[node_id] = LinkedNode(node_id, value, next_id=state.head_id)
        if state.head_id is not None:
            state.nodes[state.head_id].previous_id = node_id
        else:
            state.tail_id = node_id
        state.head_id = node_id
        state.size += 1
        return node_id

    def delete(self, state: LinkedListState[T], node_id: str) -> LinkedNode[T]:
        if node_id not in state.nodes:
            raise NotFoundError(f"unknown node: {node_id}")
        node = state.nodes[node_id]
        if node.previous_id is not None:
            state.nodes[node.previous_id].next_id = node.next_id
        else:
            state.head_id = node.next_id
        if node.next_id is not None:
            state.nodes[node.next_id].previous_id = node.previous_id
        else:
            state.tail_id = node.previous_id
        del state.nodes[node_id]
        state.size -= 1
        node.next_id = node.previous_id = None
        return node

    @staticmethod
    def _new_id(state: LinkedListState[T], node_id: str | None) -> str:
        new_id = node_id if node_id is not None else str(uuid.uuid4())
        if new_id in state.nodes:
            raise DuplicateKeyError(f"duplicate node id: {new_id}")
        return new_id


class StackRepository:
    def push(self, state: StackState[T], value: T, *, capacity: int | None = None) -> None:
        bound = state.capacity if capacity is None or state.capacity >= 0 else capacity
        CapacityUtility.require_space(len(state.values), bound)
        state.values.append(value)

    def pop(self, state: StackState[T]) -> T:
        CapacityUtility.require_not_empty(len(state.values))
        return state.values.pop()

    def peek(self, state: StackState[T]) -> T:
        CapacityUtility.require_not_empty(len(state.values))
        return state.values[-1]


class QueueRepository:
    def enqueue(self, state: QueueState[T], value: T, *, capacity: int | None = None) -> None:
        bound = state.capacity if capacity is None or state.capacity >= 0 else capacity
        CapacityUtility.require_space(len(state.values), bound)
        state.values.append(value)

    def dequeue(self, state: QueueState[T]) -> T:
        CapacityUtility.require_not_empty(len(state.values))
        return state.values.popleft()

    def peek(self, state: QueueState[T]) -> T:
        CapacityUtility.require_not_empty(len(state.values))
        return state.values[0]


class TreeRepository:
    def add_root(self, state: TreeState[T], node_id: str, value: T) -> None:
        if state.root_id is not None or state.values:
            raise InvalidInputError("tree already has a root")
        state.values[node_id] = value
        state.children[node_id] = []
        state.parent[node_id] = None
        state.root_id = node_id

    def add_child(
        self, state: TreeState[T], parent_id: str, node_id: str, value: T, *, on_duplicate: str = "reject"
    ) -> bool:
        """Attach a new leaf. Returns False when an existing node was ignored/replaced."""
        _check_duplicate_policy(on_duplicate)
        if parent_id not in state.values:
            raise NotFoundError(f"unknown parent: {parent_id}")
        if node_id in state.values:
            if on_duplicate == "reject":
                raise DuplicateKeyError(f"duplicate node: {node_id}")
            if on_duplicate == "replace":
                state.values[node_id] = value
            return False
        state.values[node_id] = value
        state.children[node_id] = []
        state.parent[node_id] = parent_id
        state.children.setdefault(parent_id, []).append(node_id)
        return True

    def delete_subtree(self, state: TreeState[T], node_id: str) -> list[str]:
        """Remove ``node_id`` and its descendants iteratively. Returns post-order ids."""
        if node_id not in state.values:
            raise NotFoundError(f"unknown node: {node_id}")
        removed: list[str] = []
        stack: list[tuple[str, bool]] = [(node_id, False)]
        while stack:
            current, expanded = stack.pop()
            if expanded:
                removed.append(current)
                continue
            stack.append((current, True))
            stack.extend((child, False) for child in reversed(state.children.get(current, [])))
        parent = state.parent.get(node_id)
        if parent is not None:
            state.children[parent].remove(node_id)
        for current in removed:
            state.children.pop(current, None)
            state.parent.pop(current, None)
            state.values.pop(current, None)
        if state.root_id == node_id:
            state.root_id = None
        return removed


class GraphRepository:
    def add_vertex(
        self, state: GraphState[T], vertex_id: str, value: T, *, on_duplicate: str = "reject"
    ) -> bool:
        _check_duplicate_policy(on_duplicate)
        if vertex_id in state.values:
            if on_duplicate == "reject":
                raise DuplicateKeyError(f"duplicate vertex: {vertex_id}")
            if on_duplicate == "replace":
                state.values[vertex_id] = value
            return False
        state.values[vertex_id] = value
        state.adjacency[vertex_id] = {}
        return True

    def add_edge(self, state: GraphState[T], source: str, target: str, weight: float = 1.0) -> None:
        missing = [v for v in (source, target) if v not in state.values]
        if missing:
            raise NotFoundError(f"unknown vertices: {missing}")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or math.isnan(weight):
            raise InvalidInputError(f"edge weight must be a number, got {weight!r}")
        state.adjacency.setdefault(source, {})[target] = weight
        if not state.directed:
            state.adjacency.setdefault(target, {})[source] = weight

    def remove_edge(self, state: GraphState[T], source: str, target: str) -> None:
        if target not in state.adjacency.get(source, {}):
            raise NotFoundError(f"unknown edge: {source}->{target}")
        del state.adjacency[source][target]
        if not state.directed:
            state.adjacency.get(target, {}).pop(source, None)

    def remove_vertex(self, state: GraphState[T], vertex_id: str) -> None:
        if vertex_id not in state.values:
            raise NotFoundError(f"unknown vertex: {vertex_id}")
        del state.values[vertex_id]
        state.adjacency.pop(vertex_id, None)
        for targets in state.adjacency.values():
            targets.pop(vertex_id, None)


# ============================================================================
# validation/validators.py
# ============================================================================
S_contra = TypeVar("S_contra", contravariant=True)


class Validator(Protocol[S_contra]):
    def validate(self, state: S_contra, *, raise_on_error: bool = False) -> ValidationReport: ...


def _finish_validation(violations: list[str], raise_on_error: bool) -> ValidationReport:
    report = ValidationReport(not violations, violations)
    if violations and raise_on_error:
        raise InvariantViolationError("; ".join(violations))
    return report


class SequenceValidator:
    def validate(self, state: SequenceState[Any], *, raise_on_error: bool = False) -> ValidationReport:
        violations: list[str] = [] if isinstance(state.values, list) else ["values must be a list"]
        return _finish_validation(violations, raise_on_error)


class ContainerValidator:
    """Stack and queue: bounded size when a capacity is set."""

    def validate(
        self, state: StackState[Any] | QueueState[Any], *, raise_on_error: bool = False
    ) -> ValidationReport:
        v: list[str] = []
        if state.capacity < -1:
            v.append("capacity must be -1 (unbounded) or >= 0")
        if state.capacity >= 0 and len(state.values) > state.capacity:
            v.append(f"size {len(state.values)} exceeds capacity {state.capacity}")
        return _finish_validation(v, raise_on_error)


class LinkedListValidator:
    def validate(self, state: LinkedListState[Any], *, raise_on_error: bool = False) -> ValidationReport:
        v: list[str] = []
        if state.size != len(state.nodes):
            v.append("size does not match node count")
        if not state.nodes and (state.head_id is not None or state.tail_id is not None):
            v.append("empty list must have no head or tail")
        if state.nodes and (state.head_id not in state.nodes or state.tail_id not in state.nodes):
            v.append("non-empty list requires valid head and tail")
        for node_id, node in state.nodes.items():
            if node.node_id != node_id:
                v.append(f"node key {node_id!r} does not match node_id {node.node_id!r}")
        visited: set[str] = set()
        current = state.head_id
        previous: str | None = None
        while current is not None:
            if current in visited:
                v.append("cycle detected in ordinary linked list")
                break
            if current not in state.nodes:
                v.append(f"missing node reference: {current}")
                break
            visited.add(current)
            node = state.nodes[current]
            if node.previous_id != previous:
                v.append(f"previous link mismatch at {current}")
            previous, current = current, node.next_id
        else:
            if previous != state.tail_id:
                v.append(f"tail_id {state.tail_id!r} is not the last reachable node {previous!r}")
        if len(visited) != len(state.nodes):
            v.append("not all nodes are reachable from head")
        return _finish_validation(v, raise_on_error)


class TreeValidator:
    def validate(self, state: TreeState[Any], *, raise_on_error: bool = False) -> ValidationReport:
        v: list[str] = []
        if not state.values:
            if state.root_id is not None:
                v.append("empty tree must have no root")
            return _finish_validation(v, raise_on_error)
        if state.root_id not in state.values:
            v.append("root is missing")
            return _finish_validation(v, raise_on_error)
        if state.parent.get(state.root_id) is not None:
            v.append("root parent must be None")
        for orphan in sorted(set(state.parent) - set(state.values)):
            v.append(f"parent entry for unknown node: {orphan}")
        for orphan in sorted(set(state.children) - set(state.values)):
            v.append(f"children entry for unknown node: {orphan}")
        visited: set[str] = set()
        active: set[str] = set()
        stack: list[tuple[str, bool]] = [(state.root_id, False)]
        while stack:
            node, exiting = stack.pop()
            if exiting:
                active.discard(node)
                continue
            if node in active:
                v.append("cycle detected")
                continue
            if node in visited:
                v.append(f"node has multiple incoming paths: {node}")
                continue
            active.add(node)
            visited.add(node)
            stack.append((node, True))
            for child in reversed(state.children.get(node, [])):
                if child not in state.values:
                    v.append(f"missing child: {child}")
                    continue
                if state.parent.get(child) != node:
                    v.append(f"parent mismatch for {child}")
                stack.append((child, False))
        if visited != set(state.values):
            v.append("not all nodes are reachable from root")
        return _finish_validation(v, raise_on_error)


class BSTValidator:
    """Strict key ordering, parent links, reachability and stored heights."""

    def __init__(self, key: Callable[[Any], Any] | None = None) -> None:
        self.key = key

    def validate(self, state: BSTState[Any], *, raise_on_error: bool = False) -> ValidationReport:
        v: list[str] = []
        if state.root_id is None:
            if state.nodes:
                v.append("nodes exist but root is None")
            return _finish_validation(v, raise_on_error)
        if state.root_id not in state.nodes:
            return _finish_validation(["root is missing"], raise_on_error)
        if state.nodes[state.root_id].parent_id is not None:
            v.append("root parent must be None")
        visited: set[str] = set()
        heights: dict[str, int] = {}
        previous_value: Any = None
        has_previous = False
        # Iterative in-order walk checks strict ordering; post-order height check below.
        stack: list[str] = []
        current: str | None = state.root_id
        while stack or current is not None:
            while current is not None:
                if current in visited:
                    return _finish_validation(v + [f"cycle at {current}"], raise_on_error)
                if current not in state.nodes:
                    return _finish_validation(v + [f"missing node: {current}"], raise_on_error)
                visited.add(current)
                node = state.nodes[current]
                for child in (node.left_id, node.right_id):
                    if child is not None and child in state.nodes and state.nodes[child].parent_id != current:
                        v.append(f"parent mismatch for {child}")
                stack.append(current)
                current = node.left_id
            node = state.nodes[stack.pop()]
            node_key = KeyResolver.resolve(node.value, key_function=self.key)
            if has_previous and not previous_value < node_key:
                v.append(f"ordering violated at {node.node_id}")
            previous_value, has_previous = node_key, True
            current = node.right_id
        if visited != set(state.nodes):
            v.append("not all nodes are reachable from root")
        post: list[tuple[str, bool]] = [(state.root_id, False)]
        while post:
            node_id, expanded = post.pop()
            node = state.nodes[node_id]
            if not expanded:
                post.append((node_id, True))
                post.extend((c, False) for c in (node.left_id, node.right_id) if c is not None)
                continue
            left_h = heights[node.left_id] if node.left_id is not None else 0
            right_h = heights[node.right_id] if node.right_id is not None else 0
            actual = 1 + max(left_h, right_h)
            heights[node_id] = actual
            if node.height != actual:
                v.append(f"stored height {node.height} != actual {actual} at {node_id}")
        return _finish_validation(v, raise_on_error)


class TrieValidator:
    def validate(self, state: TrieState, *, raise_on_error: bool = False) -> ValidationReport:
        v: list[str] = []
        terminals = 0
        stack: list[TrieNode] = [state.root]
        seen: set[int] = set()
        while stack:
            node = stack.pop()
            if id(node) in seen:
                v.append("trie node shared between paths")
                break
            seen.add(id(node))
            terminals += node.terminal
            for char, child in node.children.items():
                if len(char) != 1:
                    v.append(f"edge label must be one character, got {char!r}")
                stack.append(child)
        if terminals != state.word_count:
            v.append(f"word_count {state.word_count} != terminal nodes {terminals}")
        return _finish_validation(v, raise_on_error)


class GraphValidator:
    def validate(self, state: GraphState[Any], *, raise_on_error: bool = False) -> ValidationReport:
        v: list[str] = []
        for source, targets in state.adjacency.items():
            if source not in state.values:
                v.append(f"adjacency source missing: {source}")
            for target, weight in targets.items():
                if target not in state.values:
                    v.append(f"edge target missing: {target}")
                if isinstance(weight, bool) or not isinstance(weight, (int, float)) or math.isnan(weight):
                    v.append(f"edge weight is not a number: {source}->{target}")
                if (
                    not state.directed
                    and source <= target
                    and state.adjacency.get(target, {}).get(source) != weight
                ):
                    v.append(f"undirected reverse edge mismatch: {source}<->{target}")
                if not state.directed and source > target and source not in state.adjacency.get(target, {}):
                    v.append(f"undirected reverse edge mismatch: {target}<->{source}")
        return _finish_validation(v, raise_on_error)


def validator_for(structure_type: str, key: Callable[[Any], Any] | None = None) -> Any:
    """Validator for a structure; BST ordering honours the caller's key function."""
    if structure_type == "BST":
        return BSTValidator(key)
    return VALIDATORS.get(structure_type)


VALIDATORS: dict[str, Any] = {
    "SEQUENCE": SequenceValidator(),
    "LINKED_LIST": LinkedListValidator(),
    "STACK": ContainerValidator(),
    "QUEUE": ContainerValidator(),
    "TREE": TreeValidator(),
    "BST": BSTValidator(),
    "TRIE": TrieValidator(),
    "GRAPH": GraphValidator(),
}


# ============================================================================
# algorithms/search.py
# ============================================================================
T = TypeVar("T")


class SearchAlgorithms:
    @staticmethod
    def linear(
        values: Sequence[T],
        target: Any,
        *,
        key: Callable[[T], Any] | None = None,
        metrics: MetricsState | None = None,
    ) -> int | None:
        """Index of the first element whose key equals ``target``, else None."""
        m = metrics or MetricsState()
        for index, value in enumerate(values):
            m.iterations += 1
            m.reads += 1
            m.comparisons += 1
            if KeyResolver.resolve(value, key_function=key) == target:
                return index
        return None

    @staticmethod
    def binary(
        values: Sequence[T],
        target: Any,
        *,
        key: Callable[[T], Any] | None = None,
        metrics: MetricsState | None = None,
    ) -> int | None:
        """Index of *an* element whose key equals ``target``. Input must be sorted by key."""
        m = metrics or MetricsState()
        left, right = 0, len(values) - 1
        while left <= right:
            m.iterations += 1
            middle = (left + right) // 2
            current = KeyResolver.resolve(values[middle], key_function=key)
            m.reads += 1
            m.comparisons += 1
            if current == target:
                return middle
            m.comparisons += 1
            if current < target:
                left = middle + 1
            else:
                right = middle - 1
        return None

    @staticmethod
    def lower_bound(
        values: Sequence[T],
        target: Any,
        *,
        key: Callable[[T], Any] | None = None,
        metrics: MetricsState | None = None,
    ) -> int:
        """First index whose key is >= ``target`` (``len(values)`` if none).

        Use this when duplicates exist and the *first* occurrence matters.
        """
        m = metrics or MetricsState()
        left, right = 0, len(values)
        while left < right:
            m.iterations += 1
            m.reads += 1
            m.comparisons += 1
            middle = (left + right) // 2
            if KeyResolver.resolve(values[middle], key_function=key) < target:
                left = middle + 1
            else:
                right = middle
        return left

    @staticmethod
    def is_sorted(values: Sequence[T], *, key: Callable[[T], Any] | None = None) -> bool:
        """Non-decreasing by key. O(n), early exit, iterated at C level (no auxiliary list)."""
        keys: Iterable[Any] = values if key is None else map(key, values)
        return all(starmap(operator.le, pairwise(keys)))


# ============================================================================
# algorithms/sorting.py
# ============================================================================
T = TypeVar("T")


class SortAlgorithms:
    @staticmethod
    def bubble(
        values: Sequence[T], *, key: Callable[[T], Any] | None = None, metrics: MetricsState | None = None
    ) -> list[T]:
        """Stable, O(n^2), early exit when a pass makes no swap."""
        m = metrics or MetricsState()
        out = list(values)
        for end in range(len(out) - 1, 0, -1):
            swapped = False
            for i in range(end):
                m.iterations += 1
                m.comparisons += 1
                m.reads += 2
                if KeyResolver.resolve(out[i], key_function=key) > KeyResolver.resolve(
                    out[i + 1], key_function=key
                ):
                    out[i], out[i + 1] = out[i + 1], out[i]
                    m.swaps += 1
                    m.writes += 2
                    swapped = True
            if not swapped:
                break
        return out

    @staticmethod
    def merge(
        values: Sequence[T], *, key: Callable[[T], Any] | None = None, metrics: MetricsState | None = None
    ) -> list[T]:
        """Stable top-down merge sort. Recursion depth is ceil(log2 n)."""
        m = metrics or MetricsState()

        def sort(items: list[T], depth: int) -> list[T]:
            if len(items) <= 1:
                return items
            m.recursion_depth = depth
            m.max_recursion_depth = max(m.max_recursion_depth, depth)
            mid = len(items) // 2
            left, right = sort(items[:mid], depth + 1), sort(items[mid:], depth + 1)
            result: list[T] = []
            i = j = 0
            while i < len(left) and j < len(right):
                m.comparisons += 1
                m.reads += 2
                m.iterations += 1
                if KeyResolver.resolve(left[i], key_function=key) <= KeyResolver.resolve(
                    right[j], key_function=key
                ):
                    result.append(left[i])
                    i += 1
                else:
                    result.append(right[j])
                    j += 1
                m.writes += 1
            result.extend(left[i:])
            result.extend(right[j:])
            m.writes += len(left) - i + len(right) - j
            return result

        out = sort(list(values), 1)
        m.recursion_depth = 0
        return out

    @staticmethod
    def quick(
        values: Sequence[T], *, key: Callable[[T], Any] | None = None, metrics: MetricsState | None = None
    ) -> list[T]:
        """Unstable quicksort with Hoare partitioning on one O(n) working copy.

        Recurses into the smaller partition and loops on the larger one, so the
        call stack is O(log n) even on adversarial input (time stays O(n^2)
        worst case, O(n log n) expected).
        """
        m = metrics or MetricsState()
        out = list(values)

        def value_key(index: int) -> Any:
            m.reads += 1
            return KeyResolver.resolve(out[index], key_function=key)

        def partition(low: int, high: int) -> int:
            pivot = value_key((low + high) // 2)
            i, j = low - 1, high + 1
            while True:
                i += 1
                while value_key(i) < pivot:
                    m.comparisons += 1
                    m.iterations += 1
                    i += 1
                m.comparisons += 1
                j -= 1
                while value_key(j) > pivot:
                    m.comparisons += 1
                    m.iterations += 1
                    j -= 1
                m.comparisons += 1
                if i >= j:
                    return j
                out[i], out[j] = out[j], out[i]
                m.swaps += 1
                m.writes += 2

        def sort_range(low: int, high: int, depth: int) -> None:
            while low < high:
                m.recursion_depth = depth
                m.max_recursion_depth = max(m.max_recursion_depth, depth)
                split = partition(low, high)
                if split - low < high - split:
                    sort_range(low, split, depth + 1)
                    low = split + 1
                else:
                    sort_range(split + 1, high, depth + 1)
                    high = split

        sort_range(0, len(out) - 1, 1)
        m.recursion_depth = 0
        return out


# ============================================================================
# algorithms/traversal.py
# ============================================================================
K = TypeVar("K")


class TraversalAlgorithms:
    @staticmethod
    def bfs(
        adapter: NavigableAdapter[K],
        start: K,
        *,
        track_visited: bool = True,
        maximum_depth: int = -1,
        maximum_results: int = -1,
        metrics: MetricsState | None = None,
    ) -> list[K]:
        """Breadth-first order from ``start``.

        With ``track_visited=False`` on a cyclic topology the walk only
        terminates if ``maximum_depth`` or ``maximum_results`` bounds it; the
        governed TraversalService enforces that.
        """
        if not adapter.contains(start):
            raise InvalidInputError(f"unknown start node: {start}")
        m = metrics or MetricsState()
        result: list[K] = []
        queue: deque[tuple[K, int]] = deque([(start, 0)])
        visited: set[K] = {start} if track_visited else set()
        while queue:
            node, depth = queue.popleft()
            m.queue_operations += 1
            result.append(node)
            m.nodes_visited += 1
            if 0 <= maximum_results <= len(result):
                break
            if 0 <= maximum_depth <= depth:
                continue
            for neighbour in adapter.neighbours(node):
                m.edges_examined += 1
                if not track_visited or neighbour not in visited:
                    if track_visited:
                        visited.add(neighbour)
                    queue.append((neighbour, depth + 1))
                    m.queue_operations += 1
        return result

    @staticmethod
    def dfs(
        adapter: NavigableAdapter[K],
        start: K,
        *,
        track_visited: bool = True,
        maximum_depth: int = -1,
        maximum_results: int = -1,
        metrics: MetricsState | None = None,
    ) -> list[K]:
        """Iterative pre-order depth-first walk; neighbours visited in adapter order."""
        if not adapter.contains(start):
            raise InvalidInputError(f"unknown start node: {start}")
        m = metrics or MetricsState()
        result: list[K] = []
        stack: list[tuple[K, int]] = [(start, 0)]
        visited: set[K] = set()
        while stack:
            node, depth = stack.pop()
            m.stack_operations += 1
            if track_visited and node in visited:
                continue
            if track_visited:
                visited.add(node)
            result.append(node)
            m.nodes_visited += 1
            if 0 <= maximum_results <= len(result):
                break
            if 0 <= maximum_depth <= depth:
                continue
            for neighbour in reversed(list(adapter.neighbours(node))):
                m.edges_examined += 1
                if not track_visited or neighbour not in visited:
                    stack.append((neighbour, depth + 1))
                    m.stack_operations += 1
        return result


# ============================================================================
# algorithms/sequences.py
# ============================================================================
class SequenceAlgorithms:
    @staticmethod
    def two_sum(values: Sequence[int], target: int) -> tuple[int, int] | None:
        seen: dict[int, int] = {}
        for index, value in enumerate(values):
            if target - value in seen:
                return seen[target - value], index
            seen.setdefault(value, index)
        return None

    @staticmethod
    def maximum_subarray(values: Sequence[int]) -> int:
        """Kadane's algorithm."""
        if not values:
            raise InvalidInputError("values must not be empty")
        best = current = values[0]
        for value in values[1:]:
            current = max(value, current + value)
            best = max(best, current)
        return best

    @staticmethod
    def prefix_sums(values: Sequence[int]) -> list[int]:
        out = [0]
        for value in values:
            out.append(out[-1] + value)
        return out


class StackAlgorithms:
    PAIRS: ClassVar[dict[str, str]] = {")": "(", "]": "[", "}": "{"}

    @staticmethod
    def balanced_brackets(text: str) -> bool:
        stack: list[str] = []
        for char in text:
            if char in "([{":
                stack.append(char)
            elif char in StackAlgorithms.PAIRS and (not stack or stack.pop() != StackAlgorithms.PAIRS[char]):
                return False
        return not stack

    @staticmethod
    def evaluate_postfix(tokens: Iterable[str]) -> float:
        stack: list[float] = []
        for token in tokens:
            if token not in {"+", "-", "*", "/"}:
                try:
                    stack.append(float(token))
                except ValueError as exc:
                    raise InvalidInputError(f"invalid postfix token: {token!r}") from exc
                continue
            if len(stack) < 2:
                raise InvalidInputError("invalid postfix expression")
            right, left = stack.pop(), stack.pop()
            if token == "+":
                stack.append(left + right)
            elif token == "-":
                stack.append(left - right)
            elif token == "*":
                stack.append(left * right)
            elif right == 0:
                raise InvalidInputError("division by zero in postfix expression")
            else:
                stack.append(left / right)
        if len(stack) != 1:
            raise InvalidInputError("invalid postfix expression")
        return stack[0]

    @staticmethod
    def next_greater(values: Sequence[int]) -> list[int]:
        """Monotonic stack; -1 where no greater element follows."""
        result = [-1] * len(values)
        stack: list[int] = []
        for index, value in enumerate(values):
            while stack and values[stack[-1]] < value:
                result[stack.pop()] = value
            stack.append(index)
        return result


class QueueAlgorithms:
    @staticmethod
    def generate_binary_numbers(count: int) -> list[str]:
        if count < 0:
            raise InvalidInputError("count must be non-negative")
        queue = deque(["1"])
        result: list[str] = []
        for _ in range(count):
            current = queue.popleft()
            result.append(current)
            queue.extend((current + "0", current + "1"))
        return result

    @staticmethod
    def sliding_window_maximum(values: Sequence[int], window: int) -> list[int]:
        """Monotonic deque, O(n)."""
        if window <= 0 or window > len(values):
            raise InvalidInputError("invalid window")
        indexes: deque[int] = deque()
        result: list[int] = []
        for i, value in enumerate(values):
            while indexes and indexes[0] <= i - window:
                indexes.popleft()
            while indexes and values[indexes[-1]] <= value:
                indexes.pop()
            indexes.append(i)
            if i >= window - 1:
                result.append(values[indexes[0]])
        return result


# ============================================================================
# algorithms/linked_list.py
# ============================================================================
T = TypeVar("T")


class LinkedListAlgorithms:
    @staticmethod
    def reverse(state: LinkedListState[T]) -> LinkedListState[T]:
        """Reverse links in place. Corrupt input is rejected before any write."""
        LinkedListValidator().validate(state, raise_on_error=True)
        current = state.head_id
        while current is not None:
            node = state.nodes[current]
            node.next_id, node.previous_id = node.previous_id, node.next_id
            current = node.previous_id
        state.head_id, state.tail_id = state.tail_id, state.head_id
        return state

    @staticmethod
    def middle(state: LinkedListState[T]) -> LinkedNode[T] | None:
        """Slow/fast pointers. For even sizes returns the second middle node."""
        slow = fast = state.head_id
        while fast is not None and state.nodes[fast].next_id is not None:
            assert slow is not None
            slow = state.nodes[slow].next_id
            first = state.nodes[fast].next_id
            fast = state.nodes[first].next_id if first is not None else None
        return state.nodes[slow] if slow is not None else None

    @staticmethod
    def has_cycle(state: LinkedListState[T]) -> bool:
        """Floyd's tortoise and hare over ``next_id``; dangling ids end the walk."""

        def step(node_id: str | None) -> str | None:
            if node_id is None or node_id not in state.nodes:
                return None
            return state.nodes[node_id].next_id

        slow = fast = state.head_id
        while True:
            slow = step(slow)
            fast = step(step(fast))
            if fast is None or slow is None:
                return False
            if slow == fast:
                return True


# ============================================================================
# algorithms/trees.py
# ============================================================================
class TreeAlgorithms:
    @staticmethod
    def height(state: TreeState[Any], node_id: str | None = None) -> int:
        """Height measured in **nodes** (empty tree = 0, single node = 1)."""
        start = state.root_id if node_id is None else node_id
        if start is None:
            return 0
        if start not in state.values:
            raise NotFoundError(f"unknown node: {start}")
        best = 0
        stack: list[tuple[str, int]] = [(start, 1)]
        seen: set[str] = set()
        while stack:
            node, depth = stack.pop()
            if node in seen:
                raise InvariantViolationError(f"cycle or shared child at {node}")
            seen.add(node)
            best = max(best, depth)
            stack.extend((child, depth + 1) for child in state.children.get(node, []))
        return best

    @staticmethod
    def ancestors(state: TreeState[Any], node_id: str) -> list[str]:
        """Root-first list of ancestors (excluding ``node_id``)."""
        if node_id not in state.values:
            raise NotFoundError(f"unknown node: {node_id}")
        result: list[str] = []
        seen = {node_id}
        current = state.parent.get(node_id)
        while current is not None:
            if current in seen:
                raise InvariantViolationError(f"cycle in parent links at {current}")
            seen.add(current)
            result.append(current)
            current = state.parent.get(current)
        result.reverse()
        return result

    @staticmethod
    def lowest_common_ancestor(state: TreeState[Any], left: str, right: str) -> str | None:
        left_path = TreeAlgorithms.ancestors(state, left) + [left]
        right_path = TreeAlgorithms.ancestors(state, right) + [right]
        lca = None
        for a, b in zip(left_path, right_path, strict=False):
            if a != b:
                break
            lca = a
        return lca

    @staticmethod
    def diameter(state: TreeState[Any]) -> int:
        """Longest path measured in **edges**. Validates the tree first."""
        if state.root_id is None:
            return 0
        TreeValidator().validate(state, raise_on_error=True)
        heights: dict[str, int] = {}
        best = 0
        stack: list[tuple[str, bool]] = [(state.root_id, False)]
        while stack:
            node, expanded = stack.pop()
            if not expanded:
                stack.append((node, True))
                stack.extend((child, False) for child in reversed(state.children.get(node, [])))
                continue
            first = second = 0
            for child in state.children.get(node, []):
                child_height = heights[child]
                if child_height > first:
                    first, second = child_height, first
                elif child_height > second:
                    second = child_height
            best = max(best, first + second)
            heights[node] = first + 1
        return best

    @staticmethod
    def subtree_ids(state: TreeState[Any], node_id: str) -> list[str]:
        """Post-order ids of ``node_id`` and all its descendants."""
        if node_id not in state.values:
            raise NotFoundError(f"unknown node: {node_id}")
        out: list[str] = []
        stack: list[tuple[str, bool]] = [(node_id, False)]
        while stack:
            node, expanded = stack.pop()
            if expanded:
                out.append(node)
                continue
            stack.append((node, True))
            stack.extend((child, False) for child in reversed(state.children.get(node, [])))
        return out


# ============================================================================
# algorithms/bst.py
# ============================================================================
T = TypeVar("T")

DUPLICATE_POLICIES = frozenset({"reject", "ignore", "replace"})


class BSTAlgorithms:
    # ----------------------------------------------------------------- reads
    @staticmethod
    def search(
        state: BSTState[T], target: Any, *, key: Callable[[T], Any] | None = None
    ) -> BSTNode[T] | None:
        current = state.root_id
        while current is not None:
            node = state.nodes[current]
            value = KeyResolver.resolve(node.value, key_function=key)
            if value == target:
                return node
            current = node.left_id if target < value else node.right_id
        return None

    @staticmethod
    def inorder(state: BSTState[T]) -> list[T]:
        """Iterative in-order values (sorted by key)."""
        result: list[T] = []
        stack: list[str] = []
        current = state.root_id
        while stack or current is not None:
            while current is not None:
                stack.append(current)
                current = state.nodes[current].left_id
            node = state.nodes[stack.pop()]
            result.append(node.value)
            current = node.right_id
        return result

    @staticmethod
    def is_avl_balanced(state: BSTState[T]) -> bool:
        """Stored heights are correct and every balance factor is within [-1, 1]."""
        if state.root_id is None:
            return True
        calculated: dict[str, int] = {}
        stack: list[tuple[str, bool]] = [(state.root_id, False)]
        while stack:
            node_id, expanded = stack.pop()
            node = state.nodes[node_id]
            if not expanded:
                stack.append((node_id, True))
                if node.right_id is not None:
                    stack.append((node.right_id, False))
                if node.left_id is not None:
                    stack.append((node.left_id, False))
                continue
            left_h = calculated[node.left_id] if node.left_id is not None else 0
            right_h = calculated[node.right_id] if node.right_id is not None else 0
            actual = 1 + max(left_h, right_h)
            if abs(left_h - right_h) > 1 or node.height != actual:
                return False
            calculated[node_id] = actual
        return True

    # ------------------------------------------------------------- mutations
    @staticmethod
    def insert(
        state: BSTState[T],
        value: T,
        *,
        key: Callable[[T], Any] | None = None,
        node_id: str | None = None,
        on_duplicate: str = "reject",
    ) -> str:
        """Unbalanced insert. Returns the id of the inserted (or existing) node."""
        if on_duplicate not in DUPLICATE_POLICIES:
            raise InvalidInputError(f"on_duplicate must be one of {sorted(DUPLICATE_POLICIES)}")
        new_id = node_id if node_id is not None else str(uuid.uuid4())
        if new_id in state.nodes:
            raise DuplicateKeyError(f"duplicate node id: {new_id}")
        new_key = KeyResolver.resolve(value, key_function=key)
        if state.root_id is None:
            state.nodes[new_id] = BSTNode(new_id, value)
            state.root_id = new_id
            return new_id
        current = state.root_id
        while True:
            node = state.nodes[current]
            node_key = KeyResolver.resolve(node.value, key_function=key)
            if new_key == node_key:
                if on_duplicate == "reject":
                    raise DuplicateKeyError(f"duplicate BST key: {new_key}")
                if on_duplicate == "replace":
                    node.value = value
                return current
            side = "left_id" if new_key < node_key else "right_id"
            child = getattr(node, side)
            if child is None:
                state.nodes[new_id] = BSTNode(new_id, value, parent_id=current)
                setattr(node, side, new_id)
                BSTAlgorithms._refresh_path(state, current)
                return new_id
            current = child

    @staticmethod
    def insert_avl(
        state: BSTState[T],
        value: T,
        *,
        key: Callable[[T], Any] | None = None,
        node_id: str | None = None,
        on_duplicate: str = "reject",
    ) -> str:
        """Insert, then restore the AVL property with rotations."""
        size_before = len(state.nodes)
        inserted_id = BSTAlgorithms.insert(state, value, key=key, node_id=node_id, on_duplicate=on_duplicate)
        if len(state.nodes) > size_before:
            BSTAlgorithms._rebalance_from(state, state.nodes[inserted_id].parent_id)
        return inserted_id

    @staticmethod
    def delete(
        state: BSTState[T], target: Any, *, key: Callable[[T], Any] | None = None, rebalance: bool = False
    ) -> BSTNode[T]:
        """Remove the node whose key equals ``target`` by relinking (node ids are stable).

        Returns the detached node. With ``rebalance=True`` the AVL property is
        restored on the way back to the root.
        """
        z = BSTAlgorithms.search(state, target, key=key)
        if z is None:
            raise NotFoundError(f"BST key not found: {target!r}")
        nodes = state.nodes
        start: str | None
        if z.left_id is None:
            start = z.parent_id
            BSTAlgorithms._transplant(state, z.node_id, z.right_id)
        elif z.right_id is None:
            start = z.parent_id
            BSTAlgorithms._transplant(state, z.node_id, z.left_id)
        else:
            y_id = z.right_id
            while nodes[y_id].left_id is not None:
                y_id = nodes[y_id].left_id  # type: ignore[assignment]
            y = nodes[y_id]
            if y.parent_id != z.node_id:
                start = y.parent_id
                BSTAlgorithms._transplant(state, y_id, y.right_id)
                y.right_id = z.right_id
                nodes[y.right_id].parent_id = y_id
            else:
                start = y_id
            BSTAlgorithms._transplant(state, z.node_id, y_id)
            y.left_id = z.left_id
            nodes[y.left_id].parent_id = y_id
        del nodes[z.node_id]
        z.left_id = z.right_id = z.parent_id = None
        z.height = 1
        if rebalance:
            BSTAlgorithms._rebalance_from(state, start)
        else:
            BSTAlgorithms._refresh_path(state, start)
        return z

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _height(state: BSTState[T], node_id: str | None) -> int:
        return 0 if node_id is None else state.nodes[node_id].height

    @staticmethod
    def _refresh_height(state: BSTState[T], node_id: str) -> None:
        node = state.nodes[node_id]
        node.height = 1 + max(
            BSTAlgorithms._height(state, node.left_id), BSTAlgorithms._height(state, node.right_id)
        )

    @staticmethod
    def _refresh_path(state: BSTState[T], node_id: str | None) -> None:
        current = node_id
        while current is not None:
            BSTAlgorithms._refresh_height(state, current)
            current = state.nodes[current].parent_id

    @staticmethod
    def _transplant(state: BSTState[T], old_id: str, new_id: str | None) -> None:
        """Replace the subtree rooted at ``old_id`` with the one at ``new_id``."""
        parent_id = state.nodes[old_id].parent_id
        if parent_id is None:
            state.root_id = new_id
        elif state.nodes[parent_id].left_id == old_id:
            state.nodes[parent_id].left_id = new_id
        else:
            state.nodes[parent_id].right_id = new_id
        if new_id is not None:
            state.nodes[new_id].parent_id = parent_id

    @staticmethod
    def _rotate_left(state: BSTState[T], root_id: str) -> str:
        root = state.nodes[root_id]
        pivot_id = root.right_id
        if pivot_id is None:
            return root_id
        pivot = state.nodes[pivot_id]
        moved_id = pivot.left_id
        BSTAlgorithms._transplant(state, root_id, pivot_id)
        pivot.left_id = root_id
        root.parent_id = pivot_id
        root.right_id = moved_id
        if moved_id is not None:
            state.nodes[moved_id].parent_id = root_id
        BSTAlgorithms._refresh_height(state, root_id)
        BSTAlgorithms._refresh_height(state, pivot_id)
        return pivot_id

    @staticmethod
    def _rotate_right(state: BSTState[T], root_id: str) -> str:
        root = state.nodes[root_id]
        pivot_id = root.left_id
        if pivot_id is None:
            return root_id
        pivot = state.nodes[pivot_id]
        moved_id = pivot.right_id
        BSTAlgorithms._transplant(state, root_id, pivot_id)
        pivot.right_id = root_id
        root.parent_id = pivot_id
        root.left_id = moved_id
        if moved_id is not None:
            state.nodes[moved_id].parent_id = root_id
        BSTAlgorithms._refresh_height(state, root_id)
        BSTAlgorithms._refresh_height(state, pivot_id)
        return pivot_id

    @staticmethod
    def _rebalance_from(state: BSTState[T], node_id: str | None) -> None:
        """Walk to the root refreshing heights and rotating where |balance| > 1.

        Covers insertion and deletion (a child with balance 0 selects the
        single rotation, which is the correct deletion case).
        """
        current = node_id
        while current is not None:
            BSTAlgorithms._refresh_height(state, current)
            node = state.nodes[current]
            balance = BSTAlgorithms._height(state, node.left_id) - BSTAlgorithms._height(state, node.right_id)
            if balance > 1 and node.left_id is not None:
                left = state.nodes[node.left_id]
                if BSTAlgorithms._height(state, left.left_id) < BSTAlgorithms._height(state, left.right_id):
                    BSTAlgorithms._rotate_left(state, node.left_id)
                current = state.nodes[BSTAlgorithms._rotate_right(state, current)].parent_id
            elif balance < -1 and node.right_id is not None:
                right = state.nodes[node.right_id]
                if BSTAlgorithms._height(state, right.right_id) < BSTAlgorithms._height(state, right.left_id):
                    BSTAlgorithms._rotate_right(state, node.right_id)
                current = state.nodes[BSTAlgorithms._rotate_left(state, current)].parent_id
            else:
                current = node.parent_id


# ============================================================================
# algorithms/trie.py
# ============================================================================
class TrieAlgorithms:
    @staticmethod
    def insert(state: TrieState, word: str) -> bool:
        """Insert ``word``. Returns False if it was already present."""
        node = state.root
        for char in word:
            node = node.children.setdefault(char, TrieNode())
        if node.terminal:
            return False
        node.terminal = True
        state.word_count += 1
        return True

    @staticmethod
    def _find(state: TrieState, prefix: str) -> TrieNode | None:
        node = state.root
        for char in prefix:
            child = node.children.get(char)
            if child is None:
                return None
            node = child
        return node

    @staticmethod
    def search(state: TrieState, word: str) -> bool:
        node = TrieAlgorithms._find(state, word)
        return node is not None and node.terminal

    @staticmethod
    def starts_with(state: TrieState, prefix: str) -> bool:
        return TrieAlgorithms._find(state, prefix) is not None

    @staticmethod
    def autocomplete(state: TrieState, prefix: str, limit: int = -1) -> list[str]:
        """Words with ``prefix`` in lexicographic order; iterative, stops at ``limit``."""
        node = TrieAlgorithms._find(state, prefix)
        if node is None:
            return []
        result: list[str] = []
        stack: list[tuple[TrieNode, str]] = [(node, prefix)]
        while stack and not (0 <= limit <= len(result)):
            current, word = stack.pop()
            if current.terminal:
                result.append(word)
            for char in sorted(current.children, reverse=True):
                stack.append((current.children[char], word + char))
        return result

    @staticmethod
    def delete(state: TrieState, word: str) -> bool:
        """Remove ``word`` and prune now-empty branches. Returns False if absent."""
        path: list[tuple[TrieNode, str]] = []
        node = state.root
        for char in word:
            child = node.children.get(char)
            if child is None:
                return False
            path.append((node, char))
            node = child
        if not node.terminal:
            return False
        node.terminal = False
        state.word_count -= 1
        for parent, char in reversed(path):
            child = parent.children[char]
            if child.terminal or child.children:
                break
            del parent.children[char]
        return True


# ============================================================================
# algorithms/graphs.py
# ============================================================================
DIJKSTRA_POLICIES = frozenset({"eager", "lazy", "assume_non_negative"})


class GraphAlgorithms:
    @staticmethod
    def _require_vertices(state: GraphState[Any], *vertices: str) -> None:
        missing = [v for v in vertices if v not in state.values]
        if missing:
            raise InvalidInputError(f"unknown vertices: {missing}")

    @staticmethod
    def shortest_unweighted_path(state: GraphState[Any], source: str, target: str) -> list[str]:
        """BFS shortest path by edge count; [] if unreachable."""
        GraphAlgorithms._require_vertices(state, source, target)
        adapter = GraphAdapter(state)
        queue = deque([source])
        parent: dict[str, str | None] = {source: None}
        while queue:
            current = queue.popleft()
            if current == target:
                return PathUtility.reconstruct(parent, target)
            for neighbour in adapter.neighbours(current):
                if neighbour not in parent:
                    parent[neighbour] = current
                    queue.append(neighbour)
        return []

    @staticmethod
    def dijkstra(
        state: GraphState[Any], source: str, target: str, *, negative_weight_policy: str = "eager"
    ) -> tuple[float, list[str]]:
        """Shortest weighted path with an explicit negative-weight policy.

        eager: validate every edge first; safe default; early exit at target.
        lazy: validate only inspected edges; no early exit, because an
              undiscovered negative edge could invalidate greedy finalisation.
        assume_non_negative: no validation, early exit; caller owns the precondition.
        """
        GraphAlgorithms._require_vertices(state, source, target)
        if negative_weight_policy not in DIJKSTRA_POLICIES:
            raise InvalidInputError(f"negative_weight_policy must be one of {sorted(DIJKSTRA_POLICIES)}")
        if negative_weight_policy == "eager":
            for edges in state.adjacency.values():
                if any(weight < 0 for weight in edges.values()):
                    raise AlgorithmPreconditionError("Dijkstra requires non-negative weights")
        inf = float("inf")
        distances: dict[str, float] = {source: 0.0}
        parent: dict[str, str | None] = {source: None}
        queue: list[tuple[float, str]] = [(0.0, source)]
        while queue:
            distance, node = heapq.heappop(queue)
            if distance > distances.get(node, inf):
                continue
            if node == target and negative_weight_policy != "lazy":
                break
            for neighbour, weight in state.adjacency.get(node, {}).items():
                if negative_weight_policy == "lazy" and weight < 0:
                    raise AlgorithmPreconditionError("Dijkstra requires non-negative weights")
                if neighbour not in state.values:
                    raise InvariantViolationError(f"edge {node}->{neighbour} targets unknown vertex")
                candidate = distance + weight
                if candidate < distances.get(neighbour, inf):
                    distances[neighbour] = candidate
                    parent[neighbour] = node
                    heapq.heappush(queue, (candidate, neighbour))
        if target not in distances:
            return inf, []
        return distances[target], PathUtility.reconstruct(parent, target)

    @staticmethod
    def all_simple_paths(
        state: GraphState[Any], source: str, target: str, *, maximum_paths: int = 1000
    ) -> list[list[str]]:
        """Enumerate simple paths (no repeated vertex), bounded by ``maximum_paths``.

        Iterative DFS; worst case is exponential, which is why the bound exists.
        """
        GraphAlgorithms._require_vertices(state, source, target)
        paths: list[list[str]] = []
        stack: list[tuple[str, list[str]]] = [(source, [source])]
        while stack and not (0 <= maximum_paths <= len(paths)):
            node, path = stack.pop()
            if node == target:
                paths.append(path)
                continue
            on_path = set(path)
            for neighbour in reversed(list(state.adjacency.get(node, {}))):
                if neighbour not in on_path:
                    stack.append((neighbour, path + [neighbour]))
        return paths

    @staticmethod
    def has_cycle(state: GraphState[Any]) -> bool:
        """Directed: three-colour DFS. Undirected: DFS tracking the tree edge used."""
        if state.directed:
            white, grey, black = 0, 1, 2
            colour = dict.fromkeys(state.values, white)
            for root in state.values:
                if colour[root] != white:
                    continue
                colour[root] = grey
                stack = [(root, iter(state.adjacency.get(root, {})))]
                while stack:
                    node, neighbours = stack[-1]
                    advanced = False
                    for neighbour in neighbours:
                        state_of = colour.get(neighbour, white)
                        if state_of == grey:
                            return True
                        if state_of == white:
                            colour[neighbour] = grey
                            stack.append((neighbour, iter(state.adjacency.get(neighbour, {}))))
                            advanced = True
                            break
                    if not advanced:
                        colour[node] = black
                        stack.pop()
            return False
        visited: set[str] = set()
        for root in state.values:
            if root in visited:
                continue
            visited.add(root)
            pending: list[tuple[str, str | None]] = [(root, None)]
            while pending:
                node, came_from = pending.pop()
                for neighbour in state.adjacency.get(node, {}):
                    if neighbour == came_from:
                        continue
                    if neighbour in visited:
                        return True
                    visited.add(neighbour)
                    pending.append((neighbour, node))
        return False

    @staticmethod
    def topological_sort(state: GraphState[Any]) -> list[str]:
        """Kahn's algorithm; raises if the graph is undirected or cyclic."""
        if not state.directed:
            raise AlgorithmPreconditionError("topological sort requires a directed graph")
        indegree = dict.fromkeys(state.values, 0)
        for source, targets in state.adjacency.items():
            for target in targets:
                if target not in indegree:
                    raise InvariantViolationError(f"edge {source}->{target} targets unknown vertex")
                indegree[target] += 1
        queue = deque(node for node, degree in indegree.items() if degree == 0)
        result: list[str] = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for neighbour in state.adjacency.get(node, {}):
                indegree[neighbour] -= 1
                if indegree[neighbour] == 0:
                    queue.append(neighbour)
        if len(result) != len(state.values):
            raise AlgorithmPreconditionError("graph contains a cycle")
        return result


# ============================================================================
# capabilities/base.py
# ============================================================================
F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True, slots=True)
class _IdempotencyPlan:
    store: IdempotencyStore
    scope: IdempotencyScope
    fingerprint: str
    max_entries: int


def _stable_text(value: Any) -> str:
    """Comparable text for a call argument; callables compare by qualified name."""
    if callable(value):
        return f"<callable {getattr(value, '__module__', '?')}.{getattr(value, '__qualname__', repr(value))}>"
    return repr(value)


@dataclass(frozen=True, slots=True)
class OperationSpec:
    descriptor: AlgorithmDescriptor
    handler_name: str
    required_inputs: tuple[str, ...] = ()


def operation(descriptor: AlgorithmDescriptor, *, requires: tuple[str, ...] = ()) -> Callable[[F], F]:
    """Declare a handler ``(self, context, args) -> data`` for one descriptor."""

    def decorate(function: F) -> F:
        specs = list(getattr(function, "_dsa_operations", ()))
        specs.append((descriptor, requires))
        function._dsa_operations = tuple(specs)  # type: ignore[attr-defined]
        return function

    return decorate


class BaseDSACapability:
    capability: ClassVar[str] = "BASE"
    _operations: ClassVar[dict[tuple[str, str], OperationSpec]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        table: dict[tuple[str, str], OperationSpec] = {}
        for base in reversed(cls.__mro__[1:]):
            table.update(getattr(base, "_operations", {}))
        for attribute, member in vars(cls).items():
            for descriptor, requires in getattr(member, "_dsa_operations", ()):
                if descriptor.capability != cls.capability:
                    raise TypeError(
                        f"{cls.__name__}.{attribute}: descriptor capability "
                        f"{descriptor.capability!r} != {cls.capability!r}"
                    )
                for structure in descriptor.supported_structures:
                    table[(structure, descriptor.name)] = OperationSpec(descriptor, attribute, requires)
        cls._operations = table

    # ------------------------------------------------------------ public API
    @classmethod
    def operation_specs(cls) -> dict[tuple[str, str], OperationSpec]:
        return dict(cls._operations)

    def execute(
        self,
        *,
        operation: str,
        structure_type: str,
        state: Any,
        config: Mapping[str, Any] | None = None,
        correlation_id: str | None = None,
        tenant_id: str | None = None,
        idempotency_key: str | None = None,
        idempotency_store: IdempotencyStore | None = None,
        **kwargs: Any,
    ) -> OperationResult[Any]:
        context = self.__build_context(
            operation, structure_type, state, config, correlation_id, tenant_id, idempotency_key
        )
        started = MetricsUtility.start_timer()
        snapshot: Any = None
        try:
            spec = self.__resolve_operation(context)
            context.metadata["algorithm"] = {
                "name": spec.descriptor.name,
                "time_complexity": spec.descriptor.time_complexity,
                "space_complexity": spec.descriptor.space_complexity,
            }
            self.__validate_contract(context, spec, kwargs)
            plan = self.__plan_idempotency(context, spec, kwargs, idempotency_store)
            if plan is not None:
                recorded = plan.store.get(plan.scope)
                if recorded is not None:
                    return self.__replay(context, plan, recorded)
            self._validate_preconditions(context, **kwargs)
            verify = bool(self._setting(context, "verify_invariants", kwargs))
            if verify:
                self.__verify_structure(context, kwargs)
            snapshot = self.__snapshot(context, spec, kwargs, verify)
            self._before_execute(context, **kwargs)
            data = self._execute_core(context, **kwargs)
            if verify and spec.descriptor.mutates_state:
                self.__verify_structure(context, kwargs)
            self._validate_postconditions(context, data, **kwargs)
            self._after_execute(context, data, **kwargs)
            if spec.descriptor.returns_internal_reference and self._setting(context, "copy_on_read", kwargs):
                data = CopyUtility.snapshot(data)
            result = self._build_success_result(context, data, **kwargs)
            if plan is not None:
                plan.store.put(
                    plan.scope,
                    IdempotencyRecord(plan.fingerprint, context.state, result),
                    max_entries=plan.max_entries,
                )
            return result
        except Exception as exc:
            if snapshot is not None:
                CopyUtility.restore(context.state, snapshot)
                context.warn("ROLLED_BACK", "state restored to its pre-operation snapshot")
            return self._build_failure_result(context, exc, **kwargs)
        finally:
            MetricsUtility.stop_timer(context.metrics, started)

    # ------------------------------------------------------ protected hooks
    def _validate_preconditions(self, context: DSAExecutionContext, **kwargs: Any) -> None:
        pass

    def _before_execute(self, context: DSAExecutionContext, **kwargs: Any) -> None:
        pass

    def _execute_core(self, context: DSAExecutionContext, **kwargs: Any) -> Any:
        handler = getattr(self, self._spec(context).handler_name)
        return handler(context, kwargs)

    def _validate_postconditions(self, context: DSAExecutionContext, data: Any, **kwargs: Any) -> None:
        pass

    def _after_execute(self, context: DSAExecutionContext, data: Any, **kwargs: Any) -> None:
        pass

    def _build_success_result(
        self, context: DSAExecutionContext, data: Any, **kwargs: Any
    ) -> OperationResult[Any]:
        if context.found is False:
            return ResultBuilder.not_found(context.operation, context, data=data)
        return ResultBuilder.success(context.operation, data, context.affected_count, context.found, context)

    def _build_failure_result(
        self, context: DSAExecutionContext, error: Exception, **kwargs: Any
    ) -> OperationResult[Any]:
        if (
            isinstance(error, NotFoundError)
            and self._safe_setting(context, "missing_key_policy", kwargs) == "result"
        ):
            context.info("NOT_FOUND", str(error))
            return ResultBuilder.not_found(context.operation, context)
        if self._safe_setting(context, "validation_mode", kwargs) != "result":
            raise error
        return ResultBuilder.failure(context.operation, error, context)

    # ------------------------------------------------- protected utilities
    @staticmethod
    def _setting(
        context: DSAExecutionContext, key: str, kwargs: Mapping[str, Any], scope: str | None = None
    ) -> Any:
        return resolve_config(key, context.config, kwargs, scope=scope)

    @staticmethod
    def _safe_setting(context: DSAExecutionContext, key: str, kwargs: Mapping[str, Any]) -> Any:
        """Resolve without letting a bad value mask the original failure."""
        try:
            return resolve_config(key, context.config, kwargs)
        except ConfigurationError:
            return resolve_config(key)

    def _metrics(self, context: DSAExecutionContext, kwargs: Mapping[str, Any]) -> MetricsState | None:
        """The context metrics, or None (kernel uses a throwaway) when tracking is off."""
        return context.metrics if self._setting(context, "track_metrics", kwargs) else None

    def _spec(self, context: DSAExecutionContext) -> OperationSpec:
        return self._operations[(context.structure_type, context.operation)]

    # ----------------------------------------------------- private invariants
    def __build_context(
        self,
        operation: str,
        structure_type: str,
        state: Any,
        config: Mapping[str, Any] | None,
        correlation_id: str | None,
        tenant_id: str | None,
        idempotency_key: str | None,
    ) -> DSAExecutionContext:
        context = DSAExecutionContext(
            str(uuid.uuid4()),
            normalise_name(structure_type),
            self.capability,
            normalise_name(operation),
            state,
            MappingProxyType(dict(config or {})),
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
        )
        propagation = propagation_metadata(correlation_id, tenant_id, idempotency_key)
        if propagation:
            context.metadata["propagation"] = propagation
        return context

    def __resolve_operation(self, context: DSAExecutionContext) -> OperationSpec:
        spec = self._operations.get((context.structure_type, context.operation))
        if spec is None:
            raise UnsupportedOperationError(
                f"{type(self).__name__} does not support "
                f"{(context.structure_type, self.capability, context.operation)}"
            )
        return spec

    def __validate_contract(
        self, context: DSAExecutionContext, spec: OperationSpec, kwargs: Mapping[str, Any]
    ) -> None:
        if context.state is None:
            raise InvalidInputError("state is required")
        expected = STATE_TYPES.get(context.structure_type)
        if expected is not None and not isinstance(context.state, expected):
            raise InvalidInputError(
                f"{context.structure_type} requires {expected.__name__}, got {type(context.state).__name__}"
            )
        for field_name in ("correlation_id", "tenant_id", "idempotency_key"):
            value = getattr(context, field_name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise InvalidInputError(f"{field_name} must be a non-empty string when supplied")
        missing = [name for name in spec.required_inputs if name not in kwargs]
        if missing:
            raise InvalidInputError(f"{context.operation} requires inputs: {missing}")
        if self._setting(context, "strict_mode", kwargs):
            unknown = unknown_config_keys(context.config)
            if unknown:
                raise ConfigurationError(f"unknown config keys: {unknown}")

    def __plan_idempotency(
        self,
        context: DSAExecutionContext,
        spec: OperationSpec,
        kwargs: Mapping[str, Any],
        store: IdempotencyStore | None,
    ) -> _IdempotencyPlan | None:
        """Only mutations with a key are idempotent; the key is otherwise just echoed."""
        if context.idempotency_key is None or not spec.descriptor.mutates_state:
            return None
        if store is None:
            raise ConfigurationError("idempotency_key requires an idempotency_store")
        max_entries = self._setting(context, "idempotency_max_entries", kwargs)
        if max_entries < 1:
            raise ConfigurationError("idempotency_max_entries must be >= 1")
        parts = [context.structure_type, context.capability, context.operation]
        parts += [f"{name}={_stable_text(kwargs[name])}" for name in sorted(kwargs)]
        parts += [f"config.{name}={_stable_text(context.config[name])}" for name in sorted(context.config)]
        return _IdempotencyPlan(
            store, (context.tenant_id, context.idempotency_key), "|".join(parts), max_entries
        )

    @staticmethod
    def __replay(
        context: DSAExecutionContext, plan: _IdempotencyPlan, recorded: IdempotencyRecord
    ) -> OperationResult[Any]:
        if recorded.fingerprint != plan.fingerprint or recorded.state is not context.state:
            raise IdempotencyConflictError(
                f"idempotency_key {context.idempotency_key!r} was already used for a different request"
            )
        replayed = Message("INFO", "IDEMPOTENT_REPLAY", "recorded result returned; state not modified")
        return replace(
            recorded.result,
            messages=[*recorded.result.messages, replayed],
            metadata={**recorded.result.metadata, **context.metadata, "replayed": True},
        )

    def __verify_structure(self, context: DSAExecutionContext, kwargs: Mapping[str, Any]) -> None:
        validator = validator_for(context.structure_type, kwargs.get("key"))
        if validator is not None:
            validator.validate(context.state, raise_on_error=True)

    def __snapshot(
        self, context: DSAExecutionContext, spec: OperationSpec, kwargs: Mapping[str, Any], verify: bool
    ) -> Any:
        needs_rollback = spec.descriptor.mutates_state and (not spec.descriptor.atomic or verify)
        if needs_rollback and self._setting(context, "rollback_on_failure", kwargs):
            return CopyUtility.snapshot(context.state)
        return None


# ============================================================================
# capabilities/search.py
# ============================================================================
class SearchService(BaseDSACapability):
    """A miss is a valid outcome: it yields Status.NOT_FOUND, never an error."""

    capability = "SEARCH"

    def _validate_preconditions(self, context: DSAExecutionContext, **kwargs: Any) -> None:
        if (
            context.operation in {"BINARY", "LOWER_BOUND"}
            and self._setting(context, "strict_mode", kwargs)
            and not SearchAlgorithms.is_sorted(context.state.values, key=kwargs.get("key"))
        ):
            raise AlgorithmPreconditionError(f"{context.operation} requires input sorted by key")

    @operation(
        describe(
            "LINEAR",
            capability,
            "SEQUENCE",
            "O(n)",
            "O(1)",
            postconditions=("first matching index or NOT_FOUND",),
        ),
        requires=("target",),
    )
    def _linear(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int | None:
        index = SearchAlgorithms.linear(
            context.state.values, args["target"], key=args.get("key"), metrics=self._metrics(context, args)
        )
        context.found = index is not None
        return index

    @operation(
        describe(
            "BINARY",
            capability,
            "SEQUENCE",
            "O(log n); O(n) with strict_mode sortedness check",
            "O(1)",
            preconditions=("sequence sorted by key",),
            postconditions=("some matching index or NOT_FOUND",),
        ),
        requires=("target",),
    )
    def _binary(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int | None:
        index = SearchAlgorithms.binary(
            context.state.values, args["target"], key=args.get("key"), metrics=self._metrics(context, args)
        )
        context.found = index is not None
        return index

    @operation(
        describe(
            "LOWER_BOUND",
            capability,
            "SEQUENCE",
            "O(log n); O(n) with strict_mode",
            "O(1)",
            preconditions=("sequence sorted by key",),
            postconditions=(
                "first index with key >= target",
                "NOT_FOUND (still carrying that index) if absent",
            ),
        ),
        requires=("target",),
    )
    def _lower_bound(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        # NOT_FOUND still carries the insertion point as data.
        values, key = context.state.values, args.get("key")
        index = SearchAlgorithms.lower_bound(
            values, args["target"], key=key, metrics=self._metrics(context, args)
        )
        context.found = (
            index < len(values) and KeyResolver.resolve(values[index], key_function=key) == args["target"]
        )
        if not context.found:
            context.info("INSERTION_POINT", "target absent; data is its insertion point")
        return index

    @operation(
        describe("LOOKUP", capability, "BST", "O(h)", "O(1)", returns_internal_reference=True),
        requires=("target",),
    )
    def _bst_lookup(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        node = BSTAlgorithms.search(context.state, args["target"], key=args.get("key"))
        context.found = node is not None
        return node

    @operation(describe("CONTAINS", capability, "TRIE", "O(L)", "O(1)"), requires=("word",))
    def _trie_contains(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        context.found = TrieAlgorithms.search(context.state, args["word"])
        return context.found

    @operation(
        describe(
            "PREFIX",
            capability,
            "TRIE",
            "O(L + output)",
            "O(output)",
            postconditions=("lexicographic words; bounded by maximum_results",),
        ),
        requires=("prefix",),
    )
    def _trie_prefix(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[str]:
        words = TrieAlgorithms.autocomplete(
            context.state, args["prefix"], self._setting(context, "maximum_results", args)
        )
        context.found = bool(words)
        return words


# ============================================================================
# capabilities/ordering.py
# ============================================================================
class OrderingService(BaseDSACapability):
    capability = "ORDERING"

    def _validate_preconditions(self, context: DSAExecutionContext, **kwargs: Any) -> None:
        descriptor = self._spec(context).descriptor
        if self._setting(context, "stable_sort_required", kwargs) and not descriptor.stable:
            raise AlgorithmPreconditionError(f"{descriptor.name} is not stable and stable_sort_required=True")

    def _sort(
        self, context: DSAExecutionContext, args: Mapping[str, Any], kernel: Callable[..., list[Any]]
    ) -> list[Any]:
        result = kernel(context.state.values, key=args.get("key"), metrics=self._metrics(context, args))
        if self._setting(context, "mutate_in_place", args):
            context.state.values[:] = result
            context.affected_count = len(result)
        return result

    @operation(describe("BUBBLE", capability, "SEQUENCE", "O(n^2)", "O(n) copy", stable=True))
    def _bubble(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[Any]:
        return self._sort(context, args, SortAlgorithms.bubble)

    @operation(describe("MERGE", capability, "SEQUENCE", "O(n log n)", "O(n)", stable=True))
    def _merge(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[Any]:
        return self._sort(context, args, SortAlgorithms.merge)

    @operation(
        describe(
            "QUICK",
            capability,
            "SEQUENCE",
            "O(n log n) expected, O(n^2) worst",
            "O(n) copy + O(log n) stack",
            stable=False,
        )
    )
    def _quick(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[Any]:
        return self._sort(context, args, SortAlgorithms.quick)


# ============================================================================
# capabilities/traversal.py
# ============================================================================
#: Data-driven adapter selection; extend by registering a new structure here.
ADAPTER_FACTORIES: dict[str, Callable[[Any], NavigableAdapter[Any]]] = {
    "TREE": TreeAdapter,
    "GRAPH": GraphAdapter,
}


class TraversalService(BaseDSACapability):
    capability = "TRAVERSAL"

    def _walk(
        self, context: DSAExecutionContext, args: Mapping[str, Any], kernel: Callable[..., list[Any]]
    ) -> list[Any]:
        scope = f"{context.structure_type.title()}Traversal"
        track = self._setting(context, "track_visited", args, scope=scope)
        depth = self._setting(context, "maximum_depth", args)
        limit = self._setting(context, "maximum_results", args)
        if not track and context.structure_type == "GRAPH" and depth < 0 and limit < 0:
            raise AlgorithmPreconditionError(
                "track_visited=False on a graph needs maximum_depth or maximum_results >= 0; "
                "otherwise any cycle makes the traversal unbounded"
            )
        adapter = OrderedAdapter(
            ADAPTER_FACTORIES[context.structure_type](context.state),
            self._setting(context, "neighbour_order", args),
        )
        start = args.get("start")
        if start is None:
            start = next(iter(adapter.start_nodes()), None)
        if start is None:
            context.found = False
            return []
        return kernel(
            adapter,
            start,
            track_visited=track,
            maximum_depth=depth,
            maximum_results=limit,
            metrics=self._metrics(context, args),
        )

    @operation(describe("BFS", capability, {"TREE", "GRAPH"}, "O(V+E)", "O(V)"))
    def _bfs(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[Any]:
        return self._walk(context, args, TraversalAlgorithms.bfs)

    @operation(describe("DFS", capability, {"TREE", "GRAPH"}, "O(V+E)", "O(V)"))
    def _dfs(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[Any]:
        return self._walk(context, args, TraversalAlgorithms.dfs)


# ============================================================================
# capabilities/path.py
# ============================================================================
ENDPOINTS = ("source", "target")


class PathService(BaseDSACapability):
    """Unreachable targets yield NOT_FOUND; the empty path is still returned as data."""

    capability = "PATH"

    @operation(
        describe(
            "SHORTEST_UNWEIGHTED",
            capability,
            "GRAPH",
            "O(V+E)",
            "O(V)",
            postconditions=("minimum edge-count path or NOT_FOUND",),
        ),
        requires=ENDPOINTS,
    )
    def _shortest_unweighted(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[str]:
        path = GraphAlgorithms.shortest_unweighted_path(context.state, args["source"], args["target"])
        context.found = bool(path)
        return path

    @operation(
        describe(
            "DIJKSTRA",
            capability,
            "GRAPH",
            "O((V+E) log V)",
            "O(V)",
            preconditions=("all edge weights are non-negative",),
            postconditions=("(distance, path) or NOT_FOUND with (inf, [])",),
        ),
        requires=ENDPOINTS,
    )
    def _dijkstra(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> tuple[float, list[str]]:
        policy = self._setting(context, "dijkstra_negative_weight_policy", args)
        distance, path = GraphAlgorithms.dijkstra(
            context.state, args["source"], args["target"], negative_weight_policy=policy
        )
        context.found = bool(path)
        return distance, path

    @operation(
        describe(
            "ALL_SIMPLE_PATHS",
            capability,
            "GRAPH",
            "O(paths * V) bounded by maximum_paths",
            "O(V) stack per path",
        ),
        requires=ENDPOINTS,
    )
    def _all_simple_paths(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> list[list[str]]:
        bound = self._setting(context, "maximum_paths", args)
        paths = GraphAlgorithms.all_simple_paths(
            context.state, args["source"], args["target"], maximum_paths=bound
        )
        if 0 <= bound <= len(paths):
            context.warn("TRUNCATED", f"stopped after maximum_paths={bound}")
        context.found = bool(paths)
        return paths


# ============================================================================
# capabilities/query.py
# ============================================================================
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


# ============================================================================
# capabilities/mutation.py
# ============================================================================
def _m(name: str, structure: str, time: str = "O(1)", **extra: Any) -> Any:
    return describe(name, "MUTATION", structure, time, "O(1)", mutates=True, **extra)


class MutationService(BaseDSACapability):
    capability = "MUTATION"

    def _changed(self, context: DSAExecutionContext, count: int = 1) -> None:
        context.affected_count += count

    # -- sequence
    @operation(_m("INSERT", "SEQUENCE", "O(n)"), requires=("value",))
    def _seq_insert(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        SequenceRepository().create(ctx.state, args["value"], args.get("index"))
        self._changed(ctx)
        return len(ctx.state.values)

    @operation(_m("UPDATE", "SEQUENCE"), requires=("index", "value"))
    def _seq_update(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        SequenceRepository().update(ctx.state, args["index"], args["value"])
        self._changed(ctx)

    @operation(_m("DELETE", "SEQUENCE", "O(n)"), requires=("index",))
    def _seq_delete(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        value = SequenceRepository().delete(ctx.state, args["index"])
        self._changed(ctx)
        return value

    # -- linked list
    @operation(_m("APPEND", "LINKED_LIST"), requires=("value",))
    def _ll_append(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> str:
        node_id = LinkedListRepository().append(ctx.state, args["value"], args.get("node_id"))
        self._changed(ctx)
        return node_id

    @operation(_m("PREPEND", "LINKED_LIST"), requires=("value",))
    def _ll_prepend(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> str:
        node_id = LinkedListRepository().prepend(ctx.state, args["value"], args.get("node_id"))
        self._changed(ctx)
        return node_id

    @operation(_m("DELETE", "LINKED_LIST"), requires=("node_id",))
    def _ll_delete(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        node = LinkedListRepository().delete(ctx.state, args["node_id"])
        self._changed(ctx)
        return node

    @operation(_m("REVERSE", "LINKED_LIST", "O(n)"))
    def _ll_reverse(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        LinkedListAlgorithms.reverse(ctx.state)
        self._changed(ctx, ctx.state.size)

    # -- stack / queue (capacity config is the fallback bound)
    @operation(_m("PUSH", "STACK"), requires=("value",))
    def _push(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        StackRepository().push(ctx.state, args["value"], capacity=self._setting(ctx, "capacity", args))
        self._changed(ctx)

    @operation(_m("POP", "STACK"))
    def _pop(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        value = StackRepository().pop(ctx.state)
        self._changed(ctx)
        return value

    @operation(_m("ENQUEUE", "QUEUE"), requires=("value",))
    def _enqueue(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        QueueRepository().enqueue(ctx.state, args["value"], capacity=self._setting(ctx, "capacity", args))
        self._changed(ctx)

    @operation(_m("DEQUEUE", "QUEUE"))
    def _dequeue(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        value = QueueRepository().dequeue(ctx.state)
        self._changed(ctx)
        return value

    # -- tree
    @operation(_m("ADD_ROOT", "TREE"), requires=("node_id", "value"))
    def _add_root(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        TreeRepository().add_root(ctx.state, args["node_id"], args["value"])
        self._changed(ctx)

    @operation(_m("ADD_CHILD", "TREE"), requires=("parent_id", "node_id", "value"))
    def _add_child(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        added = TreeRepository().add_child(
            ctx.state,
            args["parent_id"],
            args["node_id"],
            args["value"],
            on_duplicate=self._setting(ctx, "duplicate_policy", args),
        )
        self._changed(ctx, 1 if added else 0)
        return added

    @operation(_m("DELETE_SUBTREE", "TREE", "O(subtree)"), requires=("node_id",))
    def _delete_subtree(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> list[str]:
        removed = TreeRepository().delete_subtree(ctx.state, args["node_id"])
        self._changed(ctx, len(removed))
        return removed

    # -- BST (bst_balance_policy selects plain or AVL kernels)
    @operation(_m("INSERT", "BST", "O(h)"), requires=("value",))
    def _bst_insert(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> str:
        avl = self._setting(ctx, "bst_balance_policy", args) == "avl"
        kernel = BSTAlgorithms.insert_avl if avl else BSTAlgorithms.insert
        size = len(ctx.state.nodes)
        node_id = kernel(
            ctx.state,
            args["value"],
            key=args.get("key"),
            node_id=args.get("node_id"),
            on_duplicate=self._setting(ctx, "duplicate_policy", args),
        )
        self._changed(ctx, len(ctx.state.nodes) - size)
        return node_id

    @operation(_m("DELETE", "BST", "O(h)"), requires=("target",))
    def _bst_delete(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> Any:
        avl = self._setting(ctx, "bst_balance_policy", args) == "avl"
        node = BSTAlgorithms.delete(ctx.state, args["target"], key=args.get("key"), rebalance=avl)
        self._changed(ctx)
        return node

    # -- trie
    @operation(_m("INSERT", "TRIE", "O(L)"), requires=("word",))
    def _trie_insert(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        added = TrieAlgorithms.insert(ctx.state, args["word"])
        self._changed(ctx, int(added))
        return added

    @operation(_m("DELETE", "TRIE", "O(L)"), requires=("word",))
    def _trie_delete(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        if not TrieAlgorithms.delete(ctx.state, args["word"]):
            raise NotFoundError(f"word not found: {args['word']!r}")
        self._changed(ctx)
        return True

    # -- graph
    @operation(_m("ADD_VERTEX", "GRAPH"), requires=("vertex_id", "value"))
    def _add_vertex(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> bool:
        added = GraphRepository().add_vertex(
            ctx.state,
            args["vertex_id"],
            args["value"],
            on_duplicate=self._setting(ctx, "duplicate_policy", args),
        )
        self._changed(ctx, int(added))
        return added

    @operation(_m("ADD_EDGE", "GRAPH"), requires=("source", "target"))
    def _add_edge(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        GraphRepository().add_edge(ctx.state, args["source"], args["target"], args.get("weight", 1.0))
        self._changed(ctx)

    @operation(_m("REMOVE_EDGE", "GRAPH"), requires=("source", "target"))
    def _remove_edge(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        GraphRepository().remove_edge(ctx.state, args["source"], args["target"])
        self._changed(ctx)

    @operation(_m("REMOVE_VERTEX", "GRAPH", "O(V+E)"), requires=("vertex_id",))
    def _remove_vertex(self, ctx: DSAExecutionContext, args: Mapping[str, Any]) -> None:
        GraphRepository().remove_vertex(ctx.state, args["vertex_id"])
        self._changed(ctx)


# ============================================================================
# capabilities/validation.py
# ============================================================================
class ValidationService(BaseDSACapability):
    capability = "VALIDATION"

    @operation(describe("VALIDATE", capability, set(VALIDATORS), "O(n) / O(V+E)", "O(n)"))
    def _validate(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> ValidationReport:
        validator = validator_for(context.structure_type, args.get("key"))
        report: ValidationReport = validator.validate(
            context.state, raise_on_error=bool(args.get("raise_on_error", False))
        )
        if not report.valid:
            context.warn("INVARIANT_VIOLATIONS", f"{len(report.violations)} violation(s)")
        return report


# ============================================================================
# facade.py
# ============================================================================
RegistryKey = tuple[str, str, str]


class CapabilityRegistry:
    """(structure, capability, operation) -> service instance + descriptor."""

    def __init__(self) -> None:
        self._registry: dict[RegistryKey, BaseDSACapability] = {}

    @staticmethod
    def _key(structure_type: str | Enum, capability: str | Enum, operation: str | Enum) -> RegistryKey:
        return normalise_name(structure_type), normalise_name(capability), normalise_name(operation)

    def register(
        self,
        structure_type: str | Enum,
        capability: str | Enum,
        operation: str | Enum,
        implementation: BaseDSACapability,
        *,
        replace: bool = False,
    ) -> None:
        key = self._key(structure_type, capability, operation)
        if key[1] != implementation.capability:
            raise ValueError(
                f"{type(implementation).__name__} provides {implementation.capability}, not {key[1]}"
            )
        if (key[0], key[2]) not in implementation.operation_specs():
            raise ValueError(f"{type(implementation).__name__} declares no operation {key[2]} for {key[0]}")
        existing = self._registry.get(key)
        if existing is not None and not replace and type(existing) is not type(implementation):
            raise ValueError(f"Capability already registered differently: {key}; pass replace=True")
        self._registry[key] = implementation

    def register_service(self, implementation: BaseDSACapability, *, replace: bool = False) -> None:
        """Register every operation the service declares."""
        for structure_type, operation in implementation.operation_specs():
            self.register(
                structure_type, implementation.capability, operation, implementation, replace=replace
            )

    def resolve(
        self, structure_type: str | Enum, capability: str | Enum, operation: str | Enum
    ) -> BaseDSACapability:
        key = self._key(structure_type, capability, operation)
        try:
            return self._registry[key]
        except KeyError as exc:
            raise UnsupportedOperationError(f"Unsupported capability: {key}") from exc

    def supports(self, structure_type: str | Enum, capability: str | Enum, operation: str | Enum) -> bool:
        return self._key(structure_type, capability, operation) in self._registry

    def describe(
        self, structure_type: str | Enum, capability: str | Enum, operation: str | Enum
    ) -> AlgorithmDescriptor:
        structure, _, op = self._key(structure_type, capability, operation)
        service = self.resolve(structure_type, capability, operation)
        return service.operation_specs()[(structure, op)].descriptor

    def list_capabilities(self, structure_type: str | Enum | None = None) -> list[RegistryKey]:
        items = sorted(self._registry)
        if structure_type is None:
            return items
        wanted = normalise_name(structure_type)
        return [item for item in items if item[0] == wanted]

    def metadata(self) -> AlgorithmMetadataRegistry:
        registry = AlgorithmMetadataRegistry()
        for key in self._registry:
            registry.register(self.describe(*key))
        return registry


def build_default_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    for service in (
        SearchService(),
        OrderingService(),
        TraversalService(),
        PathService(),
        QueryService(),
        MutationService(),
        ValidationService(),
    ):
        registry.register_service(service)
    return registry


def build_algorithm_metadata() -> AlgorithmMetadataRegistry:
    """Descriptors for every operation in the default registry (consistent by construction)."""
    return build_default_registry().metadata()


class DSAFacade:
    """The single governed entry point.

    ``correlation_id``, ``tenant_id`` and ``idempotency_key`` are optional
    request-scoped identifiers. They are passed through to the result under
    ``metadata["propagation"]``. ``tenant_id`` is a label only: it namespaces
    idempotency keys but isolates no data. A keyed mutation is applied once per
    ``(tenant_id, idempotency_key)``; see :mod:`capability_oriented_dsa.core.idempotency`.
    """

    def __init__(
        self,
        registry: CapabilityRegistry | None = None,
        *,
        idempotency_store: IdempotencyStore | None = None,
    ) -> None:
        self.registry = registry or build_default_registry()
        # ``is None``, not ``or``: an empty store is falsy because it defines __len__.
        self.idempotency_store: IdempotencyStore = (
            InMemoryIdempotencyStore() if idempotency_store is None else idempotency_store
        )

    def execute(
        self,
        *,
        structure_type: str | Enum,
        capability: str | Enum,
        operation: str | Enum,
        state: Any,
        config: Mapping[str, Any] | None = None,
        correlation_id: str | None = None,
        tenant_id: str | None = None,
        idempotency_key: str | None = None,
        **kwargs: Any,
    ) -> OperationResult[Any]:
        try:
            implementation = self.registry.resolve(structure_type, capability, operation)
        except UnsupportedOperationError as exc:
            return self._routing_failure(
                structure_type,
                capability,
                operation,
                config,
                kwargs,
                exc,
                propagation_metadata(correlation_id, tenant_id, idempotency_key),
            )
        return implementation.execute(
            operation=normalise_name(operation),
            structure_type=normalise_name(structure_type),
            state=state,
            config=config,
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            idempotency_store=self.idempotency_store,
            **kwargs,
        )

    def describe(
        self, structure_type: str | Enum, capability: str | Enum, operation: str | Enum
    ) -> AlgorithmDescriptor:
        return self.registry.describe(structure_type, capability, operation)

    def capabilities(self, structure_type: str | Enum | None = None) -> list[RegistryKey]:
        return self.registry.list_capabilities(structure_type)

    @staticmethod
    def _routing_failure(
        structure_type: str | Enum,
        capability: str | Enum,
        operation: str | Enum,
        config: Mapping[str, Any] | None,
        kwargs: Mapping[str, Any],
        error: UnsupportedOperationError,
        propagation: Mapping[str, str],
    ) -> OperationResult[Any]:
        """Routing errors honour validation_mode like every other failure."""
        try:
            mode = resolve_config("validation_mode", config, kwargs)
        except ConfigurationError:
            mode = "raise"
        if mode != "result":
            raise error
        context = DSAExecutionContext(
            "routing",
            normalise_name(structure_type),
            normalise_name(capability),
            normalise_name(operation),
            None,
            dict(config or {}),
        )
        if propagation:
            context.metadata["propagation"] = dict(propagation)
        return ResultBuilder.failure(context.operation, error, context)


__all__ = [
    'DSAError',
    'InvalidInputError',
    'NotFoundError',
    'DuplicateKeyError',
    'IdempotencyConflictError',
    'InvariantViolationError',
    'UnsupportedOperationError',
    'CapacityExceededError',
    'AlgorithmPreconditionError',
    'ConfigurationError',
    'error_code',
    'ConfigKey',
    'DSA_CONFIG',
    'UNSET',
    'register_config_key',
    'resolve_config',
    'unknown_config_keys',
    'Status',
    'Message',
    'ErrorDetail',
    'MetricsState',
    'OperationResult',
    'ValidationReport',
    'DSAExecutionContext',
    'IdempotencyStore',
    'IdempotencyRecord',
    'InMemoryIdempotencyStore',
    'ResultBuilder',
    'MetricsUtility',
    'AlgorithmDescriptor',
    'AlgorithmMetadataRegistry',
    'describe',
    'KeyResolver',
    'PredicateUtility',
    'CopyUtility',
    'CapacityUtility',
    'PathUtility',
    'StructureType',
    'CapabilityName',
    'STATE_TYPES',
    'SequenceState',
    'LinkedNode',
    'LinkedListState',
    'StackState',
    'QueueState',
    'TreeState',
    'BSTNode',
    'BSTState',
    'TrieNode',
    'TrieState',
    'GraphState',
    'NavigableAdapter',
    'TreeAdapter',
    'GraphAdapter',
    'OrderedAdapter',
    'Validator',
    'SequenceValidator',
    'ContainerValidator',
    'LinkedListValidator',
    'TreeValidator',
    'BSTValidator',
    'TrieValidator',
    'GraphValidator',
    'VALIDATORS',
    'validator_for',
    'SearchAlgorithms',
    'SortAlgorithms',
    'TraversalAlgorithms',
    'SequenceAlgorithms',
    'LinkedListAlgorithms',
    'StackAlgorithms',
    'QueueAlgorithms',
    'TreeAlgorithms',
    'BSTAlgorithms',
    'TrieAlgorithms',
    'GraphAlgorithms',
    'SequenceRepository',
    'LinkedListRepository',
    'StackRepository',
    'QueueRepository',
    'TreeRepository',
    'GraphRepository',
    'BaseDSACapability',
    'OperationSpec',
    'operation',
    'SearchService',
    'OrderingService',
    'TraversalService',
    'PathService',
    'QueryService',
    'MutationService',
    'ValidationService',
    'ADAPTER_FACTORIES',
    'CapabilityRegistry',
    'DSAFacade',
    'build_default_registry',
    'build_algorithm_metadata',
    '__version__',
]
