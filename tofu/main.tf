terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = var.rustfs_access_key
  secret_key                  = var.rustfs_secret_key
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_region_validation      = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3 = var.rustfs_endpoint
  }
}

resource "aws_s3_bucket" "firmware" {
  bucket = "manafishrov-firmware"
}

resource "aws_s3_bucket_policy" "firmware_public_read" {
  bucket = aws_s3_bucket.firmware.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.firmware.arn}/*"
    }]
  })
}
