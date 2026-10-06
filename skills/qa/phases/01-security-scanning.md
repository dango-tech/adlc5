---
name: security-scanning
description: Phase 1 - Security Scanning. Runs SAST, dependency vulnerability audits, IaC scanning, and secret detection. Offers auto-fix for common patterns. Produces security-report.md.
---

# Phase 1: Security Scanning

## Purpose

Surface all security vulnerabilities in application code, dependencies, and infrastructure before deployment. Categorize findings by severity with CWE/CVE references. Offer auto-fix for mechanical issues. Gate progression on zero unresolved critical findings.

## Output

`{workspace}/.qa/{feature-name}/security-report.md` — findings organized by severity (Critical / High / Medium / Low), each with CWE/CVE reference, file path, line number, code snippet, and remediation guidance.

Intermediate artifacts (written to `.qa/{feature-name}/raw/`):
- `sast-findings.json`
- `dep-audit.json`
- `iac-findings.json` (if IaC applicable)
- `secrets-found.json`

## Prerequisites

- Phase 0 complete — `test-plan.md` confirmed and `state.json` written
- `guides/security-scanning-tools.md` loaded (Step 1 below)
- Source code present in `src/`

## Phase 1 Process

### Step 1: Load Tool Reference

Before running any scan, read `guides/security-scanning-tools.md`. Extract:
- Exact CLI invocation for each tool relevant to the detected language stack
- Rule sets to apply per language and framework
- Output format and parsing instructions for each tool's JSON output
- Known false-positive patterns to filter (e.g., Semgrep rules that commonly misfire on test files)

If `guides/security-scanning-tools.md` does not exist, proceed using the invocations documented in this phase file and note the absence in the security report.

---

### Step 2: SAST — Static Application Security Testing

Run SAST for each language detected in Phase 0. Use the primary tool if already configured; fall back to the ad-hoc invocation otherwise.

#### Python

**Primary (if Semgrep configured):**
```bash
semgrep --config=auto \
        --config=p/python \
        --config=p/owasp-top-ten \
        --config=p/secrets \
        --json \
        --output .qa/{feature}/raw/sast-findings.json \
        src/
```

**Fallback (Bandit):**
```bash
bandit -r src/ \
       -f json \
       -o .qa/{feature}/raw/sast-findings.json \
       -ll  # report medium and above; remove for all findings
```

Patterns to flag:
- SQL injection: string formatting or concatenation inside `cursor.execute()`, `session.query()`, raw SQL strings built with `%` or `f""` interpolation
- Hardcoded credentials: assignments matching `password =`, `api_key =`, `secret =` with non-env-var string values
- Unsafe deserialization: `pickle.loads()`, `yaml.load()` without `Loader=yaml.SafeLoader`
- Command injection: `subprocess.run(..., shell=True)` with user-controlled input, `os.system()` with variables
- Path traversal: `open(user_input)`, `os.path.join` with unvalidated user segments
- Weak crypto: `hashlib.md5()` or `hashlib.sha1()` used for password hashing (not checksums)
- `eval()` or `exec()` with dynamic input

#### JavaScript / TypeScript

**Primary (if Semgrep configured):**
```bash
semgrep --config=auto \
        --config=p/javascript \
        --config=p/typescript \
        --config=p/owasp-top-ten \
        --config=p/secrets \
        --json \
        --output .qa/{feature}/raw/sast-findings.json \
        src/
```

**Fallback (ESLint with security plugins):**
```bash
npx eslint \
  --plugin security \
  --plugin no-unsanitized \
  --format json \
  --output-file .qa/{feature}/raw/sast-findings.json \
  "src/**/*.{js,ts,jsx,tsx}"
```

Patterns to flag:
- XSS: `innerHTML`, `outerHTML`, `document.write()` with non-literal values; `dangerouslySetInnerHTML` without sanitization via DOMPurify
- SQL injection: template literals or string concatenation inside query functions (`db.query(\`SELECT ... ${userInput}\``)
- SSRF: user-controlled values passed directly to `fetch()`, `axios.get()`, `http.request()` without allow-list validation
- Prototype pollution: `Object.assign({}, userInput)`, `_.merge({}, userInput)` without input validation
- `eval()`, `new Function(userInput)`, `setTimeout(stringArg)`
- ReDoS: catastrophic backtracking regex patterns applied to user input
- JWT without verification: `jwt.decode()` used instead of `jwt.verify()`

#### Java

```bash
semgrep --config=auto \
        --config=p/java \
        --config=p/owasp-top-ten \
        --json \
        --output .qa/{feature}/raw/sast-findings.json \
        src/
```

Patterns to flag:
- SQL injection: string concatenation inside `Statement.execute()`, `createQuery()`, `createNativeQuery()`
- XXE: `DocumentBuilderFactory`, `SAXParserFactory`, `XMLInputFactory` without disabling external entities (`FEATURE_SECURE_PROCESSING` not set)
- Insecure deserialization: `ObjectInputStream.readObject()` with untrusted data
- Path traversal: `new File(userInput)`, `Paths.get(userInput)` without canonicalization
- Weak random: `Math.random()` or `java.util.Random` used for security tokens (use `SecureRandom`)
- Open redirect: `response.sendRedirect(userInput)` without validation

#### Go

```bash
semgrep --config=auto \
        --config=p/golang \
        --json \
        --output .qa/{feature}/raw/sast-findings-semgrep.json \
        src/

# gosec for Go-specific security issues
gosec -fmt=json -out=.qa/{feature}/raw/sast-findings-gosec.json ./...
```

Patterns to flag: hardcoded credentials, `exec.Command` with user-controlled args, `math/rand` instead of `crypto/rand` for tokens, unvalidated redirects, integer overflow in security-relevant calculations.

#### OWASP Top 10 Coverage Checklist

After running SAST, verify coverage against each OWASP Top 10 category. Mark each as Covered, Partial, or Not covered:

| OWASP ID | Category | Coverage Status |
|---|---|---|
| A01 | Broken Access Control | |
| A02 | Cryptographic Failures | |
| A03 | Injection (SQL, NoSQL, OS, LDAP) | |
| A04 | Insecure Design | |
| A05 | Security Misconfiguration | |
| A06 | Vulnerable and Outdated Components | |
| A07 | Identification and Authentication Failures | |
| A08 | Software and Data Integrity Failures | |
| A09 | Security Logging and Monitoring Failures | |
| A10 | Server-Side Request Forgery (SSRF) | |

Include this table in `security-report.md`. Categories marked "Not covered" by automated tools should be noted as requiring manual review.

**For each SAST finding, record:**
- CWE ID (e.g., CWE-89 for SQL Injection)
- File path and line number
- Severity (Critical / High / Medium / Low)
- Short description and affected code snippet (2 lines before and after the finding)
- Remediation guidance (specific, not generic — reference the exact fix for the pattern found)

---

### Step 3: Dependency Vulnerability Scanning

Run the appropriate audit tool for each dependency manifest detected in Phase 0.

#### Python

```bash
# pip-audit (preferred — uses OSV database)
pip-audit \
  --format=json \
  --output=.qa/{feature}/raw/dep-audit.json \
  --require-hashes=false

# Fallback: safety
safety check --json > .qa/{feature}/raw/dep-audit.json
```

#### Node.js

```bash
# npm
npm audit --json > .qa/{feature}/raw/dep-audit.json

# yarn
yarn audit --json > .qa/{feature}/raw/dep-audit.json

# pnpm
pnpm audit --json > .qa/{feature}/raw/dep-audit.json
```

Note: `npm audit` exit code 1 on findings is expected — do not treat as a tool failure.

#### Java (Maven)

```bash
mvn org.owasp:dependency-check-maven:check \
  -Dformat=JSON \
  -DfailBuildOnCVSS=0 \
  -DoutputDirectory=.qa/{feature}/raw/
```

#### Java (Gradle)

```bash
gradle dependencyCheckAnalyze \
  --project-prop dependencyCheckFormat=JSON \
  --project-prop dependencyCheckOutputDirectory=.qa/{feature}/raw/
```

#### Go

```bash
govulncheck -json ./... > .qa/{feature}/raw/dep-audit.json
```

#### .NET

```bash
dotnet list package --vulnerable --include-transitive --format json \
  > .qa/{feature}/raw/dep-audit.json
```

**For each dependency vulnerability, record:**

| Field | Value |
|---|---|
| CVE ID | e.g., CVE-2024-12345 |
| Package | e.g., `requests` |
| Installed version | e.g., `2.27.1` |
| Patched version | e.g., `2.31.0` |
| Severity | Critical / High / Medium / Low |
| CVSS score | e.g., 9.8 |
| Description | One-sentence summary |
| Remediation | Exact upgrade command |

**Filtering rule:** Report all Critical and High findings regardless of fix availability. For Medium and Low, only report findings that have a fix available. Unfixable Medium/Low findings are summarized as a count ("N medium/low findings with no fix available — omitted from detailed report").

---

### Step 4: IaC Security Scanning

**Only execute if `context.has_iac: true` in `state.json` (i.e., `infra/` directory exists).**

#### Checkov (multi-cloud, recommended)

```bash
checkov \
  -d infra/ \
  --output json \
  --output-file-path .qa/{feature}/raw/ \
  --compact \
  --quiet
# Output: .qa/{feature}/raw/results_checkov.json
```

#### tfsec (Terraform-specific)

```bash
tfsec infra/ \
  --format json \
  --out .qa/{feature}/raw/tfsec-findings.json \
  --no-color
```

#### cfn-nag (CloudFormation — if `.yaml` or `.json` templates present under `infra/`)

```bash
cfn_nag_scan \
  --input-path infra/ \
  --output-format json \
  > .qa/{feature}/raw/cfn-nag-findings.json
```

#### De-duplication Against the Infra Validation Baseline

If `.infra/{feature}/infra-validation-report.md` exists (recorded in `state.json` under `context.baseline_iac_findings`):

1. Load the baseline finding IDs (checkov check IDs, tfsec rule IDs, or resource path + issue combinations)
2. For each finding in current scan output: if it matches a baseline finding, mark it as `already_reported: true` — exclude from `security-report.md` but include in a separate "Previously Reported (Baseline)" appendix section
3. Only NEW findings (not in baseline) appear in the main report body

This prevents surfacing duplicate work and keeps the security report focused on what is **new**.

#### IaC Categories to Flag

| Category | Examples |
|---|---|
| Overly permissive IAM | `"Action": "*"`, `"Resource": "*"` on sensitive services (S3, Secrets Manager, KMS, IAM itself) |
| Unencrypted storage | S3 without `server_side_encryption_configuration`, unencrypted EBS volume, unencrypted RDS instance, unencrypted SQS queue |
| Public exposure | S3 with `block_public_acls = false`, security group with `cidr_blocks = ["0.0.0.0/0"]` on port 22/3389/5432/3306 |
| Missing logging | CloudTrail not enabled, S3 access logging disabled, VPC Flow Logs not configured, API Gateway access logging absent |
| Missing backup | RDS without `backup_retention_period`, DynamoDB without PITR enabled |
| Hardcoded secrets | `password =` or `secret =` literals in Terraform variable defaults or resource arguments |

---

### Step 5: Secret Detection

Run secret detection tools regardless of what was found in SAST — these tools use different techniques (entropy analysis, pattern matching against known credential formats).

#### gitleaks

```bash
# Scan working tree and git history
gitleaks detect \
  --source . \
  --report-format json \
  --report-path .qa/{feature}/raw/secrets-found.json \
  --no-git=false \
  --verbose
```

#### truffleHog

```bash
trufflehog filesystem . \
  --json \
  --only-verified \
  > .qa/{feature}/raw/trufflehog-findings.json
```

#### Manual Regex Patterns

For environments where neither tool is available, scan source and config files directly:

```bash
# Credential-like assignments
grep -rn --include="*.py" --include="*.js" --include="*.ts" \
  --include="*.yaml" --include="*.yml" --include="*.env" \
  -iE "(aws_secret|api_key|apikey|password|secret|token|private_key)\s*=\s*['\"][^'\"]{8,}['\"]" \
  . 2>/dev/null | grep -v "test\|spec\|mock\|placeholder\|example\|changeme\|your_"

# Private key headers
grep -rn "BEGIN RSA PRIVATE KEY\|BEGIN OPENSSH PRIVATE KEY\|BEGIN EC PRIVATE KEY" . 2>/dev/null

# AWS key patterns
grep -rn -E "AKIA[0-9A-Z]{16}" . 2>/dev/null

# GCP service account files
find . -name "*.json" | xargs grep -l '"type": "service_account"' 2>/dev/null
```

#### .gitignore Audit

```bash
# Check if sensitive files are excluded from git tracking
for f in .env .env.local .env.production .env.staging "*.pem" "*.key" "*service-account*.json"; do
  grep -q "$f" .gitignore 2>/dev/null || echo "MISSING from .gitignore: $f"
done

# Check if .env files are already tracked in git
git ls-files | grep -E "\.env($|\.[a-z]+$)" 2>/dev/null
```

**For each secret found, record:**
- File path and line number
- Pattern matched (e.g., "AWS access key pattern", "Generic API key assignment")
- Whether it appears in git history (indicates credential must be rotated, not just removed from HEAD)
- Severity: Critical if in committed code or git history; High if in working tree only
- Remediation: Revoke the credential immediately + move to environment variable or secrets manager + purge from git history (`git filter-repo` or BFG)

---

### Step 6: Auto-Fix Offer

**Only execute if `context.auto_fix_enabled: true` in `state.json`.**

After completing all scans (Steps 2–5), collect all findings that have a mechanical, safe auto-fix. Present the consolidated list before applying anything.

Categories of auto-fixable issues:

| Issue Type | Fix Action | Risk Level |
|---|---|---|
| npm/yarn safe upgrades | `npm audit fix` (without `--force`) | Low |
| pip safe upgrades | `pip install --upgrade {package}` to patched version | Low |
| ESLint auto-fixable rules | `eslint --fix src/` | Low |
| Ruff auto-fixable rules | `ruff check --fix src/` | Low |
| Black / Prettier formatting | `black src/` or `prettier --write src/` | Low |
| Hardcoded API key → env var | Replace literal with `os.environ.get("KEY_NAME")` or `process.env.KEY_NAME` | Medium — requires env var setup |
| Missing S3 encryption block | Add `server_side_encryption_configuration` to Terraform resource | Medium — IaC change |
| Missing `block_public_acls` | Add `aws_s3_bucket_public_access_block` resource | Medium — IaC change |

Present the list and prompt:

```
I found {N} auto-fixable issues across {categories}. How would you like to proceed?

Auto-fixable issues:
  1. {N} npm packages with safe upgrades (npm audit fix)
  2. {N} ESLint auto-fixable rule violations (eslint --fix)
  3. Hardcoded API key in src/config.py:42 → move to env var
  4. Missing S3 encryption in infra/modules/storage/main.tf:18

Options:
  1. Apply all auto-fixes
  2. Apply each fix one at a time (I will show the diff before writing)
  3. Skip auto-fix — I will fix manually

Enter 1, 2, or 3:
```

If option 1 or 2 is selected:
- For each fix: show the exact file path, the before/after diff, then write the change
- Record every applied fix in `state.json` under `results.security.auto_fixes_applied` with: file path, fix type, description
- Add an "Auto-Fixes Applied" section to `security-report.md` listing every change

---

### Step 7: Categorize and Produce security-report.md

Write `{workspace}/.qa/{feature-name}/security-report.md` with the following structure.

**Severity definitions:**

| Severity | Criteria | Deployment Impact |
|---|---|---|
| Critical | Active secrets committed to code or history; CVSS ≥ 9.0 vulnerabilities with public exploits; SQL injection / RCE in reachable code paths; public cloud storage containing sensitive data | Blocks deployment — must resolve |
| High | CVSS 7.0–8.9; insecure direct object references; missing authentication on API endpoints; overly permissive IAM (`*` on sensitive resources) | Should fix before deploy; user must explicitly accept risk to proceed |
| Medium | CVSS 4.0–6.9; non-critical misconfigurations; low-probability attack paths; advisory IaC issues | Fix in next sprint; logged in deployment clearance |
| Low | CVSS < 4.0; defensive hardening recommendations; informational findings | Informational only |

**security-report.md structure:**

```markdown
# Security Report: {feature-name}

Date: {date}
Phase: 1 — Security Scanning
Tools run: {list}

## Summary

| Severity | Count | Blocking |
|---|---|---|
| Critical | N | Yes |
| High | N | No (risk acceptance required) |
| Medium | N | No |
| Low | N | No |

## OWASP Top 10 Coverage
[table from Step 2]

## Critical Findings

### CRIT-001: {Short title}
- **CWE:** CWE-{ID} — {CWE name}
- **File:** `src/path/to/file.py:42`
- **Tool:** Semgrep / Bandit / Manual
- **Description:** {One paragraph explaining the vulnerability and its exploitability}
- **Code Snippet:**
  ```
  [code context]
  ```
- **Remediation:** {Specific fix — not generic advice}

[repeat for each critical finding]

## High Findings
[same structure]

## Medium Findings
[same structure — can be condensed if many]

## Low Findings
[list format acceptable]

## Dependency Vulnerabilities
[table: CVE, Package, Installed, Patched, Severity, CVSS, Remediation command]

## IaC Findings (New — not in the baseline report)
[table: Rule ID, Resource, Issue, Severity, Remediation]

## Previously Reported (Baseline)
[list of finding IDs already in infra-validation-report.md — not repeated in detail]

## Secrets Found
[table: File, Line, Pattern, Git History, Severity, Action Required]

## Auto-Fixes Applied
[table: File, Fix Type, Description — or "No auto-fixes applied"]
```

---

### Step 8: Gate Check

After presenting `security-report.md`, apply the gate rules:

**If zero critical findings:**
```
Security scan complete.

Summary: {N} high, {N} medium, {N} low findings.
Report: .qa/{feature-name}/security-report.md

Ready to proceed to Phase 2: Quality Gate?
```

**If critical findings exist:**
```
⛔ Security scan found {N} critical finding(s). Deployment is blocked.

These must be resolved before Phase 2 can begin:
  [list each critical finding — CRIT-001, CRIT-002, ...]

Options:
  1. Apply available auto-fixes (covers {N} of {N} critical findings)
  2. I will fix manually — re-run Phase 1 when ready
  3. Show me the full security report for details
```

Do not proceed to Phase 2 until all critical findings are resolved (or explicitly overridden by the user with a documented reason, which is recorded in `state.json` under `results.security.critical_overrides`).

**If only high findings exist (no criticals):**
```
Security scan complete with {N} high finding(s).

High findings are not blocking but represent real risk. How would you like to proceed?
  1. Fix high findings now (recommended)
  2. Accept the risk and continue to Phase 2 (risks will be logged in deployment clearance)
  3. Show me the full report to decide finding-by-finding
```

If the user accepts risk on high findings, record each accepted finding in `state.json`:

```json
{
  "results": {
    "security": {
      "critical_count": 0,
      "high_count": 3,
      "medium_count": 7,
      "low_count": 12,
      "auto_fixes_applied": [],
      "accepted_risk_findings": ["HIGH-001", "HIGH-002"],
      "gate_passed": true,
      "gate_passed_at": "{ISO timestamp}"
    }
  }
}
```

Update `state.json` phase to `"phase": "security-scanning"`, `"status": "complete"` before signaling readiness for Phase 2.
