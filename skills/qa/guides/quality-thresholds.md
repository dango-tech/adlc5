---
name: quality-thresholds
description: Default quality thresholds for @qa Phase 2 Quality Gate. Defines pass/fail/warning thresholds for coverage, complexity, duplication, and linting. Loaded before Phase 2 begins.
---

# Quality Thresholds Reference

Load this guide before Phase 2. It defines the default thresholds applied when no upstream PRT NFRs or Plan design docs specify different targets.

## Overview

These are the defaults. The PRT always overrides defaults. Plan operations guidance overrides coverage defaults for safety-critical paths. When a PRT exists at `.prt/{feature}/prt.md`, read Section 7 (Non-Functional Requirements) first and apply any explicit targets before consulting this file.

---

## 1. Test Coverage Thresholds

| Tier | Line Coverage | Branch Coverage | When to Apply |
|---|---|---|---|
| Production-critical | 90% | 80% | Auth, payments, data integrity |
| Standard | 80% | 70% | General application code |
| Minimum acceptable | 70% | 60% | Legacy code or thin adapters |
| Advisory only | 50% | 40% | Glue code, generated code |

**Application rules:**

- Apply **Standard** tier by default to all files unless a specific rule below escalates or downgrades.
- Escalate to **Production-critical** for any file whose path matches: `auth/`, `payments/`, `security/`, `encryption/`, `session/`, `token/`, `credential/`.
- Downgrade to **Advisory only** for files matching: `*_generated.*`, `*_pb2.py`, `*.pb.go`, `proto/`, `migrations/`, `__generated__/`.
- Files below the Advisory threshold are noted in the report but do not cause a gate failure.
- Files below Standard but above Minimum acceptable are PASS-WITH-WARNINGS.
- Files below Minimum acceptable in non-advisory paths are FAIL.

**Tool reference:**

```bash
# Python
coverage run -m pytest && coverage report --fail-under=80

# JavaScript / TypeScript (Jest)
jest --coverage --coverageThreshold='{"global":{"lines":80,"branches":70}}'

# Go
go test -coverprofile=coverage.out ./... && go tool cover -func=coverage.out

# Java (Maven + JaCoCo)
mvn test jacoco:report
# Configure threshold in pom.xml <jacoco:check> goal
```

---

## 2. Code Complexity Thresholds

| Metric | Warning | Fail | Tool |
|---|---|---|---|
| Cyclomatic complexity (per function) | > 10 | > 20 | radon, eslint `complexity`, PMD |
| Cognitive complexity (per function) | > 15 | > 30 | SonarQube, Semgrep |
| Lines per function | > 40 | > 80 | Manual, eslint `max-lines-per-function` |
| Lines per file | > 300 | > 600 | Manual, eslint `max-lines` |
| Parameters per function | > 4 | > 7 | eslint `max-params`, pylint |

**Gate impact:**
- Any function in the FAIL range → FAIL status for Quality Gate (unless it is in a generated or legacy file).
- Functions in the WARNING range → PASS-WITH-WARNINGS; list as hotspots in the report.
- Hotspot functions must be included in the Complexity section of the quality report with a refactoring recommendation.

**Tool invocations:**

```bash
# Python — cyclomatic complexity
radon cc src/ -s -j > radon-cc.json

# JavaScript / TypeScript — add to .eslintrc
# "complexity": ["warn", 10]
# "max-lines-per-function": ["warn", {"max": 40}]

# Java — PMD
pmd check -d src/ -R rulesets/java/quickstart.xml -f json > pmd-results.json
```

---

## 3. Code Duplication Thresholds

| Level | Threshold | Gate Impact |
|---|---|---|
| Acceptable | < 3% | No action |
| Warning | 3–7% | PASS-WITH-WARNINGS; log and recommend refactoring |
| Fail | > 7% | FAIL; flag as quality gate failure |

**Configuration:**
- Minimum token length: 50 tokens (jscpd default — prevents false positives on short boilerplate).
- Exclude from duplication scan: `**/vendor/`, `**/node_modules/`, `**/__generated__/`, `**/migrations/`, `**/proto/`.

**Tool invocation:**

```bash
# jscpd (multi-language, preferred)
jscpd src/ \
  --min-tokens 50 \
  --ignore "**/node_modules/**,**/__generated__/**,**/migrations/**" \
  --reporters json \
  --output jscpd-results/
```

---

## 4. Linting Thresholds

| Severity | Threshold | Gate Impact |
|---|---|---|
| Error | 0 | FAIL if any errors exist after auto-fix |
| Warning | ≤ 10 | PASS-WITH-WARNINGS if ≤ 10; FAIL if > 10 |
| Info | Any | Never affects gate |

**Auto-fix rule:** If `auto_fix_enabled: true` in `state.json`, always offer to run the fixer before counting errors. Only count errors that remain AFTER auto-fix.

```bash
# Python — ruff (preferred for speed)
ruff check src/ --fix --output-format json > ruff-results.json

# JavaScript / TypeScript
eslint src/ --ext .js,.ts,.jsx,.tsx --fix --format json > eslint-results.json

# Go
golangci-lint run --fix --out-format json > golangci-results.json
```

**After auto-fix:** Re-run the linter without `--fix` to get the final count. Only report the post-fix state in the quality report; note "N issues auto-fixed" in the Auto-Fixes Applied section.

---

## 5. Standards Compliance Thresholds

| Check | Warning | Fail |
|---|---|---|
| Functions without error handling | > 5% of functions | > 20% of functions |
| API endpoints without input validation | > 0 | N/A — any unvalidated endpoint is a FAIL |
| PII logged (detected patterns) | > 0 | > 0 — always blocks deployment |
| Unresolved TODOs in critical paths | > 0 | N/A — advisory; never a gate blocker |
| Missing docstrings on public APIs | > 20% | > 50% |

**PII pattern detection:** Scan log statements for patterns: `email`, `password`, `ssn`, `social_security`, `credit_card`, `card_number`, `phone`, `dob`, `date_of_birth`. Any log statement containing these field names (case-insensitive) with a non-null value is a PII logging finding at Critical severity.

**Error handling detection:** Look for functions that `raise`, `throw`, or `panic` without a corresponding `try/catch`, `except`, or `recover` block. Exclude functions explicitly annotated as `@noqa` or with a suppression comment.

---

## 6. PRT Override Rules

When `.prt/{feature}/prt.md` contains NFRs with explicit targets, those override the defaults above. Read Section 7 of the PRT before applying any threshold.

| PRT NFR | Overrides |
|---|---|
| "Test coverage: X%" | Line Coverage threshold for all Standard-tier files |
| "Performance SLA: p95 < Xms" | Sets the p95 target for Phase 3 performance tests |
| "Compliance: SOC 2" | Escalates all auth and data-handling paths to Production-critical tier |
| "Compliance: HIPAA" | All PHI-handling code escalated to Production-critical; PII logging = Critical finding (no exception) |
| "Compliance: PCI DSS" | Cardholder data paths = Production-critical; any unencrypted transmission of cardholder data = Critical finding (blocks deployment) |
| "Compliance: GDPR" | PII logging threshold reduced to zero tolerance across all paths, not just critical |

When a compliance framework is specified in the PRT, note it in the Quality Gate Report header and in the deployment-clearance.md Policy Compliance Matrix.
