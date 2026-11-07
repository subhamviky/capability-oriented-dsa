"""Framework exception hierarchy.

Every exception carries a stable ``code`` so that structured failure results
(``validation_mode="result"``) expose a machine-readable error code instead of
an exception class name.
"""

from __future__ import annotations

from typing import ClassVar


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
