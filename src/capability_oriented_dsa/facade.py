"""Capability registry, default wiring and the unified facade."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any

from .capabilities.base import BaseDSACapability
from .capabilities.mutation import MutationService
from .capabilities.ordering import OrderingService
from .capabilities.path import PathService
from .capabilities.query import QueryService
from .capabilities.search import SearchService
from .capabilities.traversal import TraversalService
from .capabilities.validation import ValidationService
from .core.config import resolve_config
from .core.errors import ConfigurationError, UnsupportedOperationError
from .core.idempotency import IdempotencyStore, InMemoryIdempotencyStore
from .core.metadata import AlgorithmDescriptor, AlgorithmMetadataRegistry
from .core.results import DSAExecutionContext, OperationResult, ResultBuilder, propagation_metadata
from .structures.states import normalise_name

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
