terraform {
  required_version = "~> 1.11.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.46.0"
    }
    minio = {
      source  = "aminueza/minio"
      version = "3.37.0"
    }
  }
}
