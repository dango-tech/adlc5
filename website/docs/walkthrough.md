---
description: "Follow one small example through ADLC5 requirements, planning, bounded tasks, implementation, and verification."
---

# First feature walkthrough

This walkthrough shows how a small change moves through the ADLC5 stages. The
commands and artifacts are illustrative; run them in your own application
repository and follow the evidence produced there.

## Example request

Suppose a command-line tool has a `label` command that trims whitespace but does
not reject a label containing only spaces. The desired behavior is to reject it
with a clear error and preserve valid labels.

Write the observable behavior, constraints, and acceptance evidence in plain
language. For example: “A blank label is rejected before it is saved; valid
labels keep their existing behavior; tests cover both cases.”

## Specify

In the application repository, initialize a feature and invoke the lifecycle:

```bash
/path/to/adlc5/scripts/init-feature.sh --feature reject-blank-label --interaction hitl
```

```text
@adlc5 for reject-blank-label
```

Review the requirement and acceptance criteria. Confirm the behavior for edge
cases such as leading/trailing whitespace and existing stored values before
implementation begins.

## Plan

The agent checks repository guidance and existing validation paths, then records
the smallest safe design. For this example, that may be a validation at the
existing command boundary plus focused tests. If the current behavior has data
migration implications, stop and resolve those in the plan.

## Tasks

Break the change into bounded work, such as:

1. Add a failing test for blank input and retain a passing test for a valid label.
2. Add the validation at the current input boundary.
3. Run the declared tests and inspect the final diff.

For code-spec-backed work, the story lists allowed files, tests, signatures when
needed, and acceptance criteria in its required frontmatter.

## Implement and verify

The implementation stage builds the change, runs the declared checks, and
records evidence. Mechanical verification can confirm file boundaries, test
presence/results, lint, debug-noise scans, and declared signatures. A passing
story check alone does not establish pull-request readiness.

Before calling the work ready, inspect the current patch and run the applicable
readiness gate from the application repository:

```bash
/path/to/adlc5/scripts/adlc5 gate --feature reject-blank-label --gate pr-ready --workspace .
```

`pr-ready` covers the selected readiness profile. Deployment and live host
qualification require separate evidence; see [completion limits](lifecycle.md#what-completion-establishes).
