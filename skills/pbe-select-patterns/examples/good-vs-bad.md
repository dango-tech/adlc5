# S5 — Good vs Bad Pattern Selection

## Requirements trace

### Bad

> "Use Observer, Strategy, and Facade."

No requirement IDs; pattern shopping.

### Good

| R3: Notify on status change | events | Observer | GoF — decouples UI from domain |

---

## Large-scope first

### Bad

Pick **Decorator** before defining use case boundaries.

### Good

S2: `NotificationPort` adapter → then Observer among domain subscribers.

---

## Density

### Bad

Three patterns listed with no collaboration.

### Good

Repository (port) + Strategy (pricing) + Factory (strategy selection)—documented data flow.

---

## Catalog discipline

### Bad

Propose new catalog entry during S5 without S8.

### Good

GoF ad hoc for one-off; note "watch for S4 if second team repeats."
