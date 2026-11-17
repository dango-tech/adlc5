# ADLC5 golden state implementation plan

**Status:** Proposed for review. Baseline is GitHub `main` at `e79b73a` (5.3.2).

## Outcome

An engineer can describe a feature, resolve material questions, review the repository context and plan, and follow delivery to a reviewable PR. If the run stops, the engineer can see the exact blocker, the next action, what evidence still applies, and what the run consumed. A fresh session resumes from that evidence.

Keep Specify → Plan → Tasks → Implement and the existing `tiny`, `standard`, and `high_risk` profiles. The existing kernel owns decisions, transitions, and evidence. Host adapters translate native capabilities. Pulse displays the same records that drive the runner. Use deterministic tooling for Git, indexing, validation, tests, and measurement. Route judgment by task and risk.

The next release should fix the observed waste before expanding the framework. In the observed consumer run, Codex attempted the opening Git isolation gate three times in 99 seconds. It recorded 580,296 tokens, including 439,296 cache reads, and never advanced. All attempts used `host default`, and the third escalated to the reasoning tier. The recorded failure was generic. The first regression should reproduce the repeated-failure behavior with a synthetic Git gate failure and an executor spy.

The [existing golden harness](golden-harness-implementation.md) already supplies intent readiness, scope and acceptance anchors, and evidence freshness. Its [qualification protocol](golden-harness-qualification.md) remains the reference for the broader comparative campaign. This plan extends that work through execution, operations, and release qualification.

## Delivery sequence

Each row is a reviewable increment. File paths are relative to the distribution root. Exercise delivery flows in disposable consumer repos or `dogfood/`.

| Increment | Scope | Acceptance |
| --- | --- | --- |
| **0. Freeze the baseline** | Extend the existing evaluator and test fixtures. Pin source, cases, oracles, budgets, hosts, and models. | Reproduce retry waste locally and verify the test detects attempted worker launches. Freeze comparable external quality evidence before changing the runner. |
| **1. Deterministic bootstrap** | Extract shared bootstrap diagnostics from existing Git, state, and gate behavior. Route runner and in-agent entry points through the same result. | Valid bootstrap uses zero model calls. A blocked workspace produces one actionable diagnostic and zero worker launches. |
| **2. Bounded execution and resume** | Use the existing runner journal, worker envelopes, questions, and model configuration. Add typed stops, task-sized briefs, and enforceable launch limits. | Repeated unchanged blockers cannot escalate. Interruptions preserve accepted work. A fresh process continues from the recorded next action. |
| **3. Engineering evidence and brownfield context** | Improve the constitution and index workflow, scoped planning, and profile-specific tests/evidence. | Existing repositories retain their commands and standards. A bounded feature can use targeted context and produce traceable acceptance and CI evidence. |
| **4. Guided Pulse** | Project decisions, blockers, attempts, and evidence from the existing kernel records. Ship deep links and host-native action handoffs. | One feature page explains the ask, why work stopped, what it consumed, and how to resume. Counts reconcile across all drill-down levels. |
| **5. Host qualification** | Exercise install, first delivery, interruption, resume, and uninstall on native app and CLI surfaces. | Every claimed surface has a versioned signed-in qualification receipt and a documented capability level. |
| **6. Release qualification** | Run the frozen comparison, check upgrade/rollback, verify signed-off artifacts, and publish scoped results. | The release satisfies the gates below. Claims match measured data, supported surfaces, and published package provenance. |

Increments 1 and 2 form the first release candidate. Increment 3 can begin after the bootstrap contract stabilizes. Pulse can implement read-only projections against synthetic records once the result schema is agreed. Live end-to-end qualification follows integrated runner and Pulse checks.

## 0. Baseline and fixtures

- Extend `scripts/tests/test-runner-core.py`, `scripts/tests/test-runner-hosts.py`, and the existing evaluation harness. Include an unchanged Git-gate failure, a valid Git setup, a workspace outside the allowed roots, a stale condition repaired without restarting the feature, and mixed worker failures.
- Freeze a tiny change, a representative standard brownfield feature, a greenfield consumer, and a high-risk feature with a real approval and an interruption. Keep the existing six-case and extended case banks intact. Add or pin representative Git revisions where those banks need real-repository coverage.
- Record start/end events, worker launches, observed usage, reruns, user interventions, and external acceptance for the baseline. Distinguish replayed deterministic fixtures from signed-in delivery. Preserve failed runs and missing telemetry.

## 1. Deterministic bootstrap and actionable blockers

- Reuse feature initialization, gate checks, and workspace binding in `scripts/init-feature.sh`, `scripts/runner/run.py`, and the kernel. Use one canonical absolute workspace, branch, starting commit, and feature identity. Validate relevant write boundaries and actual Git metadata placement, declared commands, and available host capabilities. Use safe scoped checks for filesystem permissions and paths.
- Return a machine-readable outcome with the attempted step, failed condition, offending path or command identifier, evidence, and safe next action. Persist a sanitized record so CLI, MCP, and Pulse can refer to the same blocker. Surface workspace permission and product decisions through their existing distinct paths.
- Run Git isolation as kernel work. Verify an already-correct worktree and advance through the normal gate. For a conflicting or unwritable checkout, preserve existing work and give the engineer a specific way to rebind or regain access.

**Required tests:** no worker launch for valid bootstrap or a deterministic bootstrap blocker. Cover current and existing feature branches, linked worktrees, stale bindings, symlink/sandbox boundaries, unavailable Git metadata, dirty state, and branch contention. Rerunning after a repair advances once without duplicating state.

## 2. Cost control, recovery, and host adapters

### Execution and context

- Use `scripts/runner/run.py`, `hosts.py`, and the existing pack generator. Bind one worker to one stage step or story. Build one shared evidence section and a bounded story-specific section. Select the current phase guidance. Preserve acceptance criteria, constraints, and applicable failure behavior when trimming optional detail.
- Measure the complete assembled brief before launch. Enforce its configured cap. If required material exceeds the cap, split the work or return a structured blocker. Record estimated brief size and actual observed usage separately. Benchmark cold and warm context paths.
- Extend the existing policy configuration with per-step and per-feature limits for time, attempts, and observed usage. Reserve budget before a worker launch and reconcile after exit. Document that feature-level accounting can lag. Enforce provider-side token or dollar limits where the host supports them. With delayed or absent accounting, use a conservative launch bound and a worker timeout. Require a capable adapter and pricing/accounting path for any policy that promises a hard dollar cap.
- Validate routing before launch. A strict cost policy requires a supported model resolved for each applicable tier. Record requested tier/model and observed model separately. Route ordinary edits and test authoring to a configured execution model. Run existing test, lint, build, and coverage commands directly. Route ambiguity, architecture, high-risk review, and novel diagnosis to the approved reasoning tier.

### Retry and recovery

- Classify outcomes as passed, missing input, missing permission, quota or transient host failure, test/review failure, invalid output, and recovery required. Retry a confirmed transient failure only within policy. Repeated failures with the same blocker fingerprint require changed input or a recorded decision. Model escalation requires a specific reasoning gap and remaining budget. Quota pauses preserve the known retry time when supplied by the host.
- Reuse the journal and workspace lock. Make result ingestion, evidence, and usage replay safe after a restart. Bind receipts to the actual commit or diff, intent, policy, and applicable commands. Store the next action before exit. Reuse prior decisions and verified artifacts when their dependencies still match.
- Preserve user, concurrent, and unclassified edits during recovery. Constrain cleanup to recorded attempt-owned changes in the correct worktree. When ownership is uncertain, preserve the working tree and surface a recovery blocker. Keep existing state and archived usage readable with additive fields and explicit unknown values.

**Required tests:** no retry on an unchanged mechanical blocker. Fault-inject exits after launch, result validation, evidence ingestion, usage recording, and before transition. Resume twice to check idempotence. Confirm a changed requirement invalidates affected evidence and prompts for the new decision once. Cover quota, timeout, stale lock, budget exhaustion, interrupted writes, and preservation of concurrent edits. Check host fallback and partial-accounting behavior.

## 3. Engineering standards and repository onboarding

- Guide greenfield teams through intended architecture, ownership, boundaries, commands, and initial test/CI setup. For brownfield, discover existing repo guidance and use its current architecture and commands. Offer ADLC5 defaults where the repository lacks a standard. Write generated suggestions as drafts for review in Git.
- Extend `repo-spec` and `repo-index` only where the fixture identifies a gap. Plan from the tracked constitution and a fresh map of affected modules and tests. Measure full refresh, targeted retrieval, and re-indexing at a fixed brownfield revision. Add incremental indexing only if baseline refresh cost justifies it. Keep any future OpenViking mirror optional and derived from the same reviewed sources.
- Map intent to stories, acceptance anchors, files and canonical checks before build. Require applicable compatibility, state migration, idempotence, recovery, and performance evidence. Use design patterns where the change has a concrete design problem. Review the diff for boundaries, duplication, complexity, and reuse. Scope check requirements to the repo and risk profile.
- Reuse evidence commands and the existing PR-ready gate. Record applicable unit, integration, and end-to-end checks plus configured coverage thresholds. Track local checks, remote CI, review approval, deploy clearance, and production observation as distinct milestones.

**Required tests:** run greenfield and brownfield fixtures. Preserve existing constitution files and canonical commands. Demonstrate the compact tiny path, a standard multistory change, and a high-risk flow with independent review and genuine approval. Reject stale evidence, missing applicable checks, and invalid acceptance mappings. Validate any index change against fresh full-build output.

## 4. Pulse as the engineer's working view

- Extend the existing Pulse projection and schema. On the workflow page, show the feature ask, readiness and unresolved decisions, repo mode and applicable standards, plan/story progress, current blocker, and links to evidence. Place the actionable blocker or decision ahead of the full lifecycle detail.
- Provide **Review decision**, **Review evidence**, and **Resume** handoffs through the host or exact kernel command. Start with the existing read-only board and MCP snapshot. A host integration that submits a decision must use the existing `answer` path and preserve intent, approval scope, and stale-decision validation.
- Attribute attempt data using existing run, node, session, story, and attempt identities. Display requested and observed models, fresh and cached token buckets, known cost and accounting source, elapsed and wait time, test coverage from its report, and retry/failure reason. Show unavailable measurements and the attributable subtotal. Deduplicate hook and runner observations where they share stable identity. Never sum independently overlapping time as elapsed or average coverage percentages with unequal denominators.
- Roll up feature → stage → story/step → attempt, and feature → repository. Show delivery outcome rate with a denominator and observation window. Show attempts separately to expose rework. Include failed and interrupted spend. Make archives and worktrees navigable via stable links.

**Required tests:** fixture with one feature across two hosts, a failed attempt, an interruption, a duplicate event, and partial usage. Verify totals and time math, cache freshness, archive fidelity, safe rendering, permission boundaries, and direct links. Exercise the engineer's identify-blocker → resolve → resume flow in a live app during qualification.

## 5. Qualify each host and surface

Use [the existing host matrix](host-qualification-cycles.md). For each supported combination record the artifact digest, host/version, OS, entry point, permission mode, requested and observed models, accounting capability, and evidence links. Use a repo-scoped opt-out and verify the project can still use its native agent workflow.

| Host | CLI qualification | App or IDE qualification |
| --- | --- | --- |
| Codex | Structured worker results, workspace permissions, model resolution, process restart and usage records | Clean local plugin install, MCP in the correct workspace, start a feature, handle a decision, open Pulse and resume |
| Claude Code | Headless output, declared command permission, denial recovery, intended routing and transcript usage | Clean Code-tab install, Pulse card and navigation, start/resolve/resume and usable evidence links |
| Cursor | Headless output, sandbox decision, scoped write and fresh-session resume | Clean IDE install and trust prompts, skills/MCP and Pulse handoff, with usage checked under the advertised account capability |
| Hermes | Attended delivery and restart through the CLI. Qualify unattended independently within its container boundary before advertising it | Verify the attached profile/backend, shared state and Pulse handoff, then start/resolve/resume from Desktop |

On each supported CLI mode, deliver a small full Specify → PR-ready change, recover an interruption, and reject stale evidence after changed intent. On each supported app, verify the full engineer interaction starting at clean installation. Record remote CI and actual PR creation separately when tested. Capture failure results and surface restrictions. A package smoke test is install evidence only. Marketplace approvals, additional OSs, cloud modes, and unattended modes require their own matrix rows.

## 6. Release and benchmark gates

1. **Correctness and continuity.** Zero bypasses of approval, acceptance anchors, workspace ownership, or current-evidence checks in the release suite. Zero duplicate progression or lost approved answers in restart tests. Pass the existing required local and remote CI checks, plus profile-specific acceptance and host qualification.
2. **Practical adoption.** On each claimed app surface, an engineer can find the feature ask, current blocker, and next action, then resume from the correct workspace. Include at least one engineer who did not build the harness in onboarding and recovery trials. Record task completion, intervention, and where discovery failed.
3. **Measured overhead and economics.** Start on Codex and Claude with matched direct-agent, frozen 5.3.2, candidate same-model, and candidate tiered arms. Keep host permissions, starting revisions, external quality oracles, review rubric, user availability, and budgets fixed. Preregister repetitions and accounting sources. Run the corrected repeatable protocol on Cursor and Hermes to support claims about those hosts. Reserve the broader Spec Kit campaign for a scoped comparison, using the existing extended protocol.
4. **Comparison rules.** Report external quality and release readiness separately. Report accepted features divided by started runs, time to PR-ready with unfinished runs visible, human interventions, and total campaign spend divided by accepted features when cost coverage and billing basis permit. Show failed and quota-paused runs and paid API cost versus subscription usage separately. Compare matched cases and report uncertainty. Publish a savings claim only for the measured cohort that meets the existing quality and accounting requirements.
5. **Artifact and recovery verification.** Rebuild the four packages from the release commit, verify manifests and digests, and install the actual candidate artifacts on claimed surfaces. Prove upgrade from 5.3.2 on an active feature and read compatibility for archives. Document a tested rollback or forward-recovery path for any record migration. Keep install, package publication, and deployment receipts distinct.

The proposed targets are zero model calls in deterministic bootstrap, zero repeated attempts on unchanged mechanical blockers, and zero lost accepted decisions in the interruption suite. Before each matched campaign, choose the primary efficiency metric based on the accounting available. Target a **20% reduction versus the frozen baseline** in either median active time to an accepted feature or total comparable spend per accepted feature. Include failed-run spend in the latter. Require no observed critical quality regression and no regression in accepted-feature rate on the tested workloads. Report both efficiency measures where observable, along with the failed-run burden. Require enough observations to support any public claim.

The first PR should add the replay fixture and make the bootstrap gate deterministically solvable or actionable. Its demo should show a valid worktree advancing without a model call, a blocked worktree yielding one diagnostic, and a repaired workspace resuming in the same feature. Promote a release to golden for the tested enterprise delivery scope only when evidence for all required gates is attached to that release.
