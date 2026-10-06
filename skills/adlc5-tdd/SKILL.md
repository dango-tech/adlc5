---
name: adlc5-tdd
description: ADLC5 TDD discipline — FIRST tests, red-green-refactor, Boy Scout rule. Used during Implement by @adlc5-implement and @build-implementer. Link to Clean Code knowledge base.
---

# ADLC5 — TDD Discipline

## Intent

Canonical **Test-Driven Development** practices for ADLC5 Tasks code specs and Implement build work. Referenced by `@adlc5-tasks`, `@adlc5-implement`, and `@build-implementer`.

**Knowledge base (primary):** [../knowledge-base/02-clean-code.md](../../shared/docs/knowledge-base/02-clean-code.md) — Part II, especially Ch 9 (Unit Tests) and Ch 12 (Emergence)  
**Playbook:** [../playbook.md](../../shared/docs/playbook.md) — Implement stage gates  
**Rules:** R3 `cc-functions-and-tests.mdc`

### Model recommendation

**Tier:** implementation — used with `@build-implementer`; inherit parent model. See [model-matrix.md](../../core/guides/model-matrix.md).

---

## When to apply

- **Tasks (`tasks-2-code-spec`):** List tests before implementation tasks
- **Implement (`implement-1-build`):** Write failing test → minimal code → refactor
- **Rework:** Add regression test before fix when bug found post-implementation

---

## FIRST principles

From [Clean Code Ch 9](../../shared/docs/knowledge-base/02-clean-code.md):

| Letter | Principle | Agent rule |
|--------|-----------|------------|
| **F** | Fast | Unit tests run in seconds; mock I/O at boundaries |
| **I** | Independent | No shared mutable state; order-agnostic |
| **R** | Repeatable | Same result in CI and locally; no flaky timing |
| **S** | Self-validating | Pass/fail without manual inspection |
| **T** | Timely | Written **before** production code (TDD) |

**One assert per concept** — multiple assertions OK when testing one behavior.

---

## Red → Green → Refactor

```
┌─────────┐     ┌─────────┐     ┌───────────┐
│   RED   │ ──► │  GREEN  │ ──► │ REFACTOR  │
│ failing │     │ minimal │     │  improve  │
│  test   │     │  pass   │     │  re-test  │
└─────────┘     └─────────┘     └───────────┘
       ▲                              │
       └──────── next task ───────────┘
```

### Red

- Pick next task from code spec (tests section first)
- Write the smallest test expressing desired behavior
- Run — confirm failure message is meaningful (wrong reason = fix test)

### Green

- Write **minimal** code to pass — no speculative features
- Run — confirm green; do not proceed with failing tests

### Refactor

- Rename, extract, deduplicate ([G5 Duplication](../../shared/docs/knowledge-base/02-clean-code.md))
- Re-run tests after each refactor step
- **Boy Scout rule:** leave code cleaner than you found it

---

## Boy Scout rule

> Leave the code cleaner than you found it.

During refactor step only:

- Improve names in touched files ([N1 heuristic](../../shared/docs/knowledge-base/02-clean-code.md))
- Split functions doing more than one thing ([G30](../../shared/docs/knowledge-base/02-clean-code.md))
- Do not expand scope beyond current story file boundaries

---

## Code spec alignment

TDD in Delivery is spec-driven:

1. Code spec lists test file, test name, scenario
2. Implementer writes that test (red)
3. Implements matching signature from spec (green)
4. Refactors to match project patterns

If test and spec conflict — **stop and report** to orchestrator (possible spec bug → rework guide).

---

## Test quality bar

- **Behavior over implementation** — assert outcomes, not private internals
- **Boundaries** — happy path, edge cases, error paths per acceptance criteria
- **Learning tests** — for third-party APIs you don't control ([Clean Code Ch 8](../../shared/docs/knowledge-base/02-clean-code.md))
- **Test code as clean as prod** — readable arrange/act/assert

Avoid:

- Tests that mirror implementation line-for-line
- Broad mocks that don't reflect real contracts
- Skipping red step ("write test and code together" without seeing failure)

---

## Diagnosis when red won't go green

1. Is the **test** wrong? (bad mock, wrong expectation) → fix test
2. Is the **code** wrong? (spec violation) → fix code
3. Is the **spec** ambiguous? → report; don't guess

Never weaken assertions to match buggy code.

---

## Integration with ADLC5 lifecycle

| Stage | TDD role |
|-------|----------|
| Tasks | Tests named in code spec |
| Implement build | Red-green-refactor per `@build-implementer` |
| Implement verify | Verifier confirms spec tests exist and pass |

**Invoke chain:** `@adlc5` → `@adlc5-implement` → `@build-implementer` (follows this skill)

---

## Quick reference

- **Functions:** small, one thing, stepdown rule ([Ch 3](../../shared/docs/knowledge-base/02-clean-code.md))
- **Emergence:** all tests pass → no duplication → expresses intent → minimal elements ([Ch 12](../../shared/docs/knowledge-base/02-clean-code.md))
- **Smells in review:** cite G/F/N/T IDs from the knowledge base during Implement review
