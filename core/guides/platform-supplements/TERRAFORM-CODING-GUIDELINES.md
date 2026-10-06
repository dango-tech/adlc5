# Terraform Coding Guidelines - Enterprise Grade (Provider-Agnostic Base)

**Version:** 2.0  
**Last Updated:** 2026  
**Target:** Production Terraform infrastructure requiring high quality, security, and maintainability

> **Two-tier guide system:** This base guide covers provider-agnostic Terraform conventions. For cloud-specific patterns (resource examples, IAM, encryption, networking, compute, state backends), load the appropriate supplement:
> - AWS → `TERRAFORM-AWS-SUPPLEMENT.md`
> - GCP → `TERRAFORM-GCP-SUPPLEMENT.md`
>
> The supplement is selected automatically based on `context.detected_stack.cloud_provider` in state.json.

---

## Table of Contents

1. [Philosophy](#philosophy)
2. [Code Style](#code-style)
3. [Type Safety](#type-safety)
4. [Documentation](#documentation)
5. [Architecture](#architecture)
6. [Error Handling](#error-handling)
7. [Testing](#testing)
8. [Security](#security)
9. [Performance](#performance)
10. [Dependencies](#dependencies)
11. [Logging & Observability](#logging--observability)
12. [Code Review](#code-review)
13. [Tooling](#tooling)

---

## Philosophy

Follow **Infrastructure as Code (IaC)** principles:
- Declarative over imperative: describe desired state, not steps
- Idempotency: running the same code twice produces the same result
- Immutable infrastructure: replace, don't patch
- Plan before apply: always review the execution plan
- Version everything: infrastructure code is treated like application code

**Core Principles:**
- Write code for humans first, machines second
- Optimize for readability and maintainability
- Modules should be opinionated and do one thing well
- Security is not optional: least privilege everywhere
- State is sacred: protect, encrypt, and back up state files
- Test infrastructure changes before applying to production
- Separate environments with clear boundaries

---

## Code Style

### Base Standard

Follow the **HashiCorp Terraform Style Guide** with `terraform fmt` as the baseline:

**Formatting:**
- Indentation: 2 spaces (never tabs)
- Encoding: UTF-8
- Line endings: LF (Unix style)
- Run `terraform fmt` before every commit
- Align equals signs for consecutive single-line arguments

**Naming Conventions:**
```hcl
# Resources — lowercase with underscores, singular nouns
# Do NOT repeat the resource type in the name
resource "<provider>_<type>" "web_server" {}     # [GOOD]
resource "<provider>_<type>" "web_server_instance" {}  # [BAD] repeats "instance"

# Single-instance resources — use "main" or "this"
resource "<provider>_network" "main" {}

# Multiple similar resources — use meaningful names
resource "<provider>_subnet" "public" {}
resource "<provider>_subnet" "private" {}

# Variables — lowercase with underscores
variable "instance_type" {}
variable "enable_monitoring" {}   # Boolean: positive name with enable/disable
variable "ram_size_gb" {}         # Numeric: include unit in name

# Outputs — lowercase with underscores
output "instance_id" {}
output "load_balancer_dns_name" {}

# Locals — lowercase with underscores
locals {
  common_tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Project     = var.project_name
  }
}

# Data sources — lowercase with underscores
data "<provider>_image" "base" {}

# Modules — lowercase with underscores
module "vpc" {
  source = "./modules/vpc"
}
```

See the cloud-provider supplement for concrete resource naming examples.

**Argument Ordering within Resource Blocks:**
```hcl
resource "<provider>_compute_instance" "web_server" {
  # 1. Meta-arguments first
  count = var.instance_count

  # 2. Required arguments
  image         = data.<provider>_image.base.id
  instance_type = var.instance_type
  subnet_id     = <provider>_subnet.public.id

  # 3. Optional arguments
  monitoring = true

  # 4. Tags/labels (always last argument before blocks)
  tags = merge(local.common_tags, {
    Name = "web-server-${count.index}"
    Role = "web"
  })

  # 5. Nested blocks (separated by blank line)
  disk {
    size_gb   = 20
    encrypted = true
  }

  # 6. Meta-argument blocks last
  lifecycle {
    create_before_destroy = true
  }
}
```

**Comments:**
```hcl
# Use hash for single-line comments
# Explain the WHY, not the WHAT

# This firewall rule allows internal traffic only because
# the load balancer handles all external connections
resource "<provider>_firewall_rule" "internal" {
  # ...
}

# TODO: Remove this after the 2026-Q3 migration is complete
```

**Avoid:**
- Dashes in resource/variable/output names (use underscores)
- Overly generic resource names: `resource`, `main1`, `temp`
- Deep nesting of ternary operators
- Hardcoded values that should be variables
- Repeated literal values (use locals)

---

## Type Safety

### Variable Types

**Always declare types and add validation:**
```hcl
# String with validation
variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

# Number with validation
variable "instance_count" {
  description = "Number of instances to create"
  type        = number
  default     = 1

  validation {
    condition     = var.instance_count >= 1 && var.instance_count <= 10
    error_message = "Instance count must be between 1 and 10."
  }
}

# Boolean with positive naming
variable "enable_monitoring" {
  description = "Whether to enable detailed monitoring"
  type        = bool
  default     = true
}

# List of strings
variable "availability_zones" {
  description = "List of availability zones for deployment"
  type        = list(string)

  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "At least 2 availability zones are required for high availability."
  }
}

# Map of strings
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Complex object type
variable "database_config" {
  description = "Database instance configuration"
  type = object({
    engine         = string
    engine_version = string
    instance_class = string
    storage_gb     = number
    multi_az       = bool
    backup_retention_days = optional(number, 7)
  })

  validation {
    condition     = contains(["postgres", "mysql"], var.database_config.engine)
    error_message = "Database engine must be postgres or mysql."
  }

  validation {
    condition     = var.database_config.storage_gb >= 20
    error_message = "Minimum storage is 20 GB."
  }
}
```

**Sensitive variables:**
```hcl
variable "database_password" {
  description = "Master password for the database"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.database_password) >= 16
    error_message = "Database password must be at least 16 characters."
  }
}
```

**Nullable variables:**
```hcl
variable "custom_domain" {
  description = "Optional custom domain for the application"
  type        = string
  default     = null
  nullable    = true
}

# Usage with conditional — create resource only when value is provided
resource "<provider>_dns_record" "custom" {
  count = var.custom_domain != null ? 1 : 0

  name   = var.custom_domain
  type   = "A"
  target = <provider>_load_balancer.main.ip_address
}
```

---

## Documentation

### Variable and Output Descriptions

**Required for all variables and outputs (1-2 sentences):**
```hcl
variable "vpc_cidr_block" {
  description = "CIDR block for the VPC. Must be a /16 or larger network."
  type        = string
  default     = "10.0.0.0/16"
}

output "vpc_id" {
  description = "The ID of the VPC created by this module."
  value       = <provider>_network.main.id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs for load balancer placement."
  value       = <provider>_subnet.public[*].id
}
```

### Module README

**Auto-generate with terraform-docs. Every module must include:**

```markdown
# VPC Module

Creates a VPC with public and private subnets, NAT gateways, and route tables.

## Usage

```hcl
module "vpc" {
  source = "./modules/vpc"

  environment        = "prod"
  vpc_cidr_block     = "10.0.0.0/16"
  availability_zones = ["zone-a", "zone-b", "zone-c"]
  enable_nat_gateway = true
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.8.0 |
| <provider> | ~> X.0 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| environment | Deployment environment | string | - | yes |
| vpc_cidr_block | CIDR block for the VPC | string | 10.0.0.0/16 | no |

## Outputs

| Name | Description |
|------|-------------|
| vpc_id | The ID of the VPC |
| public_subnet_ids | List of public subnet IDs |
```

### Inline Comments

```hcl
# [GOOD] Explain WHY, not WHAT
# Allow traffic from the load balancer only, not directly from the internet.
# This ensures all traffic passes through WAF/security rules.
resource "<provider>_firewall_rule" "allow_lb" {
  direction   = "ingress"
  port        = 80
  protocol    = "tcp"
  source      = <provider>_load_balancer.main.id
}

# [BAD] Restating the obvious
# Allow ingress on port 80 from load balancer
resource "<provider>_firewall_rule" "allow_lb" {
  # ...
}
```

### CHANGELOG for Modules

```markdown
# Changelog

## [1.2.0] - 2026-02-10
### Added
- Support for custom domain with Route53

### Changed
- Default instance type updated to t3.medium

## [1.1.0] - 2026-01-15
### Added
- NAT gateway high availability across AZs

### Fixed
- Security group rule ordering issue
```

---

## Architecture

### Standard Module Structure

```
modules/
├── network/
│   ├── main.tf           # Primary resources
│   ├── variables.tf      # Input variables
│   ├── outputs.tf        # Output values
│   ├── versions.tf       # Required providers and Terraform version
│   ├── locals.tf         # Local values (optional, if many)
│   ├── data.tf           # Data sources (optional, if many)
│   └── README.md         # Module documentation
├── compute/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── versions.tf
│   └── README.md
└── database/
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    ├── versions.tf
    └── README.md
```

### Root Module Structure

```
environments/
├── dev/
│   ├── main.tf           # Module calls
│   ├── variables.tf
│   ├── outputs.tf
│   ├── versions.tf
│   ├── backend.tf        # Remote state configuration
│   ├── terraform.tfvars  # Environment-specific values
│   └── providers.tf      # Provider configuration
├── staging/
│   ├── main.tf
│   ├── ...
└── prod/
    ├── main.tf
    ├── ...
```

### Feature-Based File Grouping

```hcl
# [GOOD] Group related resources in logically named files
# network.tf — VPC/VNet, subnets, gateways, route tables
# compute.tf — container clusters, services, task/workload definitions
# database.tf — database instances, subnet groups
# security.tf — firewall rules, security groups, IAM
# storage.tf  — object storage buckets, block storage
```

See the cloud-provider supplement for concrete resource examples per file.

### Module Composition

```hcl
# environments/prod/main.tf
module "network" {
  source = "../../modules/network"

  environment        = var.environment
  vpc_cidr_block     = "10.0.0.0/16"
  availability_zones = var.availability_zones
}

module "compute" {
  source = "../../modules/compute"

  environment    = var.environment
  vpc_id         = module.network.vpc_id
  subnet_ids     = module.network.private_subnet_ids
  desired_count  = 3
  container_port = 8080
}

module "database" {
  source = "../../modules/database"

  environment       = var.environment
  vpc_id            = module.network.vpc_id
  subnet_ids        = module.network.private_subnet_ids
  database_config   = var.database_config
  database_password = var.database_password
}
```

### Remote State

Configure a remote backend with encryption and state locking. The specific backend depends on your cloud provider:

- **AWS:** S3 + DynamoDB locking (see AWS supplement)
- **GCP:** GCS with versioning (see GCP supplement)
- **Azure:** Azure Blob Storage with lease locking

```hcl
# Cross-stack state reference (provider-agnostic pattern)
data "terraform_remote_state" "network" {
  backend = "<backend_type>"
  config = {
    # backend-specific config — see provider supplement
  }
}

# Use outputs from remote state
module "compute" {
  subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids
}
```

---

## Error Handling

### Preconditions and Postconditions

```hcl
# Precondition: validate assumptions before resource creation
resource "<provider>_compute_instance" "web_server" {
  image         = data.<provider>_image.base.id
  instance_type = var.instance_type

  lifecycle {
    precondition {
      condition     = data.<provider>_image.base.architecture == "x86_64"
      error_message = "The selected image must be x86_64 architecture."
    }

    postcondition {
      condition     = self.public_ip != ""
      error_message = "The instance must have a public IP assigned."
    }
  }
}
```

### Check Blocks (continuous validation)

```hcl
# check blocks validate assertions about infrastructure state
check "health_check" {
  data "http" "app_health" {
    url = "https://${<provider>_load_balancer.main.dns_name}/health"
  }

  assert {
    condition     = data.http.app_health.status_code == 200
    error_message = "Application health check failed after deployment."
  }
}
```

### Variable Validation

```hcl
variable "cidr_block" {
  description = "CIDR block for the VPC"
  type        = string

  validation {
    condition     = can(cidrhost(var.cidr_block, 0))
    error_message = "Must be a valid CIDR block (e.g., 10.0.0.0/16)."
  }

  validation {
    condition     = tonumber(split("/", var.cidr_block)[1]) <= 24
    error_message = "CIDR block must be /24 or larger."
  }
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]+\\.[a-z]{2,}$", var.domain_name))
    error_message = "Must be a valid domain name."
  }
}
```

### Lifecycle Rules for Safety

```hcl
# Protect stateful resources from accidental destruction
resource "<provider>_database_instance" "main" {
  # ...

  lifecycle {
    prevent_destroy = true
  }
}

# Ignore externally managed changes
resource "<provider>_autoscaling_group" "app" {
  # ...

  lifecycle {
    ignore_changes = [desired_capacity]  # Managed by auto-scaling policies
  }
}

# Create replacement before destroying old resource
resource "<provider>_compute_instance" "web_server" {
  # ...

  lifecycle {
    create_before_destroy = true
  }
}
```

### Moved Blocks for Refactoring

```hcl
# Safely rename resources without destroy/recreate
moved {
  from = <provider>_compute_instance.web
  to   = <provider>_compute_instance.web_server
}

# Move into a module
moved {
  from = <provider>_network.main
  to   = module.network.<provider>_network.main
}
```

---

## Testing

### Validation and Planning

```bash
# Always validate syntax first
terraform validate

# Always review the plan before applying
terraform plan -out=tfplan

# Apply only from a saved plan
terraform apply tfplan
```

### Native Terraform Tests

```hcl
# tests/network_test.tftest.hcl
run "creates_network_with_correct_cidr" {
  command = plan

  variables {
    environment    = "test"
    vpc_cidr_block = "10.0.0.0/16"
  }

  assert {
    condition     = <provider>_network.main.cidr_block == "10.0.0.0/16"
    error_message = "Network CIDR block does not match expected value."
  }
}

run "creates_correct_number_of_subnets" {
  command = plan

  variables {
    environment        = "test"
    availability_zones = ["zone-a", "zone-b"]
  }

  assert {
    condition     = length(<provider>_subnet.public) == 2
    error_message = "Should create one public subnet per zone."
  }

  assert {
    condition     = length(<provider>_subnet.private) == 2
    error_message = "Should create one private subnet per zone."
  }
}

run "rejects_invalid_environment" {
  command = plan

  variables {
    environment = "invalid"
  }

  expect_failures = [
    var.environment,
  ]
}
```

### Integration Tests (Terratest)

```go
// test/network_test.go
package test

import (
    "testing"

    "github.com/gruntwork-io/terratest/modules/terraform"
    "github.com/stretchr/testify/assert"
)

func TestNetworkModule(t *testing.T) {
    t.Parallel()

    terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
        TerraformDir: "../modules/network",
        Vars: map[string]interface{}{
            "environment":        "test",
            "vpc_cidr_block":     "10.99.0.0/16",
            "availability_zones": []string{"zone-a", "zone-b"},
        },
    })

    defer terraform.Destroy(t, terraformOptions)
    terraform.InitAndApply(t, terraformOptions)

    vpcId := terraform.Output(t, terraformOptions, "vpc_id")
    assert.NotEmpty(t, vpcId)

    publicSubnetIds := terraform.OutputList(t, terraformOptions, "public_subnet_ids")
    assert.Len(t, publicSubnetIds, 2)
}
```

### Static Analysis (Policy as Code)

```bash
# Checkov — static analysis for security
checkov -d . --framework terraform

# tfsec — security scanner
tfsec .

# OPA/Conftest — custom policy checks
conftest test . -p policies/

# Example OPA policy (policies/main.rego)
# package main
#
# deny[msg] {
#   resource := input.resource.<provider>_storage_bucket[name]
#   not resource.encryption
#   msg := sprintf("Storage bucket '%s' must have encryption enabled", [name])
# }
```

---

## Security

### Secrets Management

```hcl
# [GOOD] Mark sensitive variables
variable "database_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

# [GOOD] Mark sensitive outputs
output "database_connection_string" {
  description = "Database connection string (contains credentials)"
  value       = "postgresql://${var.db_user}:${var.db_password}@${<provider>_database.main.endpoint}"
  sensitive   = true
}

# [BAD] Never hardcode secrets
resource "<provider>_database_instance" "main" {
  password = "my-secret-password"  # NEVER DO THIS
}

# [GOOD] Use your cloud provider's secret manager
# AWS: aws_secretsmanager_secret_version / aws_ssm_parameter
# GCP: google_secret_manager_secret_version
# Azure: azurerm_key_vault_secret
# See the cloud-provider supplement for concrete examples.
```

### Remote State Encryption

Remote state must be encrypted at rest and protected with state locking:

- **AWS:** S3 with `encrypt = true`, KMS key, DynamoDB locking
- **GCP:** GCS with CMEK encryption, built-in locking
- **Azure:** Blob Storage with encryption, lease-based locking

See the cloud-provider supplement for the concrete backend configuration.

### IAM / Access Control — Least Privilege

Every cloud provider has an IAM system. Regardless of provider, follow these principles:

- **Scope permissions to specific actions and resources** — never use wildcard `*` for both action and resource
- **Use roles over static credentials** (service accounts, managed identities, IAM roles)
- **Prefer resource-level bindings** over broad project/account-level permissions
- **Separate duty** — different roles for deployment, application runtime, and admin

See the cloud-provider supplement for concrete IAM resource examples.

### Encryption at Rest

All data stores must be encrypted at rest. Use customer-managed keys (CMK/CMEK) for production:

- **Object storage** (S3, GCS, Blob Storage) — server-side encryption with managed key
- **Databases** (RDS, Cloud SQL, Azure SQL) — storage encryption enabled
- **Block storage** (EBS, Persistent Disks, Managed Disks) — encrypted volumes

See the cloud-provider supplement for provider-specific encryption resource examples.

**Security Checklist:**
- [ ] No secrets in code, variables, or version control
- [ ] Remote state encrypted and locked
- [ ] All `sensitive` flags set on variables and outputs containing credentials
- [ ] IAM/access policies follow least privilege principle
- [ ] All storage encrypted at rest (object storage, databases, block storage)
- [ ] All data in transit encrypted (TLS/SSL)
- [ ] Firewall rules / security groups restrict access to minimum needed
- [ ] Public access blocked on object storage (unless explicitly required)
- [ ] Provider credentials managed via roles/service accounts (not static keys)
- [ ] Static analysis (tfsec/checkov) passes with no critical findings

---

## Performance

### Minimize Provider Calls

```hcl
# [GOOD] Use count/for_each for multiple similar resources
resource "<provider>_subnet" "public" {
  for_each = toset(var.availability_zones)

  network_id        = <provider>_network.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr_block, 8, index(var.availability_zones, each.value))
  availability_zone = each.value

  tags = merge(local.common_tags, {
    Name = "public-${each.value}"
    Tier = "public"
  })
}

# [BAD] Separate resources for each (repetitive, hard to maintain)
resource "<provider>_subnet" "public_a" {
  network_id        = <provider>_network.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "zone-a"
}

resource "<provider>_subnet" "public_b" {
  network_id        = <provider>_network.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "zone-b"
}
```

### Targeted Operations

```bash
# Apply changes to specific resources only (use sparingly)
terraform apply -target=module.compute

# Refresh specific resources
terraform apply -refresh-only -target=<provider>_compute_instance.web_server
```

### State Splitting

```
# Split state by volatility and blast radius
# Long-lived infrastructure (VPC, RDS) - rarely changes
environments/prod/foundation/
├── main.tf      # VPC, subnets, NAT gateways, RDS
├── backend.tf   # Separate state file

# Short-lived infrastructure (ECS, Lambda) - changes frequently
environments/prod/application/
├── main.tf      # ECS services, Lambda functions, ALB
├── backend.tf   # Separate state file
```

### Parallelism Tuning

```bash
# Increase parallelism for faster applies (default: 10)
terraform apply -parallelism=20

# Decrease for rate-limited APIs
terraform apply -parallelism=5
```

### Limit Expression Complexity

```hcl
# [BAD] Complex nested ternary
locals {
  instance_type = var.environment == "prod" ? "m5.xlarge" : var.environment == "staging" ? "m5.large" : "t3.medium"
}

# [GOOD] Break into multiple locals
locals {
  instance_type_map = {
    prod    = "m5.xlarge"
    staging = "m5.large"
    dev     = "t3.medium"
  }
  instance_type = local.instance_type_map[var.environment]
}

# [BAD] Complex interpolation with many functions
locals {
  result = join(",", sort(distinct(flatten([for k, v in var.map : [for i in v : upper(trim(i))]]))))
}

# [GOOD] Break into steps
locals {
  flattened = flatten([for k, v in var.map : [for i in v : upper(trim(i))]])
  unique    = distinct(local.flattened)
  sorted    = sort(local.unique)
  result    = join(",", local.sorted)
}
```

---

## Dependencies

### Provider Version Pinning

```hcl
# versions.tf
terraform {
  required_version = ">= 1.8.0, < 2.0.0"

  required_providers {
    # Pin your cloud provider — see supplement for recommended version
    <provider> = {
      source  = "hashicorp/<provider>"
      version = "~> X.Y"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}
```

### Module Version Pinning

```hcl
# [GOOD] Pin to specific version or version range
module "network" {
  source  = "<registry>/<module>/<provider>"
  version = "X.Y.Z"
}

# [GOOD] Pin to a Git tag
module "custom" {
  source = "git::https://github.com/myorg/terraform-module.git?ref=v1.2.0"
}

# [BAD] No version constraint
module "network" {
  source = "<registry>/<module>/<provider>"
}

# [BAD] Pointing to branch (mutable reference)
module "custom" {
  source = "git::https://github.com/myorg/terraform-module.git?ref=main"
}
```

See the cloud-provider supplement for recommended community modules and versions.

### Lock File

```bash
# Always commit .terraform.lock.hcl to version control
# It pins exact provider versions and checksums

# Update lock file when upgrading providers
terraform init -upgrade

# Verify lock file integrity
terraform providers lock \
  -platform=linux_amd64 \
  -platform=darwin_amd64 \
  -platform=darwin_arm64
```

### Dependency Updates

- Review provider changelogs before upgrading
- Test upgrades in dev/staging before production
- Update providers monthly for security patches
- Use Dependabot or Renovate for automated PRs

---

## Logging & Observability

### Terraform Logging

```bash
# Set log level for debugging
export TF_LOG=DEBUG        # TRACE, DEBUG, INFO, WARN, ERROR
export TF_LOG_PATH=terraform.log

# Provider-specific logging
export TF_LOG_PROVIDER=DEBUG
```

### Audit Trails via CI/CD

```yaml
# GitHub Actions example
- name: Terraform Plan
  run: terraform plan -out=tfplan -no-color 2>&1 | tee plan-output.txt

- name: Post Plan to PR
  uses: actions/github-script@v7
  with:
    script: |
      const plan = require('fs').readFileSync('plan-output.txt', 'utf8');
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: `## Terraform Plan\n\`\`\`\n${plan}\n\`\`\``
      });
```

### Drift Detection

```bash
# Detect configuration drift
terraform plan -detailed-exitcode
# Exit code 0: No changes
# Exit code 1: Error
# Exit code 2: Changes detected (drift)

# Schedule drift detection in CI/CD (e.g., nightly)
# Alert if exit code is 2
```

### Resource Tagging / Labeling for Observability

```hcl
locals {
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Team        = var.team_name
    CostCenter  = var.cost_center
  }
}
```

Apply `common_tags` (AWS/Azure) or `common_labels` (GCP) to every resource. See the cloud-provider supplement for the tagging/labeling conventions and provider-specific tag features (e.g., `default_tags`).

---

## Code Review

### Review Checklist

**Plan Output:**
- [ ] Reviewed `terraform plan` output thoroughly
- [ ] No unexpected resource deletions or replacements
- [ ] Changes match the intended scope
- [ ] Sensitive values not exposed in plan

**Code Quality:**
- [ ] `terraform fmt` applied (no formatting issues)
- [ ] `terraform validate` passes
- [ ] Naming follows conventions (underscores, singular, no type repetition)
- [ ] Variables have descriptions and type constraints
- [ ] Outputs have descriptions
- [ ] Validation blocks on variables where appropriate
- [ ] No hardcoded values (use variables or locals)

**Architecture:**
- [ ] Resources grouped logically in files
- [ ] Modules used for reusable patterns
- [ ] State separation appropriate (blast radius minimized)
- [ ] Dependencies between resources are clear

**Security:**
- [ ] No secrets in code or tfvars committed to VCS
- [ ] Sensitive flags on appropriate variables/outputs
- [ ] IAM / access control follows least privilege
- [ ] Encryption enabled on all data stores
- [ ] Firewall rules / security groups restrict to minimum access
- [ ] tfsec/checkov passes

**Safety:**
- [ ] `prevent_destroy` on stateful resources (databases, S3 buckets)
- [ ] `create_before_destroy` where zero-downtime needed
- [ ] `moved` blocks for renames/refactors (no destroy/recreate)
- [ ] Backup/snapshot policies in place

### Review Process

**Requirements:**
- Minimum 2 approvals for production infrastructure
- `terraform plan` output reviewed by at least one reviewer
- All automated checks must pass (fmt, validate, tfsec, checkov)
- No unresolved comments
- Production applies gated behind manual approval

**Review Guidelines:**
- Be respectful and constructive
- Always check the plan output, not just the code diff
- Verify blast radius: what else is affected?
- Check for state management implications
- Distinguish between blocking and non-blocking comments

---

## Tooling

### Required Tools

**Code Formatting:**
- `terraform fmt` - Built-in formatter (run before every commit)

**Validation & Linting:**
- `terraform validate` - Syntax and type validation
- `TFLint` - Terraform linter with provider-specific rules

**Security Scanning:**
- `tfsec` - Security scanner for Terraform
- `checkov` - Policy-as-code static analysis
- `OPA/Conftest` - Custom policy validation (optional)

**Documentation:**
- `terraform-docs` - Auto-generate README from variables/outputs

**Testing:**
- `terraform test` - Native testing framework
- `Terratest` - Go-based integration testing

### Pre-Commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/antonbabenko/pre-commit-tf
    hooks:
      - id: terraform_fmt
      - id: terraform_validate
      - id: terraform_tflint
        args:
          - --args=--config=__GIT_WORKING_DIR__/.tflint.hcl
      - id: terraform_tfsec
      - id: terraform_docs
        args:
          - --args=--config=.terraform-docs.yml
      - id: terraform_checkov
        args:
          - --args=--quiet
          - --args=--skip-check CKV_AWS_18,CKV_AWS_21
```

### TFLint Configuration

```hcl
# .tflint.hcl — provider-agnostic rules
# Add the provider-specific plugin from your supplement
rule "terraform_naming_convention" {
  enabled = true
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}

rule "terraform_typed_variables" {
  enabled = true
}

rule "terraform_unused_declarations" {
  enabled = true
}
```

See the cloud-provider supplement for the provider-specific TFLint plugin (`tflint-ruleset-aws`, `tflint-ruleset-google`, etc.).

### CI/CD Pipeline

**Required checks before merge:**
```bash
# Initialize
terraform init -backend=false

# Format check
terraform fmt -check -recursive

# Validate
terraform validate

# Lint
tflint --init && tflint

# Security scan
tfsec . --minimum-severity HIGH
checkov -d . --framework terraform --quiet

# Auto-generate docs
terraform-docs markdown table . --output-file README.md

# Plan (for each environment)
terraform plan -out=tfplan -detailed-exitcode

# Native tests
terraform test
```

**Production apply pipeline:**
```bash
# Plan with saved output
terraform plan -out=tfplan

# Manual approval gate (in CI/CD)

# Apply from saved plan only
terraform apply tfplan

# Post-apply validation
terraform output -json > outputs.json
# Run health checks against deployed infrastructure
```

---

## Quick Reference

### Daily Workflow

1. **Before coding:**
   - Pull latest changes
   - Review current state: `terraform plan`
   - Create feature branch

2. **While coding:**
   - Follow naming conventions (underscores, singular)
   - Add descriptions to all variables and outputs
   - Add validation blocks where appropriate
   - Use `terraform fmt` and `terraform validate` frequently

3. **Before pushing:**
   - Run `terraform fmt -check -recursive`
   - Run `terraform validate`
   - Run `tflint` and `tfsec`
   - Review `terraform plan` output carefully
   - Update module README with `terraform-docs`

4. **Code review:**
   - Share `terraform plan` output with reviewers
   - Address all comments
   - Ensure CI passes
   - Get 2 approvals
   - Squash and merge

5. **Applying:**
   - Apply to dev first, then staging, then production
   - Use saved plan files: `terraform plan -out=tfplan && terraform apply tfplan`
   - Verify deployment with health checks
   - Monitor for drift

### Common Commands

```bash
# Initialize working directory
terraform init

# Format all files
terraform fmt -recursive

# Validate configuration
terraform validate

# Plan changes
terraform plan

# Plan with saved output
terraform plan -out=tfplan

# Apply from saved plan
terraform apply tfplan

# Apply with auto-approve (CI/CD only, never interactive)
terraform apply -auto-approve

# Show current state
terraform show

# List resources in state
terraform state list

# Import existing resource
terraform import <provider>_compute_instance.web_server <resource-id>

# Move resource in state (refactoring)
terraform state mv <provider>_compute_instance.old <provider>_compute_instance.new

# Remove resource from state (without destroying)
terraform state rm <provider>_compute_instance.legacy

# Destroy infrastructure
terraform destroy

# Lint
tflint

# Security scan
tfsec .

# Generate docs
terraform-docs markdown table . --output-file README.md

# Run tests
terraform test

# Upgrade providers
terraform init -upgrade

# Install pre-commit hooks
pre-commit install
pre-commit run --all-files
```

---

## References

- [HashiCorp Terraform Style Guide](https://developer.hashicorp.com/terraform/language/style)
- [HashiCorp Terraform Recommended Practices](https://developer.hashicorp.com/terraform/cloud-docs/recommended-practices)
- [HashiCorp Standard Module Structure](https://developer.hashicorp.com/terraform/language/modules/develop/structure)
- [Terraform Best Practices (community)](https://www.terraform-best-practices.com/)
- [tfsec Documentation](https://aquasecurity.github.io/tfsec/)
- [Checkov Documentation](https://www.checkov.io/1.Welcome/What%20is%20Checkov.html)
- [Terratest Documentation](https://terratest.gruntwork.io/)

**Cloud-Provider Supplements:**
- AWS-specific patterns → `TERRAFORM-AWS-SUPPLEMENT.md`
- GCP-specific patterns → `TERRAFORM-GCP-SUPPLEMENT.md`

---

**Questions or suggestions?** Update this document through team discussion and code review.

**Version History:**
- v2.0 (2026) - Refactored to provider-agnostic base with cloud-specific supplements
- v1.0 (2026) - Initial enterprise-grade guidelines
