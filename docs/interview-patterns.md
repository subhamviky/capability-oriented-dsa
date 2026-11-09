# Interview patterns and where they live

Most data-structure-and-algorithm questions, in interviews and in design
reviews alike, are a small number of ideas wearing different clothes. This page
sorts those ideas into **core** and **derived**, names the recurring problems
each one answers, and says where the answer lives in this package. It also says
plainly what is not here.

Nothing on this page is new computer science. It is a map.

## Two tiers

**Core** concepts are the things everything else is built from: a *structure*
that holds state under an invariant, and the *algorithm families* that work on
it. They have a state type, a validator and governed operations.

**Derived** concepts are approaches and patterns. They add no new structure.
They reuse a core one and say *how to think* about a problem: remember
subproblems, commit to the best local choice, try every decision, keep a
window, hash for O(1) lookup. In this package they are kernels over a
`SEQUENCE` and appear as their own capabilities (`OPTIMIZATION`,
`ENUMERATION`) or as `QUERY` operations, and carry the same descriptor
(complexity, preconditions, postconditions) as any core operation.

### Core structures

| Structure | State | Invariant (checked by `VALIDATE`) |
|---|---|---|
| Sequence | `SequenceState` | a list |
| Linked list | `LinkedListState` | head, tail, size and links agree |
| Stack, Queue | `StackState`, `QueueState` | size within capacity |
| Tree | `TreeState` | one root, parent and child links agree |
| BST | `BSTState` | left < node < right; parent links and stored heights agree |
| Trie | `TrieState` | word count matches terminal nodes |
| Graph | `GraphState` | edges reference vertices; undirected edges are symmetric |
| Heap | `HeapState` | every parent sorts before its children |
| Union-find | `UnionFindState` | parents form trees; sizes and component count agree |

A **hash map** is deliberately not a state type. Python's `dict` and `set`
already are one, and wrapping them would add a name and no contract. Hashing
appears below as the *patterns* built on it.

### Core algorithm families

| Family | Capability | Used for |
|---|---|---|
| Searching | `SEARCH` | binary search, lower bound, first-true over an answer space, trie and BST lookup |
| Ordering | `ORDERING` | bubble, merge, quick sort, with explicit stability |
| Traversal | `TRAVERSAL` | BFS and DFS over any tree or graph through one adapter |
| Paths | `PATH` | unweighted shortest path, Dijkstra, bounded path enumeration |
| Structure queries | `QUERY` | height, LCA, cycle, topological order, peek, find |
| Mutation | `MUTATION` | insert, delete, push, pop, union, with atomic updates |

### Derived approaches and patterns

| Derived concept | Built on | Where |
|---|---|---|
| Hashing patterns (frequency, grouping, prefix-sum counts) | a hash map, prefix sums | `SEQUENCE / QUERY` |
| Two pointers, sliding window | sequence, queue | `SEQUENCE / QUERY` |
| Monotonic stack and deque | stack, queue | `SEQUENCE / QUERY` (`NEXT_GREATER`, `SLIDING_WINDOW_MAXIMUM`) |
| Top-k, k-way merge | heap | `SEQUENCE / QUERY` |
| Binary search on the answer | lower bound | `SEQUENCE / SEARCH / FIRST_TRUE` |
| Dynamic programming | arrays, and lower bound for LIS | `SEQUENCE / OPTIMIZATION` |
| Greedy | sorting | `SEQUENCE / OPTIMIZATION` |
| Backtracking | depth-first search over decisions | `SEQUENCE / ENUMERATION` |
| Connected components, cycle edge, Kruskal | union-find | `UNION_FIND` plus a few lines |

## Choosing the idea from the shape of the question

| If the question says… | Reach for | Here |
|---|---|---|
| sorted, or "smallest X such that …" | binary search, lower bound | `LOWER_BOUND`, `FIRST_TRUE` |
| "have I seen this", count by key, group by key | hash map | `FREQUENCY`, `GROUP_ANAGRAMS`, `HAS_DUPLICATE` |
| contiguous subarray or substring | prefix sums, window, Kadane | `PREFIX_SUMS`, `SUBARRAY_SUM_COUNT`, `LONGEST_UNIQUE_WINDOW`, `MAXIMUM_SUBARRAY` |
| pair in a sorted array, or from both ends | two pointers | `PAIR_SUM_SORTED`, `MAX_AREA` |
| k largest, k closest, merge k sorted | heap | `TOP_K`, `MERGE_SORTED` |
| next greater, nearest larger | monotonic stack | `NEXT_GREATER` |
| level by level, fewest steps | BFS | `TRAVERSAL / BFS`, `SHORTEST_UNWEIGHTED` |
| cheapest path with weights | Dijkstra | `DIJKSTRA` |
| order with prerequisites, detect circular dependency | topological sort | `TOPOLOGICAL_SORT`, `HAS_CYCLE` |
| groups that merge, are two items connected | union-find | `UNION`, `CONNECTED`, `COMPONENT_COUNT` |
| prefix of a word | trie | `TRIE / SEARCH / PREFIX` |
| ancestor, hierarchy scope | tree | `ANCESTORS`, `LOWEST_COMMON_ANCESTOR` |
| every subset, ordering or selection | backtracking | `ENUMERATION` |
| best value, and smaller answers feed bigger ones | dynamic programming | `OPTIMIZATION` |
| best value, and the locally best choice is provably safe | greedy | `MERGE_INTERVALS`, `MAX_NON_OVERLAPPING`, `CAN_JUMP` |

## Problem map

**Direct** means an operation here is the answer. **Composed** means one or two
operations plus a few lines of your own. **Kernel** means a direct kernel exists
but there is no governed operation. Anything not listed is in
[Not covered](#not-covered).

### Arrays, strings and hashing

| Typical question | Idea | Here | Fit |
|---|---|---|---|
| Two sum | hash map | `SEQUENCE / QUERY / TWO_SUM` | Direct |
| Contains duplicate | hash set | `HAS_DUPLICATE` | Direct |
| Valid anagram | frequency counts | `FREQUENCY` on both, compare | Composed |
| Group anagrams | hash on sorted letters | `GROUP_ANAGRAMS` | Direct |
| Top k frequent elements | frequency, then heap | `FREQUENCY`, then `TOP_K` over the counts | Composed |
| Longest consecutive sequence | hash set, start at run heads | `LONGEST_CONSECUTIVE` | Direct |
| Subarray sum equals k | prefix sums and a hash map | `SUBARRAY_SUM_COUNT` | Direct |
| First unique character | frequency, then scan | `FIRST_UNIQUE` | Direct |
| Maximum subarray | Kadane | `MAXIMUM_SUBARRAY` | Direct |
| Range sum query | prefix sums | `PREFIX_SUMS` | Direct |
| Next greater element | monotonic stack | `NEXT_GREATER` | Direct |

### Two pointers and sliding windows

| Typical question | Idea | Here | Fit |
|---|---|---|---|
| Two sum II (sorted input) | two pointers | `PAIR_SUM_SORTED` | Direct |
| Container with most water | two pointers | `MAX_AREA` | Direct |
| Longest substring without repeats | variable window and last-seen map | `LONGEST_UNIQUE_WINDOW` on `list(text)` | Direct |
| Minimum size subarray sum | variable window | `MIN_SUBARRAY_LENGTH` | Direct |
| Sliding window maximum | monotonic deque | `SLIDING_WINDOW_MAXIMUM` | Direct |

### Searching, sorting and intervals

| Typical question | Idea | Here | Fit |
|---|---|---|---|
| Binary search | binary search | `SEARCH / BINARY` | Direct |
| Search insert position | lower bound | `SEARCH / LOWER_BOUND` | Direct |
| Smallest capacity, speed or size that works | binary search on the answer | `FIRST_TRUE` with your predicate | Composed |
| Sort an array | comparison sort | `ORDERING` | Direct |
| Kth largest element | heap of size k | `TOP_K`, take the last | Composed |
| Merge k sorted lists (as arrays) | k-way merge | `MERGE_SORTED` | Direct |
| Merge intervals | sort then sweep | `MERGE_INTERVALS` | Direct |
| Non-overlapping intervals (fewest removals) | greedy by earliest end | `MAX_NON_OVERLAPPING`, count minus kept | Composed |
| Insert interval | merge | append, then `MERGE_INTERVALS` | Composed |
| Jump game | greedy reach | `CAN_JUMP` | Direct |

### Linked lists, stacks and queues

| Typical question | Idea | Here | Fit |
|---|---|---|---|
| Reverse a linked list | pointer reversal | `LINKED_LIST / MUTATION / REVERSE` | Direct |
| Middle of a linked list | fast and slow pointers | `LINKED_LIST / QUERY / MIDDLE` | Direct |
| Linked-list cycle | Floyd | `LINKED_LIST / QUERY / HAS_CYCLE` | Direct |
| Valid parentheses | stack | `StackAlgorithms.balanced_brackets` | Kernel |
| Evaluate postfix | stack | `StackAlgorithms.evaluate_postfix` | Kernel |
| Generate binary numbers | queue | `QueueAlgorithms.generate_binary_numbers` | Kernel |

### Trees, BSTs and tries

| Typical question | Idea | Here | Fit |
|---|---|---|---|
| Level-order traversal | BFS | `TREE / TRAVERSAL / BFS` | Direct |
| Pre-order / DFS | DFS | `TREE / TRAVERSAL / DFS` | Direct |
| Maximum depth | height | `TREE / QUERY / HEIGHT` | Direct |
| Diameter of a tree | height at each node | `TREE / QUERY / DIAMETER` | Direct |
| Lowest common ancestor | ancestors | `TREE / QUERY / LOWEST_COMMON_ANCESTOR` | Direct |
| Validate a BST | order invariant | `BST / VALIDATION / VALIDATE` | Direct |
| BST insert, delete, search; balance | BST, AVL | `BST / MUTATION`, `BST / SEARCH / LOOKUP` | Direct |
| Kth smallest in a BST | in-order | `BST / QUERY / INORDER`, then index | Composed |
| Implement a trie, autocomplete | trie | `TRIE / MUTATION`, `TRIE / SEARCH` | Direct |

### Graphs and union-find

| Typical question | Idea | Here | Fit |
|---|---|---|---|
| BFS or DFS of a graph | traversal | `GRAPH / TRAVERSAL` | Direct |
| Shortest path, unweighted | BFS | `GRAPH / PATH / SHORTEST_UNWEIGHTED` | Direct |
| Shortest path, weighted | Dijkstra | `GRAPH / PATH / DIJKSTRA` | Direct |
| Course schedule (can finish?) | cycle detection | `GRAPH / QUERY / HAS_CYCLE` | Direct |
| Course schedule II (order) | topological sort | `GRAPH / QUERY / TOPOLOGICAL_SORT` | Direct |
| Number of connected components | union-find | `UNION_FIND / QUERY / COMPONENT_COUNT` | Direct |
| Redundant connection | union-find | `UNION` returns `False` for the edge that closes a cycle | Direct |
| Are two items connected | union-find | `UNION_FIND / QUERY / CONNECTED` | Direct |
| Number of islands | components of a grid | build `GraphState` or union neighbours, then count | Composed |
| Word ladder | BFS on an implicit graph | build the graph, `SHORTEST_UNWEIGHTED` | Composed |
| Minimum spanning tree (Kruskal) | sort edges, union-find | `ORDERING`, then `UNION` per edge | Composed |
| Accounts merge | union-find on shared keys | `UNION` per shared key, then group by `FIND` | Composed |

### Heaps

| Typical question | Idea | Here | Fit |
|---|---|---|---|
| Kth largest, top k | heap of size k | `TOP_K` | Direct |
| K closest points | heap on `(distance, point)` | `TOP_K` with `largest=False` over tuples | Composed |
| Merge k sorted lists | k-way merge | `MERGE_SORTED` | Direct |
| Priority queue | heap | `HEAP / MUTATION / PUSH`, `POP`; `QUERY / PEEK` | Direct |
| Median of a data stream | two heaps | one max `HeapState`, one min `HeapState`, rebalance | Composed |

### Dynamic programming

| Typical question | Idea | Here | Fit |
|---|---|---|---|
| House robber | take or skip | `HOUSE_ROBBER` | Direct |
| Longest increasing subsequence | tails array and lower bound | `LONGEST_INCREASING_SUBSEQUENCE` | Direct |
| Coin change (fewest coins) | unbounded knapsack | `COIN_CHANGE` | Direct |
| 0/1 knapsack | take or skip per item | `KNAPSACK_01` | Direct |
| Partition equal subset sum | knapsack with weight = value | `KNAPSACK_01` with half the total as capacity | Composed |
| Longest common subsequence | two-sequence table | `LONGEST_COMMON_SUBSEQUENCE` | Direct |
| Edit distance | two-sequence table | `EDIT_DISTANCE` | Direct |

### Backtracking

| Typical question | Idea | Here | Fit |
|---|---|---|---|
| Subsets | include or skip | `ENUMERATION / SUBSETS` | Direct |
| Permutations | choose from the unused | `PERMUTATIONS` | Direct |
| Combinations | choose k, in order | `COMBINATIONS` | Direct |
| Combination sum | reuse candidates | `COMBINATION_SUM` | Direct |
| N-Queens | place row by row, prune attacks | `BacktrackingAlgorithms.n_queens` | Kernel |

Every enumeration is lazy and bounded: `enumeration_limit` caps the results
(and the result says it was truncated) and `enumeration_max_nodes` caps the
work. Equal values are treated as distinct positions, so "subsets II" style
de-duplication is yours to add.

## Not covered

These come up in interviews and are **not** in the package. Some are
deliberate, some are simply not built yet.

- **Hash map as a structure**, and anything designed around one: LRU and LFU caches, randomized sets, time-based key-value stores. A `dict` is the structure; the design is the question.
- **Strings beyond hashing and windows:** KMP, rolling hash, palindromes, parsing, minimum window substring.
- **Dynamic programming beyond the six above:** grid paths, word break, palindromic substrings, bitmask and tree DP, and returning the *solution* rather than its value.
- **Backtracking on grids and constraints:** word search, sudoku, palindrome partitioning, generate parentheses.
- **Range structures:** segment tree, Fenwick tree, sparse table.
- **Graph algorithms beyond the above:** bipartite check, strongly connected components, Bellman-Ford, Floyd-Warshall, MST as a single operation.
- **Greedy beyond intervals and jumps:** task scheduling, gas station, Huffman coding.
- **Math and bits:** bit manipulation, primes, gcd, modular arithmetic, geometry, matrix manipulation.
- **Linked-list manipulation beyond reverse, middle and cycle:** merging lists, removing the nth node, copying with random pointers.

## Operation index

Every registered operation, by structure and capability. A test fails if an
operation is registered and missing here.

| Structure / capability | Operations |
|---|---|
| `BST / MUTATION` | `DELETE`, `INSERT` |
| `BST / QUERY` | `INORDER`, `IS_AVL_BALANCED` |
| `BST / SEARCH` | `LOOKUP` |
| `BST / VALIDATION` | `VALIDATE` |
| `GRAPH / MUTATION` | `ADD_EDGE`, `ADD_VERTEX`, `REMOVE_EDGE`, `REMOVE_VERTEX` |
| `GRAPH / PATH` | `ALL_SIMPLE_PATHS`, `DIJKSTRA`, `SHORTEST_UNWEIGHTED` |
| `GRAPH / QUERY` | `HAS_CYCLE`, `TOPOLOGICAL_SORT` |
| `GRAPH / TRAVERSAL` | `BFS`, `DFS` |
| `GRAPH / VALIDATION` | `VALIDATE` |
| `HEAP / MUTATION` | `POP`, `PUSH` |
| `HEAP / QUERY` | `PEEK` |
| `HEAP / VALIDATION` | `VALIDATE` |
| `LINKED_LIST / MUTATION` | `APPEND`, `DELETE`, `PREPEND`, `REVERSE` |
| `LINKED_LIST / QUERY` | `HAS_CYCLE`, `MIDDLE` |
| `LINKED_LIST / VALIDATION` | `VALIDATE` |
| `QUEUE / MUTATION` | `DEQUEUE`, `ENQUEUE` |
| `QUEUE / QUERY` | `PEEK` |
| `QUEUE / VALIDATION` | `VALIDATE` |
| `SEQUENCE / ENUMERATION` | `COMBINATIONS`, `COMBINATION_SUM`, `PERMUTATIONS`, `SUBSETS` |
| `SEQUENCE / MUTATION` | `DELETE`, `INSERT`, `UPDATE` |
| `SEQUENCE / OPTIMIZATION` | `CAN_JUMP`, `COIN_CHANGE`, `EDIT_DISTANCE`, `HOUSE_ROBBER`, `KNAPSACK_01`, `LONGEST_COMMON_SUBSEQUENCE`, `LONGEST_INCREASING_SUBSEQUENCE`, `MAX_NON_OVERLAPPING`, `MERGE_INTERVALS` |
| `SEQUENCE / ORDERING` | `BUBBLE`, `MERGE`, `QUICK` |
| `SEQUENCE / QUERY` | `FIRST_UNIQUE`, `FREQUENCY`, `GROUP_ANAGRAMS`, `HAS_DUPLICATE`, `LONGEST_CONSECUTIVE`, `LONGEST_UNIQUE_WINDOW`, `MAXIMUM_SUBARRAY`, `MAX_AREA`, `MERGE_SORTED`, `MIN_SUBARRAY_LENGTH`, `NEXT_GREATER`, `PAIR_SUM_SORTED`, `PREFIX_SUMS`, `READ`, `SLIDING_WINDOW_MAXIMUM`, `SUBARRAY_SUM_COUNT`, `TOP_K`, `TWO_SUM` |
| `SEQUENCE / SEARCH` | `BINARY`, `FIRST_TRUE`, `LINEAR`, `LOWER_BOUND` |
| `SEQUENCE / VALIDATION` | `VALIDATE` |
| `STACK / MUTATION` | `POP`, `PUSH` |
| `STACK / QUERY` | `PEEK` |
| `STACK / VALIDATION` | `VALIDATE` |
| `TREE / MUTATION` | `ADD_CHILD`, `ADD_ROOT`, `DELETE_SUBTREE` |
| `TREE / QUERY` | `ANCESTORS`, `DIAMETER`, `HEIGHT`, `LOWEST_COMMON_ANCESTOR` |
| `TREE / TRAVERSAL` | `BFS`, `DFS` |
| `TREE / VALIDATION` | `VALIDATE` |
| `TRIE / MUTATION` | `DELETE`, `INSERT` |
| `TRIE / SEARCH` | `CONTAINS`, `PREFIX` |
| `TRIE / VALIDATION` | `VALIDATE` |
| `UNION_FIND / MUTATION` | `ADD`, `UNION` |
| `UNION_FIND / QUERY` | `COMPONENT_COUNT`, `CONNECTED`, `FIND` |
| `UNION_FIND / VALIDATION` | `VALIDATE` |
