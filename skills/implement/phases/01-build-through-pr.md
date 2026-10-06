# Implement — Build through PR

## Build

Tiny work uses the bounded `change.md` and spec handoff; avoid an artificial
spec tree. Other profiles use planned stories and generated context packs.
Inspect the existing flow/callers, implement the bounded change, then submit
actual build results with `adlc5 evidence build --file build.json`.

Configure consumer acceptance/regression and required quality commands in
`evidence/checks.json`. Run `adlc5 evidence check`; selected required runners
must exist and enforce the chosen policy. Use `transition implement-2-verify`
after the build gate passes.

## Verify and integrate

Have the reviewer inspect the current diff against acceptance, using mechanical
boundary/test/signature checks to narrow the work. Submit actual identities,
disposition and blocking findings via `evidence review`. Rework blockers and
rerun current evidence. Standard/high-risk need a fresh reviewer session.

When integration is enabled, declare a required named `integration` command
and test cross-story wiring/E2E. The kernel certifies results; never set
`implement.integration.status` manually.

## QA and PR readiness

High-risk needs a required named `security` command that tests the applicable
trust/data boundary or runs the appropriate scanner, plus the QA clearance
artifact and explicit human approval. A `CLEARED` marker alone is insufficient.

Advance through enabled steps with `adlc5 transition TARGET`. At
`implement-5-pr`, `transition completed` requires fresh passing evidence and
selected approvals. Opening a PR is separate: use `@pr-reviewer` when authorized
and record its actual URL/publication metadata; never invent a PR to earn readiness.

Compact memory after completion. See [completion commands](../../../docs/evidence-completion.md).
