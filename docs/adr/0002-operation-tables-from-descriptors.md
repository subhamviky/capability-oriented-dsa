# ADR 0002: Operations are declared with descriptors; dispatch is a table lookup

- Status: accepted

## Context

Routing through a registry only removes conditionals if the services behind it
don't branch on the operation again. Algorithm metadata kept in a separate
registry can also drift from what is actually routable.

## Decision

A service method is marked `@operation(describe(...), requires=(...))`.
`BaseDSACapability.__init_subclass__` collects these into a class-level table
keyed by `(structure, operation)`. `_execute_core` looks the handler up.
`CapabilityRegistry.register_service` registers every declared key, and
`CapabilityRegistry.metadata()` derives the `AlgorithmMetadataRegistry`.

## Consequences

- Adding an operation means adding a method, with no edits to existing branches.
- Every routable operation has a descriptor by construction.
- Required inputs are validated before the kernel runs.
- One operation name can have different kernels per structure. Metadata
  lookup takes `structure=` to disambiguate.
- `_execute_core` remains a protected hook, so a service with an unusual
  lifecycle can still override it.
