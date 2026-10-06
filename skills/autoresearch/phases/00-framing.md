---
name: autoresearch-framing
description: Phase 0 — Campaign framing. Problem statement, ADLC5 spec handoff link, success criteria.
---

# Phase 0 — Campaign framing

## Purpose

Define the **campaign** scope before decomposing into tasks. One campaign = one optimization or experimentation theme with multiple independent mutable targets.

## Entry

- `state.json.mode` is `campaign`
- `phase_status.framing` is not `completed`

## Steps

### 1. Campaign name

Confirm kebab-case `campaign_name` matches `.autoresearch/{campaign}/`.

### 2. ADLC5 handoff (when present)

If invoked from `specify-4-handoff` or the user supplies a feature:

- Read `spec_handoff_path` (default `.adlc5/{feature}/spec-handoff.md`)
- Set `adlc5_feature` and `spec_handoff_path` in campaign `state.json`
- Pull problem summary and acceptance criteria into [framing.md](../templates/framing.md)

If no ADLC5 feature, interview via chat for problem statement and success criteria.

### 3. Framing interview (AskQuestion + chat)

**AskQuestion** — batch up to 2:

| `id` | Options |
|------|---------|
| `interaction_mode` | `hitl` / `autonomous` |
| `max_tasks` | `4` / `8` / `12` |

Chat: constraints (GPU, data paths, repos to avoid), guardrails, and what **not** to optimize.

### 4. Write framing.md

Fill [templates/framing.md](../templates/framing.md) at campaign root.

### 5. State update

```json
{
  "current_phase": "autoresearch-0b-decompose",
  "phase_status": { "framing": "completed", "decompose": "in_progress" }
}
```

## Exit

Route to [00b-decompose.md](00b-decompose.md).
