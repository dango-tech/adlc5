---
description: "ADLC5 is an AI coding delivery workflow for software teams: Specify, Plan, Tasks, and Implement, connected by repository intelligence and current evidence."
---

# ADLC5 developer guide

<img alt="ADLC5 — AI Development Lifecycle" src="assets/brand/logo-light.svg#only-light" width="480">
<img alt="ADLC5 — AI Development Lifecycle" src="assets/brand/logo-dark.svg#only-dark" width="480">

**Public preview.** Workflow contracts are tested; comparative coding-quality
results and outside-contributor qualification remain pending.

ADLC5 gives AI coding tools a repeatable delivery workflow: **Specify → Plan →
Tasks → Implement**, connected by a fifth pillar: **Intelligence**. Intelligence
gathers repository knowledge, assembles focused context, and grounds progression
in current evidence. Agent skills handle judgment; one deterministic kernel owns
progression and checks. It aims for repeatable acceptance and failure handling,
not identical generated code.

Read [why an AI coding tool needs a delivery workflow](https://medium.com/@abishek.y/your-ai-coding-tool-needs-a-delivery-workflow-9919b0b58bb4).

Use ADLC5 in your application repository. This repository distributes the
framework and a portable `dogfood/` consumer example.

## Five pillars, connected delivery

**Specify · Plan · Tasks · Implement · Intelligence.** The first four are delivery
stages; Intelligence connects them to your codebase. Models supply reasoning;
ADLC5 supplies structured knowledge, focused context, and deterministic checks.

| Intelligence capability | Role in delivery |
| --- | --- |
| Repository maps | Locate relevant modules, symbols, import dependencies, and tests before planning. |
| Reviewed guidance | Carry architecture, boundaries, and commands across agent sessions. |
| Focused context packs | Equip each agent with its story, acceptance, and repository guidance. |
| Freshness and evidence | Refresh stale maps and require current checks and review before completion. |

The distinction is how these capabilities connect the lifecycle. Read
[Intelligence](intelligence.md) for a worked flow, commands, and honest limits.
SOUL supports this pillar as the reasoning discipline across the four stages.

[Download host plugin packages](downloads.md) for Codex, Claude Code, Cursor,
and Hermes Agent. See [configuration](configuration.md) for shared storage and
worktree overrides.

## Choose your next step

| If you want to… | Start here |
| --- | --- |
| Install for your agent host | [Installation](installation.md) |
| Deliver your first feature | [Quickstart](quickstart.md) |
| See the stages in a complete example | [Walkthrough](walkthrough.md) |
| Diagnose a failed command or gate | [Troubleshooting](support.md) |
| Check releases and host support | [Releases](releases.md) |

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

The [reference](reference.md) links to canonical repository documentation,
kernel commands, skill map, and [GitHub Wiki overview](https://github.com/dango-tech/adlc5/wiki/ADLC5-Overview).
The [README](https://github.com/dango-tech/adlc5#readme) remains the install-oriented
project entry point; repository documents define the technical contracts.

## Get help and contribute

Use [GitHub Discussions](https://github.com/dango-tech/adlc5/discussions) for
questions and ideas, or [GitHub Issues](https://github.com/dango-tech/adlc5/issues)
for reproducible bugs. Read the [support guide](support.md) before filing.
