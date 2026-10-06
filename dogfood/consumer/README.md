# Portable consumer

This standard-library inventory module is an intentionally incomplete starting
point for six frozen delivery tasks. Existing behavior tests pass; each independent
acceptance test fails until its task is delivered. It is not a reference solution.

```bash
cd dogfood/consumer
python3 regression.py
```

Prepare a disposable run from the framework root:

```bash
python3 scripts/evaluation/run-case.py prepare --case tiny-label \
  --arm candidate --host codex --model YOUR_ACTUAL_MODEL \
  --directory /tmp/adlc5-tiny-label-candidate-1
```

Read the resulting `HANDOFF.md` in a fresh host session. It supplies the task,
frozen check commands, budget, framework location, and recording requirements.
Change only the disposable consumer. Keep acceptance/regression scripts outside
that repo unchanged. `--arm baseline` materializes the pre-change framework from
the revision in `templates/evaluation/cases.json`; `--arm direct` supplies equivalent checks without an ADLC5 lifecycle.
Candidate points to the current working framework and records its dirty status.
Use a fixed candidate checkout for actual comparisons; do not change framework
files halfway through a run.

Record observed review, rework, interventions, telemetry and usage in
`observations.json`, preserving actual run/node identities and accounting sources.
Collect after delivery:

```bash
python3 scripts/evaluation/run-case.py collect \
  --directory /tmp/adlc5-tiny-label-candidate-1
```

The collector runs the frozen tests, hashes logs, checks frozen test integrity,
and uses `evaluate-runs.py`. Failed commands cannot earn success. Missing
accounting and unobserved escaped defects remain unknown; they are not free runs
or zero defects. Collection overwrites its outcome snapshot instead of appending
a duplicate outcome. Logs and private observations stay in the disposable run.
Wall time includes time waiting for humans; token accounting must come from the
host, provider, or explicitly labeled estimates.

To test resume, interrupt after a stage finishes, close the host conversation,
and start a new session with `HANDOFF.md`, feature files and the kernel's
`state get`/`pilot` output. Continue through `transition` and evidence operations
in candidate ADLC5, rather than patching completion fields. A new conversation
is essential to test recovery without chat history.

High-risk cases exercise path containment and atomic data replacement. Genuine
human approval remains necessary; the runner never writes approval evidence.
The path case explicitly excludes adversarial concurrent symlink replacement;
the write case promises atomic replacement, not power-loss durability.

The automated pilot test validates preparation, all six failing initial acceptance
checks, passing regressions, frozen anchors and unknown accounting. It does not
measure host-agent delivery quality or satisfy live resume/human review acceptance.

A scripted kernel contract demo needs no subscription:

```bash
python3 scripts/evaluation/demo-consumer.py --directory /tmp/adlc5-contract-demo
```

It initializes a real consumer feature, rejects a completion jump, observes failing
acceptance, applies the one-line label change, reruns evidence checks, advances a
real transition and reads restored state in a separate process. It proves checks
alone cannot satisfy PR readiness. It never fabricates review or human approval.
This process-resume check is not a substitute for fresh host-session resume.

Framework-arm collection runs the selected framework's real `gate --gate pr-ready`
and `anchors check`; observations cannot assert those results. Direct runs need
`independent-review.json` with actual differing `coder_session_id` and
`verifier_session_id`, `disposition: "pass"`, and `blocking_findings: []`. This
review file is a local attestation, not authenticated reviewer identity. The
manifest task/config hash and framework content fingerprint must remain unchanged.
