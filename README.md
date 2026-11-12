# Capability-Oriented DSA

[![CI](https://github.com/subhamviky/capability-oriented-dsa/actions/workflows/ci.yml/badge.svg)](https://github.com/subhamviky/capability-oriented-dsa/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
![Typed](https://img.shields.io/badge/typing-mypy%20strict-informational)
![Dependencies](https://img.shields.io/badge/runtime%20dependencies-0-success)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Data-structure algorithms for enterprise developers, approached through a
platform-architect lens, with SAP/ABAP as one worked example.**

The algorithms here are classical; none of them is new. What this project
offers is a way in. It was written from enterprise practice (large
distributed systems, ABAP, platform design) rather than from competitive
programming, and it keeps the vocabulary and contracts that enterprise
developers already trust: sorted tables, keys, return codes, validations,
configuration, and one governed entry point.

> **Scope.** This is an architecture reference implementation and a learning
> bridge, not a replacement for `collections`, `bisect`, `heapq` or a graph
> library, and it makes no performance claims.

## Start with a problem you already know

You have a scale table of `(upper_limit, rate)` rows, sorted by limit, and
you need the band a quantity falls in. In ABAP that is `READ TABLE … BINARY
SEARCH`, then reading `sy-tabix` on a miss; in Java it is `Collections.binarySearch`,
which returns `-(insertion point) - 1`; in Python, `bisect_left`. Here are the same steps in three
layers, each one optional.

**1. The idea, on its own: a direct kernel.** No framework, no setup.

```python
from capability_oriented_dsa import SearchAlgorithms

scale = [(100, 5.00), (500, 4.20), (2000, 3.50)]
index = SearchAlgorithms.lower_bound(scale, 350, key=lambda row: row[0])
scale[index]  # (500, 4.2): the first band whose limit is >= 350
```

**2. The same idea with the contracts you expect: a governed call.**

```python
from capability_oriented_dsa import DSAFacade, SequenceState

result = DSAFacade().execute(
    structure_type="SEQUENCE",
    capability="SEARCH",
    operation="LOWER_BOUND",
    state=SequenceState(scale),
    target=350,
    key=lambda row: row[0],
)
result.status  # Status.NOT_FOUND: 350 is not exactly a limit (like sy-subrc = 4)
result.data  # 1: the insertion point, which is the band (like sy-tabix)
```

**3. The part ABAP never tells you about: what if the table is not sorted?**
`BINARY SEARCH` on an unsorted table returns a wrong answer without warning.
The governed call checks the precondition and says so:

```python
result = DSAFacade().execute(
    structure_type="SEQUENCE",
    capability="SEARCH",
    operation="LOWER_BOUND",
    state=SequenceState([scale[1], scale[0], scale[2]]),
    target=350,
    key=lambda row: row[0],
    config={"validation_mode": "result"},
)
result.status  # Status.FAILURE
result.errors[0].code  # 'PRECONDITION_FAILED'
```

That is the whole idea: the algorithm stays textbook-shaped, and the platform
discipline sits around it instead of inside it.

## Where to go next

| If you want to… | Read |
|---|---|
| Map enterprise constructs, and ABAP/RAP terms, to computer science terms and this package | [docs/vocabulary.md](docs/vocabulary.md) |
| See three enterprise-shaped problems solved end to end (scale lookup, calculation order, hierarchy scope) | [docs/enterprise-bridge.md](docs/enterprise-bridge.md) and [examples/enterprise_bridge.py](examples/enterprise_bridge.py) |
| Understand the layers, lifecycle and result semantics | [docs/architecture.md](docs/architecture.md) |
| Look up a configuration key | [docs/configuration.md](docs/configuration.md) |
| See common interview problems mapped to core and derived concepts, and what is not covered | [docs/interview-patterns.md](docs/interview-patterns.md) |
| Add your own algorithm | [Extending](#extending) |

## Design in one screen

| Principle | How it shows up |
|---|---|
| Direct kernels first | `SortAlgorithms.quick(values)` has no framework dependency and stays textbook-shaped. |
| Explicit state | `GraphState`, `BSTState`, … are plain dataclasses. Nothing hides in service instances. |
| Capabilities, not hierarchies | One BFS/DFS serves trees and graphs through the `NavigableAdapter` port. |
| One governed entry point | `BaseDSACapability.execute()` owns the lifecycle: public method, protected hooks, private invariants. |
| Core, then derived | Structures and algorithm families are core. Dynamic programming, greedy, backtracking, hashing and window patterns are derived: they reuse a core structure and are bounded by explicit limits. |
| Declared, not branched | `@operation(descriptor)` builds the dispatch table, and the registry and metadata derive from it. |
| Central configuration | 22 registered keys resolved as `kwargs > config > env > scoped default > default`, cast and validated. |
| Honest results | `SUCCESS` / `NOT_FOUND` / `FAILURE` with stable error codes; misses are outcomes, not exceptions. |

## What is in the box

100 governed operations. *Core* structures and algorithm families come first; *derived* approaches reuse them and add no new structure (see [docs/interview-patterns.md](docs/interview-patterns.md)).

| Structure | Governed capabilities |
|---|---|
| Sequence | linear / binary / lower-bound search · bubble / merge / quick sort · two-sum, Kadane, prefix sums, next-greater, sliding-window max · insert / update / delete |
| Linked list | append / prepend / delete / reverse · middle · Floyd cycle detection |
| Stack, Queue | push / pop / peek · enqueue / dequeue / peek, with bounded capacity |
| Tree | BFS / DFS · height · diameter · ancestors · LCA · add / delete subtree |
| BST | lookup · inorder · insert / delete, plain or AVL (`bst_balance_policy`) |
| Trie | contains · prefix autocomplete · insert / delete |
| Graph | BFS / DFS · BFS shortest path · Dijkstra (eager, lazy or trusted negative-weight policy) · bounded all-simple-paths · cycle detection · topological sort · vertex/edge mutations |
| Heap | push / pop / peek · top-k and k-way merge over a sequence |
| Union-find | add / union · find / connected / component count |
| **Derived:** hashing, windows | duplicates, frequency, anagram groups, longest consecutive run, subarray-sum counts · sorted pair sum, longest unique window, shortest window, max area |
| **Derived:** `OPTIMIZATION` | dynamic programming (house robber, LIS, coin change, 0/1 knapsack, LCS, edit distance) and greedy (merge intervals, max non-overlapping, jump game) |
| **Derived:** `ENUMERATION` | backtracking: subsets, permutations, combinations, combination sum, bounded and lazy |
| All | `VALIDATION/VALIDATE`: iterative structural invariant checks |

Every operation is self-describing:

```python
DSAFacade().describe("GRAPH", "PATH", "DIJKSTRA")
# AlgorithmDescriptor(name='DIJKSTRA', time_complexity='O((V+E) log V)',
#                     preconditions=('all edge weights are non-negative',), ...)
```

## Install

Requires Python 3.11+. No runtime dependencies.

```bash
pip install "git+https://github.com/subhamviky/capability-oriented-dsa"
```

Or copy **`standalone/dsa_framework.py`**, a generated single-file edition with
the same API that is also available at standalone/dsa_framework.py. Don't import both
editions in one process: their classes and config registries are distinct
objects.

## Extending

New algorithms are added by declaration, never by editing a branch:

```python
class AStarPathService(BaseDSACapability):
    capability = "PATH"

    @operation(describe("A_STAR", capability, "GRAPH", "O(E log V)", "O(V)",
                        preconditions=("non-negative weights",)),
               requires=("source", "target", "heuristic"))
    def _a_star(self, context, args):
        ...

registry = build_default_registry()
registry.register_service(AStarPathService())
DSAFacade(registry).execute(structure_type="GRAPH", capability="PATH", operation="A_STAR", ...)
```

The complete runnable version is in [examples/extend_with_astar.py](examples/extend_with_astar.py).

## What this does not give you

State is in memory. The optional `correlation_id`, `tenant_id` and
`idempotency_key` give a call the same request-scoped identifiers the E2A base
classes use, but `tenant_id` isolates no data and idempotency records are
process-local and protect sequential retries only (concurrent same-key calls can
both apply), so there is no durable exactly-once delivery, no persistence and
no audit trail. There is no ABAP or Java port. See the closing section of
[docs/enterprise-bridge.md](docs/enterprise-bridge.md) before applying the
pattern near a production system.

## Quality gates

- `ruff` lint and format, and `mypy --strict`, all clean
- The test suite runs against **both** editions: unit, Hypothesis property tests (sorts, searches, AVL insert/delete, trie, graph traversals), governed-lifecycle tests, hardening tests for deep inputs, malformed structures and edge cases, and the enterprise examples
- Iterative kernels verified at 3,000-deep inputs (above CPython's recursion limit)
- CI on Python 3.11 to 3.13 (Linux), with a coverage gate, a standalone-freshness check and a wheel install check

## Documentation

| Document | Purpose |
|---|---|
| [docs/vocabulary.md](docs/vocabulary.md) | Enterprise constructs mapped to computer science terms and to this package, with ABAP/RAP in detail |
| [docs/enterprise-bridge.md](docs/enterprise-bridge.md) | Construct-to-capability table and three worked examples |
| [docs/interview-patterns.md](docs/interview-patterns.md) | Core versus derived concepts, common problems mapped to operations, and what is not covered |
| [docs/architecture.md](docs/architecture.md) | Layers, lifecycle, result semantics, capability matrix, extension guide |
| [docs/configuration.md](docs/configuration.md) | Every config key, its default, allowed values and cost |
| [docs/adr/](docs/adr/) | Architecture decision records |
| [CHANGELOG.md](CHANGELOG.md) | Change history |

## Lineage

The governance ideas (request-scoped state, kwargs > config > env > default
resolution, one governed public entry point, public/protected/private
ownership, registries over conditionals, and the `correlation_id` /
`tenant_id` / `idempotency_key` request identifiers) are carried over from the author's
[E2A framework](https://github.com/subhamviky/e2a-framework), applied here to
a domain small enough to inspect end to end. There is no code dependency
between the two.

Used in the completed Order-to-Cash projects (pinned to a release tag): the
[reconciliation engine](https://github.com/subhamviky/aws-reconciliation-engine)
matches bank payments with `KNAPSACK_01`, bounded `SUBSETS`, `LOWER_BOUND` and
`UNION_FIND`; the [O2C assistant](https://github.com/subhamviky/order-to-cash-agentic-ai)
re-ranks retrieval results with `TOP_K`; the settlement platform's audit service
assigns risk bands with `LOWER_BOUND`.

## License

[MIT](LICENSE) © Subham Gupta
