---
name: pr-reviewer-review
description: PR Review Phase 02 — Review branch diff before merge.
---

# Phase 02 — Review

## Purpose

Review the feature branch changes before merge. Complements **@craftsmanship-code-review** (S1) and Delivery verification — PR Review focuses on **diff scope, risk, and merge readiness**, not replacing smell heuristics.

## Steps

1. Detect branch:

```bash
./scripts/pr-reviewer-detect.sh --workspace .
```

2. Obtain PR context:

**GitHub** (`provider: github`, `gh_authenticated: true`):

```bash
./scripts/pr-reviewer-gh.sh --action status --branch "{branch}"
./scripts/pr-reviewer-gh.sh --action diff --branch "{branch}"
./scripts/pr-reviewer-gh.sh --action checks --branch "{branch}"
```

**Fallback / no PR yet:**

```bash
git diff origin/{base_branch}...HEAD
```

3. Scope review to ADLC5 feature artifacts when present:
   - `.adlc5/{feature}/spec-handoff.md`
   - Code specs / design docs referenced in canonical state and memory index
   - `.qa/{feature}/deployment-clearance.md`

4. Produce structured report at `.adlc5/{feature}/pr-reviewer/review.md`:

```markdown
## PR Review review — {feature}
**Verdict:** approve | request_changes | comment

### Scope
- Files changed: N
- Commits: ...

### Findings
| Severity | File | Note |
|----------|------|------|

### Merge readiness
- [ ] Tests/lint per selected profile and `pr-ready`
- [ ] No unresolved blockers
```

5. **AskQuestion:** post comments on host? (yes / no / N/A manual host)

6. Invoke **@craftsmanship-code-review** on the same diff when the selected profile requires it and it has not yet run.

## Exit criteria

- [ ] `review.md` written
- [ ] User informed of verdict and next step (merge, fix, respond phase)
