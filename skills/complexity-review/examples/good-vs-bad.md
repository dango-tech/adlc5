# S3c — Good vs Bad Complexity Review

## Hot path identification

### Bad

> "Performance looks fine."

No paths, no O(·).

### Good

> **Hot path:** `enrichOrders` — nested loop orders × items (lines 44–52). **Observed:** O(n×m); at n=m=10⁴ → 10⁸ iterations.

---

## N+1 detection

### Bad

Missing ORM query-in-loop because only counting for-loops.

### Good

Flag AP6: `orders.forEach(o => repo.getItems(o.id))` — n DB round-trips.

---

## Verdict

### Bad

**fail** because code "could be faster" without n context.

### Good

**fail** — AP1 at expected n=10⁵; S3b specified O(n log n); observed O(n²).

---

## N/A

### Bad

N/A on PR adding graph traversal over user-supplied DAG.

### Good

N/A only when diff has no unbounded loops and S3b documented small n with evidence.
