# Implement — Build through PR

## implement-1-build

1. `tiny`: implement the bounded `spec-handoff.md` directly; no synthetic story
   or empty batch scaffolding. Other profiles read
   `state.tasks.parallel_batches`.
2. For each planned story, spawn `@build-implementer` with its generated
   context pack.
3. Run `./scripts/run-tests.sh` and `./scripts/run-lint.sh` per story completion.
4. Story status → `implementation_complete` only when tests pass.

Gate: `./scripts/check-gates.py --gate implement-1-build`

## implement-2-verify

Spawn `@assure-verifier` per story. `@assure-verifier` runs `./scripts/verify-story.py` first when the code spec has lever-2 frontmatter — it reasons about what that leaves, not the whole story from scratch. Rework via `@adlc5-assure-reworker` (max 3 attempts).

Sync report: `./scripts/sync-verification-report.sh --feature "{feature}"`

## implement-3-integrate

Integration story + E2E. Set `implement.integration.status: completed`.

## implement-4-qa

Invoke `@qa`. Require `.qa/{feature}/deployment-clearance.md` with `CLEARED`.

## implement-5-pr

Invoke `@pr-reviewer`. Record PR URL in state.

## Terminal gate

```bash
./scripts/check-gates.py --feature "{feature}" --gate pr-ready
./scripts/memory/compact-stage.sh --feature "{feature}" --stage implement
```
