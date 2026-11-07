"""ORDERING capability: sorting with explicit stability and mutation policy."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ..algorithms.sorting import SortAlgorithms
from ..core.errors import AlgorithmPreconditionError
from ..core.metadata import describe
from ..core.results import DSAExecutionContext
from .base import BaseDSACapability, operation


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
