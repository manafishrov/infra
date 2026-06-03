variable "rustfs_endpoint" {
  type    = string
  default = "http://rustfs-svc.rustfs.svc.cluster.local:9000"
}

variable "rustfs_access_key" {
  type      = string
  sensitive = true
}

variable "rustfs_secret_key" {
  type      = string
  sensitive = true
}

variable "firmware_ci_secret_key" {
  type      = string
  sensitive = true
}

variable "firmware_ci_secret_key_version" {
  type    = number
  default = 1
}

variable "twenty_app_secret_key" {
  description = "Secret key for the Twenty CRM application IAM user (RustFS access to manafishrov-twenty bucket)"
  type        = string
  sensitive   = true
}

variable "twenty_app_secret_key_version" {
  description = "Bumped to rotate twenty_app_secret_key"
  type        = number
  default     = 1
}
