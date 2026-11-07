# Enterprise bridge

How the capabilities in this package line up with problems enterprise and SAP
developers already solve with ABAP internal tables, CDS hierarchies and
calculation sequences. Every Python example below is in
[`examples/enterprise_bridge.py`](../examples/enterprise_bridge.py) and is
executed by `tests/test_enterprise_bridge.py` against both editions, so the
output shown here is real.

> **Scope.** The scenarios are generic enterprise shapes (scale tables,
> dependent calculation items, location hierarchies). They are not claims
> about how any SAP product implements them internally. The ABAP fragments are
> illustrations of the construct being compared; they are not compiled
> against a system.

## Construct to capability

| Enterprise construct | Capability here | What the governed layer adds |
|---|---|---|
| `READ TABLE … BINARY SEARCH` on a sorted table | `SEQUENCE / SEARCH / BINARY` | Checks the table really is sorted. ABAP gives undefined results on an unsorted table and says nothing. |
| `READ TABLE … BINARY SEARCH` miss, then using `sy-tabix` | `SEQUENCE / SEARCH / LOWER_BOUND` | The insertion point is returned as data, with a `NOT_FOUND` status instead of a `sy-subrc` you must remember to test. |
| Scale or interval table (value falls in a band) | `LOWER_BOUND` over band upper limits | Same as above, plus a stable error code when the scale is mis-sorted. |
| Items that must be calculated in dependency order | `GRAPH / QUERY / TOPOLOGICAL_SORT`, `HAS_CYCLE` | A cycle is a structured `FAILURE`, not an endless loop or a silently wrong order. |
| Parent/child hierarchy (organisation, location, stage structure) | `TREE / QUERY / ANCESTORS`, `LOWEST_COMMON_ANCESTOR` | Iterative, safe on deep hierarchies; an unknown node id comes back as `NOT_FOUND`, not an exception. |
| Routes, lanes, networks | `GRAPH / PATH / SHORTEST_UNWEIGHTED`, `DIJKSTRA`, `ALL_SIMPLE_PATHS` | Negative-weight policy and path-count bounds are explicit configuration. |
| Value help by prefix | `TRIE / SEARCH / PREFIX` | Result size bounded by `maximum_results`. |
| Hashed table lookup, plain `LOOP` | none | **Nothing.** A dict or a loop is already the right tool; this package does not wrap it. |

## 1. Scale lookup: which band does a quantity fall in?

A scale table holds `(upper_limit, rate)` rows sorted by limit. A quantity
belongs to the first row whose limit is `>=` the quantity, which is exactly
`LOWER_BOUND`.

```python
facade.execute(
    structure_type="SEQUENCE",
    capability="SEARCH",
    operation="LOWER_BOUND",
    state=dsa.SequenceState(SCALE),
    target=350,
    key=lambda row: row[0],
)
```

```text
350  -> NOT_FOUND, data=1   band (500, 4.2)
500  -> SUCCESS,   data=1   exact upper limit
2500 -> NOT_FOUND, data=3   == len(SCALE): beyond the last band
rows out of order -> FAILURE, PRECONDITION_FAILED
```

Two things to know:

- `NOT_FOUND` here is normal. `LOWER_BOUND` reports `NOT_FOUND` whenever the
  quantity is not exactly a limit, and still carries the insertion point. For a
  band lookup the insertion point is the answer. It is valid when it is less
  than `len(rows)`.
- The ABAP equivalent reads the same way:

```abap
READ TABLE lt_scale ASSIGNING FIELD-SYMBOL(<ls_band>)
     WITH KEY upper_limit = lv_qty BINARY SEARCH.
" sy-subrc = 4: sy-tabix is the index of the first row with a greater key,
" or lines( lt_scale ) + 1 if there is none (beyond the last band).
```

  ABAP indexes from 1 and Python from 0, so index `1` here is `sy-tabix = 2`.

## 2. Calculation order: what can be computed first?

Items that depend on one another form a directed graph: an edge `A -> B`
means A must be computed before B.

```text
BASE_FREIGHT -> FUEL_SURCHARGE -> TOTAL
BASE_FREIGHT -> VOLUME_DISCOUNT -> TOTAL
```

```text
order: BASE_FREIGHT, FUEL_SURCHARGE, VOLUME_DISCOUNT, TOTAL
add the edge TOTAL -> BASE_FREIGHT:
    HAS_CYCLE = True, TOPOLOGICAL_SORT -> FAILURE
```

Calculation sequences are usually a fixed order in code or a configured
sequence number. The value of deriving the order is that adding an item cannot
silently produce a wrong order, and a circular dependency is reported as a
result you can act on before any calculation starts.

## 3. Hierarchy scope: what do two entries share?

```text
EMEA
├── DE ── PLANT_1000, PLANT_2000
└── FR ── PLANT_3000
```

```text
ANCESTORS(PLANT_1000)                       -> [EMEA, DE]   (root first)
LOWEST_COMMON_ANCESTOR(PLANT_1000, PLANT_2000) -> DE
LOWEST_COMMON_ANCESTOR(PLANT_1000, PLANT_3000) -> EMEA
```

The lowest common ancestor answers "which node's rules apply to both?", for
example the narrowest scope at which two plants can share a setting.

## What this does not give you

Read these before putting the pattern near a production system.

- **In-memory state.** Structures are Python dataclasses. There is no
  persistence and no audit trail. The optional `correlation_id`, `tenant_id`
  and `idempotency_key` follow the E2A naming, but `tenant_id` isolates no data
  and idempotency records are process-local (see
  [architecture.md](architecture.md#request-scoped-identifiers)).
- **Python only.** There is no ABAP or Java port. The tables above map
  concepts; they are not a translation.
- **Not a replacement for the platform.** ABAP hashed and sorted tables,
  database indexes and CDS hierarchy views are the right tools at data scale.
  The value here is the contract around an algorithm (preconditions checked,
  misses as outcomes, stable codes), shown on problems small enough to read
  end to end.
