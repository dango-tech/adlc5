# S3 — Good vs Bad Pattern Advisory

## Problem framing

### Bad

> "Use Factory pattern for this service."

Pattern first; no forces.

### Good

> **Problem:** Object creation for notification channels is scattered across controllers. **Forces:** New channels quarterly; tests must stub delivery without HTTP.

---

## Pattern selection

### Bad

Recommending **Singleton** for convenience without concurrency or test isolation analysis.

### Good

Recommend **Factory Method** in adapter layer; reject **Abstract Factory** because only one product hierarchy exists today (OCP sufficient with FM).

---

## Confusion pairs

### Bad

Using **Decorator** when behavior is fully replaced → should be **Strategy**.

### Good

Document: "Behavior extension at runtime with stacked responsibilities → Decorator; full algorithm swap → Strategy."

---

## Density

### Bad

Observer + Strategy + Facade + Singleton listed with no collaboration story.

### Good

Strategy for pricing; Factory Method creates Strategy instances; single Facade at adapter boundary for external API—integrated stack.
