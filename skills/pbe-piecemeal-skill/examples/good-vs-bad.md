# S9 — Good vs Bad Piecemeal Implementation

## MVP scope

### Bad

Build codegen + wizard + three skills before any team uses v1.

### Good

Single skill: intake → checklist → output template covering primary variability point.

---

## Perfect Pattern

### Bad

Delay shipping until "complete" pattern automation.

### Good

Ship 80% skill in current iteration; v1.1 backlog explicit.

---

## Consumability test

### Bad

> "Skill written."

No dry-run on exemplar.

### Good

Dry-run log: agent followed steps on `services/billing/outbox/` — gaps listed.

---

## Spec link

### Bad

Orphan skill with no link from `docs/patterns/<id>.md`.

### Good

Pattern spec **Implementation** section: `@outbox-relay` + version note.
