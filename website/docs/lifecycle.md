# Lifecycle

ADLC5 follows **Specify → Plan → Tasks → Implement**. Skills exercise judgment;
the `scripts/adlc5` kernel owns state, transitions, checks, and evidence.

| Stage | Invoke | Expected output | Completion gate |
| --- | --- | --- | --- |
| Specify | `@adlc5-specify` | Behavior, constraints, acceptance, explicit risk assessment | `specify-complete` |
| Plan | `@adlc5-plan` | Reuse, intended change, boundaries, and decisions | `plan-complete` |
| Tasks | `@adlc5-tasks` | Bounded stories and checkable specs | `tasks-complete` |
| Implement | `@adlc5-implement` | Patch, checks, independent review, current evidence | `pr-ready` |

The five pillars are **Specify · Plan · Tasks · Implement · Intelligence**.
[Intelligence](intelligence.md) grounds the four stages in repository knowledge,
reviewed guidance, focused context, and current evidence.

Use `@adlc5 for my-feature` to orchestrate the whole flow. SOUL keeps cross-cutting
reasoning guards in view while deterministic gates remain the enforcement.

## Lock acceptance before building

Assess risk explicitly. Authentication, money, secrets, migration, concurrency,
destructive changes, public compatibility, disputed requirements, or uncertain
risk require the high-risk profile and its mandatory human PR approval.

Initialize consumer-owned acceptance, then lock its definitions:

```bash
/path/to/adlc5/scripts/adlc5 anchors lock --feature my-feature --workspace .
/path/to/adlc5/scripts/adlc5 pilot --feature my-feature --workspace .
```

Use `adlc5 transition` with the next enabled step reported by `pilot`. The kernel
rejects jumps and requires the relevant gates. Generic `state set` is for metadata,
not completion. Standard work needs machine-checkable story specs; tiny work keeps
its decisions in `change.md`.

## Build, check, and review

At `implement-1-build`, record implemented story IDs with `evidence build`.
Declare real consumer commands in `.adlc5/my-feature/evidence/checks.json` and run
them through `evidence check`. Profiles retaining integration require a named
integration command. Selected quality thresholds require checks that enforce them.

```bash
/path/to/adlc5/scripts/adlc5 evidence check --feature my-feature --workspace .
/path/to/adlc5/scripts/adlc5 gate --feature my-feature --gate pr-ready --workspace .
```

Reviewers inspect the actual patch against acceptance and record their actual
session identities. Standard and high-risk profiles require distinct coder and
reviewer sessions; distinct models are required when policy requests them.
Relevant edits make prior checks, reviews, or approvals stale.

See [evidence-backed completion](https://github.com/dango-tech/adlc5/blob/main/docs/evidence-completion.md)
for JSON formats, review and approval commands, recovery, and exact completion steps.

## What completion establishes

`pr-ready` means the selected profile's required checks and review passed for
current inputs. It does not establish deployment, public availability, legal
clearance, or defect-free production operation. Live delivery/resume qualification
must be recorded per host before broader claims.

Local records are writable. Enforcement is procedural, not authentication against
a malicious local actor. Acceptance anchor refs are local and are not transferred
by ordinary clone, fetch, or push. Use an external approval system when repository
writers are adversarial.

Deployment needs separate clearance and actual authorization. Successful local
tests alone do not publish a site or prove production behavior.
