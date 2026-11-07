"""Governed capability lifecycle.

``BaseDSACapability.execute`` is the single public entry point. Subclasses
declare operations with the ``@operation(descriptor)`` decorator; the base
class builds an operation table keyed by ``(structure_type, operation)`` and
dispatches through it, so services contain no ``if operation == ...`` routing.

Lifecycle (public -> protected -> private)::

    execute()
      __build_context            private   request-scoped context, frozen config
      __resolve_operation        private   operation table lookup
      __validate_contract        private   state type, required inputs, config keys
      _validate_preconditions    protected capability-specific checks
      __verify_structure (pre)   private   optional full invariant check
      __snapshot                 private   rollback point for non-atomic mutations
      _before_execute            protected
      _execute_core              protected dispatches to the declared handler
      __verify_structure (post)  private   after mutations
      _validate_postconditions   protected
      _after_execute             protected
      _build_success_result      protected
      on failure: rollback -> _build_failure_result (missing_key_policy, validation_mode)
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, ClassVar, TypeVar

from ..core.config import resolve_config, unknown_config_keys
from ..core.errors import (
    ConfigurationError,
    IdempotencyConflictError,
    InvalidInputError,
    NotFoundError,
    UnsupportedOperationError,
)
from ..core.idempotency import IdempotencyRecord, IdempotencyScope, IdempotencyStore
from ..core.metadata import AlgorithmDescriptor
from ..core.results import (
    DSAExecutionContext,
    Message,
    MetricsState,
    MetricsUtility,
    OperationResult,
    ResultBuilder,
    propagation_metadata,
)
from ..core.utilities import CopyUtility
from ..structures.states import STATE_TYPES, normalise_name
from ..validation.validators import validator_for

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
