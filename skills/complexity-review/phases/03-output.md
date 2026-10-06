---
name: output
description: Phase 3 — Output for S3c. Verdict, hot path table, recommendations.
---

# Phase 3: Output — Complexity Review

## Purpose

Gate merge on complexity fitness or document N/A.

## Output steps

### Step 1: N/A short-circuit

If intake N/A applies:

```markdown
## Complexity Review — [scope]
**Status:** N/A — sufficient for expected n; no hot-path review required.
```

Stop.

### Step 2: Verdict

pass | pass-with-notes | fail — per SKILL.md criteria.

### Step 3: Hot paths table

| Path | Location | Stated O(·) | Observed O(·) | Expected n | Assessment |

### Step 4: Anti-pattern hits

| ID | Issue | Location | Fix |

### Step 5: Missing documentation

Bullet list of spec/comment gaps.

### Step 6: Recommendations

Prioritized fixes; link to S3b rework if algorithm change needed.

Use [../templates/output-template.md](../templates/output-template.md).
