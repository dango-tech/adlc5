# S3b — Good vs Bad Algorithm Advisory

## NFR capture

### Bad

> "Should be fast."

No n, no latency number.

### Good

> n ≈ 2×10⁵ SKUs peak; p99 lookup < 50ms; in-memory budget 512MB per pod.

---

## Recommendation

### Bad

> "Use a hash map."

No O(·); ignores range queries.

### Good

> **Sorted array + binary search** — O(log n) lookup; O(n) rebuild on bulk import acceptable (batch nightly). Rejected hash: need range queries by SKU prefix.

---

## N/A path

### Bad

Skipping advisory entirely on batch job processing millions of rows.

### Good

> **N/A** not appropriate — document O(n log n) external sort with streaming I/O; flag S3c.

---

## Architecture

### Bad

Embedding Redis client calls inside entity class.

### Good

Use case defines `ProductCatalog` port; adapter implements indexed lookup (R2).
