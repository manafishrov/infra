output "manafishrov_twenty_rustfs_access_key_id" {
  value = minio_iam_user.twenty_app.name
}

output "manafishrov_twenty_rustfs_secret_access_key" {
  value     = var.manafishrov_twenty_app_secret_key
  sensitive = true
}
