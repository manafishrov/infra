variable "rustfs_endpoint" {
  type = string
}

variable "rustfs_access_key" {
  type      = string
  sensitive = true
}

variable "rustfs_secret_key" {
  type      = string
  sensitive = true
}
