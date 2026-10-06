---
name: output
description: Phase 3 — Output for S7. Write docs/patterns/<id>.md catalog entry.
---

# Phase 3: Output — Pattern Description

## Purpose

Publish org pattern specification to catalog.

## Output steps

### Step 1: Write file

Path: `docs/patterns/<pattern-id>.md`

Use [../templates/output-template.md](../templates/output-template.md) — user must approve file creation per agent discipline.

### Step 2: Cross-link

- Update `related_patterns` on peer entries if needed
- Remove or archive `_candidates/` stub

### Step 3: Consumability check

- One-screen summary in opening paragraphs
- Findable name and tags for S5 search

### Step 4: S9 handoff

If `implementation: skill`:

```markdown
### Next: @pbe-piecemeal-skill for MVP automation
```

### Step 5: Quality gate

All S7 checklist items from SKILL.md.
