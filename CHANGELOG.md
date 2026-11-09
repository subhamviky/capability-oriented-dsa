# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Two core structures: `HEAP` (`HeapState`; push, pop, peek) and `UNION_FIND` (`UnionFindState`; add, union, find, connected, component count), each with a validator.
- Derived approaches over a sequence: hashing patterns (duplicates, frequency, anagram groups, longest consecutive run, subarray-sum count, first unique), two pointers and windows (sorted pair sum, longest unique window, shortest subarray, max area), heap patterns (`TOP_K`, `MERGE_SORTED`) and `SEARCH / FIRST_TRUE` for binary search on an answer.
- New capabilities `OPTIMIZATION` (dynamic programming: house robber, longest increasing subsequence, coin change, 0/1 knapsack, longest common subsequence, edit distance; greedy: merge intervals, max non-overlapping, jump game) and `ENUMERATION` (backtracking: subsets, permutations, combinations, combination sum), plus an `n_queens` kernel.
- Three configuration keys bounding the derived approaches: `dp_max_cells`, `enumeration_limit`, `enumeration_max_nodes` (22 keys in total, 100 governed operations).
- `docs/interview-patterns.md`: core versus derived concepts, common problems mapped to operations, and what is not covered.

## [0.1.0] - 2026-11-07

Initial release.

- Layered package (`core`, `structures`, `validation`, `algorithms`, `capabilities`, `facade`) plus a generated single-file edition (`standalone/dsa_framework.py`).
- Explicit state for sequence, linked list, stack, queue, tree, BST, trie and graph; atomic repositories; iterative validators for every structure.
- Direct kernels: linear/binary/lower-bound search; bubble/merge/quick sort; BFS/DFS over a `NavigableAdapter` port; two-sum, Kadane, prefix sums, next-greater, sliding-window maximum; linked-list reverse/middle/cycle; tree height/diameter/ancestors/LCA; plain and AVL BST insert/delete; trie insert/delete/autocomplete; BFS shortest path, Dijkstra with negative-weight policies, bounded all-simple-paths, cycle detection, topological sort.
- Governed layer: `DSAFacade`, `CapabilityRegistry`, `BaseDSACapability` lifecycle, `@operation(descriptor)` declarations, 64 operations across SEARCH, ORDERING, TRAVERSAL, PATH, QUERY, MUTATION and VALIDATION.
- 19 configuration keys resolved as `kwargs > config > env > scoped default > default`, cast and validated.
- Optional request identifiers on every governed call: `correlation_id` and `tenant_id` pass through to `metadata["propagation"]`; `idempotency_key` makes a keyed mutation apply once per `(tenant_id, key)` for sequential retries, with a bounded, pluggable, in-memory `IdempotencyStore`.
- Structured results with `SUCCESS` / `NOT_FOUND` / `FAILURE`, stable error codes, metrics and rollback.
- Tests run against both editions, including Hypothesis property tests. CI covers Ruff, `mypy --strict`, standalone freshness, Python 3.11 to 3.13 plus Windows/macOS, coverage, a wheel check, and a tag-driven release.
