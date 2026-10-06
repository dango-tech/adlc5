# Promotion packet — {feature-name}

**Prepared:** {ISO-8601-timestamp}  
**Feature:** `.adlc5/{feature}/`  
**Prerequisite:** Implement complete
**Status:** pending_review

## Summary

| Metric | Count |
|--------|-------|
| Candidates | {n} |
| With evidence | {n} |
| Conflicts | {n} |

## Candidates

### {candidate-id}

**Proposed target:** `wiki/entities/{slug}.md`  
**Source:** `.adlc5/{feature}/memory/promotion-candidates.md`  
**Claim:** {one-line claim}

**Evidence:**

- `{path}:{start-end}` @ `{commit-short}`

**Doc conflict (if any):**

- `{doc-path}` — stale / contradicts code

**Review question:** Accept as project truth?

- Options: promote_entity | promote_concept | reject | investigate

---

## Human actions

1. Run `@adlc5-project-wiki promote-review` (AskQuestion batches).
2. Write `approved.json` in this directory (ids + targets only).
3. Run `promote-apply.sh --feature {feature-name}`.
