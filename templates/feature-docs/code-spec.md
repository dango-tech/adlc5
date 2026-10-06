<!--
Code-spec skeleton — copy to .adlc5/{feature}/tasks/code-spec/{story-id}.md
during tasks-2-code-spec and fill in both the frontmatter and the prose.

The frontmatter is validated by ./scripts/tasks/spec-lint.py — it backs the
tasks-2-code-spec-complete gate and is what ./scripts/verify-story.py reads
during implement-2-verify. Required: story_id, files_to_create,
files_to_modify (each may be an empty list, but the key must exist), tests
(non-empty), acceptance_criteria (non-empty). signatures is optional but,
when present, lets verify-story.py cross-check against .agent-cache/symbols.json.

The prose body below the frontmatter is what a human or @build-implementer
reads for judgment calls the frontmatter can't express (why this approach,
edge cases, error handling) — the frontmatter is the checklist, not a
replacement for it.
-->
---
story_id: US-000
files_to_create:
  - path/to/new_file.py
files_to_modify:
  - path/to/existing_file.py
tests:
  - file: path/to/test_file.py
    name: test_happy_path
    scenario: one-sentence description of the scenario under test
  - file: path/to/test_file.py
    name: test_edge_case
    scenario: one-sentence description
acceptance_criteria:
  - AC-1
  - AC-2
signatures:
  - symbol: function_or_class_name
    kind: function
    file: path/to/new_file.py
---

# {story-id} — {title}

## Goal

One paragraph: what this story delivers and why.

## Tests first (red)

For each entry in `tests[]` above, describe the scenario and expected
behavior in enough detail that the implementer writes the test before the
code.

## Implementation tasks (green)

Ordered list of the smallest steps that make the tests above pass.

## API / signatures

Public signatures this story introduces or changes — types, params,
returns, exceptions. Mirror `signatures[]` above; this is where you explain
*why*, not just restate the frontmatter.

## Out of scope

Explicit exclusions — what a reader might expect this story to cover that
it deliberately does not.
