# `<PLATFORM>` Platform Supplement — Template

<!--
This file is the normative template for ADLC5 platform supplements.

A platform supplement captures the invariants of a specific hosted runtime
(topology, identity model, tenant model, environment ladder, event plane,
routing, data-residency rules) that no amount of framework or
cloud-provider guidance can express.

Token contract (agent companion):
- NORMATIVE ONLY — no narrative, no rationale, no marketing.
- Tables over prose wherever a table is sufficient.
- MUST / MUST NOT / MAY rules — never "should consider".
- No mermaid diagrams.
- No examples beyond the minimum needed to disambiguate a rule.
- Every section heading below is REQUIRED. Sections that do not apply to
  the platform are kept with the body "Not applicable." — do not delete.

Authoring instructions (delete this comment block in the populated supplement):
1. Copy this file to `<PLATFORM>-PLATFORM-SUPPLEMENT.md` (uppercase).
2. Replace every `<…>` placeholder with the platform's authoritative value.
3. Source field names, regexes, and rules from the platform's authoritative
   architecture document (preferably its `.agent.md` companion if one exists).
4. Wire the new supplement into both subagent inventory blocks
   (`subagents/build-implementer.md` and `subagents/adlc5-assure-reworker.md`) in
   the same commit, verbatim-aligned.
5. Add the supplement's metadata to the Loading Trigger row below.
-->

**Loaded alongside:** the base language guide, framework supplement (if any), and cloud-provider supplement (if any).
**Applies when:** `state.json.context.detected_stack.platform == "<platform-name>"` AND `platform_supplement_loaded == true`.
**Precedence:** This supplement wins over the cloud-provider supplement and the framework supplement for architectural / integration rules. The base language guide wins for language-level coding conventions.

| Loading Trigger | Value |
|---|---|
| `platform` field | `"<platform-name>"` (lowercase, kebab-case) |
| Detection signals | `<list — e.g., .platform-name/, PLATFORM.md, adlc5-plan.config.yaml `platform:` key, explicit user assertion>` |
| Authoritative source | `<path or URL to the platform's normative architecture document>` |
| Last reconciled with source | `<YYYY-MM-DD>` |

---

## 1. Abbreviations

| Abbrev | Meaning |
|---|---|
| `<ABBR>` | `<full term>` |

---

## 2. Environments

| Tier | Region(s) | Promotion gate | Artefact identity |
|---|---|---|---|
| `<engineering / dev / qa / stage / prod>` | `<regions present at this tier>` | `<approval / automated / N/A>` | `<same artefact at every tier? yes/no>` |

**Invariants:**

1. `<MUST / MUST NOT statement about artefact identity across tiers>`
2. `<MUST / MUST NOT statement about region presence>`

---

## 3. Region codes

| Code grammar | Regex |
|---|---|
| `<grammar — e.g., {cloud}-{region-short}>` | `<regex — e.g., ^[ag]-[a-z]{2}\d$>` |

| Code | Cloud | Geographic region | Environments present |
|---|---|---|---|
| `<a-us1>` | `<aws>` | `<us-east-1>` | `<dev, qa, stage, prod>` |

---

## 4. Tenant / workspace / isolation unit

| Aspect | Value |
|---|---|
| Identifier name | `<tenant_id / workspace_id / org_id / …>` |
| Identifier grammar | `<plain-language description>` |
| Identifier regex | `<regex>` |
| Authoritative registry | `<service or database name>` |
| Classification fields owned by registry | `<env, tier, region, data classification, active flag, …>` |

**Reserved identifiers that are NOT tenants (exclusion list):**

| Reserved identifier | Purpose | Bypass behaviour |
|---|---|---|
| `<env-marker / system tenant / synthetic id>` | `<what it represents>` | `<which validations skip this id>` |

**Rules:**

1. **MUST** resolve `<classification field>` via `<authoritative registry>` only. No shadow registries; no inferring from identifier prefix.
2. **MUST NOT** derive `<env / tier / region / SLA / data classification>` from the identifier prefix. Prefix characters are non-authoritative hints only.
3. **MUST NOT** treat any identifier in the exclusion list above as a tenant in business logic.
4. `<additional MUST / MUST NOT rules specific to the platform>`

---

## 5. Control plane / data plane split

*(Delete this section if the platform does not have a CP/DP separation.)*

| Plane | Hosts | Processes tenant data? | Region(s) |
|---|---|---|---|
| Control plane (CP) | `<list of services / responsibilities>` | `<no / yes>` | `<region or region list>` |
| Data plane (DP) | `<list of services / responsibilities>` | `<no / yes>` | `<region or region list>` |

**What crosses the boundary:**

| From → To | Crossing mechanism | Synchronous? | Tenant data allowed? |
|---|---|---|---|
| `<CP → DP / DP → CP>` | `<event / API / config push>` | `<yes / no>` | `<yes / no — with conditions>` |

**Portability invariants (MUST / MUST NOT):**

1. `<MUST statement about cloud / region portability for one plane>`
2. `<MUST NOT statement about hard-coded cloud / region literals in the other plane>`

---

## 6. Identity and access

**Authorisation hierarchy (top-to-bottom, each level is required by the next):**

```
<identity provider> → <environment access> → <isolation-unit assignment> → <role(s)> → <{features, data objects}>
```

| Layer | Source of truth | What it grants |
|---|---|---|
| `<identity>` | `<provider>` | `<authentication only>` |
| `<environment access>` | `<provider>` | `<which envs the identity may touch>` |
| `<isolation-unit assignment>` | `<authoritative registry>` | `<which tenants/workspaces the identity may operate against>` |
| `<role>` | `<authoritative registry>` | `<which capabilities apply within an isolation unit>` |

**Asymmetries (if any):**

| Identity class | Allowed environments | Notes |
|---|---|---|
| `<internal staff>` | `<dev, qa, stage, prod>` | `<…>` |
| `<external client>` | `<prod only>` | `<…>` |

**Rules:**

1. **MUST NOT** bypass any layer of the hierarchy ("admin override" is itself a role and MUST appear in the registry).
2. **MUST NOT** grant role permissions that exceed the isolation-unit assignment.
3. `<additional MUST / MUST NOT rules>`

---

## 7. Data residency / egress

| Aspect | Default posture |
|---|---|
| Egress | `<default-deny / default-allow>` |
| Cross-region tenant data movement | `<forbidden / allowed via platform-replication path / allowed with documented exception>` |
| External destination additions | `<self-service / manual exception process / forbidden>` |

**Rules:**

1. **MUST** keep tenant data within its assigned region (per the authoritative registry) unless the platform-provided replication path is used.
2. **MUST NOT** add an external destination via ad-hoc service code; use the documented exception process: `<process name or URL>`.
3. `<additional MUST / MUST NOT rules>`

---

## 8. Event plane

*(Delete this section if the platform does not provide a managed event plane.)*

| Aspect | Value |
|---|---|
| Wire standard | `<CloudEvents 1.0 / Avro / proto / custom>` |
| Producer boundary | `<single API / direct-to-bus / both>` |
| Topic naming convention | `<grammar>` |
| Topic naming regex | `<regex>` |
| Routing-header grammar | `<grammar — e.g., header name + value format>` |
| Channel semantics | `<at-least-once / exactly-once / at-most-once>` |
| Tenant-scoped vs region-wide topology | `<table or one-line statement>` |

**Producer / consumer rules:**

| # | Rule | Applies to |
|---|---|---|
| 1 | `<MUST / MUST NOT rule>` | `<producer / consumer / both>` |

---

## 9. Traceability

| Aspect | Value |
|---|---|
| Correlation-id carrier | `<W3C Trace Context / `X-Correlation-Id` header / in-body field>` |
| Per-hop rule | `<MUST forward verbatim / MUST regenerate / MUST chain via parent-id>` |
| Trace context required at | `<API ingress / event publish / log line / all of the above>` |

---

## 10. Discovery questions (Phase 1A)

These questions are pre-pended to the Phase 1A discovery question set when this supplement is loaded. Each question MUST be answerable from the authoritative source where possible, and only escalated to the user when the source cannot answer.

1. **`<First classification question — establishes the context that all subsequent questions branch on>`**
   - **Option A:** `<branch label — short description>`
   - **Option B:** `<branch label — short description>`
   - Disambiguation rule: `<one-line rule for choosing>`. If unsure, the design MUST resolve this with the platform owner before proceeding.

2. **`<Second question — gated by Q1>`**
   - **If Option A:** `<what to confirm / decide>`
   - **If Option B:** `<what to confirm / decide>`

3. `<Additional questions, each gated explicitly on Q1 if branch-specific>`

---

## 11. Rollout questions (Phase 1C)

These questions are pre-pended to the Phase 1C production-readiness checklist when this supplement is loaded. Each question assumes the §10 Q1 classification has been answered.

1. `<Rollout-order question across the §2 environment ladder>`
2. **Failure-domain analysis (gated by §10 Q1).**
   - **If Option A:** `<MUST / MUST NOT statement about cross-region or cross-cell synchronous dependencies>`
   - **If Option B:** `<MUST / MUST NOT statement adapted to that branch>`
3. `<Tenant-onboarding question, if applicable>`
4. `<Egress / data-residency question, if applicable>`
5. `<Authoritative-registry change-latency question, if applicable>`

---

## 12. Integration rules

These rules are evaluated by the Phase 3 Step 4b design quality gate when this supplement is loaded. Each rule MUST be a single, testable, MUST / MUST NOT statement.

| # | Rule | Failure signal | Fix |
|---|---|---|---|
| 1 | `<MUST / MUST NOT statement>` | `<what an unsound design looks like>` | `<what to change to make it sound>` |
| 2 | `<MUST / MUST NOT statement>` | `<what an unsound design looks like>` | `<what to change to make it sound>` |

---

## 13. Precedence

Where this supplement contradicts the cloud-provider supplement (`TERRAFORM-AWS-SUPPLEMENT.md` / `TERRAFORM-GCP-SUPPLEMENT.md` / `TERRAFORM-AZURE-SUPPLEMENT.md`), **this supplement wins.**

Where this supplement contradicts a framework supplement, **this supplement wins** for architectural / integration rules; the framework supplement wins for framework-specific patterns (DI, routing, persistence, test harness).

Where this supplement contradicts the base coding guide, **this supplement wins** for architectural / integration rules; the base guide wins for language-level coding conventions (style, type hints, doc format).
