# Deliver code with ADLC5

<img alt="ADLC5 — AI Development Lifecycle" src="assets/brand/logo-light.svg#only-light" width="480">
<img alt="ADLC5 — AI Development Lifecycle" src="assets/brand/logo-dark.svg#only-dark" width="480">

**Public preview.** Workflow contracts are tested; comparative coding-quality
results and outside-contributor qualification remain pending.

**Specify → Plan → Tasks → Implement.** ADLC5 is a coding harness that combines
agent judgment with one deterministic kernel for progression and checks.
It aims for repeatable acceptance and failure handling, not identical generated code.

Use it in your application repository. This repository distributes the framework
and a portable `dogfood/` consumer example.

## Five pillars, connected delivery

**Specify · Plan · Tasks · Implement · Intelligence.**

Four pillars structure delivery. Intelligence connects them to your codebase.
ADLC5 gathers repository knowledge, gives agents relevant context, and uses
current evidence to guide delivery. Models supply reasoning; the framework
supplies structured knowledge, context, and deterministic checks.

| Intelligence capability | Role in delivery |
| --- | --- |
| Repository maps | Locate relevant modules, symbols, import dependencies, and tests before planning. |
| Reviewed guidance | Carry architecture, boundaries, and commands across agent sessions. |
| Focused context packs | Equip each agent with its story, acceptance, and repository guidance. |
| Freshness and evidence | Refresh stale maps and require current checks and review before completion. |

The distinction is how these capabilities connect the lifecycle. Read
[Intelligence](intelligence.md) for a worked flow, commands, and honest limits.
SOUL supports this pillar as the reasoning discipline across the four stages.

## Start here

1. [Install ADLC5](installation.md) for your agent host.
2. [Initialize your workspace and feature](quickstart.md).
3. Invoke `@adlc5 for my-feature` and follow the [four-stage lifecycle](lifecycle.md).

## Proportionate depth

| Work | Delivery artifacts |
| --- | --- |
| Tiny | A single `change.md` with behavior, reuse, boundaries, acceptance, and risks |
| Standard | A brief `design/plan.md` and machine-checkable story specs |
| High risk | Detailed design, independent critique, QA, and human approval |

Knowledge-base and craftsmanship material are pulled in when a concrete problem
needs them. SOUL is a reasoning guard across the four stages, not an extra stage.

## Evidence before completion

Checks and reviews must apply to the current patch and acceptance inputs.
`pr-ready` establishes the required checks and review for the selected profile;
deployment and live host qualification need separate evidence.
Read the [completion limits](lifecycle.md#what-completion-establishes) before making release claims.

The [reference](reference.md) links to the canonical repository documentation,
kernel commands, and skill map. The site is a curated entry point; repository
documents remain authoritative.
