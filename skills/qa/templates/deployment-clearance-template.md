# Deployment Clearance — [Feature Name]

**Overall Status:** CLEARED / BLOCKED / CLEARED-WITH-EXCEPTIONS  
**Issued:** [YYYY-MM-DD HH:MM UTC]  
**Feature:** [feature-name]  
**Validated by:** @qa skill v1.0.0  
**Valid Until:** [YYYY-MM-DD HH:MM UTC] *(24 hours from issue — clearances expire to prevent stale approvals)*

---

```
╔══════════════════════════════════════════════════════════╗
║  STATUS: CLEARED / BLOCKED / CLEARED-WITH-EXCEPTIONS     ║
║  Feature: [feature-name]                                  ║
║  Issued:  [YYYY-MM-DD HH:MM UTC]                          ║
╚══════════════════════════════════════════════════════════╝
```

---

## 1. Clearance Summary

| Phase | Category | Status | Details |
|---|---|---|---|
| Phase 1 | Security — SAST | PASS / FAIL / PASS-WITH-WARNINGS | [e.g., "0 Critical, 0 High, 2 Medium (SEC-003, SEC-004) — non-blocking"] |
| Phase 1 | Security — Dependencies | PASS / FAIL / PASS-WITH-WARNINGS | [e.g., "0 Critical, 0 High — all CVEs resolved via auto-fix"] |
| Phase 1 | Security — IaC | PASS / N/A | [e.g., "N/A — no IaC present" or "2 findings resolved"] |
| Phase 1 | Security — Secrets | PASS / FAIL | [e.g., "0 secrets detected"] |
| Phase 2 | Quality — Coverage | PASS / FAIL / PASS-WITH-WARNINGS | [e.g., "78% line (target 80%) — warning"] |
| Phase 2 | Quality — Lint | PASS / FAIL | [e.g., "0 errors, 3 warnings"] |
| Phase 2 | Quality — Complexity | PASS-WITH-WARNINGS | [e.g., "1 hotspot above warning threshold"] |
| Phase 2 | Quality — Standards | PASS / FAIL | [e.g., "0 deviations"] |
| Phase 3 | Performance | PASS / FAIL / N/A | [e.g., "p95 312ms — exceeds 200ms target" or "N/A — no targets defined"] |
| Phase 3 | Accessibility | PASS / FAIL / N/A | [e.g., "0 Critical, 2 Serious violations" or "N/A — not UI-facing"] |
| Phase 3 | Bundle | PASS / N/A | [e.g., "287 KB — within 400 KB default target" or "N/A"] |
| Phase 4 | Compliance Matrix | PASS / FAIL | [e.g., "All applicable policies passed"] |

---

## 2. Deployment Readiness Score

**[N] / [N] policies passed ([N]%)**

| Score | Interpretation |
|---|---|
| 100% | All policies passed — CLEARED |
| 90–99% | Minor warnings only — CLEARED-WITH-EXCEPTIONS if no Critical/High blocking issues |
| 70–89% | Significant warnings or accepted risks — CLEARED-WITH-EXCEPTIONS only if all blocking issues resolved and risks explicitly accepted |
| < 70% | Multiple failures — BLOCKED |

**This clearance:** [N]/[N] ([N]%) — [CLEARED / CLEARED-WITH-EXCEPTIONS / BLOCKED]

---

## 3. Blocking Issues

*Any unresolved issue in this table prevents deployment. CLEARED status cannot be issued while this table has rows.*

| ID | Severity | Phase | Description | Required Action |
|---|---|---|---|---|
| [SEC-001] | Critical | Phase 1 | SQL injection in `src/auth/login.py:42` (CWE-89) | Apply parameterized query fix; re-run Phase 1 |
| [QG-001] | Blocking | Phase 2 | API endpoint `/users/create` has no input validation | Add validation; re-run Phase 2 |

*(If no blocking issues, write: "None — deployment is cleared to proceed.")*

---

## 4. Accepted Risks

*All entries in this table have been explicitly acknowledged by a named person. Acceptance was recorded at the timestamp shown.*

| # | Severity | Finding | Phase | Accepted By | Timestamp | Notes |
|---|---|---|---|---|---|---|
| 1 | High | [SEC-002] Unrestricted file upload — MIME type not validated | Phase 1 | [Name / Role] | [YYYY-MM-DD HH:MM UTC] | [e.g., "Vendor patch expected Q3 2026; WAF rule #42 deployed as interim mitigation; 30-day review scheduled"] |

*(If no risks accepted, write: "None.")*

---

## 5. Non-Blocking Recommendations

| Priority | Finding | Phase | Recommendation | Suggested Sprint |
|---|---|---|---|---|
| High | [e.g., Coverage gap in `password_reset.py` — 71% vs 90% target] | Phase 2 | Add tests for token expiry and invalid-token branches | Next sprint |
| Medium | [e.g., `moment` bundle inclusion — adds 67 KB gzipped] | Phase 3 | Replace with `date-fns` partial import | Next sprint |
| Medium | [e.g., A11Y-002 focus visibility — WCAG 2.1 SC 2.4.7] | Phase 3 | Add `:focus` outline styles to search input | Next sprint |
| Low | [e.g., Complexity hotspot in `process_invoice` — CC=13] | Phase 2 | Refactor discount calculation into separate method | Sprint +2 |

*(If none, write: "None.")*

---

## 6. Policy Compliance Matrix

| Policy | Status | Source Phase | Notes |
|---|---|---|---|
| No unresolved Critical SAST findings | ✅ PASS / ❌ FAIL | Phase 1 | [e.g., "0 Critical findings"] |
| No unresolved Critical dependency CVEs | ✅ PASS / ❌ FAIL | Phase 1 | [e.g., "All CVEs resolved via dependency upgrades"] |
| No active secrets in codebase | ✅ PASS / ❌ FAIL | Phase 1 | [e.g., "gitleaks returned 0 findings"] |
| IaC security scan passed (if applicable) | ✅ PASS / ⬜ N/A | Phase 1 | [e.g., "N/A — no IaC present"] |
| Test suite passes with no failures | ✅ PASS / ❌ FAIL | Phase 2 | [e.g., "170/170 tests passing"] |
| Line coverage meets threshold | ✅ PASS / ⚠️ WARN / ❌ FAIL | Phase 2 | [e.g., "78% vs 80% target — warning"] |
| Zero lint errors (post-auto-fix) | ✅ PASS / ❌ FAIL | Phase 2 | [e.g., "0 errors, 3 warnings"] |
| No PII logged | ✅ PASS / ❌ FAIL | Phase 2 | [e.g., "No PII patterns detected in log statements"] |
| All API endpoints have input validation | ✅ PASS / ❌ FAIL | Phase 2 | [e.g., "All 7 endpoints validated"] |
| Performance targets met (if defined) | ✅ PASS / ⚠️ WARN / ❌ FAIL / ⬜ N/A | Phase 3 | [e.g., "p95 312ms vs 200ms target — FAIL" or "N/A"] |
| WCAG accessibility targets met (if UI-facing) | ✅ PASS / ⚠️ WARN / ❌ FAIL / ⬜ N/A | Phase 3 | [e.g., "0 Critical, 2 Serious (accepted)" or "N/A"] |
| All compliance framework requirements met | ✅ PASS / ❌ FAIL / ⬜ N/A | Phase 4 | [e.g., "SOC 2 — auth paths at Production-critical tier"] |
| All accepted risks explicitly documented | ✅ PASS / ❌ FAIL | Phase 4 | [e.g., "1 risk accepted — see Section 4"] |

---

## 7. Artifact Trail

All supporting evidence for this clearance:

- **Security Report:** `.qa/[feature-name]/security-report.md`
- **Quality Gate Report:** `.qa/[feature-name]/quality-report.md`
- **Performance & Accessibility Report:** `.qa/[feature-name]/performance-accessibility-report.md` *(if applicable)*
- **Test State:** `.qa/[feature-name]/state.json`
- **Infra Validation Baseline Report (cross-reference):** `.infra/[feature-name]/infra-validation-report.md` *(if present)*

---

## 8. Next Step

**If CLEARED or CLEARED-WITH-EXCEPTIONS:**

> Next: hand this clearance to your deployment pipeline.

**If BLOCKED:**

> Resolve the blocking issues listed in Section 3 above, then re-run:
> `@qa for [feature-name]`
>
> Issues to resolve before re-run:
> - [List each blocking issue ID and one-line action]
