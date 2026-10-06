# S1 — Good vs Bad Review Examples

Brief examples of craftsmanship review comments and code patterns.

## Finding comments

### Bad

> "This function is too long and messy. Please refactor."

No smell ID, no location, no actionable fix.

### Good

> **G5 / major** — `OrderService.applyDiscounts` (lines 42–78) duplicates validation logic from `validateOrder`. Extract `assertOrderEligible(order)` shared helper.

---

## Code: naming (N1)

### Bad

```typescript
function proc(d: any) {
  return d.x + d.y;
}
```

### Good

```typescript
function computeLineTotal(lineItem: LineItem): Money {
  return lineItem.unitPrice.plus(lineItem.tax);
}
```

---

## Code: tests (T5)

### Bad

```typescript
expect(service.internalCache.size).toBe(1);
```

Asserts implementation detail.

### Good

```typescript
expect(await service.getUser("u1")).toEqual(expectedUser);
```

Asserts observable behavior.

---

## Review scope

### Bad

Rewriting untouched files "while we're here."

### Good

Boy Scout fixes limited to lines changed in the PR; out-of-scope issues filed separately.
