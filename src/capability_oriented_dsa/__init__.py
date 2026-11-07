"""Capability-Oriented DSA.

Direct algorithm kernels over explicit state, plus an optional governed
execution layer (``DSAFacade``) adding configuration, validation, metrics and
structured results. Every name in ``__all__`` is public API; module paths
below this package are an implementation detail and may move.
"""

from __future__ import annotations

from .algorithms.bst import BSTAlgorithms
from .algorithms.graphs import GraphAlgorithms
from .algorithms.linked_list import LinkedListAlgorithms
from .algorithms.search import SearchAlgorithms
from .algorithms.sequences import QueueAlgorithms, SequenceAlgorithms, StackAlgorithms
from .algorithms.sorting import SortAlgorithms
from .algorithms.traversal import TraversalAlgorithms
from .algorithms.trees import TreeAlgorithms
from .algorithms.trie import TrieAlgorithms
from .capabilities.base import BaseDSACapability, OperationSpec, operation
from .capabilities.mutation import MutationService
from .capabilities.ordering import OrderingService
from .capabilities.path import PathService
from .capabilities.query import QueryService
from .capabilities.search import SearchService
from .capabilities.traversal import ADAPTER_FACTORIES, TraversalService
from .capabilities.validation import ValidationService
from .core.config import (
    DSA_CONFIG,
    UNSET,
    ConfigKey,
    register_config_key,
    resolve_config,
    unknown_config_keys,
)
from .core.errors import (
    AlgorithmPreconditionError,
    CapacityExceededError,
    ConfigurationError,
    DSAError,
    DuplicateKeyError,
    IdempotencyConflictError,
    InvalidInputError,
    InvariantViolationError,
    NotFoundError,
    UnsupportedOperationError,
    error_code,
)
from .core.idempotency import IdempotencyRecord, IdempotencyStore, InMemoryIdempotencyStore
from .core.metadata import AlgorithmDescriptor, AlgorithmMetadataRegistry, describe
from .core.results import (
    DSAExecutionContext,
    ErrorDetail,
    Message,
    MetricsState,
    MetricsUtility,
    OperationResult,
    ResultBuilder,
    Status,
    ValidationReport,
)
from .core.utilities import CapacityUtility, CopyUtility, KeyResolver, PathUtility, PredicateUtility
from .facade import CapabilityRegistry, DSAFacade, build_algorithm_metadata, build_default_registry
from .structures.adapters import GraphAdapter, NavigableAdapter, OrderedAdapter, TreeAdapter
from .structures.repositories import (
    GraphRepository,
    LinkedListRepository,
    QueueRepository,
    SequenceRepository,
    StackRepository,
    TreeRepository,
)
from .structures.states import (
    STATE_TYPES,
    BSTNode,
    BSTState,
    CapabilityName,
    GraphState,
    LinkedListState,
    LinkedNode,
    QueueState,
    SequenceState,
    StackState,
    StructureType,
    TreeState,
    TrieNode,
    TrieState,
)
from .validation.validators import (
    VALIDATORS,
    BSTValidator,
    ContainerValidator,
    GraphValidator,
    LinkedListValidator,
    SequenceValidator,
    TreeValidator,
    TrieValidator,
    Validator,
    validator_for,
)

__version__ = "0.1.0"

__all__ = [
    # errors
    "DSAError",
    "InvalidInputError",
    "NotFoundError",
    "DuplicateKeyError",
    "IdempotencyConflictError",
    "InvariantViolationError",
    "UnsupportedOperationError",
    "CapacityExceededError",
    "AlgorithmPreconditionError",
    "ConfigurationError",
    "error_code",
    # configuration
    "ConfigKey",
    "DSA_CONFIG",
    "UNSET",
    "register_config_key",
    "resolve_config",
    "unknown_config_keys",
    # results & metadata
    "Status",
    "Message",
    "ErrorDetail",
    "MetricsState",
    "OperationResult",
    "ValidationReport",
    "DSAExecutionContext",
    "IdempotencyStore",
    "IdempotencyRecord",
    "InMemoryIdempotencyStore",
    "ResultBuilder",
    "MetricsUtility",
    "AlgorithmDescriptor",
    "AlgorithmMetadataRegistry",
    "describe",
    # utilities
    "KeyResolver",
    "PredicateUtility",
    "CopyUtility",
    "CapacityUtility",
    "PathUtility",
    # state
    "StructureType",
    "CapabilityName",
    "STATE_TYPES",
    "SequenceState",
    "LinkedNode",
    "LinkedListState",
    "StackState",
    "QueueState",
    "TreeState",
    "BSTNode",
    "BSTState",
    "TrieNode",
    "TrieState",
    "GraphState",
    # ports & adapters
    "NavigableAdapter",
    "TreeAdapter",
    "GraphAdapter",
    "OrderedAdapter",
    # validators
    "Validator",
    "SequenceValidator",
    "ContainerValidator",
    "LinkedListValidator",
    "TreeValidator",
    "BSTValidator",
    "TrieValidator",
    "GraphValidator",
    "VALIDATORS",
    "validator_for",
    # kernels
    "SearchAlgorithms",
    "SortAlgorithms",
    "TraversalAlgorithms",
    "SequenceAlgorithms",
    "LinkedListAlgorithms",
    "StackAlgorithms",
    "QueueAlgorithms",
    "TreeAlgorithms",
    "BSTAlgorithms",
    "TrieAlgorithms",
    "GraphAlgorithms",
    # repositories
    "SequenceRepository",
    "LinkedListRepository",
    "StackRepository",
    "QueueRepository",
    "TreeRepository",
    "GraphRepository",
    # governed layer
    "BaseDSACapability",
    "OperationSpec",
    "operation",
    "SearchService",
    "OrderingService",
    "TraversalService",
    "PathService",
    "QueryService",
    "MutationService",
    "ValidationService",
    "ADAPTER_FACTORIES",
    "CapabilityRegistry",
    "DSAFacade",
    "build_default_registry",
    "build_algorithm_metadata",
    "__version__",
]
