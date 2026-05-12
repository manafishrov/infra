terraform {
  required_version = "= 1.11.5"

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
  name   = "manafishrov-firmware-ci"
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

data "cloudflare_zone" "manafishrov" {
  filter = {
    name = "manafishrov.com"
  }
}

locals {
  dns_records = {

    website = {
      name    = "@"
      type    = "A"
      content = "185.158.133.1"
    }
    lovable_website = {
      name    = "_lovable"
      type    = "TXT"
      content = "lovable_verify=d08e77b7813bf8ea7c8ba5b4595fa0ac678d5f323b53024fec04d291f60e061d"
    }

    files = {
      name    = "files"
      type    = "A"
      content = "185.158.133.1"
    }
    lovable_files = {
      name    = "_lovable.files"
      type    = "TXT"
      content = "lovable_verify=1633dd859817ff1068321b7dd3f0fa29bdb51a5cd7a4e94962465cd91130c1dc"
    }

    sim = {
      name    = "sim"
      type    = "A"
      content = "185.158.133.1"
    }
    lovable_sim = {
      name    = "_lovable.sim"
      type    = "TXT"
      content = "lovable_verify=868dafebfa40ff43475f6a3a4c9c535837b9a2f7ecd4dc245bf2a50034863bf0"
    }

    beta = {
      name    = "beta"
      type    = "CNAME"
      content = "cname.super.so"
    }

    landing = {
      name    = "landing"
      type    = "CNAME"
      content = "manafishrov.github.io"
    }
    ui = {
      name    = "ui"
      type    = "CNAME"
      content = "manafishrov.github.io"
    }

    s3 = {
      name    = "s3"
      type    = "CNAME"
      content = "router.gullhaugveien.michaelbrusegard.com"
    }

    dmarc = {
      name    = "_dmarc"
      type    = "TXT"
      content = "v=DMARC1; p=quarantine;"
    }

    dkim_k2_updates = {
      name    = "k2._domainkey.updates"
      type    = "CNAME"
      content = "dkim2.mcsv.net"
    }
    dkim_k3_updates = {
      name    = "k3._domainkey.updates"
      type    = "CNAME"
      content = "dkim3.mcsv.net"
    }

    protonmail_domainkey_updates = {
      name    = "protonmail._domainkey.updates"
      type    = "CNAME"
      content = "protonmail.domainkey.dvobtm6qh2g4ugep6qy5niizj5ksma5s7hdehpq7igj63htmwngja.domains.proton.ch"
    }
    protonmail2_domainkey_updates = {
      name    = "protonmail2._domainkey.updates"
      type    = "CNAME"
      content = "protonmail2.domainkey.dvobtm6qh2g4ugep6qy5niizj5ksma5s7hdehpq7igj63htmwngja.domains.proton.ch"
    }
    protonmail3_domainkey_updates = {
      name    = "protonmail3._domainkey.updates"
      type    = "CNAME"
      content = "protonmail3.domainkey.dvobtm6qh2g4ugep6qy5niizj5ksma5s7hdehpq7igj63htmwngja.domains.proton.ch"
    }

    updates_mx_protonmail = {
      name     = "updates"
      type     = "MX"
      content  = "mail.protonmail.ch"
      priority = 20
    }
    updates_mx_protonmail_sec = {
      name     = "updates"
      type     = "MX"
      content  = "mailsec.protonmail.ch"
      priority = 30
    }
    updates_spf = {
      name    = "updates"
      type    = "TXT"
      content = "v=spf1 include:_spf.protonmail.ch ~all"
    }
    updates_protonmail_verification = {
      name    = "updates"
      type    = "TXT"
      content = "protonmail-verification=acc7d667357e78d99f1a07a06b39bf6ffe63b11f"
    }

    send_updates_mx = {
      name     = "send.updates"
      type     = "MX"
      content  = "feedback-smtp.eu-west-1.amazonses.com"
      priority = 10
    }
    send_updates_spf = {
      name    = "send.updates"
      type    = "TXT"
      content = "v=spf1 include:amazonses.com -all"
    }

    resend_domainkey_updates = {
      name    = "resend._domainkey.updates"
      type    = "TXT"
      content = "p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDL3dpUyho6F57ks3Gkl6l5v8goijjgshbz3WRr3KLapemuhKoGoHothE3YKyHlw7hSIreChyoWHr4QACFNNHZivJD1vfhb+f3UBMp+4TSfZkGVs1IM3jKTMZWo28gUk4qOXVyztN4TktgAP7Yw+RT/elZAT2cL5WMk1mvvB5QBUQIDAQAB"
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
