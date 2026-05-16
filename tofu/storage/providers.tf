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

provider "minio" {
  minio_server   = trimsuffix(replace(replace(var.rustfs_endpoint, "https://", ""), "http://", ""), "/")
  minio_ssl      = startswith(var.rustfs_endpoint, "https://")
  minio_user     = var.rustfs_access_key
  minio_password = var.rustfs_secret_key
}
