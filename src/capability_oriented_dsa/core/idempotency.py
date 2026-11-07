"""Idempotency store port and a bounded in-memory implementation.

A governed mutation called twice with the same ``idempotency_key`` (and the
same ``tenant_id`` namespace) is applied once; the repeat returns the recorded
result. The built-in store is process-local and not durable: a restart forgets
every key, so it models the contract rather than providing exactly-once
delivery. Supply your own :class:`IdempotencyStore` to change that.

It is also **not safe for concurrent callers**. Replay is a lookup, then the
mutation, then a record, and that sequence is not an atomic claim, so two
simultaneous calls with the same key can both apply. Use it for sequential
retries, or put an atomic claim in front of the mutation.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Protocol

from .results import OperationResult

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
