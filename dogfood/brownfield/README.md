# Paired brownfield diagnostic

This opt-in fixture exercises one existing consumer with a frozen three-story
feature on Codex and Claude. Run the deterministic framework checks first.
This diagnostic does not modify or use the published comparative case banks.

## Prepare equivalent sessions

From a frozen framework checkout, materialize the fixture into a new,
operator-controlled directory.

```sh
python3 dogfood/brownfield/prepare.py /tmp/adlc5-paired-inventory
diff -r /tmp/adlc5-paired-inventory/codex /tmp/adlc5-paired-inventory/claude
```

Keep the operator files outside the writable worker repositories. Sibling paths
alone do not enforce secrecy. Provision each worker with access only to its own
checkout and the frozen framework installation. Package the framework with
`scripts/package-plugin.py`, which explicitly excludes `dogfood/` from the
Codex and Claude payloads. Do not mount the framework source checkout in either
worker environment. The operator should run the
oracle in a separate environment and give the worker only the exact contents of
`operator/TASK.md`. Record its digest along with the installed framework
revision, host versions, model identities, routing, caps and timestamps for
both sessions. Keep the input, release candidate, decision script, and
checkpoint condition fixed for both.

Assign an operator and independent reviewer before starting each host. Pin a
hard deadline at exactly 60 elapsed minutes after the initial task is submitted.
Record the start and concrete UTC deadline before any later action. The clock
includes stakeholder response, interruption, restart, CI, review and rework.
Run with the same limit for each host. At the deadline, record the last verified
milestone and classify remaining work as timed out. Evidence that arrives later
can be retained with its timestamp.

Before live work, verify each seed digest against `operator/fixture.json`.
Initialize the authorized disposable Git repository from one exact seed and
check out its initial commit into both independent workspaces. Record that
same initial Git SHA for each. Run from each consumer root and save the actual
exit status and log for both commands.

```sh
python3 -m unittest regression
python3 -m unittest regression reservation_check
```

Expect the regression command to pass and the required check to fail because
`reserve_stock` is absent. Do not advance either session with a mismatched
seed or a different failure. Configure `inventory-contract` as a required
check on the authorized disposable GitHub repository before using PR readiness
as remote evidence. The push workflow checks out and verifies the triggering commit and
associates the required check with that commit. Confirm the recorded check run
is tied to the actual PR head SHA.

## Operate the paired run

1. Open independent fresh Codex and Claude sessions. Provide the same task
   and invoke the installed ADLC5 workflow. Give each host the same authority
   over its checkout and record the selected route and rationale. Public
   compatibility is classified as high-risk in the evaluation contract.
2. Use `operator/stakeholder.md` for the consequential decision. Record when
   it was asked and answered, whether implementation had started, and which
   questions the repo already answered. Permit normal host tooling. Record
   retries, corrected decisions, guidance and interventions as they occur.
3. Interrupt after the Tasks handoff is recorded and before the first
   implementation edit. Record the elapsed time, Git status, feature state
   and last completed stage. Close the original conversation. Start a new
   conversation using the same consumer checkout and the task text, with
   only the feature name and instruction to resume. Let the new session
   discover and use the feature artifacts and kernel state. Record the
   first action and whether it resumed at the intended point without replay
   or operator remediation. If a host bypasses the checkpoint, record the miss.
4. Before delivery, verify frozen anchors using the manifest and run the
   regression and required check again. Exercise the real ADLC5 `pr-ready`
   and anchor gates. Keep command output and capture any QA or human
   approvals genuinely required by the selected route. The operator runs
   the private oracle against the exact proposed head in a disposable copy.

   ```sh
   python3 /tmp/adlc5-paired-inventory/operator/oracle.py /path/to/exact-head-checkout
   ```

   The oracle exercises shortage and input rejection, byte-for-byte preview,
   quantity updates, order and field preservation, and an injected filesystem
   publication failure. Its expected outcomes come from the task and the
   private decision. A failure in the injection itself requires operator
   triage before attribution.
5. With remote work authorized, open separate PRs from the same frozen base.
   Record PR URL, base SHA, latest head SHA, exact-head required workflow
   output, and real independent review that explicitly identifies its reviewed
   SHA. Reviewer identity must differ from the coding session. If a push
   changes head, refresh anchors, oracle, required CI, and independent review
   before recording final disposition. Do not merge as part of this diagnostic
   without separate authorization.

Record one outcome per host. Keep actual check results, initial and final SHAs,
resumption observations, anchor integrity, interventions, independent review,
and all known blocking findings. Preserve the following timing and ownership
fields.

| Field | Evidence |
|---|---|
| `operator_id`, `coding_session_ids`, `reviewer_id` | Human/operator ownership and distinct initial, resumed, and independent review identities |
| `started_at_utc`, `deadline_at_utc`, `last_verified_at_utc`, `ended_at_utc` | UTC timestamps for task submission, cutoff, last milestone, and terminal disposition |
| `elapsed_seconds`, `stakeholder_wait_seconds`, `interruption_seconds`, `ci_wait_seconds`, `review_wait_seconds` | Total wall time and measured milestone waits, which can overlap |
| `pending_owner` | Person or system responsible for the next blocked or incomplete milestone, if any |

Capture host-sourced usage and cost where available and retain unknown values
for unobserved data. Classify
missing remote authorization or unavailable host execution as blocked and show
which evidence exists. One paired delivery is a diagnostic, and does not
estimate a comparative quality or cost advantage.
