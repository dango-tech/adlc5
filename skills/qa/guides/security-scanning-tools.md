---
name: security-scanning-tools
description: Tool reference for @qa Phase 1 security scanning. Covers SAST tools, dependency scanners, IaC scanners, and secret detectors with CLI invocations, output formats, and false-positive guidance.
---

# Security Scanning Tools Reference

Load this guide before Phase 1. It contains all CLI invocations, output parsing keys, and false-positive suppression patterns for every tool category used in security scanning.

---

## 1. SAST Tools

### Semgrep (preferred — multi-language, CI-friendly)

**When to prefer:** Default choice for Python, JavaScript, TypeScript, Go, Java, Ruby, and mixed-language codebases. Fastest to set up with no language-specific configuration.

**Installation:**
```bash
pip install semgrep
# or
brew install semgrep
```

**CLI invocation:**
```bash
semgrep \
  --config=auto \
  --config=p/owasp-top-ten \
  --config=p/secrets \
  --config=p/jwt \
  --json \
  -o findings.json \
  src/
```

Add a language-specific ruleset alongside `p/owasp-top-ten`:

| Language | Additional flag |
|----------|----------------|
| Python | `--config=p/python` |
| JavaScript | `--config=p/javascript` |
| TypeScript | `--config=p/typescript` |
| Java | `--config=p/java` |
| Go | `--config=p/golang` |

**Output format — key fields to extract:**
```json
{
  "results": [
    {
      "check_id": "python.lang.security.audit.hardcoded-password",
      "path": "src/auth/config.py",
      "start": { "line": 42 },
      "extra": {
        "severity": "ERROR",
        "message": "Hardcoded password found"
      }
    }
  ]
}
```

**Severity mapping:** `ERROR` → High/Critical, `WARNING` → Medium, `INFO` → Low

---

### Bandit (Python-specific)

**When to prefer:** Python-only codebases; complements Semgrep for deeper Python AST analysis.

**Installation:**
```bash
pip install bandit
```

**CLI invocation:**
```bash
# Medium and high severity only (recommended default)
bandit -r src/ -f json -o bandit-findings.json -ll

# Include low severity findings
bandit -r src/ -f json -o bandit-findings.json -l
```

Note: `-ll` = medium + high only. `-l` = low + medium + high. Use `-ll` for gate decisions; use `-l` for full advisory reports.

**Output format — key fields:**
```json
{
  "results": [
    {
      "test_id": "B105",
      "test_name": "hardcoded_password_string",
      "filename": "src/auth/utils.py",
      "line_number": 17,
      "issue_severity": "HIGH",
      "issue_confidence": "MEDIUM",
      "issue_text": "Possible hardcoded password: 'admin123'"
    }
  ]
}
```

---

### ESLint Security Plugins (JavaScript / TypeScript)

**When to prefer:** JavaScript/TypeScript projects that already have ESLint configured. Integrates into existing lint runs.

**Installation:**
```bash
npm install --save-dev eslint-plugin-security eslint-plugin-no-secrets
```

**`.eslintrc.json` configuration to add:**
```json
{
  "plugins": ["security", "no-secrets"],
  "extends": ["plugin:security/recommended"],
  "rules": {
    "no-secrets/no-secrets": ["error", { "tolerance": 4.2 }]
  }
}
```

**CLI invocation:**
```bash
eslint src/ --ext .js,.ts,.jsx,.tsx --format json -o eslint-security.json
```

**Output format — key fields:**
```json
[
  {
    "filePath": "src/api/handler.ts",
    "messages": [
      {
        "ruleId": "security/detect-non-literal-regexp",
        "severity": 2,
        "message": "Non-literal argument to RegExp Constructor",
        "line": 34,
        "column": 18
      }
    ]
  }
]
```

---

### gosec (Go-specific)

**When to prefer:** Go codebases; provides Go-aware security checks beyond what Semgrep covers (e.g., `G304` file path injection, `G401` weak crypto).

**Installation:**
```bash
go install github.com/securego/gosec/v2/cmd/gosec@latest
```

**CLI invocation:**
```bash
gosec -fmt=json -out=gosec-findings.json ./...
```

**Output format — key fields:**
```json
{
  "Issues": [
    {
      "rule_id": "G304",
      "details": "Potential file inclusion via variable",
      "file": "internal/fileserver/handler.go",
      "line": "89",
      "severity": "HIGH",
      "confidence": "HIGH",
      "cwe": { "id": "22", "url": "https://cwe.mitre.org/data/definitions/22.html" }
    }
  ]
}
```

---

### SonarQube (Enterprise alternative)

**When to use:** When the project already has a SonarQube instance. Supports SARIF output for standardized ingestion.

**Key difference:** SonarQube runs server-side. Trigger via `sonar-scanner` CLI; results are pulled from the server API after analysis completes.

**SARIF output support:** SonarQube 9.9+ exports SARIF via the REST API. Use SARIF for unified finding ingestion when mixing SonarQube with other tools.

---

## 2. Dependency Vulnerability Scanners

### pip-audit (Python — preferred)

**CVE database:** OSV (Open Source Vulnerabilities) + PyPA Advisory Database. Updated continuously.

**CVSS scores:** Available via OSV records.

**Installation:**
```bash
pip install pip-audit
```

**CLI invocation:**
```bash
# Audit and output JSON
pip-audit --format=json -o pip-audit-results.json

# Auto-upgrade vulnerable packages (apply with caution — test afterward)
pip-audit --fix
```

**Output format — key fields:**
```json
{
  "dependencies": [
    {
      "name": "requests",
      "version": "2.25.1",
      "vulns": [
        {
          "id": "PYSEC-2023-74",
          "fix_versions": ["2.31.0"],
          "aliases": ["CVE-2023-32681"],
          "description": "Unintended leak of Proxy-Authorization header"
        }
      ]
    }
  ]
}
```

---

### safety (Python — alternative)

**CVE database:** Safety DB (curated). Free tier is 1–2 days behind; paid tier is real-time.

**Installation:**
```bash
pip install safety
```

**CLI invocation:**
```bash
safety check --json > safety-results.json
```

---

### npm audit (Node.js)

**CVE database:** GitHub Advisory Database. Updated continuously.

**CVSS scores:** Available in `severity` field.

**CLI invocation:**
```bash
npm audit --json > npm-audit.json

# Auto-fix compatible updates
npm audit fix

# Fix including breaking changes — use with caution; test thoroughly
npm audit fix --force
```

**Output format — key fields:**
```json
{
  "vulnerabilities": {
    "lodash": {
      "severity": "high",
      "via": [
        {
          "source": 1088980,
          "cve": "CVE-2021-23337",
          "title": "Command Injection"
        }
      ],
      "fixAvailable": { "name": "lodash", "version": "4.17.21" }
    }
  }
}
```

---

### yarn audit (Node.js)

**CVE database:** Same as npm (GitHub Advisory Database).

**CLI invocation:**
```bash
yarn audit --json > yarn-audit.json
```

Note: yarn v1 `audit` does not support `--fix`. To fix yarn v1 projects, use `npm audit fix` or manually run `yarn upgrade <package>@<safe-version>`.

---

### OWASP Dependency-Check (Java / Maven)

**CVE database:** NVD (NIST National Vulnerability Database). Requires NVD API key for best update frequency.

**CVSS scores:** Available from NVD records.

**CLI invocation (Maven):**
```bash
mvn org.owasp:dependency-check-maven:check -Dformat=JSON
```

**Output:** `target/dependency-check-report.json`

**Key fields:** `dependencies[].vulnerabilities[].name` (CVE ID), `dependencies[].vulnerabilities[].cvssv3.baseScore`, `dependencies[].vulnerabilities[].severity`

---

### govulncheck (Go)

**CVE database:** Go Vulnerability Database (vuln.go.dev). Maintained by the Go team.

**CVSS scores:** Not always available; severity indicated by impact description.

**Installation:**
```bash
go install golang.org/x/vuln/cmd/govulncheck@latest
```

**CLI invocation:**
```bash
govulncheck -json ./... > govuln-results.json
```

---

### dotnet list package (\.NET)

**CVE database:** GitHub Advisory Database via NuGet.

**CLI invocation:**
```bash
dotnet list package --vulnerable --include-transitive 2>&1
```

Note: Output is plain text, not JSON. Parse for lines containing `(!)` which indicate vulnerable packages.

---

## 3. IaC Security Scanners

Check `context.has_iac` in `state.json` before running any of these tools. If false, skip this section entirely.

If AWS IaC MCP tools are available (e.g. from a deploy plugin such as `plugin-deploy-on-aws-awsiac`), use `check_cloudformation_template` and `validate_cloudformation_template` MCP tools directly — they are faster and pre-integrated.

---

### checkov (preferred — multi-cloud)

**Supports:** Terraform, CloudFormation, ARM, Kubernetes manifests, Dockerfile, GitHub Actions, Azure Pipelines.

**Installation:**
```bash
pip install checkov
```

**CLI invocation:**
```bash
checkov -d infra/ --output json > checkov-results.json
```

**Output format — key fields:**
```json
{
  "results": {
    "failed_checks": [
      {
        "check_id": "CKV_AWS_18",
        "check_name": "Ensure the S3 bucket has access logging enabled",
        "resource": "aws_s3_bucket.data_bucket",
        "file_path": "infra/s3.tf",
        "file_line_range": [12, 28]
      }
    ]
  }
}
```

---

### tfsec (Terraform-specific)

Note: `tfsec` has been absorbed into `trivy` in newer versions. For Terraform, `trivy config` is the forward-compatible invocation.

**CLI invocation (legacy tfsec):**
```bash
tfsec infra/ --format json > tfsec-results.json
```

**CLI invocation (trivy, preferred for new projects):**
```bash
trivy config infra/ --format json > trivy-config.json
```

---

### trivy (multi-purpose)

**Supports:** Terraform, CloudFormation, Kubernetes, Dockerfile, container images, filesystem scanning.

**Installation:**
```bash
brew install aquasecurity/trivy/trivy
# or
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh
```

**CLI invocations:**
```bash
# IaC/config scanning
trivy config infra/ --format json > trivy-config.json

# Container image scanning
trivy image <image:tag> --format json > trivy-image.json
```

---

### cfn-nag (CloudFormation)

**When to use:** CloudFormation-only projects; provides CF-specific checks beyond what checkov covers.

**Installation:**
```bash
gem install cfn-nag
```

**CLI invocation:**
```bash
cfn_nag_scan --input-path infra/ --output-format json > cfn-nag-results.json
```

---

## 4. Secret Detection

### gitleaks (preferred — git-aware)

**Why preferred:** Scans git history in addition to the working tree; catches secrets that were added and later deleted.

**Installation:**
```bash
brew install gitleaks
# or
go install github.com/zricethezav/gitleaks/v8@latest
```

**CLI invocation:**
```bash
gitleaks detect \
  --source . \
  --report-format json \
  --report-path gitleaks-results.json
```

**Custom rules:** Define in `.gitleaks.toml` at the project root:
```toml
[allowlist]
  description = "Global allowlist"
  regexes = [
    # Reason: test fixture, not a real key
    "AKIAIOSFODNN7EXAMPLE"
  ]
```

**Output format — key fields:**
```json
[
  {
    "Description": "AWS Access Key",
    "File": "config/deploy.yml",
    "Line": 14,
    "Secret": "AKIA***REDACTED***",
    "Commit": "a1b2c3d4"
  }
]
```

---

### truffleHog (entropy-based alternative)

**When to use:** Alongside gitleaks for high-assurance scanning; higher false-positive rate, so treat as supplementary.

**Installation:**
```bash
pip install trufflehog
# or
brew install trufflehog
```

**CLI invocation:**
```bash
trufflehog filesystem . --json > trufflehog-results.json
```

Note: Filter results to `SourceMetadata.Data.Filesystem.file` + `Raw` fields. Entropy findings without a matching regex pattern should be treated as advisory only.

---

### Manual Regex Patterns (fallback when tools unavailable)

Use these patterns when neither gitleaks nor truffleHog is available. Search with `grep -rn` or equivalent:

| Pattern Type | Regex |
|---|---|
| AWS access key | `AKIA[0-9A-Z]{16}` |
| AWS secret key | `[0-9a-zA-Z/+]{40}` |
| GCP service account | `"type": "service_account"` |
| Private key block | `-----BEGIN (RSA \|EC \|DSA )?PRIVATE KEY-----` |
| Generic secret assignment | `(password\|passwd\|secret\|token\|api_key\|apikey)\s*[:=]\s*['"]\S{8,}['"]` (case-insensitive) |

**.env gitignore check:** Read `.gitignore` and verify it contains an entry for `.env`. If missing, flag as a finding: "`.env` file is not gitignored — risk of committing secrets to version control."

---

## 5. Output Parsing Reference

Quick-reference field paths for automated finding extraction:

| Tool | File path field | Line number field | Severity field | ID / Rule field |
|------|----------------|------------------|----------------|-----------------|
| Semgrep | `results[].path` | `results[].start.line` | `results[].extra.severity` | `results[].check_id` |
| Bandit | `results[].filename` | `results[].line_number` | `results[].issue_severity` | `results[].test_id` |
| npm audit | key in `vulnerabilities` object | N/A (package-level) | `vulnerabilities.{name}.severity` | `vulnerabilities.{name}.via[].cve` |
| checkov | `results.failed_checks[].file_path` | `results.failed_checks[].file_line_range` | N/A (policy-based) | `results.failed_checks[].check_id` |
| gitleaks | `[].File` | `[].Line` | N/A (all critical) | `[].Description` |
| gosec | `Issues[].file` | `Issues[].line` | `Issues[].severity` | `Issues[].rule_id` |

---

## 6. False Positive Management

Never suppress a finding without a documented reason. Suppressions without justification are a red flag in code review.

| Tool | Suppression mechanism | Format |
|---|---|---|
| Semgrep | Inline comment | `# nosemgrep: rule-id  # reason: test fixture` |
| Semgrep | File-level exclude | Add to `paths.exclude` in `.semgrep.yml` with a comment block |
| gitleaks | Allowlist entry | Add regex to `[allowlist]` in `.gitleaks.toml` with `description = "reason"` |
| checkov | Inline comment | `# checkov:skip=CKV_AWS_18:reason: public bucket intentional for static site` |
| checkov | CLI flag | `--skip-check CKV_AWS_18` (use only in CI config, never silently) |
| Bandit | Inline comment | `# nosec B105  # reason: not a real password, test fixture` |
| gosec | Inline comment | `//#nosec G304  -- reason: path is validated upstream` |

**Common false positives to watch for:**

- Semgrep `p/secrets` fires on test fixtures with placeholder values → verify against actual entropy; suppress with reason if confirmed fake
- checkov `CKV_AWS_117` (Lambda inside VPC) → false positive if VPC access is intentionally not required; document the architectural decision
- gitleaks fires on base64-encoded non-secret strings → verify decoded content; suppress with reason if confirmed non-secret
- Bandit `B101` (assert used) → false positive in test files; exclude `tests/` from Bandit scope using `-x tests/`
