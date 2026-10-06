---
name: quality-gate
description: Phase 2 - Quality Gate. Runs test suites, measures coverage, lints code, checks complexity and duplication, and validates standards compliance. Produces quality-report.md with an overall PASS/FAIL/PASS-WITH-WARNINGS verdict.
---

## Purpose

Enforce code quality standards before deployment. Run existing tests, measure coverage against targets, lint for style violations, flag complexity hotspots and duplication, and verify the codebase follows the coding guidelines from `@adlc5-plan`.

## Output

`quality-report.md` — overall gate status (PASS / FAIL / PASS-WITH-WARNINGS) plus:
- Test results (pass/fail/skip counts, coverage %)
- Linting results (errors/warnings/auto-fixable count)
- Code quality metrics (complexity hotspots, duplication %, unresolved TODOs)
- Standards compliance deviations

## Prerequisites

- Phase 1 (Security Scanning) complete — `security-report.md` exists
- `guides/quality-thresholds.md` loaded before any analysis begins
- Source code available at `src/`

## Phase 2 Process

---

### Step 1: Load Quality Thresholds

Read `guides/quality-thresholds.md` before any analysis. Extract:

| Threshold | Default | Source |
|---|---|---|
| Line coverage target | 80% | `quality-thresholds.md` |
| Branch coverage target | 70% | `quality-thresholds.md` |
| Max cyclomatic complexity per function | 10 | `quality-thresholds.md` |
| Max duplication percentage | 5% | `quality-thresholds.md` |
| Max TODO/FIXME in critical paths | 0 | `quality-thresholds.md` |

Then check if PRT NFRs override any defaults. Read `.prt/{feature}/prt.md` if it exists — the NFRs section may specify tighter or looser thresholds. PRT values always take precedence over defaults.

Record the resolved thresholds in `state.json` under `results.quality.thresholds` so later phases can reference them without re-parsing.

---

### Step 2: Run the Test Suite

**Prefer ADLC5 scripts** (JSON stdout + exit codes; emits telemetry when feature state exists):

```bash
./scripts/run-tests.sh --feature "{feature}"
./scripts/score-coverage.py --feature "{feature}" --threshold {line_coverage_target}
./scripts/run-lint.sh --feature "{feature}"
```

Parse script JSON for pass/fail counts and coverage. Fall back to language-specific commands below when scripts report `skipped`.

**Python (pytest):**

```bash
pytest src/ --tb=short --junit-xml=test-results.xml \
  --cov=src --cov-report=json:coverage.json \
  --cov-report=term-missing
```

Parse `test-results.xml` for: total tests, passed, failed, skipped, errors. Parse `coverage.json` for line/branch coverage per file.

**JavaScript/TypeScript (Jest):**

```bash
npx jest --ci --coverage --coverageReporters=json \
  --json --outputFile=jest-results.json
```

Parse `jest-results.json` for: `numTotalTests`, `numPassedTests`, `numFailedTests`, `numPendingTests`. Parse `coverage/coverage-summary.json` for per-file coverage.

**Java (Maven + JaCoCo):**

```bash
mvn test jacoco:report
```

Parse `target/surefire-reports/*.xml` for test results. Parse `target/site/jacoco/jacoco.xml` for coverage.

**Go:**

```bash
go test ./... -v -json -coverprofile=coverage.out > test-results.json
go tool cover -func=coverage.out > coverage-summary.txt
```

**dotnet:**

```bash
dotnet test --logger "junit;LogFilePath=test-results.xml" \
  --collect:"XPlat Code Coverage"
```

After running, compare overall coverage against the threshold from Step 1. Flag if below target and record the delta. If tests fail with runtime errors (missing env vars, DB not available), document the failure reason and attempt to run unit tests only (skip integration tests) using appropriate flags (`-m "not integration"` for pytest, `--testPathPattern` for Jest).

---

### Step 3: Identify Coverage Gaps

Parse the coverage report to identify under-tested code.

**Priority order for coverage gap analysis:**
1. Files with 0% coverage — never executed by any test
2. Functions/methods with 0% coverage
3. Critical path files with coverage below the branch target
4. API handlers, authentication, payment processing, data access layer — always flag at `High` risk regardless of coverage %

Produce a coverage gap table. Include only files at risk — omit files meeting their targets:

| File | Function | Line Coverage | Branch Coverage | Risk Level |
|---|---|---|---|---|
| `src/auth/login.py` | `validate_token()` | 45% | 30% | High |
| `src/payments/charge.py` | `process_refund()` | 0% | 0% | High |
| `src/utils/cache.py` | `invalidate_key()` | 62% | 55% | Medium |

Risk levels:
- **High:** 0% coverage OR in a critical path (auth, payments, data access) with < 60%
- **Medium:** Below line coverage target but not in a critical path
- **Low:** Below branch coverage target only

---

### Step 4: Run Linter

Detect the project language and run the appropriate linter.

**Python (Ruff — preferred; falls back to flake8):**

```bash
ruff check src/ --output-format=json > lint-results.json
# fallback
flake8 src/ --format=json > lint-results.json
```

**JavaScript/TypeScript (ESLint):**

```bash
npx eslint src/ --format=json > lint-results.json
```

**Java (Checkstyle):**

```bash
mvn checkstyle:check
```

**Go (golangci-lint):**

```bash
golangci-lint run ./... --out-format=json > lint-results.json
```

**dotnet (dotnet-format):**

```bash
dotnet format --verify-no-changes --report lint-results.json
```

From the output, extract:
- Total errors (severity: error)
- Total warnings (severity: warning)
- Auto-fixable count (run `eslint --fix-dry-run` / `ruff --fix-only --dry-run` to determine)

If `auto_fix_enabled: true` in `state.json` and auto-fixable count > 0, offer to apply fixes before finalizing the report. Do not apply fixes silently — always confirm with the user first.

---

### Step 5: Check Code Complexity

Measure cyclomatic complexity per function and flag anything above the threshold.

**Python (radon):**

```bash
radon cc src/ --average --json > complexity.json
```

**JavaScript/TypeScript:**

ESLint `complexity` rule produces complexity data inline with linting (should already be configured in `.eslintrc`). If not configured, add it temporarily:

```json
{ "rules": { "complexity": ["warn", 10] } }
```

**Java (PMD):**

```bash
pmd check -d src/ -R category/java/design.xml/CyclomaticComplexity \
  -f json > pmd-results.json
```

**Go (gocyclo):**

```bash
gocyclo -over 10 ./... > complexity.txt
```

Produce a complexity hotspot table. Include only functions that exceed the threshold:

| File | Function | Cyclomatic Complexity | Threshold | Recommended Action |
|---|---|---|---|---|
| `src/order/processor.py` | `process_order()` | 18 | 10 | Refactor — extract sub-functions |
| `src/auth/permissions.py` | `check_access()` | 14 | 10 | Refactor — reduce conditional depth |

Functions with complexity > 2× threshold (e.g., > 20 when threshold is 10) should be flagged as `FAIL`-level findings rather than warnings.

---

### Step 6: Check Code Duplication

**jscpd works across all languages and is the preferred tool:**

```bash
npx jscpd src/ --reporters json --output duplication-report/
```

From `duplication-report/jscpd-report.json`, extract:
- `statistics.total.percentage` — overall duplication percentage
- `duplicates` array — each entry contains source files, start/end lines, and the duplicated fragment

Flag if duplication percentage exceeds the threshold from Step 1. Produce a duplication summary:

| File A | Lines | File B | Lines | Duplicated Lines |
|---|---|---|---|---|
| `src/api/users.py` | 45–78 | `src/api/groups.py` | 112–145 | 34 |

If duplication > threshold, suggest consolidation: extract the duplicated logic into a shared utility module.

---

### Step 7: Check for TODO/FIXME/HACK Comments

Run a language-agnostic scan across all source files:

```bash
grep -rn "TODO\|FIXME\|HACK\|XXX\|TEMP\|KLUDGE" src/ \
  --include="*.py" --include="*.ts" --include="*.js" \
  --include="*.java" --include="*.go" --include="*.cs"
```

Produce a full table of findings. Mark each with whether it is in a critical path:

| File | Line | Type | Comment | In Critical Path? |
|---|---|---|---|---|
| `src/auth/login.py` | 87 | TODO | `# TODO: add rate limiting` | Yes — auth module |
| `src/utils/cache.py` | 34 | FIXME | `# FIXME: race condition under load` | No |
| `src/payments/charge.py` | 156 | HACK | `# HACK: retry 3x to work around flaky upstream` | Yes — payments |

Critical path definition: any file under `auth/`, `payments/`, `billing/`, `security/`, `database/`, `dal/`, or any file whose name contains `login`, `token`, `credential`, `encrypt`, `decrypt`, `payment`, `charge`, `session`.

All TODO/FIXME/HACK comments in critical paths are **advisory blockers** — they appear in the gate status as warnings and must be acknowledged by the user before proceeding to Phase 3.

---

### Step 8: Standards Compliance Check

Load the coding guidelines for the detected language from the `@adlc5-plan` skill guides directory:

| Language | Guideline File |
|---|---|
| Python | `../adlc5-plan/guides/PYTHON-CODING-GUIDELINES.md` |
| Java | `../adlc5-plan/guides/JAVA-CODING-GUIDELINES.md` |
| TypeScript/React | `../adlc5-plan/guides/REACT-CODING-GUIDELINES.md` |
| Angular | `../adlc5-plan/guides/ANGULAR-CODING-GUIDELINES.md` |

Sample 5–10 representative files (prefer files touched in the current feature). Check for:

**Error handling:** Are exceptions caught and logged, or silently swallowed? Look for bare `except:` / `catch (e) {}` blocks with no logging.

**Logging patterns:** Is structured logging used? Are log messages free of PII (no emails, names, passwords, tokens in log strings)? Are log levels used correctly (DEBUG for trace, INFO for milestones, WARN for recoverable issues, ERROR for failures)?

**Input validation:** Are inputs validated at API entry points before reaching business logic? Look for direct use of request params in queries or commands without sanitization.

**Dependency injection:** Are external dependencies injected (passed in) or hardcoded (instantiated inline)? Hardcoded dependencies make code untestable and environment-specific.

Produce a compliance deviations table:

| File | Line | Deviation | Guideline Reference | Severity |
|---|---|---|---|---|
| `src/api/users.py` | 45 | Exception caught and silently swallowed | Python Guidelines §6.3 | Medium |
| `src/auth/login.py` | 102 | Password logged at DEBUG level | Python Guidelines §7.1 (PII in logs) | High |
| `src/db/queries.py` | 67 | Raw string interpolation in SQL query | Python Guidelines §8.2 | High |

---

### Step 9: Determine Gate Status and Produce quality-report.md

Apply the following decision table to determine the overall gate verdict:

| Condition | Gate Status |
|---|---|
| All tests pass AND coverage ≥ target AND zero lint errors AND no functions above complexity threshold | PASS |
| Tests pass AND coverage ≥ target AND lint warnings only (zero errors) AND medium complexity flagged | PASS-WITH-WARNINGS |
| Any test failures OR coverage < target OR lint errors > 0 OR any function > 2× complexity threshold | FAIL |

If auto-fixable lint errors exist and `auto_fix_enabled: true`, offer to run the appropriate fix command before finalizing the report. Do not auto-apply without user confirmation.

Write `quality-report.md` to `.qa/{feature}/quality-report.md`. The overall verdict must appear at the top of the document in a clearly visible banner. Include all tables produced in Steps 3–8.

Update `state.json`:
```json
{
  "phase_status": { "quality": "completed" },
  "results": {
    "quality": {
      "gate_status": "PASS|FAIL|PASS-WITH-WARNINGS",
      "tests_total": 0,
      "tests_passed": 0,
      "tests_failed": 0,
      "coverage_percentage": 0.0,
      "coverage_target": 80.0,
      "lint_errors": 0,
      "lint_warnings": 0,
      "complexity_violations": 0,
      "duplication_percentage": 0.0,
      "todo_fixme_in_critical_paths": 0
    }
  }
}
```

---

### Step 10: User Confirmation Gate

Present the gate outcome and ask how to proceed before moving to the next phase.

**If PASS:**
> "Quality gate passed. Coverage: {X}%, lint errors: 0, no complexity violations. Ready to proceed to Phase 3 (Performance/Accessibility) or Phase 4 (Compliance)?"

**If PASS-WITH-WARNINGS:**
> "Quality gate passed with warnings.
>
> Warnings: {N} lint warnings, {N} coverage gaps below target, {N} TODOs in critical paths.
>
> These are non-blocking but should be resolved before the next release. Proceed to next phase?"

**If FAIL:**
> "Quality gate failed.
>
> Blocking issues:
> - {N} test failures — see test-results.xml
> - Coverage {X}% is below target {Y}%
> - {N} lint errors in: {file list}
>
> Fix the issues above and re-run Phase 2. Or, if you want to override and proceed, confirm explicitly."

Do not advance to Phase 3 until the user confirms. Record the confirmation in `state.json` as `phase_status.quality_confirmed: true`.
