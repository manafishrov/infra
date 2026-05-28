output "twenty_storage_access_key_id" {
  value = minio_iam_user.twenty_app.name
}

output "twenty_storage_secret_access_key" {
  value     = var.twenty_app_secret_key
  sensitive = true
}
