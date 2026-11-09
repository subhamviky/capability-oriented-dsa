# Vocabulary: from enterprise terms to computer science terms and this package

If `lower_bound`, `NavigableAdapter` or `topological sort` sound foreign, the
ideas behind them usually are not. This page pairs constructs you already use
in enterprise systems, on any platform, with the computer science term for them
and the closest thing in this package. ABAP and RAP terms follow as one
detailed example.

## Enterprise construct to computer science term

| Enterprise construct | Computer science term | In this package |
|---|---|---|
| Rate, scale or price band table | Sorted array, lower bound (binary search) | `SEQUENCE / SEARCH / LOWER_BOUND`, `BINARY` |
| Master data by key (customer, material) | Hash map | none; a `dict` already does this well |
| Work queue, retry list, message backlog | Queue (FIFO) | `QUEUE / MUTATION` and `QUERY`, with bounded capacity |
| Approval chain, undo history, nested call | Stack (LIFO) | `STACK / MUTATION` and `QUERY` |
| Organisation, cost-centre, product or location hierarchy | Tree | `TREE / QUERY / ANCESTORS`, `LOWEST_COMMON_ANCESTOR` |
| Dependent calculation steps, build or task dependencies | Directed acyclic graph, topological sort | `GRAPH / QUERY / TOPOLOGICAL_SORT`, `HAS_CYCLE` |
| Routes, lanes, service dependencies | Graph, shortest path | `GRAPH / PATH / SHORTEST_UNWEIGHTED`, `DIJKSTRA` |
| Type-ahead, value help by prefix | Trie | `TRIE / SEARCH / PREFIX` |
| Priority-ordered work, SLA or due-date queue | Heap (priority queue) | `HEAP / MUTATION / PUSH`, `POP`; `SEQUENCE / QUERY / TOP_K` |
| Duplicate or related records that must be merged into groups | Union-find (disjoint sets) | `UNION_FIND / MUTATION / UNION`, `QUERY / COMPONENT_COUNT` |
| Counts or groups by key, de-duplication | Hash map patterns | `FREQUENCY`, `GROUP_ANAGRAMS`, `HAS_DUPLICATE` |
| Overlapping validity periods, booking windows | Intervals (greedy) | `OPTIMIZATION / MERGE_INTERVALS`, `MAX_NON_OVERLAPPING` |

The same lower-bound idea under other platforms' names, all reporting a miss as
the position where the key would be inserted:

| Platform | Construct | On a miss |
|---|---|---|
| ABAP | `READ TABLE … BINARY SEARCH` | `sy-subrc = 4`, `sy-tabix` = insertion point |
| Java | `Collections.binarySearch(list, key)` | returns `-(insertion point) - 1` |
| Java | `TreeMap.ceilingKey(key)` | the first key `>=` the target |
| SQL | `WHERE upper_limit >= :qty ORDER BY upper_limit FETCH FIRST ROW ONLY` | the first row at or above the target (an index can serve it) |
| Python | `bisect.bisect_left(keys, target)` | the first position `>=` the target |

> These are **analogies, not equivalences**. Each row names the nearest concept
> so a new term has somewhere to land.

## ABAP and RAP terms, in detail

Where a match is loose, the note column says so.

### Data and lookup

| You know | Here | Note |
|---|---|---|
| Internal table (standard or sorted) | `SequenceState.values`, a Python list | Order and sortedness are your responsibility, exactly as with `BINARY SEARCH` in ABAP, except this package can check it for you. |
| Table key, `WITH KEY` | the `key=` function plus `target` | `key=lambda row: row[0]` plays the role of the key component. |
| `sy-subrc = 0` | `Status.SUCCESS` | |
| `sy-subrc = 4` | `Status.NOT_FOUND` | A miss is an outcome you branch on, not an exception. |
| `sy-tabix` after a failed binary search | `data` of a `LOWER_BOUND` result | The insertion point. Zero-based here, one-based in ABAP. |
| Hashed table lookup | a Python `dict` | No capability wraps it; none is needed. |

### Structure and relationships

| You know | Here | Note |
|---|---|---|
| Parent/child association, hierarchy | `TreeState` (`children`, `parent`) | `ANCESTORS` and `LOWEST_COMMON_ANCESTOR` answer the usual scope questions. |
| Dependencies between calculation items | `GraphState(directed=True)` | An edge `A -> B` means A comes first. `TOPOLOGICAL_SORT` yields a valid order; `HAS_CYCLE` detects circular dependencies. |
| Network of locations or lanes | `GraphState` with weighted edges | `DIJKSTRA` for cheapest route, `SHORTEST_UNWEIGHTED` for fewest hops. |
| Value help by prefix | `TrieState`, `PREFIX` | |

### Behaviour and governance

| You know | Here | Note |
|---|---|---|
| Method in a global class | an `@operation` on a capability service | The declaration carries name, complexity, preconditions and postconditions. |
| Public, protected and private sections | `BaseDSACapability`: one public `execute()`, protected hooks, private invariants | Same ownership rule as the E2A base classes. |
| RAP validation | the descriptor's `preconditions`, checked before the kernel runs | Loose match: it guards an algorithm's input, not a business entity. |
| RAP action | an operation reached through `DSAFacade.execute(...)` | Loose match: no draft, no persistence. |
| Customizing or configuration table | `DSA_CONFIG`, resolved as `kwargs > config > env > scoped default > default` | Every key is registered, typed and listed in [configuration.md](configuration.md). |
| `RAISE EXCEPTION` | `validation_mode="raise"` (the default) | `"result"` returns a `FAILURE` result with a stable error code instead. |
| `ROLLBACK WORK` | snapshot and rollback on failed mutations | Applies when `atomic=False` or `verify_invariants` is on; atomic repositories validate before the first write. |
| Application log | `OperationResult.metrics` | Loose match: counters such as comparisons, not a persistent log. |

## Algorithm words, plainly

| Word | Meaning |
|---|---|
| Kernel | The algorithm itself, with no framework around it. `SearchAlgorithms.binary(values, target)`. |
| Governed | The same kernel called through `DSAFacade`, with checks, metrics and a structured result. |
| Invariant | A rule a structure must always satisfy, such as "a BST's left subtree is smaller". `VALIDATE` checks them. |
| Lower bound | The position of the first element not smaller than the target. |
| Topological order | An ordering where every item appears after the items it depends on. |
| Dynamic programming | Solving a problem by storing answers to smaller overlapping problems, so each is computed once. |
| Greedy | Always taking the locally best choice, when that is provably globally best. |
| Backtracking | Trying each decision in turn and undoing it, which is depth-first search over a tree of choices. |
| O(log n), O(n) | How the work grows with input size. Every operation lists its own in its descriptor. |
