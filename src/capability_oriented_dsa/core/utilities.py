"""Concrete, stateless helpers shared by kernels, repositories and services."""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from typing import Any, TypeVar

from .config import UNSET
from .errors import CapacityExceededError, InvalidInputError, InvariantViolationError

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
