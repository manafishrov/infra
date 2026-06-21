provider "minio" {
  minio_server   = trimsuffix(replace(replace(var.rustfs_endpoint, "https://", ""), "http://", ""), "/")
  minio_ssl      = startswith(var.rustfs_endpoint, "https://")
  minio_user     = var.rustfs_access_key
  minio_password = var.rustfs_secret_key
}
