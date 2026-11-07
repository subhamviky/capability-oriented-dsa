# ADR 0003: "Not found" is an outcome; a missing reference is policy-driven

- Status: accepted

## Decision

- A search miss, an unreachable target or an empty traversal is a valid answer:
  `Status.NOT_FOUND`, `found=False`, and the kernel's data is still returned
  (the insertion point, or `(inf, [])`).
- A missing *referenced* key (deleting an unknown node, an unknown vertex)
  raises `NotFoundError` in kernels and repositories. At the governed boundary,
  `missing_key_policy="result"` (the default) maps it to `NOT_FOUND`, and
  `"raise"` re-raises it.
- `NotFoundError` subclasses `InvalidInputError`, so callers catching `InvalidInputError`
  also handle missing references.
