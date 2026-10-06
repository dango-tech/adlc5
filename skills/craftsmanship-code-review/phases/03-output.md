---
name: output
description: Phase 3 — Output for S1. Produce verdict, findings table, and handoff recommendations.
---

# Phase 3: Output — Craftsmanship Code Review

## Purpose

Deliver a structured review artifact the author and `@pr-reviewer` can act on. Cite smell IDs; prioritize fixes.

## Output location

- PR comment (inline or summary)
- Saved markdown alongside feature artifacts when user requests persistence
- Template: [../templates/output-template.md](../templates/output-template.md)

## Step 1: Determine verdict

| Condition | Verdict |
|-----------|---------|
| No blocking/major findings | **pass** |
| Major only, merge acceptable with follow-up | **pass-with-notes** |
| Any blocking finding | **fail** |

## Step 2: Write findings table

Sort by severity (blocking → info). Required columns:

| ID | Smell | Severity | Location | Recommendation |

Every row must include a smell ID (G/F/N/T) or explicit "convention" if project-specific.

## Step 3: Document strengths

List 1–3 genuine positives — encourages Boy Scout culture and confirms good patterns to keep.

## Step 4: Prioritized fix list

Number fixes in merge order:

1. Blocking items
2. Major items in changed files
3. Boy Scout safe wins
4. Deferred minor (optional ticket)

## Step 5: Complete checklist

Include the standard S1 checklist from SKILL.md — all boxes explicitly checked or explained.

## Step 6: Handoffs

If escalations were noted in Phase 2, add:

```markdown
### Recommended follow-up reviews
- [ ] S2 — [reason]
- [ ] S3c — [reason]
- [ ] S6 — [reason]
```

## Step 7: PR vocabulary snippet

Optional short block for copy-paste into PR:

```markdown
> **S1 Craftsmanship Review:** pass-with-notes — G5 duplication in `foo.ts`; add boundary test for empty input (T1).
```

## Output quality gate

- [ ] Verdict stated
- [ ] All findings have smell IDs and locations
- [ ] Strengths included
- [ ] Checklist complete
- [ ] No findings outside diff scope (unless escalated)
