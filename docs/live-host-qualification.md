# Live host qualification — 2026-10-20

Actual signed-in host processes ran against disposable consumers using this
candidate's `run_worker`, question/answer ingestion, resume recovery and readiness
validator. This is bounded feasibility evidence, not the comparative campaign
or a full enterprise lifecycle certification. No consumer production repo,
installed plugin, deployment or external account configuration was changed.

| Native host | Version | Question → fresh-process implementation | Independent review → changed intent → safe stop |
|---|---|---|---|
| Codex | CLI 0.162.1 | Passed | Passed |
| Claude Code | 2.1.299 | Passed | Passed after bounded fixture repair |
| Cursor Agent | 2026.10.01-e373342 | Passed | Passed |
| Hermes | 0.22.0, local e06df9c2eae6 | Passed in attended terminal mode | Not executed |

The first scenario asked who could export tenant records, recorded the scripted
stakeholder's admin-only answer through the canonical answer command, archived
the consumed question and launched a fresh host process. External checks verified
denied roles, tenant isolation and input preservation. Product answers added no
commands to an allowlist. No host repeated the resolved role question in the
tested handoff. These assertions describe this fixture, not a population rate.

For the second scenario, a different actual host session reviewed current intent
and implementation. The evaluator recorded the reviewed readiness artifact and
verified it passed. The requirement then changed to allow members a still-undefined
redacted field subset. The kernel rejected the old review, excluded old answers,
archived stale pending input and accepted a newly revision-bound field-policy
question. Each tested host stopped without changing implementation while that
decision remained unresolved. A correct safe stop is not completed changed-feature
delivery. The evaluator supplied actual source contents to read-only review
sessions; tests remained outside the consumer and were not delegated to the coder.

## Failures discovered and addressed

- Codex rejected `--sandbox workspace-write` combined with `--approve-for-me`.
  The adapter now uses the latter, which selects workspace-write with automatic
  approval review. No sandbox-bypass flag was added.
- Codex's strict provider schema rejected the prior open-ended worker result.
  The shared strict envelope now carries encoded step payloads; invalid payloads
  and envelope overrides fail before ingestion. Older result files stay readable.
- Claude correctly denied unapproved shell commands. A kernel-computed current
  intent digest now accompanies the brief, avoiding a needless shell permission
  just to prepare a product question. Actual command denials still surface as
  separate permission requests. No broad shell allowlist was introduced.
- Cursor's JSON transport concatenated commentary and a fenced final JSON object.
  The adapter accepts one final fenced result and rejects ambiguous/trailing
  results, then validates identity and the payload normally.
- The first read-only review driver used ambiguous file references and prohibited
  Codex's available file-reading mechanism. Those probes stopped without claiming
  review success. The driver was corrected to supply exact source contents, as a
  kernel context pack would. These were qualification-driver failures.
- Claude's independent review found that a null tenant could match untenanted
  records in the disposable implementation. The scripted scope was clarified,
  a fresh coding process repaired it, and external invalid-tenant checks passed
  before independent review passed. This exposed a gap in the initial fixture's
  acceptance coverage; it is not hidden as a first-pass success. The original six
  comparative cases and their frozen acceptance script remain unchanged.

## Evidence and limits

Private local artifacts retain native outputs, attempt/schema/result files,
driver scripts, external assertions and a source manifest. Initial failures and
retries remain in native logs. Review coverage headings were normalized by the
evaluator from explicit reviewer assessments; no passing review was invented.
This exploratory qualification evolved during fixes; it is not a frozen matched
experiment and cannot support relative cost or reliability claims.

Codex and Cursor did not expose model IDs through the normalized result fields;
those remain unknown. Claude reported `claude-sonnet-5-5`. Hermes's attended UI
showed `gpt-6-luna` and distinct native session IDs, but its runner result contains
an attempt-ID fallback and no provider usage. Native UI observations are separate
from normalized telemetry; no missing usage is counted as zero cost.

Hermes was exercised only through supported attended mode. Its unattended
container guard remains intact, and changed-intent review is unqualified there.
These runs did not certify OS-level containment, plugin UI/trust/hook dispatch,
every approval path, full Specify-to-PR delivery, different technology stacks or
production behavior. Existing contract tests cover additional mechanical paths.

The full contract suite and all three host package checks passed after the
adapter fixes. The 144-run comparative campaign remains unexecuted by instruction.
