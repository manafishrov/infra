variable "rustfs_endpoint" {
  type = string
}

variable "RUSTFS_ACCESS_KEY" {
  type      = string
  sensitive = true
}

variable "RUSTFS_SECRET_KEY" {
  type      = string
  sensitive = true
}
