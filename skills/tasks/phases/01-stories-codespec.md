# Tasks — Stories and code specs

## tasks-1-stories

1. Decompose design into parallelizable stories with file boundaries.
2. Assign `batch` numbers for conflict-free parallel implement.
3. Update `state.tasks.stories[]` with `{ id, title, status, batch, files[], depends_on[] }`.
4. Run `./scripts/tasks/render-board.sh --feature "{feature}"`.

Greenfield: include Story 0 scaffold when `scope.repo_profile` is `greenfield` — see [scaffold-registry.md](../../../core/guides/scaffold-registry.md).

## tasks-2-code-spec

For each story, write `tasks/code-spec/{story-id}.md` starting from
[templates/feature-docs/code-spec.md](../../../templates/feature-docs/code-spec.md):

1. **YAML frontmatter first** — `story_id`, `files_to_create`, `files_to_modify`
   (each a list, may be empty), `tests[]` (non-empty — file + name + scenario
   per case), `acceptance_criteria[]` (non-empty), optional `signatures[]`.
   This is what `./scripts/tasks/spec-lint.py` and `./scripts/verify-story.py`
   read — the code-spec-complete gate now lints it, not just checks that a
   `.md` file exists.
2. **Tests first (prose)** — for each `tests[]` entry, describe the scenario
   and expected behavior in enough detail to write the test before the code.
3. Public API doc stubs — mirror `signatures[]`, explain the *why*.
4. Acceptance criteria trace to spec-handoff.

Lint before moving on:

```bash
./scripts/tasks/spec-lint.py --feature "{feature}" --workspace .
```

## Exit

Gate `tasks-complete` + memory compaction.
