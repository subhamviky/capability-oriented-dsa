"""Central configuration registry.

Resolution order (highest wins)::

    kwargs > config mapping > environment variable > scoped default > default

Every source is passed through the key's ``cast`` and checked against its
``choices``, so ``config={"mutate_in_place": "false"}`` behaves the same as the
environment variable ``DSA_MUTATE_IN_PLACE=false``.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .errors import ConfigurationError

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
