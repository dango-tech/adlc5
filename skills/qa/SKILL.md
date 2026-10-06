---
name: qa
description: QA - Security Scanning, Quality Gate & Deployment Clearance - Runs SAST, dependency audits, IaC scanning, test coverage, code quality, and optional performance/accessibility checks. Produces a deployment-clearance.md gate artifact for the consumer's deployment pipeline. Runs as the implement-4-qa substep of the lifecycle (Specify → Plan → Tasks → Implement) or standalone.
author: ADLC5 Contributors
---

# QA — Security Scanning, Quality Gate & Deployment Clearance

## Intent

This skill runs a structured quality, security, and compliance pipeline against application code built during `@adlc5-implement` and optionally IaC in `infra/`. It produces a `deployment-clearance.md` gate artifact that the consumer's deployment pipeline checks before provisioning.

**User invokes:** `@qa for [feature]`

**Agent guides through:**
1. **Phase 0: Test Discovery** — Detect test frameworks and tools, determine which test categories apply, produce a confirmed test plan
2. **Phase 1: Security Scanning** — SAST, dependency vulnerability scan, IaC scan (if `infra/` present), secret detection; optional auto-fix via `test-fixer` subagent
3. **Phase 2: Quality Gate** — Run tests, measure coverage, lint, check complexity and duplication, validate standards compliance
4. **Phase 3: Performance & Accessibility** *(optional)* — Load testing against NFR targets, WCAG accessibility audit, bundle analysis
5. **Phase 4: Compliance & Policy Enforcement** — Aggregate all reports, enforce policies, produce `deployment-clearance.md`

**Pipeline position:**
```
Specify → Plan → Tasks → Implement (implement-4-qa: @qa) → pr-ready
```

Invoked by `@adlc5-implement` at the `implement-4-qa` substep, or standalone via `@qa`.

**Downstream gate:** `deployment-clearance.md` is the contract with the consumer's deployment pipeline (deployment itself is outside ADLC5 scope — see [production-ready.md](../../core/governance/production-ready.md)). It must always be produced, regardless of outcome. A starter CI hook is available at [github-workflows/security-scan.yml](../../templates/github-workflows/security-scan.yml).

## Workspace Setup

### On First Invocation

When `@qa` is invoked, **ALWAYS**:

1. **Extract feature name** from user's request (convert to kebab-case)
2. **Check for state file:** Read `{workspace}/.qa/{feature-name}/state.json`
3. **If state file doesn't exist:**
   - Output the model recommendation notice (see [Model Recommendation](#model-recommendation))
   - Ask all preference questions (see [Initial Preferences Setup](#initial-preferences-setup))
   - Run upstream detection (see [Upstream Detection](#upstream-detection))
   - Create `.qa/{feature-name}/` directory in workspace
   - Create initial `state.json` with feature name and detected context
   - Start Phase 0 (Test Discovery)
4. **If state file exists:**
   - Read current phase and resume from there
   - Load context (feature name, preferences, upstream flags, etc.)

### Initial Preferences Setup

**On first invocation, before starting Phase 0, output the model recommendation, then collect preferences via AskQuestion** (Cursor Q&A form). See [core/guides/askquestion-convention.md](../../core/guides/askquestion-convention.md). **Do not** use numbered chat lists.

#### Model Recommendation

Before asking any preference questions, output this notice:

```
Recommended model tier: reasoning (security / clearance).
Map tier → your host model via config.yaml model_profiles.
See core/guides/model-matrix.md.

Switch via your host model picker before continuing if you are on a fast/light model.
(Subagents inherit parent model — do not set model: "fast".)
```

Call **AskQuestion** (batch up to 2 questions):

| Question id | Maps to | Options |
|-------------|---------|---------|
| `qa_log` | `context.save_qa_log` | yes / no |
| `auto_fix` | `context.auto_fix_enabled` | yes / no |
| `perf_a11y` | `context.has_performance_targets` + Phase 3 | yes (run Phase 3) / no (skip) |

If `save_qa_log` is `true`, create and maintain `qa-log.md` throughout the process.
If `save_qa_log` is `false`, skip all Q&A logging (do not create or update qa-log.md).

Store all preferences in state:
```json
{
  "context": {
    "save_qa_log": true,
    "auto_fix_enabled": true,
    "has_performance_targets": false,
    "is_ui_facing": false
  }
}
```

### Upstream Detection

Run on first invocation, after preferences are collected. Check for upstream artifacts in this order:

1. `src/` — application code (required; if absent, warn and ask user to confirm correct path)
2. `infra/` — IaC directory, typically from [`@infra`](../infra/SKILL.md) (optional; set `context.has_iac: true` if found)
3. `.adlc5/{feature}/design/1c-operations.md` — security design + performance targets
4. `.prt/{feature}/prt.md` — NFRs + compliance requirements
5. `.infra/{feature}/infra-validation-report.md` — baseline IaC security findings from [`@infra`](../infra/SKILL.md) (optional)

Announce what was found before proceeding:
```
"Found upstream artifacts:
  ✅ src/ — application code present
  ✅ infra/ — IaC present (will include IaC security scanning)
  ✅ .adlc5/{feature}/design/1c-operations.md — security design loaded
  ⚠️  .prt/{feature}/prt.md — not found (will use defaults for NFR targets)

Proceeding to Phase 0: Test Discovery."
```

### State File Schema

The agent MUST create and maintain this file at `{workspace}/.qa/{feature-name}/state.json`.

**State authority:** this file is stage-local working state for `@qa` only. The lifecycle source of truth remains `.adlc5/{feature}/state.json` — on completion the orchestrator records the outcome there (`implement-4-qa` gate), and `./scripts/adlc5 gate` reads the clearance artifact, not this file. Prefer `./scripts/adlc5 state get --feature "{feature}"` when inspecting lifecycle state.

```json
{
  "feature_name": "string (kebab-case)",
  "current_phase": "0",
  "phase_status": {
    "test_discovery": "not_started|in_progress|completed",
    "security_scanning": "not_started|in_progress|completed",
    "quality_gate": "not_started|in_progress|completed",
    "performance_accessibility": "not_started|in_progress|completed|skipped",
    "compliance": "not_started|in_progress|completed"
  },
  "test_plan": {
    "applicable_categories": [],
    "tools_detected": [],
    "tools_recommended": [],
    "gaps": []
  },
  "results": {
    "security": {
      "sast_findings": { "critical": 0, "high": 0, "medium": 0, "low": 0 },
      "dependency_vulnerabilities": { "critical": 0, "high": 0, "medium": 0, "low": 0 },
      "iac_findings": { "critical": 0, "high": 0, "medium": 0, "low": 0 },
      "secrets_detected": 0,
      "auto_fixes_applied": 0
    },
    "quality": {
      "tests_passed": 0,
      "tests_failed": 0,
      "tests_skipped": 0,
      "coverage_percentage": null,
      "coverage_target": 80,
      "lint_errors": 0,
      "lint_warnings": 0,
      "complexity_hotspots": 0,
      "duplication_percentage": null
    },
    "performance": {
      "response_time_p95": null,
      "throughput_rps": null,
      "error_rate": null,
      "targets_met": null
    },
    "accessibility": {
      "wcag_violations": { "critical": 0, "serious": 0, "moderate": 0, "minor": 0 },
      "lighthouse_score": null
    },
    "compliance": {
      "status": "pending|cleared|blocked|cleared-with-exceptions",
      "blocking_issues": 0,
      "accepted_risks": 0
    }
  },
  "artifacts": {
    "test_plan": ".qa/{feature-name}/test-plan.md",
    "security_report": ".qa/{feature-name}/security-report.md",
    "quality_report": ".qa/{feature-name}/quality-report.md",
    "performance_accessibility_report": ".qa/{feature-name}/performance-accessibility-report.md",
    "deployment_clearance": ".qa/{feature-name}/deployment-clearance.md",
    "qa_log": ".qa/{feature-name}/qa-log.md"
  },
  "context": {
    "save_qa_log": true,
    "has_iac": false,
    "is_ui_facing": false,
    "has_performance_targets": false,
    "auto_fix_enabled": true
  },
  "rework_history": [],
  "last_updated": "ISO8601 timestamp"
}
```

### Workspace Artifact Structure

All generated files go in the **user's workspace** (NOT in the skills directory):

```
{workspace}/
├── .qa/
│   └── {feature-name}/
│       ├── state.json                          # State tracking (agent creates this)
│       ├── qa-log.md                           # OPTIONAL: Q&A log (only if user opts in)
│       ├── test-plan.md                        # Phase 0 output: confirmed test plan
│       ├── security-report.md                  # Phase 1 output: SAST + dependency + IaC + secrets
│       ├── quality-report.md                   # Phase 2 output: coverage + lint + complexity
│       ├── performance-accessibility-report.md # Phase 3 output (optional)
│       └── deployment-clearance.md             # Phase 4 output: gate artifact for the deployment pipeline
├── src/
│   └── [application code from @adlc5-plan]
└── infra/
    └── [IaC — optional]
```

## Phase Flow & State Management

### Phase Detection Logic

**`current_phase` → step ID mapping** (see [phase-registry.md](../../core/guides/phase-registry.md)):

| `current_phase` | Legacy | `phase_status` key | Phase Guide |
|-----------------|--------|-------------------|-------------|
| `qa-0-test-discovery` | `0` | `test_discovery` | `phases/00-test-discovery.md` |
| `qa-1-security-scanning` | `1` | `security_scanning` | `phases/01-security-scanning.md` |
| `qa-2-quality-gate` | `2` | `quality_gate` | `phases/02-quality-gate.md` |
| `qa-3-performance-accessibility` | `3` | `performance_accessibility` | `phases/03-performance-accessibility.md` |
| `qa-4-compliance` | `4` | `compliance` | `phases/04-compliance.md` |
| `completed` | — | — | Feature complete |

Normalize legacy IDs on read; write new IDs only.

```
1. Extract feature name from user's request (convert to kebab-case)
2. Read {workspace}/.qa/{feature-name}/state.json
3. If file doesn't exist:
   → Output model recommendation
   → Collect preferences (Q&A log, auto-fix, performance/accessibility)
   → Run upstream detection; set context flags in state
   → Create .qa/{feature-name}/ directory
   → Create state.json with current_phase: "0"
   → Start Phase 0
4. If file exists:
   → Read current_phase field (see mapping table above)
   → If "completed": Announce feature is done, offer to revisit or start a new feature
   → Otherwise: Announce resume context and continue from that phase
```

### Phase Transitions

Interaction mode determines transition behavior (see [Autonomous mode](#autonomous-mode)):

**HITL mode (default): Never auto-advance phases. Always ask user for confirmation.**

After completing work in a phase:
1. Save the phase artifact to workspace
2. Update `state.json` with completed status and numeric findings counts
3. **AskQuestion:** "Phase [N] complete. Ready to move to Phase [N+1]?" — Yes / Revise / Pause
4. If yes → Update `state.json` `current_phase`, start next phase
5. If no → Keep in current phase for refinements

**Approval is per-phase, never cumulative.** When the user says "yes", "proceed", "continue", or any similar affirmation, this ONLY grants approval to advance to the **immediately next phase** — never beyond. After completing that next phase, you MUST stop and ask for approval again before advancing further.

### Autonomous mode

When `@qa` is invoked by the `@adlc5` autopilot at `implement-4-qa` — i.e. `.adlc5/{feature}/state.json` has `autopilot.mode: autonomous`, or `.adlc5/{feature}/policies.yaml` sets `autopilot.interaction_mode: autonomous` — replace per-phase confirmation with gate-driven flow:

- **Skip preference questions:** use defaults (`save_qa_log: true`, `auto_fix_enabled: false`, Phase 3 per upstream NFR/UI detection). Never enable auto-fix without explicit user opt-in, even autonomously.
- **Auto-advance phases** after saving each phase artifact and updating state — do not AskQuestion between phases.
- **Still halt (hard escalation) on:** unresolved critical/high security findings, secrets detected, or a `BLOCKED` clearance — report to the orchestrator, which applies `hard_escalation: security_critical` from `policies.yaml`. Never mark accepted risks autonomously; risk acceptance always requires the user.
- Phases 1 and 2 remain mandatory; `deployment-clearance.md` must still always be produced.

**Note on Phase 3 skip:** If `context.is_ui_facing` is `false` AND `context.has_performance_targets` is `false`, skip Phase 3: set `performance_accessibility` to `"skipped"` and advance directly to Phase 4. No user confirmation needed for this skip — it was already decided during preferences.

**Note on downstream handoff:** After Phase 4 completes, announce:
```
"@qa complete. Deployment clearance is at .qa/{feature-name}/deployment-clearance.md.
Status: [CLEARED | BLOCKED | CLEARED-WITH-EXCEPTIONS]

Next step: @deploy for {feature-name} (clearance-gated; requires human deploy_approval)."
```

### Subagent Usage

The orchestrator MAY spawn subagents for Phase 1 and Phase 2 to run checks in parallel:

- **`test-scanner`** (Phase 1): Spawned when running SAST + dependency audit + IaC scan in parallel. Read-only except for writing the security report. Prompt must include: feature name, paths to scan, whether IaC is present (`context.has_iac`), baseline findings from the infra validation report if available.
- **`test-fixer`** (Phase 1–2): Spawned when `auto_fix_enabled: true` and fixable issues were found. Write access to `src/` and `infra/`. Prompt must include: specific findings to fix with file paths and line numbers. Must report back every change made before applying.
- **`test-runner`** (Phase 2): Spawned when running test suite execution + coverage reporting. Prompt must include: feature name, detected test framework, test command, coverage tool.

**Direct mode:** The orchestrator can run all phases without spawning subagents. Subagents are optional parallel optimization, not required.

## Phase Reference Guides

The agent should read these files from the skills directory for detailed methodology:

- **Phase 0:** Read `phases/00-test-discovery.md` — Framework detection, tool inventory, test category analysis, test plan output
- **Phase 1:** Read `phases/01-security-scanning.md` — SAST methodology, dependency audit, IaC scan, secret detection, auto-fix rules
- **Phase 1 Tools:** Read `guides/security-scanning-tools.md` — Tool invocation reference, CLI syntax, output parsing
- **Phase 2:** Read `phases/02-quality-gate.md` — Test execution, coverage measurement, lint, complexity analysis, standards compliance
- **Phase 2 Thresholds:** Read `guides/quality-thresholds.md` — Default thresholds for coverage, complexity, duplication, lint error budgets
- **Phase 3:** Read `phases/03-performance-accessibility.md` — Load testing setup, NFR comparison, WCAG audit, Lighthouse, bundle analysis
- **Phase 4:** Read `phases/04-compliance.md` — Policy aggregation, clearance determination, exception handling, deployment-clearance.md format
- **Agent Instructions:** Read `guides/test-agent-instructions.md` on every invocation — Persona, tone, behavioral rules
- **Templates:** Read the appropriate template before producing each report artifact

## Resuming Work

If user invokes `@qa` in a workspace with existing state:

1. **Extract feature name** from user's request
2. **Read state file:** `{workspace}/.qa/{feature-name}/state.json`
3. **Announce context:** "Resuming @qa for '{feature_name}'. Currently in Phase {N}: {phase_name}."
4. **Load artifacts:** Read relevant phase reports from workspace
5. **Continue from current phase**

**Note:** If user doesn't specify feature name, list available features by scanning the `.qa/` directory:

```
User: "@qa"
Agent: "Found existing @qa projects in this workspace:
        1. payment-gateway (Phase 1: Security Scanning — in progress)
        2. user-profile (Phase 4: Compliance)
        3. notifications-system (Phase 0: Test Discovery)

        Which feature would you like to continue with, or would you like to start a new one?"
```

If the `.qa/` directory doesn't exist or is empty, treat this as a new invocation and start from preferences.

## Agent Instructions Summary

### On Every Invocation

1. **Extract feature name** from user's request (or list available if not specified)
2. **Read workspace state:** `{workspace}/.qa/{feature-name}/state.json`
3. **Determine phase:** Extract `current_phase` or start at `"0"` for new features
4. **Load agent instructions:** Read `guides/test-agent-instructions.md` for persona, tone, and behavioral rules
5. **Load phase guide:** Read appropriate `phases/{N}-*.md` file
6. **Load supplementary guides:** Read `guides/security-scanning-tools.md` before Phase 1; read `guides/quality-thresholds.md` before Phase 2
7. **Load workspace artifacts:** Read relevant upstream files (security design, user stories, NFRs, prior reports)
8. **Execute phase:** Follow methodology from phase guide; load template before producing each artifact
9. **Save artifacts:** Write to `{workspace}/.qa/{feature-name}/...`
10. **Update results in state:** Write numeric findings counts to `results` in `state.json` after each phase
11. **Update Q&A log (if enabled):** If `context.save_qa_log` is `true`, append Q&A to `qa-log.md`
12. **Update state:** Write updated `{workspace}/.qa/{feature-name}/state.json`
13. **Ask for confirmation:** Before advancing to next phase

### Never Do

- ❌ Auto-advance phases without user confirmation in HITL mode (autonomous mode auto-advances per [Autonomous mode](#autonomous-mode))
- ❌ Modify `src/` or `infra/` files without explicit user opt-in via auto-fix confirmation (applies in autonomous mode too)
- ❌ Skip Phase 1 (security scanning) — security is never optional
- ❌ Declare CLEARED status if any unresolved critical or high security findings remain
- ❌ Declare quality gate PASS if test coverage is below the configured threshold without user acknowledgment
- ❌ Run `terraform apply`, `kubectl apply`, or any provisioning commands
- ❌ Assume IaC is present — always check `context.has_iac` before attempting IaC scanning
- ❌ Skip the `deployment-clearance.md` artifact — it is the contract with the downstream deployment pipeline and must always be produced
- ❌ Mark accepted risks without the user explicitly acknowledging them
- ❌ Produce a deployment clearance without first completing Phases 1 and 2
- ❌ Interpret "proceed" or "continue" as approval for more than one phase transition — approval is always for the immediately next phase only (HITL mode)
- ❌ Mark accepted risks or declare CLEARED-WITH-EXCEPTIONS autonomously — risk acceptance always requires the user
- ❌ Save artifacts to the skills directory — all output goes in the user's workspace under `.qa/`

### Always Do

- ✅ Read state from `.qa/{feature-name}/state.json`
- ✅ Load `guides/test-agent-instructions.md` on every invocation
- ✅ Detect upstream artifacts (design docs, `infra/`, PRT) on first invocation and set context flags
- ✅ Read `guides/security-scanning-tools.md` before Phase 1
- ✅ Read `guides/quality-thresholds.md` before Phase 2
- ✅ Load the appropriate template before producing each report artifact
- ✅ Save all artifacts to `.qa/{feature-name}/`
- ✅ Update `results` in `state.json` with numeric findings counts after each phase
- ✅ Log all Q&A exchanges to `qa-log.md` immediately (if enabled)
- ✅ **AskQuestion** before phase transitions
- ✅ When auto-fix is enabled and fixable issues are found, list every proposed change before applying and ask for confirmation
- ✅ Produce `deployment-clearance.md` in Phase 4 regardless of outcome (CLEARED, BLOCKED, or CLEARED-WITH-EXCEPTIONS)
- ✅ After Phase 4: announce the deployment-pipeline handoff with clearance status
- ✅ When Phase 3 is skipped, set `phase_status.performance_accessibility` to `"skipped"` in state.json

## Quality Standards

Every phase output must meet these standards:

- **Test Discovery:** Every applicable test category identified with rationale; no gaps left undocumented; tool recommendations include install command and version
- **Security Scanning:** All OWASP Top 10 patterns checked; every finding has a CWE/CVE reference and remediation guidance; IaC findings reference specific resource and line number; no secrets or keys appear in report output
- **Quality Gate:** Coverage target enforced; every lint error listed with file and line number; standards deviations cited to specific guideline rules; complexity hotspots include function name, file, and cyclomatic complexity score
- **Performance & Accessibility:** Results compared against explicit NFR targets from `.prt/{feature}/prt.md` or `.adlc5/{feature}/design/1c-operations.md` — never vague "good/bad" assessments; WCAG violations tied to specific criteria (e.g., WCAG 2.1 AA 1.4.3); Lighthouse scores include category breakdown
- **Deployment Clearance:** Every blocking issue listed explicitly with phase origin and finding reference; accepted risks logged with user acknowledgment quote and timestamp; overall status (CLEARED / BLOCKED / CLEARED-WITH-EXCEPTIONS) prominently displayed at top of document; artifact timestamp and feature context recorded
