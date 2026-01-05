# main.tf
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

resource "google_vertex_ai_reasoning_engine" "reasoning_engine" { # The core reasoning engine resource
  display_name = "Terraform"
  project      = var.project_id
  description  = "A basic reasoning engine"
  region       = var.region

  spec {
    agent_framework = "google-adk" # Specifies the agent is built with the Agent Development Kit
    service_account = google_service_account.reasoning_engine_sa.email

    package_spec {
      dependency_files_gcs_uri = "gs://${google_storage_bucket.vertex_ai_staging_bucket.name}/${google_storage_bucket_object.dependencies.name}"
      pickle_object_gcs_uri    = "gs://${google_storage_bucket.vertex_ai_staging_bucket.name}/${google_storage_bucket_object.agent_pickle.name}"
      python_version           = "3.12"
      requirements_gcs_uri     = "gs://${google_storage_bucket.vertex_ai_staging_bucket.name}/${google_storage_bucket_object.requirements.name}"
    }
  }
  depends_on = [
    time_sleep.wait_for_iam_propagation
  ]
}

# IAM bindings for the dedicated service account
resource "google_service_account" "reasoning_engine_sa" {
  account_id   = "reasoning-engine-sa"
  display_name = "Reasoning Engine Service Account"
}

locals {
  sa_roles = toset([
    "roles/aiplatform.user",
    "roles/storage.objectViewer",
    "roles/logging.logWriter",
    "roles/secretmanager.secretAccessor",
  ])
}

resource "google_project_iam_member" "reasoning_engine_sa_roles" {
  for_each = local.sa_roles
  project  = var.project_id
  role     = each.key
  member   = google_service_account.reasoning_engine_sa.member
  depends_on = [
    google_project_service.project_apis
  ]
}

variable "project_id" {
  description = "The Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "The Google Cloud region for deployment (e.g., us-central1)."
  type        = string
  default     = "us-central1"
}

variable "bucket_name" {
  description = "The name of the GCS bucket for Vertex AI staging. Must be globally unique."
  type        = string
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  apis_to_enable = toset([
    "aiplatform.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "storage.googleapis.com",
  ])
}

resource "google_project_service" "project_apis" {
  for_each           = local.apis_to_enable
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_storage_bucket" "vertex_ai_staging_bucket" {
  project                     = var.project_id
  name                        = var.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true # Be cautious with this in production environments
  depends_on = [
    google_project_service.project_apis
  ]
}

# Upload agent artifacts to the staging bucket
resource "google_storage_bucket_object" "agent_pickle" {
  name   = "agent.pkl"
  bucket = google_storage_bucket.vertex_ai_staging_bucket.name
  source = "../agent.pkl" # Assumes agent.pkl is in the parent directory
}

resource "google_storage_bucket_object" "requirements" {
  name   = "requirements.txt"
  bucket = google_storage_bucket.vertex_ai_staging_bucket.name
  source = "../requirements.txt" # Assumes requirements.txt is in the parent directory
}

resource "google_storage_bucket_object" "dependencies" {
  name   = "empty.tar.gz"
  bucket = google_storage_bucket.vertex_ai_staging_bucket.name
  source = "../empty.tar.gz" # Assumes an empty tarball for dependencies is in the parent directory
}

# Secret management for the agent
resource "google_secret_manager_secret" "agent_secret" {
  secret_id = "agent-secret"
  replication {
    auto {}
  }
  depends_on = [
    google_project_service.project_apis["secretmanager.googleapis.com"]
  ]
}

resource "google_secret_manager_secret_version" "agent_secret_version" {
  secret      = google_secret_manager_secret.agent_secret.id
  secret_data = "my-super-secret-value"
}

# A delay to ensure IAM permissions are propagated before creating the reasoning engine
resource "time_sleep" "wait_for_iam_propagation" {
  create_duration = "60s"

  depends_on = [
    google_project_iam_member.reasoning_engine_sa_roles
  ]
}

output "reasoning_engine_name" {
  description = "The full resource name of the deployed Vertex AI Reasoning Engine."
  value       = google_vertex_ai_reasoning_engine.reasoning_engine.name
}
