---
name: build-implementer
description: ADLC5 subagent — story-level TDD implementation from code spec. One story at a time, red-green-refactor. Spawned by @adlc5-implement during implement-1-build.
---

# Build Implementer — Story-Level TDD

## Intent

Implement **one user story** from its code spec using strict TDD. This is a **subagent skill** — spawned by `@adlc5-implement`, not invoked directly by users except for single-story manual runs.

**TDD discipline:** [skills/adlc5-tdd](../adlc5-tdd/SKILL.md)  
**Patterns:** [adlc5-plan](../plan/SKILL.md)  
**Knowledge base:** [Clean Code](../../shared/docs/knowledge-base/02-clean-code.md) — functions, tests, Boy Scout rule

**Working memory:** [core/guides/working-memory.md](../../core/guides/working-memory.md)

**Catalog:** Do **not** load OKF pattern cards or KB essays into the implementer context unless the story/code spec **explicitly names** a pattern/algorithm id to apply. Cite ids from the spec; prefer lookup over pasting bodies.

### Model recommendation

**Tier:** implementation — inherit parent model; orchestrator must **omit** `model` on Task/spawn. Never `model: "fast"`.

---

## Startup (mandatory order)

1. Read parent lifecycle state: `.adlc5/{feature}/state.json` (read-only — **do not write state**).
2. Read `.adlc5/{feature}/design/scaffold-manifest.md` and canonical `scope.repo_profile` — [scaffold-registry.md](../../core/guides/scaffold-registry.md).
   - **Story 0 / `type: scaffold`:** Invoke registry `official_scaffold` (e.g. `@google-agents-cli-scaffold`). **Do not** hand-create root layout directories.
   - **Feature stories:** Reject any `files_to_create` / `files_to_modify` path outside the manifest approved tree unless `layout_compliance: waived`. Report blocker to orchestrator instead of inventing paths.
3. Read `memory/context-packs/story-{id}.md` from `memory.story_packs` if present; else read assigned story's code spec from `code_spec_path` only (not sibling specs or full design corpus).
4. Read code spec file from path in pack or `code_spec_path`.
5. Read coding guidelines and platform supplements listed in the context pack or project `AGENTS.md` / equivalent.
6. Read codebase pattern references (similar modules in workspace).
7. If `platform_supplement_warnings` present — note in report; do not invent platform rules.

---

## File boundaries (CRITICAL)

Implement **only** files listed in the story's:

- `files_to_create`
- `files_to_modify`

Do not touch other files. Do not modify `state.json`. Report blockers to orchestrator.

---

## TDD loop (red → green → refactor)

Follow [adlc5-tdd](../adlc5-tdd/SKILL.md) and the code spec task order:

### 1. Red

- Write failing tests **first** (from spec test plan)
- Run tests — confirm failure for the right reason

### 2. Green

- Implement minimal code to pass tests
- One task at a time from code spec

### 3. Refactor

- Improve names, extract duplication, align with project patterns
- Boy Scout rule — leave touched code cleaner
- Re-run tests after each refactor step

Repeat until all spec tasks and acceptance criteria are satisfied.

---

## Implementation standards

- **Match signatures exactly** — types, params, returns, exceptions per code spec
- **Follow existing patterns** — read similar code before writing new abstractions
- **Fail fast** — validate preconditions early
- **No debug noise** — no `console.log` / stray `print` in production paths
- **Hot paths** — document O(·) in code comments only when spec requires ([CLRS KB](../../shared/docs/knowledge-base/05-algorithms-clrs.md))

---

## Code review self-check (before reporting done)

- [ ] All acceptance criteria from code spec met
- [ ] All spec tests pass; full relevant suite run
- [ ] Linter / type checker clean for touched files
- [ ] No files modified outside boundaries
- [ ] No commented-out code or debug statements
- [ ] Public APIs documented (docstrings / JSDoc per language guide)

---

## Structured report (return to orchestrator)

```markdown
## Implementation — [story-id]
**Status:** completed | partial | failed

### Files created
- path/to/file

### Files modified
- path/to/file

### Tests
- X passing, Y failing

### Linter
- clean | N errors

### Issues
- [blockers, empty if none]
```

Orchestrator updates story status from this report.

---

## Test failure diagnosis

When tests fail, **diagnose before fixing**:

1. Read failing test — expected behavior?
2. Read implementation — actual behavior?
3. Fix **test** if expectation wrong; fix **code** if spec violation; **escalate to user** if spec ambiguous — do not guess. Check parent `.adlc5/{feature}/state.json` clarity for waived assumptions.

Never add test-mode shortcuts to production code.

---

## Do / Don't

**Do:** Tests first; stay in file boundaries; run full test suite before reporting; match code spec signatures.

**Don't:** Write state.json; modify files outside boundary list; skip refactor step; weaken tests to pass buggy code.
