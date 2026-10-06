# Craftsmanship Code Review — [scope / PR title]

**Date:** [YYYY-MM-DD]  
**Reviewer:** [@craftsmanship-code-review / agent]  
**ADLC5 stage:** Implement
**Verdict:** pass | pass-with-notes | fail

---

## Intake summary

| Field | Value |
|-------|-------|
| Scope | [N files — list or PR link] |
| Change type | feature / refactor / bugfix |
| Test files in diff | yes / partial / none |

---

## Findings (by severity)

| Severity | ID | Smell | Location | Recommendation |
|----------|-----|-------|----------|----------------|
| blocking | G5 | Duplication | `path:line` | Extract shared … |
| major | T1 | Insufficient tests | `path:line` | Add case for … |
| minor | N1 | Non-descriptive name | `path:line` | Rename to … |

---

## Strengths

- [Specific positive observation with location]

---

## Suggested fixes (priority order)

1. [Blocking or highest-impact fix]
2. [Next fix]

---

## Checklist

- [ ] Names (N)
- [ ] Functions (F / G30)
- [ ] General smells (G)
- [ ] Tests (T)
- [ ] Error handling
- [ ] No AI slop in changed hunks

---

## Follow-up reviews

- [ ] S2 — [reason or N/A]
- [ ] S3c — [reason or N/A]
- [ ] S6 — [reason or N/A]

---

## PR comment snippet

> **S1:** [verdict] — [one-line summary of top finding or "clean diff"]
