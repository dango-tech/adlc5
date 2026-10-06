# Terraform — GCP Supplement

**Loaded alongside:** `TERRAFORM-CODING-GUIDELINES.md` (base guide)  
**Applies when:** `detected_stack.cloud_provider` is `gcp`

This supplement provides GCP-specific Terraform patterns, resource conventions, and Architecture Framework alignment that extend the provider-agnostic base guide.

---

## Provider Configuration

```hcl
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.30"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Beta features (preview APIs, new resource types)
provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
}
```

---

## Remote State (GCS)

```hcl
terraform {
  backend "gcs" {
    bucket = "mycompany-terraform-state"
    prefix = "prod/infrastructure"
  }
}

# Cross-stack state reference
data "terraform_remote_state" "network" {
  backend = "gcs"
  config = {
    bucket = "mycompany-terraform-state"
    prefix = "prod/network"
  }
}
```

GCS buckets used for state should have:
- Versioning enabled (for state recovery)
- Uniform bucket-level access
- CMEK encryption
- Access limited to CI/CD service accounts

---

## Naming Conventions

GCP resource naming examples:

```hcl
# Resources — lowercase with underscores, singular nouns
resource "google_compute_instance" "web_server" {}      # GOOD
resource "google_compute_instance" "web_server_instance" {}  # BAD — repeats "instance"

# Single-instance resources — use "main" or "this"
resource "google_compute_network" "main" {}

# Multiple similar resources — use meaningful names
resource "google_compute_subnetwork" "public" {}
resource "google_compute_subnetwork" "private" {}
```

GCP resource names (the `name` argument) typically use hyphens:

```hcl
resource "google_compute_instance" "web_server" {
  name = "${var.project}-web-server-${var.environment}"
}
```

---

## IAM — Least Privilege

```hcl
# Bind a specific role to a service account on a specific resource
resource "google_project_iam_member" "app_storage" {
  project = var.gcp_project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.app.email}"
}

# Custom role for fine-grained permissions
resource "google_project_iam_custom_role" "app_custom" {
  role_id     = "appCustomRole"
  title       = "App Custom Role"
  permissions = [
    "storage.objects.get",
    "storage.objects.list",
    "pubsub.topics.publish",
  ]
}
```

- **Never** assign `roles/owner` or `roles/editor` to service accounts
- Prefer resource-level IAM bindings over project-level
- Use `google_project_iam_member` (additive) over `google_project_iam_binding` (authoritative) to avoid clobbering
- Use Workload Identity Federation for external workloads (not service account keys)

---

## Secrets Management

```hcl
# Retrieve secrets from Secret Manager
data "google_secret_manager_secret_version" "db_password" {
  secret = "prod-database-password"
}

resource "google_sql_database_instance" "main" {
  root_password = data.google_secret_manager_secret_version.db_password.secret_data
}

# Grant access to the secret
resource "google_secret_manager_secret_iam_member" "app_access" {
  secret_id = google_secret_manager_secret.db_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app.email}"
}
```

Never hardcode secrets in `.tf` files or `terraform.tfvars` committed to VCS.

---

## Encryption (CMEK)

```hcl
# KMS key for customer-managed encryption
resource "google_kms_key_ring" "main" {
  name     = "${var.project}-keyring"
  location = var.gcp_region
}

resource "google_kms_crypto_key" "main" {
  name     = "${var.project}-key"
  key_ring = google_kms_key_ring.main.id

  lifecycle {
    prevent_destroy = true
  }
}

# Cloud SQL with CMEK
resource "google_sql_database_instance" "main" {
  encryption_key_name = google_kms_crypto_key.main.id
}

# GCS with CMEK
resource "google_storage_bucket" "main" {
  encryption {
    default_kms_key_name = google_kms_crypto_key.main.id
  }
}

# BigQuery with CMEK
resource "google_bigquery_dataset" "main" {
  default_encryption_configuration {
    kms_key_name = google_kms_crypto_key.main.id
  }
}
```

---

## Networking Patterns

```hcl
# VPC with custom subnets
resource "google_compute_network" "main" {
  name                    = "${var.project}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "private" {
  name          = "${var.project}-private"
  ip_cidr_range = var.private_cidr
  region        = var.gcp_region
  network       = google_compute_network.main.id

  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.pods_cidr
  }
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.services_cidr
  }
}

# Cloud NAT for outbound from private subnets
resource "google_compute_router" "main" {
  name    = "${var.project}-router"
  region  = var.gcp_region
  network = google_compute_network.main.id
}

resource "google_compute_router_nat" "main" {
  name                               = "${var.project}-nat"
  router                             = google_compute_router.main.name
  region                             = var.gcp_region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# Firewall rules
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.project}-allow-internal"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  source_ranges = [var.private_cidr]
}
```

---

## Compute Patterns

### Cloud Run

```hcl
resource "google_cloud_run_v2_service" "app" {
  name     = "${var.project}-app"
  location = var.gcp_region

  template {
    containers {
      image = var.container_image

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "DB_HOST"
        value = google_sql_database_instance.main.private_ip_address
      }

      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }
    }

    scaling {
      min_instance_count = var.environment == "prod" ? 1 : 0
      max_instance_count = 10
    }

    vpc_access {
      connector = google_vpc_access_connector.main.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
  }
}
```

### GKE

```hcl
resource "google_container_cluster" "main" {
  name     = "${var.project}-gke"
  location = var.gcp_region

  initial_node_count       = 1
  remove_default_node_pool = true

  network    = google_compute_network.main.name
  subnetwork = google_compute_subnetwork.private.name

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  workload_identity_config {
    workload_pool = "${var.gcp_project_id}.svc.id.goog"
  }
}

resource "google_container_node_pool" "main" {
  name       = "main-pool"
  cluster    = google_container_cluster.main.id
  node_count = var.node_count

  autoscaling {
    min_node_count = 1
    max_node_count = var.max_nodes
  }

  node_config {
    machine_type    = var.machine_type
    service_account = google_service_account.gke_nodes.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
  }
}
```

### Cloud Functions

```hcl
resource "google_cloudfunctions2_function" "processor" {
  name     = "${var.project}-processor"
  location = var.gcp_region

  build_config {
    runtime     = "nodejs20"
    entry_point = "handler"
    source {
      storage_source {
        bucket = google_storage_bucket.functions.name
        object = google_storage_bucket_object.function_source.name
      }
    }
  }

  service_config {
    max_instance_count = 10
    available_memory   = "256M"
    timeout_seconds    = 60

    environment_variables = {
      TABLE_ID = google_bigquery_table.main.table_id
    }

    service_account_email = google_service_account.function.email
  }
}
```

---

## Database Patterns

```hcl
resource "google_sql_database_instance" "main" {
  name                = "${var.project}-${var.environment}"
  database_version    = "POSTGRES_16"
  region              = var.gcp_region
  deletion_protection = var.environment == "prod"
  encryption_key_name = google_kms_crypto_key.main.id

  settings {
    tier              = var.db_tier
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = var.environment == "prod"
      backup_retention_settings {
        retained_backups = var.environment == "prod" ? 30 : 7
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
    }

    insights_config {
      query_insights_enabled  = true
      record_application_tags = true
    }

    maintenance_window {
      day          = 7
      hour         = 3
      update_track = "stable"
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

# Read replica
resource "google_sql_database_instance" "read_replica" {
  count                = var.environment == "prod" ? 1 : 0
  name                 = "${var.project}-${var.environment}-replica"
  master_instance_name = google_sql_database_instance.main.name
  database_version     = "POSTGRES_16"
  region               = var.gcp_region

  replica_configuration {
    failover_target = false
  }

  settings {
    tier              = var.db_tier
    availability_type = "ZONAL"
  }
}
```

---

## Labeling Strategy

```hcl
locals {
  common_labels = {
    environment = var.environment
    project     = var.project_name
    managed-by  = "terraform"
    team        = var.team_name
    cost-center = var.cost_center
  }
}

resource "google_compute_instance" "web_server" {
  labels = merge(local.common_labels, {
    role = "web"
  })
}
```

GCP labels must be lowercase letters, numbers, underscores, or hyphens. Use hyphens for multi-word values.

---

## Observability

```hcl
# Monitoring alert policy
resource "google_monitoring_alert_policy" "cpu_high" {
  display_name = "${var.project} - High CPU"
  combiner     = "OR"

  conditions {
    display_name = "CPU > 80%"
    condition_threshold {
      filter          = "resource.type = \"gce_instance\" AND metric.type = \"compute.googleapis.com/instance/cpu/utilization\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8
      duration        = "300s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.name]
}

# Log sink for centralized logging
resource "google_logging_project_sink" "main" {
  name        = "${var.project}-log-sink"
  destination = "storage.googleapis.com/${google_storage_bucket.logs.name}"
  filter      = "severity >= WARNING"
}
```

---

## GCS Hardening

```hcl
resource "google_storage_bucket" "main" {
  name          = "${var.project}-${var.environment}-data"
  location      = var.gcp_region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.main.id
  }

  public_access_prevention = "enforced"
}
```

---

## TFLint GCP Plugin

```hcl
# .tflint.hcl
plugin "google" {
  enabled = true
  version = "0.27.0"
  source  = "github.com/terraform-linters/tflint-ruleset-google"
}
```

---

## GCP-Specific Community Modules

Pin versions when using community modules:

```hcl
module "network" {
  source  = "terraform-google-modules/network/google"
  version = "9.1.0"
}

module "gke" {
  source  = "terraform-google-modules/kubernetes-engine/google"
  version = "31.0.0"
}
```

---

## References

- [Google Provider Documentation](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Google Cloud Architecture Framework](https://cloud.google.com/architecture/framework)
- [terraform-google-modules (community)](https://github.com/terraform-google-modules)
- [tfsec GCP Checks](https://aquasecurity.github.io/tfsec/latest/checks/google/)
