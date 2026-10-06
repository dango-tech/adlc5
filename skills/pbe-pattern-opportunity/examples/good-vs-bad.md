# S4 — Good vs Bad Opportunity Scan

## Problem statement

### Bad

> "We use Singleton in three places."

Name without forces; Singleton is often an antipattern.

### Good

> **Problem:** Need single coordinated cache of config across handlers without stale reads. **Evidence:** three services with duplicate refresh logic (paths …).

---

## Rule of Three

### Bad

Three copies of same file in one repo from copy-paste = 3 contexts.

### Good

Three **unique** bounded contexts (billing, auth, campaigns) with same outbox shape.

---

## Action routing

### Bad

> "Add to catalog immediately."

### Good

> **outbox-relay:** Meets Rule of Three → **Proceed to S8** before S7.

---

## Scope

### Bad

Cataloging a one-line utility as org pattern.

### Good

Defer idiom until recurrence proven; use GoF/local helper ad hoc.
