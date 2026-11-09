# Configuration reference

Every governed call resolves each key with the same precedence:

```text
kwargs  >  config mapping  >  environment variable  >  scoped default  >  default
```

All sources are cast and checked against the key's allowed values, so `config={"strict_mode": "false"}`, `strict_mode=False` and `DSA_STRICT_MODE=false` behave identically. With `strict_mode` on (the default), an unknown key in the `config` mapping is rejected with `ConfigurationError` instead of being silently ignored.

Register extension keys with `register_config_key(ConfigKey(...))`; re-registering an identical spec is a no-op, a conflicting one raises.

| Key | Environment | Default | Allowed | Scoped defaults | Used by | Effect |
|---|---|---|---|---|---|---|
| `strict_mode` | `DSA_STRICT_MODE` | `True` | — | — | all capabilities | Reject unknown config keys and verify cheap-to-moderate preconditions (e.g. O(n) sortedness check before governed binary search). |
| `validation_mode` | `DSA_VALIDATION_MODE` | `'raise'` | `raise`, `result` | — | all capabilities | 'raise' re-raises failures; 'result' returns a FAILURE OperationResult. |
| `track_metrics` | `DSA_TRACK_METRICS` | `True` | — | — | all capabilities | Record operation counters in OperationResult.metrics. Elapsed time is always recorded. |
| `verify_invariants` | `DSA_VERIFY_INVARIANTS` | `False` | — | — | mutation, traversal, analysis | Run the full structural validator before reads and after mutations. O(n) per call. |
| `mutate_in_place` | `DSA_MUTATE_IN_PLACE` | `False` | — | — | ORDERING | Write the sorted output back into SequenceState.values. |
| `idempotency_max_entries` | `DSA_IDEMPOTENCY_MAX_ENTRIES` | `1024` | — | — | MUTATION with an idempotency_key | Recorded idempotent results kept per store; the oldest is evicted beyond this. Must be >= 1. |
| `copy_on_read` | `DSA_COPY_ON_READ` | `True` | — | — | operations returning internal references | Deep-copy nodes/values that alias internal state before returning them. |
| `rollback_on_failure` | `DSA_ROLLBACK_ON_FAILURE` | `True` | — | — | MUTATION | Restore the pre-operation state when a non-atomic mutation fails. |
| `duplicate_policy` | `DSA_DUPLICATE_POLICY` | `'reject'` | `ignore`, `reject`, `replace` | — | MUTATION insert/add operations | 'reject' raises DuplicateKeyError; 'ignore' leaves state unchanged; 'replace' overwrites the stored value. |
| `missing_key_policy` | `DSA_MISSING_KEY_POLICY` | `'result'` | `raise`, `result` | — | lookups and deletes | 'result' returns NOT_FOUND; 'raise' treats a missing key as a failure. |
| `track_visited` | `DSA_TRACK_VISITED` | `True` | — | TreeTraversal: `False`; GraphTraversal: `True` | TRAVERSAL | Skip already-visited nodes. Disabling it on a graph requires maximum_depth >= 0. |
| `neighbour_order` | `DSA_NEIGHBOUR_ORDER` | `'natural'` | `natural`, `reversed`, `sorted` | — | TRAVERSAL | Order in which neighbours are expanded. |
| `maximum_depth` | `DSA_MAXIMUM_DEPTH` | `-1` | — | — | TRAVERSAL | Stop expanding below this depth; -1 means unbounded. |
| `maximum_results` | `DSA_MAXIMUM_RESULTS` | `-1` | — | — | TRAVERSAL, autocomplete | Stop after emitting this many results; -1 means unbounded. |
| `maximum_paths` | `DSA_MAXIMUM_PATHS` | `1000` | — | — | PATH ALL_SIMPLE_PATHS | Upper bound on enumerated paths; enumeration is exponential in the worst case. |
| `capacity` | `DSA_CAPACITY` | `-1` | — | — | STACK/QUEUE MUTATION | Fallback bound applied when the container state's own capacity is -1. |
| `stable_sort_required` | `DSA_STABLE_SORT_REQUIRED` | `False` | — | — | ORDERING | Reject sort algorithms whose descriptor is not stable. |
| `dijkstra_negative_weight_policy` | `DSA_DIJKSTRA_NEGATIVE_WEIGHT_POLICY` | `'eager'` | `assume_non_negative`, `eager`, `lazy` | — | PATH DIJKSTRA | 'eager' scans all edges first; 'lazy' checks inspected edges and disables early exit; 'assume_non_negative' skips checks. |
| `bst_balance_policy` | `DSA_BST_BALANCE_POLICY` | `'unbalanced'` | `avl`, `unbalanced` | — | BST MUTATION | 'avl' rebalances after insert/delete; 'unbalanced' does not. |
| `dp_max_cells` | `DSA_DP_MAX_CELLS` | `5000000` | — | — | OPTIMIZATION (table-based dynamic programming) | Refuse inputs whose DP table would exceed this many cells; -1 means unbounded. |
| `enumeration_limit` | `DSA_ENUMERATION_LIMIT` | `1000` | — | — | ENUMERATION | Return at most this many solutions and flag the result truncated; -1 means unbounded. |
| `enumeration_max_nodes` | `DSA_ENUMERATION_MAX_NODES` | `1000000` | — | — | ENUMERATION | Fail with CAPACITY_EXCEEDED once the search has visited this many states; -1 means unbounded. |

## Cost notes

- `strict_mode=True` makes governed `BINARY` / `LOWER_BOUND` O(n) because sortedness is verified first. Pass `strict_mode=False` when the caller already guarantees ordering.
- `verify_invariants=True` runs the full structural validator before the operation and again after a mutation (O(n) each), and takes a rollback snapshot. Use it in tests and at trust boundaries, not in hot loops.
- `rollback_on_failure` only costs anything for operations whose descriptor sets `atomic=False`, or when `verify_invariants` is on. Built-in mutations are atomic.
- `idempotency_max_entries` bounds memory: each recorded entry keeps its result and a reference to the state it was applied to, so a large state stays alive until its entry is evicted.
- `dp_max_cells`, `enumeration_limit` and `enumeration_max_nodes` bound the derived approaches. A table or search that would exceed them fails (or, for `enumeration_limit`, truncates and says so) instead of allocating without limit.
- `copy_on_read` deep-copies results that alias internal state (`PEEK`, `READ`, `MIDDLE`, BST `LOOKUP`).

_This table is generated from `DSA_CONFIG`; `tests/test_registry_and_docs.py` fails if a registered key is missing here._
