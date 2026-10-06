---
name: pbe-piecemeal-skill
description: >-
  Create MVP pattern implementation — skill, rule, or hook delivering ~80%
  catalog value early. Use at Catalog stage after S7 spec. Invoke with
  @pbe-piecemeal-skill.
---

# S9 — PBE Piecemeal Skill

**ADLC5 stage:** Catalog (Production — implementation)  
**Skill ID:** S9  
**Knowledge base:** [Part I §I.5 Piecemeal Pattern Creation](../../shared/docs/knowledge-base/01-pbe.md)  
**Rules:** R0 `pbe-core-values.mdc`  
**Playbook:** Part I §I.5 (Piecemeal), §I.2 (implementation types)

Implement from the **one** S7 spec id under edit — do not paste sibling catalog cards into the skill authoring turn.

## Purpose


### Model recommendation

**Tier:** balanced. See [core/guides/model-matrix.md](../../core/guides/model-matrix.md) and config.yaml model_profiles.

Ship ~80% pattern consumability as skill, rule, or hook—during the current project, not at harvest time. S9 implements the S7 spec incrementally; avoid Perfect Pattern full automation upfront.

## When to invoke

- S7 spec approved; `implementation: skill | rule-only | hook` decided
- Ship 80% consumability before full automation (wizard, codegen, M2T)
- Iteration adds pattern asset during current project (not "harvest at end")

**Antipattern guard:** Avoid Perfect Pattern — MVP first, expand from feedback.

## Phase workflow

| Phase | File | Focus |
|-------|------|-------|
| 1 — Intake | [phases/01-intake.md](phases/01-intake.md) | S7 spec, artifact type |
| 2 — Analysis | [phases/02-analysis.md](phases/02-analysis.md) | MVP scope, variability coverage |
| 3 — Output | [phases/03-output.md](phases/03-output.md) | Author artifact, wire invoke |

**Template:** [templates/output-template.md](templates/output-template.md)  
**Examples:** [examples/good-vs-bad.md](examples/good-vs-bad.md)

## Steps (summary)

1. **Read S7 spec** — Variability points, consequences, related patterns.
2. **Choose artifact type** — Skill (guided workflow), rule (always-on constraint), or hook (automation).
3. **Define MVP scope** — Minimum steps that deliver repeatable value; defer codegen/wizards.
4. **Author artifact** — Follow existing `skills/*/SKILL.md` or `.cursor/rules/*.mdc` conventions:
   - YAML frontmatter (`name`, `description`)
   - When to invoke, steps, output format
   - Link to `docs/patterns/<id>.md` and playbook section
5. **Wire invoke** — Document `@skill-name` or rule activation; update pattern metadata `implementation`.
6. **Test consumability** — Dry-run on exemplar from S10; agent can follow without guessing.
7. **Version & feedback** — Pattern is alive; note v1.0 limitations and planned v1.1 expansions.

## Artifact selection guide

| Need | Artifact |
|------|----------|
| Guided review/selection workflow | `skills/<name>/SKILL.md` |
| Always-on constraint | `.cursor/rules/<name>.mdc` |
| Event-driven guard or hint | `.cursor/hooks.json` + script |

## MVP scope guidance

| Include in v1 | Defer to v1.1+ |
|---------------|----------------|
| Core workflow steps | Codegen / wizards |
| Output template | Full phase library |
| Link to pattern spec | M2T model integration |
| One exemplar dry-run | Multi-repo exemplars |

## Integration with ADLC5

```
S7 spec → S9 MVP → S5 consumption → S6 verification in PRs
```

Update pattern `version` when S9 expands coverage.

## Output format

```markdown
## Piecemeal Implementation — [pattern-id]

### MVP delivered
| Artifact | Path | Covers variability |
|----------|------|-------------------|

### Deferred (v1.1+)
- …

### Invoke
@…

### Verification
- [ ] Dry-run on exemplar
- [ ] Linked from pattern spec
- [ ] Playbook Part X skill map updated (if applicable)
```

Reference: playbook Part I §I.5 (Piecemeal), §I.2 (implementation types), Part I §I.7 (Perfect Pattern antipattern).

## Quality gates

- [ ] Covers primary variability point from S7
- [ ] `@invoke` documented
- [ ] Pattern spec cross-linked
- [ ] Dry-run completed on S10 exemplar
- [ ] v1.0 limitations explicit

## Handoffs

| Outcome | Next |
|---------|------|
| Skill authored | S5 can reference in catalog search |
| Rule authored | Always-on in Cursor sessions |
| Hook authored | Verify hooks.json registration |

## Authoring conventions

Mirror existing craftsmanship skills in `skills/`:

- YAML frontmatter with `name` and `description`
- **ADLC5 stage** and **Knowledge base** links at top of body
- Phase files optional in v1; link to S7 spec required
- Output format section with markdown template
- `@invoke` name matches directory kebab-case

Rules (`.cursor/rules/*.mdc`) need globs and `alwaysApply` decision documented in implementation record.

Hooks require entry in `.cursor/hooks.json`—coordinate with repo hook owners before merge.

## Feedback loop

After first production use:

- Collect S6 drift findings → S7 spec patch
- Expand S9 artifact to v1.1 covering deferred variability
- Bump pattern `version` semver appropriately

Patterns are **alive** (R0)—MVP is start, not finish.
