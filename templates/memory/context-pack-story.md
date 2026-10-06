# Context pack — Story {story-id}

**Feature:** {feature-name}  
**Pack version:** 1  
**Generated:** {ISO-8601-timestamp} (`tasks-2-code-spec` complete)

## Goal (one paragraph)

{What this story delivers for the user/system}

## Acceptance criteria (excerpt)

- {AC 1}
- {AC 2}

## File boundaries

**Create:** {paths}  
**Modify:** {paths}

## Code spec

**Path:** `.adlc5/{feature}/tasks/code-spec/{story-id}.md`
**Read the spec file for full test plan and task order** — do not rely on this pack alone.

## Test commands

```bash
{command to run this story's tests}
```

## Stack / guides

- `detected_stack`: {from scaffold manifest / repository inspection}
- Guides: `skills/adlc5-plan/guides/{stack}.md`

## Repository context

- Constitution: `AGENTS.md`, `.agents/architecture.yaml`, `.agents/boundaries.yaml`, `.agents/commands.yaml`
- Index: `.agent-cache/repo-index.json`
- Snapshot: {from .agent-cache/manifest.json}
- Selected records: {module/symbol/dependency/test paths named by code spec}

## Patterns (optional)

Only if this story **names** a pattern/algorithm to apply: list concept **ids** (e.g. `gof/strategy`) — do **not** paste OKF card bodies or catalog indexes into this pack.

## Dependencies / risks

- {open risk or blocker}
- `platform_supplement_warnings`: {from state if any}

## Out of scope for this story

- {explicit exclusions}
