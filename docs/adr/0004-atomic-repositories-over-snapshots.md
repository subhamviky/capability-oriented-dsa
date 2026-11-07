# ADR 0004: Atomic mutations instead of a snapshot per call

- Status: accepted

## Context

`rollback_on_failure` defaults to true. The obvious implementation, deep-copying state before every mutation, would turn building an
n-element structure through the facade into O(n²).

## Decision

Repositories and mutating kernels validate before their first write, so a
raised exception leaves state untouched. Descriptors declare `atomic=True` by
default. The lifecycle snapshots state only when a mutation is declared
`atomic=False` (typically an extension) or when `verify_invariants` is on,
because the post-mutation check can fail after the write. On failure the
snapshot is restored in place and a `ROLLED_BACK` warning is attached to the
result.

## Consequences

Default governed mutations stay O(operation). Extension authors must either
keep their kernels atomic or declare `atomic=False`.
