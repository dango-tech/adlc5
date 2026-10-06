---
name: pbe-select-patterns
description: >-
  Requirements-driven pattern selection — large-scope first, catalog search,
  HFDP GoF fit. Use during Plan with functional requirements and NFRs. Invoke with
  @pbe-select-patterns.
---

# S5 — PBE Select Patterns

**ADLC5 stage:** Engineer  
**Skill ID:** S5  
**OKF catalog:** [shared/docs/patterns/index.md](../../shared/docs/patterns/index.md) (search by `requirements_tags` / `tags`)  
**Knowledge base (deep, on demand):** [Part I §I.6 Consumption + Part VI synthesis](../../shared/docs/knowledge-base/06-synthesis.md)  
**Rules:** R0, R1 `pbe-consumption.mdc`, R2, R4  
**Playbook:** Part I §I.6, Part VI §VI.1–VI.3 (decision flow, density)

### Catalog load (hard rules)

- Default: `patterns/index.md` (or one group index) — never paste the full catalog into the turn.
- Lookup: `./scripts/adlc5 patterns lookup --tags …` → open **at most 1–3** matching concept cards.
- KB essays **only if** cards are insufficient. Prefer citing **ids** in design docs over embedding card bodies.
- Do not attach catalog to Build/implementer packs unless a story explicitly names a pattern.

## Purpose


### Model recommendation

**Tier:** balanced. See [core/guides/model-matrix.md](../../core/guides/model-matrix.md) and config.yaml model_profiles.

Map functional requirements and NFRs to an integrated pattern stack—architecture first, then design, then algorithms. S5 is the Engineer gate for pattern consumption before `@adlc5-plan` Plan.

## When to invoke

- Feature design with documented requirements and scale NFRs
- Choosing between org catalog (`shared/docs/patterns/`) and community GoF
- Engineer gate for `@adlc5` before `@adlc5-plan` Plan
- Broader than S3 alone — ties requirements → architecture → design patterns

**Prefer S3 alone** for a narrow structural sub-problem; use S5 for end-to-end selection.

## Phase workflow

| Phase | File | Focus |
|-------|------|-------|
| 1 — Intake | [phases/01-intake.md](phases/01-intake.md) | Requirements, NFRs, catalog |
| 2 — Analysis | [phases/02-analysis.md](phases/02-analysis.md) | Large-scope first, density |
| 3 — Output | [phases/03-output.md](phases/03-output.md) | Layer stack, handoffs |

**Template:** [templates/output-template.md](templates/output-template.md)  
**Examples:** [examples/good-vs-bad.md](examples/good-vs-bad.md)

## Steps (summary)

1. **Requirements map** — Functional reqs + scale NFRs; tag latency, search, throughput, etc.
2. **Search OKF catalog** — `./scripts/adlc5 patterns lookup --tags …`; open ≤3 matching concepts; note hits/misses (never glob-read everything).
3. **Large-scope first** — Architecture (R2/CA) → design (HFDP) → idioms; order matters (`pbe/large-scope-first`).
4. **Pattern density** — Select complementary patterns that integrate; avoid isolated counting (`pbe/pattern-density`).
5. **GoF fit** — Load `gof/*` cards via S3 logic for gaps; cite concept ids.
6. **Algorithm layer** — If scale NFRs apply, invoke S3b (`algorithms/*` cards).
7. **Variability points** — What adapts per use case vs fixed scaffold.
8. **Document choices** — Pattern names + OKF ids + rationale for ADLC5 delivery design and PR vocabulary (S6).

## Large-scope first (R1)

```
1. Architecture (ports/adapters, boundaries) — S2 → architecture/*
2. Design (GoF structure) — S3 → gof/*
3. Algorithm (O(·) at scale) — S3b → algorithms/*
4. Idiom / catalog skill — clean-code/* or org-specific concepts
```

Never pick Decorator before boundaries exist.

## Catalog search (OKF)

Progressive disclosure (mandatory):

1. `./scripts/adlc5 patterns lookup --tags …` (ids/paths) **or** `shared/docs/patterns/index.md`
2. At most one group `index.md` (`gof/`, `algorithms/`, `pbe/`, `architecture/`, `clean-code/`)
3. **≤3** matching concept files only — cite ids in S5 output

Frontmatter fields: `requirements_tags`, `related_patterns`, `skill_invoke`, `type`, `status`.

## Integration with ADLC5

```
Specify → Plan (S5 + S2 + S3b) → Tasks → Implement (S6)
```

- S5 output feeds Tasks code specs and S6 PR vocabulary.
- New catalog entries require S4 + S8—not during S5 unless pre-approved.

## Output format

```markdown
## Pattern Selection — [feature / use case]

### Requirements ↔ patterns
| Requirement | NFR tags | Pattern(s) | Source (catalog / GoF) |
|-------------|----------|------------|------------------------|

### Layer stack (inside → out)
1. Architecture: …
2. Design: …
3. Algorithm (if any): …

### Catalog usage
- Applied: …
- Not in catalog (GoF ad hoc): …

### Density notes
…

### Handoffs
- [ ] S2 if boundaries unclear
- [ ] S3b if scale-sensitive
- [ ] S8 before adding new catalog entry
```

Reference: playbook Part I §I.6, Part VI §VI.1–VI.2 (decision flow, when to invoke each layer).

## Anti-patterns

- Pattern shopping without requirements trace
- Counting patterns for coverage metric
- Skipping S2 on greenfield service
- Catalog entry proposal without S8

## Handoffs

| Gap | Skill |
|-----|-------|
| Boundaries unclear | S2 |
| Narrow structural question | S3 |
| Scale / hot path | S3b |
| New catalog candidate | S4 → S8 |
