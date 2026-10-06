# S6 — Good vs Bad Pattern Review

## Vocabulary

### Bad

> "This isn't clean."

No pattern name; no role reference.

### Good

> **Strategy misalignment:** `Checkout` acts as Context but selects pricing via `switch(promoType)` instead of injected `PricingStrategy` (S5).

---

## Verdict

### Bad

**misaligned** because author didn't mention patterns in PR title.

### Good

**partial** — Observer Subject/Observer roles present; missing unsubscribe (memory leak risk)—document in finding.

---

## Refactor guidance

### Bad

> "Rewrite module to use patterns."

### Good

Step 1: Extract `PricingStrategy` interface. Step 2: Register concrete strategies in adapter module.

---

## Density

### Bad

Reject PR for using only one pattern when S5 specified integrated stack—without checking collaboration.

### Good

Note missing Repository port while Strategy exists—density gap vs S5 layer stack.
