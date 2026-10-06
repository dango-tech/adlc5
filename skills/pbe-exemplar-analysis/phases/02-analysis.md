---
name: analysis
description: Phase 2 — Analysis for S10. Extract roles, collaborations, variability.
---

# Phase 2: Analysis — Exemplar Analysis

## Purpose

Abstract exemplar code into pattern structure for S7.

## Analysis steps

### 1. Read exemplar code

Trace main flow:

- Entry point (adapter)
- Domain/use case core
- External I/O boundaries

### 2. Abstract problem & forces

Remove product nouns:

- Domain-specific → generic force (reliability, extensibility, consistency)

### 3. Identify roles

| Role | Exemplar symbol/module | Responsibility |

Use GoF names when aligned; org names when novel.

### 4. Map collaborations

Bullet or mermaid:

```
Context → Strategy.calculate()
Adapter → Repository.save()
```

Verify dependency direction inward (R2).

### 5. Variability across contexts

Compare exemplar A/B/C from Rule of Three:

| Point | A | B | C |

### 6. Propose pattern id/name

kebab-case id + human name.

### 7. GoF alignment

Primary GoF pattern + confusion pairs (Part IV).

### 8. Gap analysis

Missing roles, untested paths, domain leakage.

### 9. S7 readiness

Yes / No — need additional exemplar?

Proceed to [03-output.md](03-output.md).
