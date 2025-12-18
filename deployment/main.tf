terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0"
    }
  }
}

variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "location" {
  description = "The Google Cloud Location"
  type        = string
  default     = "us-central1"
}

variable "bucket_name" {
  description = "The GCS bucket name for staging"
  type        = string
}

provider "google" {
  project = var.project_id
  region  = var.location
}

# Staging bucket for agent deployment
resource "google_storage_bucket" "staging_bucket" {
  name     = var.bucket_name
  location = var.location
  uniform_bucket_level_access = true
}

# Deploy the Financial Advisor agent
resource "null_resource" "deploy_agent" {
  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = "python3 deploy.py"
    environment = {
      GOOGLE_CLOUD_PROJECT        = var.project_id
      GOOGLE_CLOUD_LOCATION       = var.location
      GOOGLE_CLOUD_STORAGE_BUCKET = var.bucket_name
    }
    working_dir = path.module
  }

  depends_on = [google_storage_bucket.staging_bucket]
}
