---
name: intake
description: Phase 1 — Intake for S2 Clean Architecture Review. Gather scope, requirements, and current module layout.
---

# Phase 1: Intake — Clean Architecture Review

## Purpose

Define architectural scope and collect inputs before mapping layers and tracing dependencies.

## Intake steps

### Step 1: Define scope

Identify boundary under review:

- New service or module name
- Package/folder paths
- PR diff (when reviewing drift)
- Feature requirements from Spec/PRT

### Step 2: Load requirements context

| Source | Extract |
|--------|---------|
| PRT / PRD | Use cases, actors, external systems |
| NFRs | Persistence, auth, messaging needs |
| S5 output | Claimed architectural patterns |
| Existing codebase | Current package layout |

### Step 3: Hypothesize layers

Draft initial layer map before reading code:

- Which use cases?
- Which external systems (ports)?
- Which frameworks (drivers)?

### Step 4: Identify entry points

List how the outside world reaches the system:

- HTTP routes, CLI, message consumers, scheduled jobs

These become adapter boundaries to verify.

### Step 5: Intake checklist

- [ ] Scope module(s) named
- [ ] Use cases listed
- [ ] External dependencies identified
- [ ] Review type: greenfield | brownfield | PR drift

Proceed to [02-analysis.md](02-analysis.md).
