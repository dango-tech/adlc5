---
name: adlc5-implement
description: ADLC5 Stage 4 Implement — TDD build, verify, integrate, QA, PR. Invoke via @adlc5-implement.
version: 4.1.0
---

# ADLC5 — Implement

**Stage 4** — deliver production-ready code through TDD and profile-routed verification, integration, QA, and PR substeps.

**Invoke:** `@adlc5-implement for [feature]`

## Persona handoff

| Step | Persona | Template |
|------|---------|----------|
| `implement-1-build` | Coder | [coder.md](../../templates/personas/coder.md) |
| `implement-2-verify` … `implement-5-pr` | Tester | [tester.md](../../templates/personas/tester.md) |

When `persona_mode.verifier_different_model: true`, spawn `@assure-verifier` on **reasoning** tier — do not inherit Coder model.

Record actual execution identities in a review JSON and submit it with
`adlc5 evidence review --feature "{feature}" --file review.json`. Standard/high-risk
require a fresh review session; different models are required only when policy selects them.
Example identity fields (alongside disposition and blocking findings):

```json
"implement": { "verification": { "independence": {
  "fresh_session": true,
  "coder_session_id": "...", "verifier_session_id": "...",
  "coder_model_id": "...", "verifier_model_id": "..."
} } }
```

`implement-2-verify` and `pr-ready` enforce the selected session/model separation policy. A human may explicitly approve a `clarity.history` `verifier_waiver`; agents must not self-approve it.

## Substeps

| Step | Skill / subagent | Gate |
|------|------------------|------|
| `implement-1-build` | `@adlc5-implement` → `@build-implementer` | `implement-1-build` |
| `implement-2-verify` | `@assure-verifier`, `@adlc5-assure-reworker` | `implement-2-verify` |
| `implement-3-integrate` | integration story / E2E | `implement-3-integrate` |
| `implement-4-qa` | `@qa` | `implement-4-qa` |
| `implement-5-pr` | `@pr-reviewer` | `implement-5-pr` |

Terminal: `./scripts/adlc5 gate --feature "{feature}" --gate pr-ready`

If implementation changes system architecture, dependency/trust boundaries, or
canonical commands, include the corresponding tracked `.agents/` update for human
review. Never regenerate or self-approve constitution changes from cache observations.

## TDD

Follow [adlc5-tdd](../../skills/adlc5-tdd/SKILL.md): red → green → refactor.

Before implementing against volatile versions, APIs, protocols, provider
capabilities, or security guidance, recheck the official primary sources cited
by Specify/Plan and follow [current-information.md](../../core/guides/current-information.md).

Generate context pack before each `@build-implementer`:

```bash
./scripts/adlc5 pack --feature "{feature}" --story-id "{id}" --persona coder
```

## Anti-hallucination

Stories reach `verified` only with verification report citing code-spec line refs. File-backed acceptance evidence must retain its locked SHA-256 through Verify and `pr-ready`; changed anchors are blockers. Command evidence locks the command definition in the acceptance manifest, not the command's runtime output; changing its text after locking is also a blocker.

## State

At Build, submit `evidence build --file build.json` with implemented `story_ids`.
Configure required commands in `evidence/checks.json`, then run `adlc5 evidence check`.
Submit the independent review via `evidence review`; use `transition TARGET` for
progression and `transition completed` at the terminal gate. Do not patch verification
or completion fields. Any relevant patch/acceptance/config change invalidates evidence.
See [evidence completion](../../docs/evidence-completion.md) for command examples.
Record a PR URL in `implement.pr.url` only when one actually exists.

## Human PR approval (policy)

When `policies.yaml` sets `autopilot.require_human_pr_approval: true`, `pr-ready` fails until a human approves. At `implement-5-pr`, AskQuestion for sign-off and submit it via `adlc5 evidence approve --file approval.json` after an explicit user response:

```json
{"type": "pr_approval", "approved_by": "user"}
```

Never write this entry without an explicit user response — autopilot halts here by design.

## Optional

- `@craftsmanship-code-review` before PR
- `@complexity-review` when scale NFRs apply
- Podman smoke via consumer `custom_gates.podman_smoke`

## Model recommendation

**Tier:** execution for `implement-1-build` (alias: implementation); reasoning for verify/QA/PR ladder.

```bash
./scripts/adlc5 resolve-model --tier execution [--platform <host>]
./scripts/adlc5 resolve-model --tier reasoning [--platform <host>]
```

Default `execution_policy: inherit` — omit `model` on `@build-implementer` / verify subagents. See [model-matrix.md](../../core/guides/model-matrix.md). Never use `fast` for implement/verify or `@qa`.
