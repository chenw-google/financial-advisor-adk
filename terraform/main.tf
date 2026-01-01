# main.tf

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

resource "google_project_service" "aiplatform_api" {
  project            = var.project_id
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "storage_api" {
  project            = var.project_id
  service            = "storage.googleapis.com"
  disable_on_destroy = false
}

resource "google_storage_bucket" "vertex_ai_staging_bucket" {
  project                     = var.project_id
  name                        = var.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true # Be cautious with this in production environments
  depends_on = [
    google_project_service.storage_api
  ]
}
