terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.42.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "5.19.0"
    }
    minio = {
      source  = "aminueza/minio"
      version = "3.33.1"
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

provider "cloudflare" {}

provider "minio" {
  minio_server   = trimsuffix(replace(replace(var.rustfs_endpoint, "https://", ""), "http://", ""), "/")
  minio_ssl      = startswith(var.rustfs_endpoint, "https://")
  minio_user     = var.rustfs_access_key
  minio_password = var.rustfs_secret_key
}

resource "minio_iam_policy" "firmware_ci" {
  name = "manafishrov-firmware-ci"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:ListBucket",
          "s3:ListBucketMultipartUploads",
        ]
        Resource = aws_s3_bucket.firmware.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:AbortMultipartUpload",
          "s3:DeleteObject",
          "s3:GetObject",
          "s3:ListMultipartUploadParts",
          "s3:PutObject",
        ]
        Resource = "${aws_s3_bucket.firmware.arn}/*"
      },
    ]
  })
}

resource "minio_iam_user" "firmware_ci" {
  name              = "manafishrov-firmware-ci"
  secret_wo         = var.firmware_ci_secret_key
  secret_wo_version = var.firmware_ci_secret_key_version
}

resource "minio_iam_user_policy_attachment" "firmware_ci" {
  user_name   = minio_iam_user.firmware_ci.name
  policy_name = minio_iam_policy.firmware_ci.name
}

data "cloudflare_zone" "manafishrov" {
  filter = {
    name = "manafishrov.com"
  }
}

locals {
  dns_records = {
    files = {
      name    = "files"
      type    = "A"
      content = "185.158.133.1"
    }
    sim = {
      name    = "sim"
      type    = "A"
      content = "185.158.133.1"
    }
    beta = {
      name    = "beta"
      type    = "CNAME"
      content = "cname.super.so"
    }
    s3 = {
      name    = "s3"
      type    = "CNAME"
      content = "router.gullhaugveien.michaelbrusegard.com"
    }
  }
}

resource "cloudflare_dns_record" "manafishrov" {
  for_each = local.dns_records

  zone_id  = data.cloudflare_zone.manafishrov.id
  name     = each.value.name
  type     = each.value.type
  content  = each.value.content
  ttl      = try(each.value.ttl, 1)
  proxied  = try(each.value.proxied, false)
  priority = try(each.value.priority, null)
}
