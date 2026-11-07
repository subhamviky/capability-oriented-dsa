"""Algorithm descriptors.

A descriptor is the single source of truth for an operation's contract. The
capability registry is built *from* descriptors, so every routable operation
is guaranteed to have one.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import UnsupportedOperationError


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
