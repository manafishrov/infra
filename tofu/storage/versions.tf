terraform {
  required_version = "~> 1.11.5"

  required_providers {
    minio = {
      source  = "aminueza/minio"
      version = "3.37.0"
    }
  }
}
