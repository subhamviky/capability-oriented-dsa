# ADR 0005: Core structures and families, derived approaches

## Status

Accepted.

## Context

Interview-style problems draw on structures (heap, union-find), approaches
(dynamic programming, greedy, backtracking) and patterns (hashing, windows).
Treating all of them as peers would make the package a flat catalogue, and
adding a structure for each approach would invent state that does not exist.

## Decision

- A **core** concept has its own state type, a validator and governed operations: sequence, linked list, stack, queue, tree, BST, trie, graph, heap, union-find.
- A **derived** concept reuses a core structure and adds no state. Approaches get their own capability when they form a family with shared limits (`OPTIMIZATION`, `ENUMERATION`); patterns stay as `QUERY` or `SEARCH` operations.
- A hash map is not a state type. `dict` and `set` are already the structure; hashing is represented by its patterns.
- Derived approaches that can blow up are bounded by registered configuration (`dp_max_cells`, `enumeration_limit`, `enumeration_max_nodes`) and say when they truncate.
- `docs/interview-patterns.md` is the map, and a test fails if a registered operation is missing from its index.

## Consequences

- New structures need a state type, validator, registration and tour test; new approaches need only a kernel, a descriptor and a registration.
- The package stays an architecture reference. Covering more problem types is a matter of adding kernels, and the "Not covered" list in the map is the honest backlog.
