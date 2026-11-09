"""SEARCH capability: positional and keyed lookups."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..algorithms.bst import BSTAlgorithms
from ..algorithms.search import SearchAlgorithms
from ..algorithms.trie import TrieAlgorithms
from ..core.errors import AlgorithmPreconditionError
from ..core.metadata import describe
from ..core.results import DSAExecutionContext
from ..core.utilities import KeyResolver
from .base import BaseDSACapability, operation


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

    @operation(
        describe(
            "FIRST_TRUE",
            capability,
            "SEQUENCE",
            "O(log n) predicate calls",
            "O(1)",
            preconditions=("predicate is monotone over the sequence: False..., then True...",),
            postconditions=("index of the first True, or NOT_FOUND carrying len(values)",),
        ),
        requires=("predicate",),
    )
    def _first_true(self, context: DSAExecutionContext, args: Mapping[str, Any]) -> int:
        values = context.state.values
        index = SearchAlgorithms.first_true(values, args["predicate"], metrics=self._metrics(context, args))
        context.found = index < len(values)
        return index
