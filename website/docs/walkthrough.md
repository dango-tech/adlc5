---
description: "Follow an illustrative CSV export request through the ADLC5 lifecycle and review."
---

# Walk through a feature

This illustrative example shows the decisions and artifacts to look for; it is not a recorded run. Use ADLC5 in your application repository, not the framework distribution. Actual artifacts, host prompts and checks depend on your repository and selected profile.

## The request

A team asks for a CSV export. The agent needs to discover existing export code and tests, and the team needs to decide which roles may export. Start with [your host setup](installation.md), then [initialize a feature](quickstart.md). The lifecycle can be invoked in the application repository:

```text
@adlc5 for csv-export
```

## Specify

Capture the request and observable acceptance criteria. For example: an authorized user can export the requested records, an unauthorized user is denied, and existing export behavior remains intact. Record unknowns rather than inventing an authorization policy.

## Decision

If the role policy is unknown, the product owner supplies it before work depends on it. Record the decision and its rationale with the feature. If the policy was already known, identify its source. The roles here are intentionally unspecified: this example is not a recommendation for your access policy.

## Plan

Inspect repository guidance, the existing CSV writer, authorization boundaries, and the project's test command. Plan to reuse the writer where appropriate and enforce the agreed policy at the existing boundary. Capture any assumptions and risks for review.

## Tasks

Create bounded stories with acceptance criteria and declared tests. Include both an allowed-role case and a denied-role case. Code-spec-backed stories also declare their file boundaries and relevant signatures, so mechanical verification can check them.

## Implement

The agent changes the application and runs the declared tests. A denied-role test should demonstrate that an unauthorized request is rejected without producing an export. Inspect actual test output; the example does not assert that a test ran or passed.

## Review

Inspect the diff, decision, and test evidence together. A story check alone does not establish pull-request readiness. Run the applicable readiness gate from the application repository, using the installed kernel path for your host:

```bash
/path/to/adlc5/scripts/adlc5 gate --feature csv-export --gate pr-ready --workspace .
```

The gate covers the selected readiness profile. Remote CI, deployment, and live host qualification require separate evidence. See [completion limits](lifecycle.md#what-completion-establishes).

## Return to the work

Feature intent, decisions, stories, state and evidence are retained in the consumer repository for later sessions. [Pulse](pulse.md) projects recorded progress and a suggested next action on demand; its output is a snapshot, not continuous monitoring. [How ADLC5 works](architecture.md) shows the boundaries and durable artifacts.
