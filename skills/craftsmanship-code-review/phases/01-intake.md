---
name: intake
description: Phase 1 — Intake for S1 Craftsmanship Code Review. Gather scope, diff context, and prior review artifacts before smell analysis.
---

# Phase 1: Intake — Craftsmanship Code Review

## Purpose

Establish review scope and context so Phase 2 analysis targets changed code without wasted effort on untouched files.

## Prerequisites

- Diff, PR link, or explicit file list from user
- Access to test files adjacent to changed production code

## Intake steps

### Step 1: Identify scope

Collect one or more of:

- PR / diff URL or `git diff` range
- Explicit file paths
- Feature name and `.adlc5/` or Delivery artifact path

Record: base branch, head commit, file count, languages detected.

### Step 2: Load prior context

Check for existing reviews that constrain S1:

| Artifact | Location | Use |
|----------|----------|-----|
| S5 pattern selection | Engineer output / design doc | Expected structure vocabulary |
| S3b algorithm advisory | Engineer output | Documented O(·) expectations |
| Delivery code spec | `.adlc5/` or `.fsd3/` | Acceptance criteria for tests |
| Prior S1 on same branch | Chat / saved markdown | Avoid duplicate findings |

### Step 3: Classify change type

Tag the review:

- **feature** — new behavior + tests expected
- **refactor** — behavior preserved; watch for test gaps
- **bugfix** — regression test required
- **config/docs-only** — S1 may be N/A

### Step 4: Note project conventions

Skim one representative file in the repo for:

- Naming style (camelCase, snake_case)
- Test framework and file layout
- Error-handling idioms (exceptions vs Result types)
- Comment density norms

Do not impose personal style — match project.

### Step 5: Intake checklist

- [ ] Scope bounded (files listed)
- [ ] Change type classified
- [ ] Test files included in scope
- [ ] Prior Plan/Implement artifacts loaded if available

## Output of intake

Brief intake note (internal or in final report header):

```markdown
**Scope:** [N files] — [paths summary]
**Change type:** feature | refactor | bugfix | docs
**Prior reviews:** S2/S3/S3b/S5 — yes/no
**Test coverage in diff:** yes | partial | none
```

Proceed to [02-analysis.md](02-analysis.md).
