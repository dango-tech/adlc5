---
name: compliance
description: Phase 4 - Compliance & Policy Enforcement. Aggregates all previous reports, enforces baseline policies, and produces the deployment-clearance.md gate artifact that the consumer's deployment pipeline checks before proceeding.
---

## Purpose

This is the final gate before deployment. Aggregate findings from all previous phases, enforce baseline security and quality policies, evaluate any compliance requirements from the PRT (GDPR, HIPAA, SOC 2, PCI DSS), compute a deployment readiness score, and generate `deployment-clearance.md`. This document is the contract between `@qa` and the consumer's deployment pipeline — deployment must not proceed without a clearance status of `CLEARED` or `CLEARED-WITH-EXCEPTIONS`.

## Output

`deployment-clearance.md` — the gate artifact containing:
- Overall status: **CLEARED** / **BLOCKED** / **CLEARED-WITH-EXCEPTIONS**
- Blocking issues (must be resolved before deployment)
- Accepted risks with explicit user acknowledgment and timestamps
- Non-blocking recommendations
- Compliance findings from PRT requirements
- Deployment readiness score

## Prerequisites

- Phase 1 (Security Scanning) complete — `security-report.md` exists
- Phase 2 (Quality Gate) complete — `quality-report.md` exists
- Phase 3 (Performance/Accessibility) complete **or** skipped — either state is valid

## Phase 4 Process

---

### Step 1: Load All Previous Reports

Read each artifact from prior phases and extract their key findings. The `state.json` `results` object is the authoritative source for numeric counts; the report files provide narrative context.

**From `security-report.md` (Phase 1), extract:**
- SAST finding counts by severity (critical / high / medium / low)
- Secrets detected count and whether they were auto-revoked
- IaC scan findings: unencrypted storage, public endpoints, hardcoded credentials
- Dependency vulnerability counts by severity
- Auto-fixes applied (list)

**From `quality-report.md` (Phase 2), extract:**
- Gate status (PASS / FAIL / PASS-WITH-WARNINGS)
- Coverage percentage vs. target
- Lint error count
- Complexity violations count
- TODO/FIXME in critical paths count
- Standards compliance deviation severity counts

**From `performance-accessibility-report.md` (Phase 3, if not skipped), extract:**
- Performance targets missed (list)
- WCAG violations by impact level (critical / serious / moderate / minor)
- Bundle size vs. target

Cross-reference each extracted value against `state.json` `results.*`. If there is a discrepancy between the report file and `state.json`, use `state.json` as the source of truth and note the discrepancy.

---

### Step 2: Apply Baseline Policy Checks

Evaluate each policy against the extracted findings. Record PASS / FAIL / N/A for each:

| # | Policy | Check Expression | Source Phase | Status |
|---|---|---|---|---|
| 1 | No unresolved critical security findings | `results.security.sast_findings.critical == 0` | Phase 1 | |
| 2 | No secrets in committed code | `results.security.secrets_detected == 0` | Phase 1 | |
| 3 | Test coverage meets minimum threshold | `results.quality.coverage_percentage >= results.quality.coverage_target` | Phase 2 | |
| 4 | Zero lint errors | `results.quality.lint_errors == 0` | Phase 2 | |
| 5 | No hardcoded credentials in IaC | IaC scan contains no `SECRET` category findings | Phase 1 | |
| 6 | All data stores encrypted at rest | IaC scan has no `unencrypted-storage` findings | Phase 1 | |
| 7 | No public database endpoints | IaC scan has no `public-db-access` findings | Phase 1 | |
| 8 | Structured logging — no PII in logs | Standards compliance shows no PII-in-logs deviations | Phase 2 | |
| 9 | All API endpoints have auth/authz | SAST + standards compliance — no unauthenticated-endpoint findings | Phase 1–2 | |
| 10 | No critical WCAG violations | `results.accessibility.wcag_violations.critical == 0` | Phase 3 | N/A if skipped |
| 11 | Performance targets met | `results.performance.targets_met == true` | Phase 3 | N/A if skipped |
| 12 | No unresolved high dependency vulnerabilities | `results.security.dependency_vulns.high == 0` | Phase 1 | |

Mark any policy as N/A only when Phase 3 was explicitly skipped. N/A policies are excluded from the readiness score denominator.

---

### Step 3: Apply Compliance Requirements from PRT

Read `.prt/{feature}/prt.md` if it exists. Extract any compliance requirements listed in the NFRs section. For each identified requirement, evaluate its status:

**GDPR / Data Privacy:**
- PII data inventory documented (what data is collected, why, retention period)
- Right-to-erasure capability exists (user data can be deleted on request)
- Consent management in place before data collection
- Data processing agreements with third-party services documented

**HIPAA:**
- PHI (Protected Health Information) encrypted at rest and in transit
- Audit logging enabled for all PHI access
- Role-based access controls on PHI data stores
- Business Associate Agreements (BAAs) documented for cloud providers handling PHI

**SOC 2:**
- Encryption at rest and in transit verified (from IaC scan)
- Access logging enabled on all sensitive resources
- Change management process documented (this deployment follows a change ticket)
- Incident response runbook exists

**PCI DSS:**
- Cardholder data (card numbers, CVVs) never stored unencrypted
- Network segmentation isolates payment processing from other systems (verified in IaC)
- Tokenization or a certified payment processor used for card handling
- Vulnerability scans current (this `@qa` run satisfies the scan requirement)

Produce a compliance status table:

| Requirement | Standard | Status | Notes |
|---|---|---|---|
| PII data inventory documented | GDPR | MET | See `docs/data-inventory.md` |
| Right-to-erasure API endpoint | GDPR | UNMET | No `/api/users/{id}` DELETE endpoint exists |
| PHI encrypted at rest | HIPAA | NOT VERIFIABLE | Requires runtime audit of RDS instance |

**Status values:**
- **MET:** Evidence found in code, IaC, or documentation
- **UNMET:** Requirement is clear but no implementation evidence found — this is a blocking finding if the requirement is mandatory
- **NOT VERIFIABLE:** Cannot be determined from static analysis — requires runtime audit; note this in the clearance document and flag for post-deployment verification

---

### Step 4: Compute Deployment Readiness Score

Count the number of policy checks that PASSED (excluding N/A policies from both numerator and denominator).

```
Score = (Passed policy checks / Total applicable policy checks) × 100
```

Map the score to a clearance tier:

| Score Range | Clearance Status | Interpretation |
|---|---|---|
| 100% | CLEARED | All checks pass — no exceptions needed |
| 85–99% | CLEARED-WITH-EXCEPTIONS | Non-critical issues only — user acknowledgment required |
| 70–84% | CLEARED-WITH-EXCEPTIONS | Mix of high and medium issues — explicit user acceptance required |
| < 70% | BLOCKED | Critical or high unresolved issues — deployment blocked |

The readiness score is informational; the actual gate status is driven by the issue classification in Step 5. A score of 90% can still result in BLOCKED if one of the failing policies is a hard blocker.

---

### Step 5: Classify Issues

**Blocking issues** (these alone set status to BLOCKED regardless of score):
- Any unresolved Critical SAST security finding
- Secrets detected in committed code that have not been revoked and rotated
- Test coverage below 50% (extreme gap — signals code is essentially untested)
- Mandatory compliance requirement with status UNMET (e.g., GDPR right-to-erasure missing when GDPR applies)
- Hardcoded credentials in IaC

**Soft-blocking issues** (status → CLEARED-WITH-EXCEPTIONS; require explicit user acceptance to proceed):
- Unresolved High SAST security findings
- Test coverage below the configured target but above 50%
- Critical WCAG violations (if UI-facing feature)
- Performance targets missed
- Unresolved High dependency vulnerabilities
- Compliance requirement with status NOT VERIFIABLE (flag for post-deployment verification)

**Non-blocking recommendations** (always logged in the clearance document, never block deployment):
- Medium and Low SAST findings
- Lint warnings
- Code complexity hotspots
- Moderate/minor WCAG violations
- Bundle size above target
- Code duplication above threshold
- TODO/FIXME in non-critical paths
- Optimization opportunities from performance analysis

---

### Step 6: Collect Explicit User Risk Acceptance

For each soft-blocking issue, present a clear, individual acceptance prompt. Do not batch these — each risk must be acknowledged separately.

```
The following issues require your explicit acceptance to proceed with deployment:

──────────────────────────────────────────────────────
Issue 1 of 2

[High] SQL injection risk
File: src/api/search.py, line 145
Finding: User-controlled input passed to a raw SQL query without parameterization
CWE: CWE-89 (SQL Injection)
Impact: An attacker could read, modify, or delete database records

Accept this risk and proceed? [Yes / No]
──────────────────────────────────────────────────────
Issue 2 of 2

[High] Test coverage below target
Current: 71%  |  Target: 80%  |  Gap: 7 files under-tested
Impact: Reduced confidence in untested code paths during production traffic

Accept this risk and proceed? [Yes / No]
──────────────────────────────────────────────────────
```

For each acceptance, record in `state.json`:
```json
{
  "results": {
    "compliance": {
      "accepted_risks": [
        {
          "severity": "High",
          "finding": "SQL injection in src/api/search.py:145",
          "cwe": "CWE-89",
          "accepted": true,
          "timestamp": "2026-03-19T14:32:00Z",
          "recommendation": "Parameterize the query before next release"
        }
      ]
    }
  }
}
```

If the user declines to accept any soft-blocking issue, that issue escalates to blocking and the overall status becomes BLOCKED.

---

### Step 7: Produce deployment-clearance.md

Write `.qa/{feature}/deployment-clearance.md` using the following structure:

```markdown
# Deployment Clearance — {feature-name}

**Overall Status:** CLEARED | BLOCKED | CLEARED-WITH-EXCEPTIONS
**Issued:** YYYY-MM-DD HH:MM UTC
**Feature:** {feature-name}
**Validated by:** @qa skill v1.0.0
**Readiness Score:** {score}% ({passed}/{applicable} policy checks passed)

---

## Clearance Summary

| Category | Status | Details |
|---|---|---|
| Security Scanning | ✅ PASS | 0 critical, 2 high (accepted), 5 medium |
| Quality Gate | ✅ PASS | 84% coverage, 0 lint errors |
| Performance | ⚠️ EXCEPTION | p95 187ms ✅, throughput 823 RPS ❌ (target 1000) |
| Accessibility | ✅ PASS | 0 critical WCAG violations |
| Compliance Policies | ✅ PASS | 11/12 policies met |

---

## Blocking Issues

_None._

---

## Accepted Risks

| # | Severity | Finding | Accepted | Timestamp |
|---|---|---|---|---|
| 1 | High | SQL injection — src/api/search.py:145 | User (session) | 2026-03-19 |
| 2 | High | Coverage 71% (target 80%) | User (session) | 2026-03-19 |

These risks are accepted for this deployment. They must be resolved before the next release.

---

## Non-Blocking Recommendations

- **Medium** — SAST: Path traversal risk in src/files/upload.py:67 — validate file paths before processing
- **Warning** — Quality: 14 lint warnings across 3 files — run `ruff --fix` to resolve
- **Warning** — Performance: Bundle size 312 KB (target 250 KB) — apply dynamic imports for chart library
- **Moderate** — Accessibility: 3 moderate WCAG violations — add visible focus indicators to ghost buttons

---

## Compliance Findings

| Requirement | Standard | Status | Notes |
|---|---|---|---|
| PII data inventory | GDPR | MET | docs/data-inventory.md |
| Right-to-erasure | GDPR | NOT VERIFIABLE | Requires post-deployment audit |

---

## Next Step

This feature is cleared for deployment with exceptions.

Hand `deployment-clearance.md` to your deployment pipeline.

This clearance expires 72 hours from issuance or upon any new commits to `src/` — whichever comes first.
```

---

### Step 8: Announce and Update State

Update `state.json`:
```json
{
  "current_phase": "completed",
  "phase_status": {
    "compliance": "completed"
  },
  "results": {
    "compliance": {
      "status": "cleared|blocked|cleared-with-exceptions",
      "readiness_score": 91,
      "policy_checks_passed": 11,
      "policy_checks_total": 12,
      "blocking_issues": 0,
      "accepted_risks": 2,
      "non_blocking_recommendations": 4,
      "clearance_issued_at": "2026-03-19T14:35:00Z"
    }
  }
}
```

**If CLEARED or CLEARED-WITH-EXCEPTIONS:**

```
@qa complete.

Status: CLEARED-WITH-EXCEPTIONS
Readiness score: 91% (11/12 policy checks passed)
Deployment clearance: .qa/{feature-name}/deployment-clearance.md

Accepted risks: 2 (logged in clearance document)
Recommendations: 4 (non-blocking — see clearance document)

Next step: hand deployment-clearance.md to your deployment pipeline.
```

**If BLOCKED:**

```
@qa complete — deployment is BLOCKED.

Blocking issues (must resolve before deployment):
1. [Critical] Hardcoded AWS credentials — src/config.py:23
   Action required: Revoke the credentials immediately, rotate them, and remove from source code.
2. [Critical] SQL injection — src/api/search.py:145
   Action required: Parameterize the query using prepared statements.

Fix these issues and re-run @qa for {feature-name} to generate a new clearance.
Clearance document not issued.
```

When BLOCKED, do not write a `deployment-clearance.md`. Write a `deployment-blocked.md` instead that lists the blocking issues and the steps required to resolve them, so the developer has a clear remediation checklist.
