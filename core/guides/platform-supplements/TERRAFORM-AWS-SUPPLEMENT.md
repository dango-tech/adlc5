# Terraform — AWS Supplement

**Loaded alongside:** `TERRAFORM-CODING-GUIDELINES.md` (base guide)  
**Applies when:** `detected_stack.cloud_provider` is `aws`

This supplement provides AWS-specific Terraform patterns, resource conventions, and Well-Architected alignment that extend the provider-agnostic base guide.

---

## Provider Configuration

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

# Multi-region pattern
provider "aws" {
  alias  = "us_west"
  region = "us-west-2"
}
```

---

## Remote State (S3 + DynamoDB)

```hcl
terraform {
  backend "s3" {
    bucket         = "mycompany-terraform-state"
    key            = "prod/infrastructure.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
    kms_key_id     = "alias/terraform-state-key"
  }
}

# Cross-stack state reference
data "terraform_remote_state" "vpc" {
  backend = "s3"
  config = {
    bucket = "mycompany-terraform-state"
    key    = "prod/vpc.tfstate"
    region = "us-east-1"
  }
}
```

---

## Naming Conventions

AWS resource naming examples:

```hcl
# Resources — lowercase with underscores, singular nouns
# Do NOT repeat the resource type in the name
resource "aws_instance" "web_server" {}      # GOOD
resource "aws_instance" "web_server_instance" {}  # BAD — repeats "instance"

# Single-instance resources — use "main" or "this"
resource "aws_vpc" "main" {}

# Multiple similar resources — use meaningful names
resource "aws_subnet" "public" {}
resource "aws_subnet" "private" {}
```

---

## IAM — Least Privilege

```hcl
# Scoped permissions per service
resource "aws_iam_role_policy" "app" {
  name = "app-policy"
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = "${aws_s3_bucket.app_data.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage"]
        Resource = aws_sqs_queue.app.arn
      },
    ]
  })
}

# NEVER do this
resource "aws_iam_role_policy" "bad" {
  policy = jsonencode({
    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}
```

- Use IAM roles (not static access keys) for service authentication
- Scope `Resource` to specific ARNs, not `"*"`
- Prefer managed policies over inline where reuse is needed
- Use `aws_iam_policy_document` data source for complex policies

---

## Secrets Management

```hcl
# Retrieve secrets from AWS Secrets Manager
data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = "prod/database/password"
}

resource "aws_db_instance" "main" {
  password = data.aws_secretsmanager_secret_version.db_password.secret_string
}

# Alternative: SSM Parameter Store for non-rotating config
data "aws_ssm_parameter" "api_key" {
  name            = "/prod/app/api-key"
  with_decryption = true
}
```

Never hardcode secrets in `.tf` files or `terraform.tfvars` committed to VCS.

---

## Encryption at Rest

```hcl
# S3
resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.main.arn
    }
  }
}

# RDS
resource "aws_db_instance" "main" {
  storage_encrypted = true
  kms_key_id        = aws_kms_key.main.arn
}

# EBS
resource "aws_ebs_volume" "data" {
  encrypted  = true
  kms_key_id = aws_kms_key.main.arn
}

# DynamoDB
resource "aws_dynamodb_table" "main" {
  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.main.arn
  }
}
```

---

## Networking Patterns

```hcl
# VPC with public/private subnets
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr_block
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = merge(local.common_tags, { Name = "${var.project}-vpc" })
}

resource "aws_subnet" "public" {
  for_each          = toset(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr_block, 8, index(var.availability_zones, each.value))
  availability_zone = each.value
  tags = merge(local.common_tags, { Name = "public-${each.value}", Tier = "public" })
}

# Security groups — restrict to minimum
resource "aws_security_group" "app" {
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

---

## Compute Patterns

### ECS Fargate

```hcl
resource "aws_ecs_cluster" "main" {
  name = "${var.project}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_service" "app" {
  name            = "app"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "app"
    container_port   = 8080
  }
}
```

### Lambda

```hcl
resource "aws_lambda_function" "processor" {
  function_name = "${var.project}-processor"
  handler       = "index.handler"
  runtime       = "nodejs20.x"
  role          = aws_iam_role.lambda.arn
  timeout       = 30
  memory_size   = 256

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.main.name
    }
  }

  tracing_config {
    mode = "Active"
  }
}
```

---

## Database Patterns

```hcl
resource "aws_db_instance" "main" {
  identifier     = "${var.project}-${var.environment}"
  engine         = "postgres"
  engine_version = "16.2"
  instance_class = var.db_instance_class

  allocated_storage     = var.db_storage_gb
  max_allocated_storage = var.db_storage_gb * 2

  multi_az               = var.environment == "prod"
  storage_encrypted      = true
  kms_key_id             = aws_kms_key.main.arn
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]

  backup_retention_period = var.environment == "prod" ? 30 : 7
  deletion_protection     = var.environment == "prod"

  performance_insights_enabled = true

  lifecycle {
    prevent_destroy = true
  }
}
```

---

## Tagging Strategy

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

# Apply to all resources
resource "aws_instance" "web_server" {
  tags = merge(local.common_tags, {
    Name = "web-server"
    Role = "web"
  })
}
```

Use `default_tags` in the provider block for tags that apply to every resource.

---

## Observability

```hcl
# CloudWatch alarms on key metrics
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${var.project}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.project}"
  retention_in_days = 30
  kms_key_id        = aws_kms_key.main.arn
}
```

---

## S3 Hardening

```hcl
resource "aws_s3_bucket_public_access_block" "main" {
  bucket                  = aws_s3_bucket.main.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets  = true
}

resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "main" {
  bucket = aws_s3_bucket.main.id
  rule {
    id     = "archive-old-objects"
    status = "Enabled"
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}
```

---

## TFLint AWS Plugin

```hcl
# .tflint.hcl
plugin "aws" {
  enabled = true
  version = "0.31.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}
```

---

## AWS-Specific Community Modules

Pin versions when using community modules:

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.8.0"
}

module "ecs" {
  source  = "terraform-aws-modules/ecs/aws"
  version = "5.9.0"
}
```

---

## References

- [AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)
- [terraform-aws-modules (community)](https://github.com/terraform-aws-modules)
- [tfsec AWS Checks](https://aquasecurity.github.io/tfsec/latest/checks/aws/)
