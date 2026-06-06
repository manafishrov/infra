resource "minio_s3_bucket" "firmware" {
  bucket = "manafishrov-firmware"
}

resource "minio_s3_bucket_policy" "firmware_public_read" {
  bucket = minio_s3_bucket.firmware.bucket
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${minio_s3_bucket.firmware.arn}/*"
    }]
  })
}

# Twenty CRM uploaded files (attachments, avatars). Private bucket — only
# the application IAM user reads/writes; downloads are proxied through the
# Twenty server, so no public access policy.
resource "minio_s3_bucket" "twenty" {
  bucket = "manafishrov-twenty"
}

locals {
  firmware_ci_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:ListBucket",
          "s3:ListBucketMultipartUploads",
        ]
        Resource = minio_s3_bucket.firmware.arn
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
        Resource = "${minio_s3_bucket.firmware.arn}/*"
      },
    ]
  })

  twenty_app_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:ListBucket",
          "s3:ListBucketMultipartUploads",
        ]
        Resource = minio_s3_bucket.twenty.arn
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
        Resource = "${minio_s3_bucket.twenty.arn}/*"
      },
    ]
  })
}

# aminueza/minio v3.33.1 returns Action arrays in non-deterministic order on
# every read (server-side normalization is unstable) and its DiffSuppressFunc
# does not absorb the difference, so every reconcile re-plans a no-op change.
# We ignore policy drift on the resource and use a sha256(...) trigger so a
# real edit still forces a recreate. Cosmetic side-effect: the tf-controller
# Plan condition can stay TerraformPlannedWithChanges - check Ready/NoDrift.
resource "terraform_data" "firmware_ci_policy_version" {
  input = sha256(local.firmware_ci_policy)
}

resource "minio_iam_policy" "firmware_ci" {
  name   = "ManafishrovFirmwareCi"
  policy = local.firmware_ci_policy

  lifecycle {
    ignore_changes       = [policy]
    replace_triggered_by = [terraform_data.firmware_ci_policy_version]
  }
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

resource "terraform_data" "twenty_app_policy_version" {
  input = sha256(local.twenty_app_policy)
}

resource "minio_iam_policy" "twenty_app" {
  name   = "ManafishrovTwentyApp"
  policy = local.twenty_app_policy

  lifecycle {
    ignore_changes       = [policy]
    replace_triggered_by = [terraform_data.twenty_app_policy_version]
  }
}

resource "minio_iam_user" "twenty_app" {
  name              = "manafishrov-twenty-app"
  secret_wo         = var.twenty_app_secret_key
  secret_wo_version = var.twenty_app_secret_key_version
}

resource "minio_iam_user_policy_attachment" "twenty_app" {
  user_name   = minio_iam_user.twenty_app.name
  policy_name = minio_iam_policy.twenty_app.name
}
