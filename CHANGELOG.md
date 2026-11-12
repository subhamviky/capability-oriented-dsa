# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.0] - 2026-11-12

Wave C, design note C-03: what the reconciliation engine needed.

### Added
- `OperationResult.complete`: `False` when a bound (`enumeration_limit`, `max_nodes`) cut the work short, so a truncated answer cannot pass for a complete one; the status stays `SUCCESS` and `metadata["truncated"]` stays (S-2).
- `SEQUENCE / OPTIMIZATION / SUBSET_SUM(target, max_nodes=…, scale=…)`: the smallest subset (ties: lowest indices) adding up exactly to the target, each element used at most once; `NOT_FOUND` when none exists; a pruned search instead of enumerating every subset (S-3).
- `UNION_FIND / MUTATION / ADD_ALL(elements)` and `GROUP_BY_KEYS(elements, keys, element_id=…)`: connect elements that share any key in O(n · k) with a key index, and return the groups (S-4). It is a MUTATION (it connects elements in the state you pass), not a QUERY as the design note first said.
- Decimal values with a declared `scale` for `SUBSET_SUM` and `KNAPSACK_01`; more fraction digits than the scale is refused, never rounded (S-5).
- `tests/test_v03.py`: property tests against brute force and pairwise unions.

## [0.2.1] - 2026-11-12

### Changed

- CI uses Node-24 action versions (`actions/checkout@v6`, `actions/setup-python@v6`, `actions/upload-artifact@v6`).
- Dependabot groups the pinned dev tools (ruff, mypy, pytest, hypothesis, build) into one pull request, so their adjacent pins no longer conflict, and groups action updates.

## [0.2.0] - 2026-11-10

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
