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

resource "minio_iam_policy" "firmware_ci" {
  name   = "manafishrovFirmwareCi"
  policy = local.firmware_ci_policy
}

resource "minio_iam_user" "firmware_ci" {
  name              = "manafishrov-firmware-ci"
  secret_wo         = var.manafishrov_firmware_ci_secret_key
  secret_wo_version = 1
}

resource "minio_iam_user_policy_attachment" "firmware_ci" {
  user_name   = minio_iam_user.firmware_ci.name
  policy_name = minio_iam_policy.firmware_ci.name
}

resource "minio_iam_policy" "twenty_app" {
  name   = "manafishrovTwentyApp"
  policy = local.twenty_app_policy
}

resource "minio_iam_user" "twenty_app" {
  name              = "manafishrov-twenty-app"
  secret_wo         = var.manafishrov_twenty_app_secret_key
  secret_wo_version = 1
}

resource "minio_iam_user_policy_attachment" "twenty_app" {
  user_name   = minio_iam_user.twenty_app.name
  policy_name = minio_iam_policy.twenty_app.name
}
