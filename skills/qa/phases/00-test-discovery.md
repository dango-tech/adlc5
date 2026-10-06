---
name: test-discovery
description: Phase 0 - Test Discovery. Scans the codebase and upstream artifacts to determine which test categories apply and produces a confirmed test plan before any scanning begins.
---

# Phase 0: Test Discovery

## Purpose

Front-load all analysis so Phases 1–4 can run without back-and-forth. Identify which test categories are applicable, what tools are already configured, what gaps exist, and what the execution priority order should be. The agent reads this phase to know exactly what to scan, detect, and produce before any security or quality scanning begins.

## Output

`{workspace}/.qa/{feature-name}/test-plan.md` — a confirmed test plan covering:
- Applicable test categories with rationale
- Detected tools (already configured) vs. recommended tools (invoked ad-hoc)
- Identified gaps with severity (blocking vs. advisory)
- Execution priority order
- Estimated scope (file counts, test file counts)

## Prerequisites

- Application code exists in `src/`
- IaC in `infra/`, @adlc5-plan design docs, and @prt docs are optional enrichments — their absence is noted and defaults are applied

## Phase 0 Process

### Step 1: Read Upstream Design Context

Before scanning the codebase, read all available upstream artifacts to extract targets, constraints, and compliance requirements that shape which tests apply.

**Read `.adlc5/{feature}/design/1c-operations.md`** if it exists. Extract:
- Security controls defined (auth mechanisms, encryption requirements, PII handling rules)
- Performance targets: p95 latency target (ms), RPS/throughput targets, error rate thresholds
- Compliance requirements: data residency, HIPAA/SOC2/PCI signals, encryption mandates

**Read `.prt/{feature}/prt.md`** if it exists. Locate the NFRs section. Extract:
- Coverage targets (line, branch, function thresholds)
- Accessibility requirements (WCAG 2.1 AA/AAA, Section 508)
- Load test thresholds (concurrent users, sustained load duration, spike test params)
- Any explicitly listed non-functional requirements that map to test categories

**Read `.infra/{feature}/infra-validation-report.md`** if it exists. Extract:
- IaC security findings already reported upstream
- Store these as `baseline_iac_findings` in state — Phase 1 will de-duplicate against this list so the security report surfaces **new** findings only, not findings the infra validation step already caught

**If none of these files exist**, record the following defaults and proceed:

| Parameter | Default |
|---|---|
| Coverage target | 80% line coverage |
| Security scope | OWASP Top 10 |
| Performance testing | Skipped (no targets defined) |
| Accessibility | Depends on UI detection in Step 5 |
| Compliance requirements | None specified |

Write these defaults to `state.json` under `context.defaults_applied: true`.

---

### Step 2: Detect Test Frameworks

Scan for config files and dependency manifests to identify what test infrastructure is already in place. For each framework, check the detection signals listed below.

| Framework | Detection Signals | Status |
|---|---|---|
| pytest | `pytest.ini`, `setup.cfg [tool:pytest]`, `pyproject.toml [tool.pytest.ini_options]`, `requirements*.txt` contains `pytest` | Detected / Not found |
| Jest | `jest.config.js`, `jest.config.ts`, `jest.config.mjs`, `package.json "jest"` key | Detected / Not found |
| Vitest | `vitest.config.ts`, `vitest.config.js`, `package.json "vitest"` key | Detected / Not found |
| JUnit 5 | `pom.xml` contains `junit-jupiter`, `build.gradle` contains `testImplementation 'org.junit.jupiter'` | Detected / Not found |
| xUnit | `*.csproj` contains `PackageReference Include="xunit"` | Detected / Not found |
| Mocha | `package.json "mocha"` key or `.mocharc.*` | Detected / Not found |
| Go test | `*_test.go` files present anywhere under `src/` | Detected / Not found |
| RSpec | `Gemfile` contains `gem 'rspec'`, `spec/` directory present | Detected / Not found |
| Playwright | `playwright.config.ts`, `@playwright/test` in `package.json` | Detected / Not found |
| Cypress | `cypress.config.ts`, `cypress.config.js`, `cypress/` directory | Detected / Not found |
| Selenium | `selenium-webdriver` in `package.json` or `pom.xml`, `conftest.py` with selenium fixture | Detected / Not found |
| k6 | `k6` binary reference in CI config, `*.k6.js` or `load-test*.js` files | Detected / Not found |
| Locust | `locustfile.py` present, `locust` in `requirements*.txt` | Detected / Not found |
| Artillery | `artillery.yml`, `artillery` in `package.json` devDependencies | Detected / Not found |

Scan commands to use:

```bash
# Find all test config files in root and subdirectories
find . -maxdepth 3 -name "pytest.ini" -o -name "jest.config.*" -o -name "vitest.config.*" \
  -o -name ".mocharc.*" -o -name "playwright.config.*" -o -name "cypress.config.*" \
  -o -name "*.k6.js" -o -name "locustfile.py" -o -name "artillery.yml" 2>/dev/null

# Count test files
find src/ -name "*test*" -o -name "*spec*" | grep -E "\.(py|js|ts|java|go|rb|cs)$" | wc -l
```

Record detected frameworks in `state.json` under `context.test_frameworks`.

---

### Step 3: Detect Security and Quality Tools

Scan for existing security and linting tool configurations to understand what's pre-wired vs. what must be invoked ad-hoc.

| Tool | Detection Signals | Category |
|---|---|---|
| Semgrep | `.semgrep.yml`, `.semgrep/` directory, `semgrep` in CI config | SAST |
| Bandit | `bandit` in `requirements*.txt`, `.bandit` config file | SAST (Python) |
| SonarQube | `sonar-project.properties`, `sonar-scanner.properties` | SAST |
| CodeQL | `.github/workflows/` contains `codeql` action | SAST |
| Snyk | `.snyk` file, `snyk` in CI config YAML | Dependency scan |
| pip-audit | `pip-audit` in `requirements*.txt` or CI config | Dependency scan (Python) |
| npm audit | Built-in if `package.json` present | Dependency scan (Node.js) |
| OWASP Dependency-Check | `pom.xml` contains `dependency-check-maven` | Dependency scan (Java) |
| govulncheck | `govulncheck` in CI config | Dependency scan (Go) |
| gitleaks | `.gitleaks.toml`, `gitleaks` in CI config | Secret detection |
| truffleHog | `trufflesecurity/trufflehog` action in CI, `trufflehog` in CI config | Secret detection |
| detect-secrets | `.secrets.baseline` file present | Secret detection |
| tfsec | `tfsec` in CI config, `.tfsec/` directory | IaC scan |
| checkov | `.checkov.yml`, `bridgecrew/checkov` in CI config | IaC scan |
| cfn-nag | `cfn_nag` in CI config, `cfn-nag` gem in Gemfile | IaC scan (CloudFormation) |
| ESLint | `.eslintrc.*`, `.eslintrc.json`, `eslint.config.*`, `eslint` in `package.json` | Linting (JS/TS) |
| Prettier | `.prettierrc`, `.prettierrc.json`, `prettier.config.*` | Formatting (JS/TS) |
| Ruff | `ruff.toml`, `pyproject.toml [tool.ruff]` | Linting (Python) |
| Flake8 | `.flake8`, `setup.cfg [flake8]`, `flake8` in `requirements*.txt` | Linting (Python) |
| Black | `pyproject.toml [tool.black]`, `black` in `requirements*.txt` | Formatting (Python) |
| Checkstyle | `checkstyle.xml`, Maven `checkstyle` plugin in `pom.xml` | Linting (Java) |
| SpotBugs | `pom.xml` contains `spotbugs`, `build.gradle` contains `spotbugs` | Static analysis (Java) |
| golangci-lint | `.golangci.yml`, `.golangci.toml` | Linting (Go) |
| dotnet-format | `.editorconfig` with C# rules, `dotnet format` in CI | Formatting (.NET) |

```bash
# Detect CI config files to scan for tool references
find . -maxdepth 3 -name ".github" -type d && ls .github/workflows/ 2>/dev/null
find . -maxdepth 2 -name ".gitlab-ci.yml" -o -name "Jenkinsfile" -o -name "azure-pipelines.yml" 2>/dev/null
```

Record detected tools in `state.json` under `context.security_tools` and `context.quality_tools`.

---

### Step 4: Detect Coverage Configuration

Identify whether coverage is already configured and what threshold is set. If no threshold is found, the default from `guides/quality-thresholds.md` applies.

**Python — pytest-cov / coverage.py:**
```bash
# Check for coverage config
cat .coveragerc 2>/dev/null
grep -A 10 "\[tool.coverage" pyproject.toml 2>/dev/null
grep "addopts" pytest.ini pyproject.toml setup.cfg 2>/dev/null | grep "cov"
```
Look for `fail_under` in `[coverage:report]` or `[tool.coverage.report]`. Note the threshold if found.

**JavaScript/TypeScript — Jest / Vitest:**
```bash
# Jest coverage threshold
grep -A 10 "coverageThreshold" jest.config.* package.json 2>/dev/null
# Vitest
grep -A 10 "coverage" vitest.config.* 2>/dev/null
```
Look for `global.lines`, `global.branches`, `global.functions`, `global.statements` thresholds.

**Java — JaCoCo:**
```bash
# Maven
grep -A 20 "jacoco" pom.xml 2>/dev/null | grep -E "minimum|counter|value"
# Gradle
grep -A 10 "jacocoTestCoverageVerification" build.gradle 2>/dev/null
```

**Go:**
```bash
# Check for coverage flags in Makefile or CI
grep -r "coverprofile\|cover" Makefile .github/workflows/ 2>/dev/null
```

Record findings in state.json:

```json
{
  "context": {
    "coverage": {
      "tool": "pytest-cov",
      "configured_threshold": 85,
      "threshold_source": ".coveragerc",
      "applying_default": false
    }
  }
}
```

---

### Step 5: Determine Applicable Test Categories

Apply the decision rules below for each category. Record the decision and rationale in the test plan.

| Category | Applies When | Default Decision |
|---|---|---|
| Unit tests | Always — source files exist | ✅ Always run |
| Integration tests | `implement-3-integrate` ran OR integration test files exist (`*integration*`, `*e2e*` in `tests/`) OR multiple service boundaries detected | ✅/❌ + rationale |
| E2E tests | E2E framework detected (Playwright, Cypress, Selenium) | ✅/❌ + rationale |
| SAST | Always | ✅ Always run |
| Dependency vulnerability scan | Dependency manifest present (`requirements*.txt`, `package.json`, `pom.xml`, `go.mod`, `Gemfile`, `*.csproj`) | ✅ if manifest found, ❌ with note if absent |
| IaC security scan | `infra/` directory exists | ✅/❌ |
| Secret detection | Always | ✅ Always run |
| Load testing | Performance targets found in `.prt/{feature}/prt.md` NFRs OR `.adlc5/{feature}/design/1c-operations.md` | ✅/❌ + target values (p95 latency, RPS) |
| Accessibility | UI-facing feature detected: `package.json` contains React/Angular/Vue/Next.js/Svelte, OR HTML/JSX/TSX files present under `src/` | ✅/❌ |
| Bundle size analysis | Frontend project detected: `package.json` with React/Angular/Vue/Next.js, build output configured | ✅/❌ |
| Compliance check | Compliance requirements found in `.prt/{feature}/prt.md` OR regulated industry signals (HIPAA, PCI, SOC2, GDPR keywords in docs/comments) | ✅/❌ |

**Service boundary detection heuristics** (for integration test decision):
```bash
# Multiple service clients = integration tests warranted
grep -r "httpx\|requests\|axios\|fetch\|grpc\|rabbitmq\|kafka\|boto3\|redis" src/ 2>/dev/null | wc -l
# Database access = integration tests warranted
grep -r "psycopg2\|sqlalchemy\|mongoose\|prisma\|hibernate\|gorm" src/ 2>/dev/null | wc -l
```

**Frontend detection:**
```bash
grep -E '"react"|"vue"|"@angular/core"|"next"|"svelte"' package.json 2>/dev/null
find src/ -name "*.jsx" -o -name "*.tsx" | head -5 2>/dev/null
```

Record each category decision and rationale in `state.json` under `context.applicable_categories`.

---

### Step 6: Identify Gaps

Gaps are test categories that **should** exist but don't — or configurations that are missing and would cause scan failures or unreliable results. Record each gap with a severity level.

**Blocking gaps** (will prevent a phase from running correctly):
- No dependency manifest found → dependency scanning cannot run → record as blocking if SAST finds import statements with third-party packages
- No test files found in `src/` → unit test phase has nothing to run → record as blocking

**Advisory gaps** (informational — surfaced in report but don't block execution):
- No integration test suite despite detecting 3+ external service clients
- No coverage threshold configured → will use default (80%) — note this as advisory
- No secret scanning config despite `.env` files present in the repo
- No performance test despite an explicit SLA target found in PRT NFRs
- No accessibility tests despite frontend framework detected
- E2E framework absent despite feature described as user-facing in PRT

For each gap, record:

```
| Gap | Severity | Recommended Action |
|---|---|---|
| No integration tests | Advisory | Add pytest-docker or testcontainers for DB/service integration |
| No coverage threshold | Advisory | Add fail_under=80 to .coveragerc |
| .env not in .gitignore | Blocking | Add .env to .gitignore immediately; check git log for committed secrets |
```

Write gap list to `state.json` under `results.discovery.gaps`.

---

### Step 7: Produce test-plan.md

Write `{workspace}/.qa/{feature-name}/test-plan.md` using the structure below. Do not use a template file if one doesn't exist — generate the full document inline.

```markdown
# Test Plan: {feature-name}

Generated: {date}
Feature: {feature-name}

## Upstream Context

| Source | Status | Key Extractions |
|---|---|---|
| .adlc5/{feature}/design/1c-operations.md | Found / Not found | [security controls, perf targets] |
| .prt/{feature}/prt.md | Found / Not found | [NFRs, coverage target, a11y reqs] |
| .infra/{feature}/infra-validation-report.md | Found / Not found | [N baseline IaC findings noted] |

## Detected Test Infrastructure

### Test Frameworks
[table from Step 2 — Detected only]

### Security & Quality Tools
[table from Step 3 — Detected only]

### Coverage Configuration
- Tool: {tool}
- Configured threshold: {X}% (or: "None — applying default: 80%")

## Applicable Test Categories

| Category | Decision | Tools | Rationale |
|---|---|---|---|
| Unit tests | ✅ Run | pytest (42 test files) | Always applicable |
| SAST | ✅ Run | Semgrep (configured), bandit (ad-hoc) | Always applicable |
| ... | | | |

## Test Gaps

| Gap | Severity | Phase | Recommendation |
|---|---|---|---|
| No integration tests | Advisory | Phase 2 | Add testcontainers or pytest-docker |
| ... | | | |

## Execution Order

1. Phase 1: Security Scanning — SAST → Dependency Scan → IaC Scan → Secret Detection
2. Phase 2: Quality Gate — Unit Tests → Coverage → Linting → Complexity
3. Phase 3: Performance & Accessibility (if applicable)
4. Phase 4: Compliance — Aggregate → Deployment Clearance

## Scope Estimate

| Category | Scope |
|---|---|
| Source files to scan | {N} files under src/ |
| Test files to run | {N} test files |
| IaC files | {N} files under infra/ (or N/A) |
| Dependency manifests | {list} |
```

---

### Step 8: User Confirmation Gate

After writing `test-plan.md`, present a summary to the user and wait for confirmation before proceeding to Phase 1.

Format the summary as follows:

```
Test Discovery complete. Here is the confirmed test plan:

Applicable categories ({N}):
  ✅ Unit tests (pytest — {N} test files detected)
  ✅ SAST (Semgrep — already configured + bandit ad-hoc)
  ✅ Dependency scanning (pip-audit)
  ✅ IaC scanning (checkov — infra/ present)
  ✅ Secret detection (gitleaks patterns)
  ✅ Load testing (p95 < 200ms target from PRT)
  ❌ Accessibility (skipped — no UI framework detected)

Gaps identified ({N}):
  ⚠️  [Advisory] No integration test suite detected despite {N} external service clients
  ⚠️  [Advisory] No coverage threshold configured — will apply default (80%)

Upstream baseline: {N} baseline IaC findings already logged — Phase 1 will report new findings only.

Full plan written to: .qa/{feature-name}/test-plan.md

Ready to proceed to Phase 1: Security Scanning? (yes / no / adjust plan)
```

If the user requests adjustments (e.g., "skip load testing", "add accessibility"), update `test-plan.md` and `state.json` accordingly before proceeding.

Write the final confirmed state to `state.json`:

```json
{
  "phase": "test-discovery",
  "status": "complete",
  "context": {
    "feature_name": "{feature-name}",
    "has_iac": true,
    "is_ui_facing": false,
    "auto_fix_enabled": true,
    "defaults_applied": false,
    "test_frameworks": ["pytest"],
    "security_tools": ["semgrep"],
    "quality_tools": ["ruff", "black"],
    "coverage": {
      "tool": "pytest-cov",
      "configured_threshold": 80,
      "threshold_source": "default"
    },
    "applicable_categories": ["unit", "sast", "dependency", "iac", "secrets"],
    "baseline_iac_findings": []
  },
  "results": {
    "discovery": {
      "test_file_count": 42,
      "source_file_count": 87,
      "gaps": []
    }
  }
}
```
