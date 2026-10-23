# Change-aware CI

`scripts/ci-plan.py` compares the PR base and head with a merge-base diff and emits
the selected suites plus a per-path explanation in the Actions job summary.
The selection covers the entire PR, including renames as additions/deletions.
Unknown paths, shared helpers, gates, installation and CI changes select full
validation. Unavailable diff information fails the plan; it never becomes a pass.

| Changed area | Selection |
|---|---|
| Documentation/site assets | Documentation build and always-on privacy |
| Pulse assets | Pulse contracts, DOM route unit test and package construction |
| Pulse readers/storage | Pulse, Linux/macOS path coverage, Windows regressions, packages and isolated installation |
| Requirements readiness and question/answer ingestion | Runner/readiness integration contracts and packages |
| Telemetry intake | Intake contracts |
| Shared/kernel/unknown paths | Full validation |

The Windows check stays present on every PR and runs Windows regressions when
platform validation is selected. `CI required` always runs and verifies every
selected dependency succeeded; required work being skipped or cancelled fails it.
Existing required Ubuntu/macOS checks remain present as lightweight validation
join points even when their platform suites are unselected. They reject missing,
failed or cancelled selected dependencies before running any selected platform
tests. This preserves the current protection rules without requiring an unsafe
ruleset migration before the new workflow is merged. Documentation-only changes
still start these small jobs, but do not rerun their contract suites. Do not add
workflow-level path filters to required workflows.

Superseded PR runs are cancelled. Main pushes, weekly scheduled runs and manual
CI dispatch use the full suite. Documentation builds run once through CI for PRs
and main; the standalone Documentation workflow is manual only. Release and
deployment triggers keep their existing contracts.

The installation smoke uses `--installation-only` on install and verification,
so it checks installed material and links without rerunning the entire suite
inside each installer. Normal install/verify defaults still run contracts.

This policy is tested as code. It is a conservative dependency map, not inferred
test coverage; new paths default to full until their dependency closure is known.
No runner-minute or monetary savings percentage is claimed without measurement.
